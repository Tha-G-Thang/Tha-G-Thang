import xbmcgui
import xbmcvfs
import os
import xbmc
import random
import time
from datetime import datetime
import traceback # Handig voor gedetailleerde foutrapportage

# Interne Addon Imports
from resources.lib.constants import PLAYLIST_DIR, FAVORITES_FILE, SMART_FOLDERS_FILE, ADDON_NAME, ADDON_ID
from resources.lib.core.base_utils import log, get_setting, save_json, load_json, format_display_entry
from resources.lib.core.scanner import get_media_files
from resources.lib.core.sorter import sort_files_for_playlist # Alleen sort_files_for_playlist is hier nodig
from resources.lib.core.set_manager import load_favorites # Nodig voor create_favorites_playlist

def create_playlist(folders=None, name=None, from_set=False):
    if not folders:
        if from_set:
            xbmcgui.Dialog().ok("Fout", "Geen mappen gevonden voor deze set.")
            return

        dialog = xbmcgui.Dialog()
        playlist_name = dialog.input('Voer afspeellijstnaam in', type=xbmcgui.INPUT_ALPHANUM)
        if not playlist_name:
            return

        folder_paths = []
        while True:
            # Start bij special://root/ zoals eerder afgesproken
            path = dialog.browse(3, 'Selecteer map', 'files', '', False, False, xbmcvfs.translatePath('special://root/'))
            if path:
                if xbmcvfs.isdir(path):
                    folder_paths.append(path)
                else:
                    xbmcgui.Dialog().ok("Ongeldige selectie", "Selecteer alstublieft een map, geen bestand.")
            else:
                break
        
        if not folder_paths:
            xbmcgui.Dialog().ok("Geen mappen geselecteerd", "Er zijn geen mappen geselecteerd om een afspeellijst van te maken.")
            return
    else:
        playlist_name = name

    log(f"Afspeellijst aanmaken: {playlist_name} uit mappen: {folders}", xbmc.LOGINFO)

    all_media_files = []
    for folder in folder_paths:
        media_in_folder = get_media_files(folder)
        log(f"Gevonden {len(media_in_folder)} mediabestanden in {folder}", xbmc.LOGINFO)
        all_media_files.extend(media_in_folder)

    if not all_media_files:
        xbmcgui.Dialog().notification(ADDON_NAME, "Geen mediabestanden gevonden in de geselecteerde mappen.", xbmcgui.NOTIFICATION_INFO, 3000)
        log("Geen mediabestanden gevonden, afspeellijst niet aangemaakt.", xbmc.LOGWARNING)
        return

    sorted_media_files = sort_files_for_playlist(all_media_files)
    
    playlist_content = "#EXTM3U\n"
    for file_path in sorted_media_files:
        playlist_content += f"{file_path}\n"

    playlist_path = xbmcvfs.translatePath(os.path.join(PLAYLIST_DIR, f"{playlist_name}.m3u"))

    # Controleer of de PLAYLIST_DIR bestaat
    if not xbmcvfs.exists(PLAYLIST_DIR):
        try:
            xbmcvfs.mkdirs(PLAYLIST_DIR)
            log(f"Mappen voor afspeellijst gemaakt: {PLAYLIST_DIR}", xbmc.LOGINFO)
        except Exception as e:
            log(f"Fout bij het maken van afspeellijstmap {PLAYLIST_DIR}: {e}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok("Fout", f"Kan afspeellijstmap niet maken: {PLAYLIST_DIR}")
            return

    try:
        # Backup maken voor het opslaan van de nieuwe playlist
        create_playlist_backup(playlist_path) # AANGEPAST: aanroep van de hernoemde functie

        with xbmcvfs.File(playlist_path, 'w') as f:
            f.write(playlist_content)
        xbmcgui.Dialog().notification(ADDON_NAME, f"Afspeellijst '{playlist_name}' aangemaakt.", xbmcgui.NOTIFICATION_INFO, 3000)
        log(f"Afspeellijst '{playlist_name}' opgeslagen in: {playlist_path}", xbmc.LOGINFO)

    except Exception as e:
        log(f"Fout bij opslaan afspeellijst: {e}", xbmc.LOGERROR)
        import traceback
        log(traceback.format_exc(), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Fout", f"Kan afspeellijst niet opslaan: {e}")

def create_favorites_playlist():
    dialog = xbmcgui.Dialog()
    favorites = load_favorites() # Gebruikt de load_favorites import
    if not favorites:
        dialog.notification(ADDON_NAME, "Geen favorieten gevonden.", xbmcgui.NOTIFICATION_INFO, 2000)
        return

    playlist_name = "Favorieten" # Standaardnaam voor favorieten afspeellijst
    playlist_path = xbmcvfs.translatePath(os.path.join(PLAYLIST_DIR, f"{playlist_name}.m3u"))
    
    log(f"Favorieten afspeellijst aanmaken: {playlist_name}", xbmc.LOGINFO)

    # De favorietenlijst zelf bevat al de paden, sorteren is optioneel hier
    # Als je de favorieten zelf wilt sorteren, kun je hier een aanroep naar sort_files_for_playlist toevoegen
    # sorted_favorites = sort_files_for_playlist([f['path'] for f in favorites])
    
    playlist_content = "#EXTM3U\n"
    for fav_item in favorites:
        playlist_content += f"{fav_item['path']}\n"

    # Controleer of de PLAYLIST_DIR bestaat
    if not xbmcvfs.exists(PLAYLIST_DIR):
        try:
            xbmcvfs.mkdirs(PLAYLIST_DIR)
            log(f"Mappen voor favorieten afspeellijst gemaakt: {PLAYLIST_DIR}", xbmc.LOGINFO)
        except Exception as e:
            log(f"Fout bij het maken van afspeellijstmap {PLAYLIST_DIR}: {e}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok("Fout", f"Kan afspeellijstmap niet maken: {PLAYLIST_DIR}")
            return

    try:
        # Backup maken voor het opslaan van de nieuwe playlist
        create_playlist_backup(playlist_path) # AANGEPAST: aanroep van de hernoemde functie

        with xbmcvfs.File(playlist_path, 'w') as f:
            f.write(playlist_content)
        xbmcgui.Dialog().notification(ADDON_NAME, f"Favorieten afspeellijst '{playlist_name}' aangemaakt.", xbmcgui.NOTIFICATION_INFO, 3000)
        log(f"Favorieten afspeellijst '{playlist_name}' opgeslagen in: {playlist_path}", xbmc.LOGINFO)
    except Exception as e:
        log(f"Fout bij opslaan favorieten afspeellijst: {e}", xbmc.LOGERROR)
        import traceback
        log(traceback.format_exc(), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Fout", f"Kan favorieten afspeellijst niet opslaan: {e}")

def create_playlist_backup(playlist_path): # AANGEPAST: functienaam
    max_backups = int(get_setting('max_playlist_backups', '5'))
    if max_backups <= 0:
        log(f"Playlist backup skipped: max_backups is set to {max_backups} or less.", xbmc.LOGINFO)
        return

    playlist_filename = os.path.basename(playlist_path)
    playlist_name_without_ext = os.path.splitext(playlist_filename)[0]
    backup_dir = xbmcvfs.translatePath(os.path.join(os.path.dirname(playlist_path), "backups"))

    if not xbmcvfs.exists(backup_dir):
        xbmcvfs.mkdirs(backup_dir)
        log(f"Created backup directory: {backup_dir}", xbmc.LOGINFO)

    existing_backups = []
    # xbmcvfs.listdir geeft (dirs, files) terug
    dirs, files = xbmcvfs.listdir(backup_dir)
    for f in files:
        if f.startswith(playlist_name_without_ext) and f.endswith(".m3u"):
            existing_backups.append(xbmcvfs.translatePath(os.path.join(backup_dir, f)))
    
    # Sorteer op modificatietijd (of creatietijd als dat consistenter is) om de nieuwste te behouden
    # Kodi's xbmcvfs.File().created() kan variëren per OS, mtime is vaak betrouwbaarder.
    existing_backups.sort(key=lambda x: xbmcvfs.File(x).mtime() if xbmcvfs.exists(x) else 0, reverse=True)
    
    for i in range(max_backups - 1, len(existing_backups)):
        log(f"Deleting old backup: {existing_backups[i]}", xbmc.LOGINFO)
        try:
            xbmcvfs.delete(existing_backups[i])
        except Exception as e:
            log(f"Error deleting old backup {existing_backups[i]}: {e}", xbmc.LOGERROR)

    # Maak nieuwe backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = xbmcvfs.translatePath(os.path.join(backup_dir, f"{playlist_name_without_ext}_{timestamp}.m3u"))
    
    try:
        xbmcvfs.copy(playlist_path, backup_path)
        log(f"Backup created: {backup_path}", xbmc.LOGINFO)
    except Exception as e:
        log(f"Error creating playlist backup {backup_path}: {e}", xbmc.LOGERROR)
        import traceback
        log(traceback.format_exc(), xbmc.LOGERROR)