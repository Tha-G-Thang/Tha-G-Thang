import xbmcgui
import xbmcvfs
import os
import xbmc # xbmc is nodig voor xbmc.translatePath
import random
import time
from datetime import datetime

from resources.lib.constants import PLAYLIST_DIR, FAVORITES_FILE, SMART_FOLDERS_FILE, ADDON_NAME, ADDON_ID # Importeer ADDON_NAME, ADDON_ID

from resources.lib.core.base_utils import log, get_setting, save_json, load_json, format_display_entry


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
            path = dialog.browse(3, 'Selecteer map', 'files', '', False, False, xbmc.translatePath('special://home/'))
            if path:
                if xbmcvfs.isdir(path):
                    folder_paths.append(path)
                else:
                    xbmcgui.Dialog().ok("Ongeldige selectie", "Selecteer alstublieft een map, geen bestand.")
            else:
                break
        
        if not folder_paths:
            xbmcgui.Dialog().ok("Geen mappen geselecteerd", "Er zijn geen mappen geselecteerd om de afspeellijst te genereren.")
            return

        xbmcgui.Dialog().notification(ADDON_NAME, "Afspeellijst wordt aangemaakt...", xbmcgui.NOTIFICATION_INFO, 2000)
        _create_playlist_from_paths(playlist_name, folder_paths)
    else:
        # Dit is de non-interactieve modus, gebruikt door update_all_sets of manage_sets
        if not name:
            log("Fout: Afspeellijstnaam ontbreekt bij niet-interactieve aanroep.", xbmc.LOGERROR)
            return
        xbmcgui.Dialog().notification(ADDON_NAME, f"Afspeellijst '{name}' wordt bijgewerkt...", xbmcgui.NOTIFICATION_INFO, 2000)
        _create_playlist_from_paths(name, folders)


def _create_playlist_from_paths(playlist_name, folder_paths_raw):
    from resources.lib.core.scanner import get_media_files # Lokale import om circular dependency te voorkomen
    from resources.lib.core.sorter import sort_files_for_playlist # Lokale import om circular dependency te voorkomen

    # 1. Sorteer de mappen zelf indien ingesteld
    folder_sort_order = get_setting('folder_sort_order', '0')
    if folder_sort_order == '1': # A-Z
        folder_paths_raw.sort(key=lambda x: os.path.basename(x).lower())
    elif folder_sort_order == '2': # Z-A
        folder_paths_raw.sort(key=lambda x: os.path.basename(x).lower(), reverse=True)

    all_media_files_with_folders = [] # Zal tuples (filepath, folder_path) bevatten

    # 2. Verzamel en sorteer bestanden binnen elke map
    for folder_path in folder_paths_raw:
        files_in_folder = get_media_files(folder_path)
        
        # Sorteer bestanden binnen de map
        sorted_files_in_folder = sort_files_for_playlist(files_in_folder)
        
        for filepath in sorted_files_in_folder:
            all_media_files_with_folders.append((filepath, folder_path))

    if not all_media_files_with_folders:
        xbmcgui.Dialog().notification(ADDON_NAME, f"Geen media gevonden in geselecteerde mappen voor '{playlist_name}'.", xbmcgui.NOTIFICATION_WARNING, 3000)
        log(f"No media files found for playlist: {playlist_name} in paths: {folder_paths_raw}", xbmc.LOGWARNING)
        return

    playlist_path = os.path.join(PLAYLIST_DIR, f"{playlist_name}.m3u")
    
    try:
        with xbmcvfs.File(playlist_path, 'w') as f:
            f.write("#EXTM3U\n")
            for filepath, original_folder_path in all_media_files_with_folders:
                display_entry = format_display_entry(filepath, original_folder_path) # Geef original_folder_path mee
                f.write(f"#EXTINF:-1,{display_entry}\n")
                f.write(f"{filepath}\n")
        
        # Roep backup functie aan
        if get_setting('enable_backups', 'true') == 'true':
            _create_playlist_backup(playlist_path)

        xbmcgui.Dialog().notification(ADDON_NAME, f"Afspeellijst '{playlist_name}' aangemaakt!", xbmcgui.NOTIFICATION_INFO, 3000)
        log(f"Playlist '{playlist_name}' created at: {playlist_path}", xbmc.LOGINFO)

    except Exception as e:
        import traceback
        xbmcgui.Dialog().notification(ADDON_NAME, f"Fout bij aanmaken afspeellijst '{playlist_name}'.", xbmcgui.NOTIFICATION_ERROR, 5000)
        log(f"Error creating playlist '{playlist_name}': {e}\n{traceback.format_exc()}", xbmc.LOGERROR)


def create_favorites_playlist():
    from resources.lib.core.set_manager import load_favorites # Lokale import
    
    favorites = load_favorites()
    if not favorites:
        xbmcgui.Dialog().notification(ADDON_NAME, "Geen favorieten gevonden.", xbmcgui.NOTIFICATION_WARNING, 3000)
        return

    playlist_name = get_setting('favorites_playlist_name', 'My Favorites')
    playlist_path = os.path.join(PLAYLIST_DIR, f"{playlist_name}.m3u")

    try:
        with xbmcvfs.File(playlist_path, 'w') as f:
            f.write("#EXTM3U\n")
            # Favorieten hebben geen 'original_folder_path', dus geef None mee
            for fav in favorites:
                filepath = fav['path']
                display_entry = format_display_entry(filepath, None) 
                f.write(f"#EXTINF:-1,{display_entry}\n")
                f.write(f"{filepath}\n")

        # Roep backup functie aan
        if get_setting('enable_backups', 'true') == 'true':
            _create_playlist_backup(playlist_path)

        xbmcgui.Dialog().notification(ADDON_NAME, f"Afspeellijst '{playlist_name}' van favorieten aangemaakt!", xbmcgui.NOTIFICATION_INFO, 3000)
        log(f"Favorites playlist '{playlist_name}' created at: {playlist_path}", xbmc.LOGINFO)

    except Exception as e:
        import traceback
        xbmcgui.Dialog().notification(ADDON_NAME, f"Fout bij aanmaken favorieten afspeellijst '{playlist_name}'.", xbmcgui.NOTIFICATION_ERROR, 5000)
        log(f"Error creating favorites playlist '{playlist_name}': {e}\n{traceback.format_exc()}", xbmc.LOGERROR)

def _create_playlist_backup(playlist_path):
    enable_backups = get_setting('enable_backups', 'true') == 'true'
    max_backups = int(get_setting('max_backups', '3'))

    if not enable_backups or max_backups <= 0:
        return

    playlist_filename = os.path.basename(playlist_path)
    playlist_name_without_ext = os.path.splitext(playlist_filename)[0]
    backup_dir = os.path.join(os.path.dirname(playlist_path), "backups") # Backup directory naast de playlist

    if not xbmcvfs.exists(backup_dir):
        xbmcvfs.mkdirs(backup_dir)
        log(f"Created backup directory: {backup_dir}", xbmc.LOGINFO)

    # Verwijder oude backups
    existing_backups = []
    # xbmcvfs.listdir geeft (dirs, files) terug
    dirs, files = xbmcvfs.listdir(backup_dir)
    for f in files:
        if f.startswith(playlist_name_without_ext) and f.endswith(".m3u"):
            existing_backups.append(os.path.join(backup_dir, f))
    
    # Sorteer op modificatietijd (of creatietijd als dat consistenter is) om de nieuwste te behouden
    # Kodi's xbmcvfs.File().created() kan variëren per OS, mtime is vaak betrouwbaarder.
    existing_backups.sort(key=lambda x: xbmcvfs.File(x).mtime(), reverse=True)
    
    for i in range(max_backups - 1, len(existing_backups)):
        log(f"Deleting old backup: {existing_backups[i]}", xbmc.LOGINFO)
        try:
            xbmcvfs.delete(existing_backups[i])
        except Exception as e:
            log(f"Error deleting old backup {existing_backups[i]}: {e}", xbmc.LOGERROR)

    # Maak nieuwe backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"{playlist_name_without_ext}_{timestamp}.m3u")
    
    try:
        xbmcvfs.copy(playlist_path, backup_path)
        log(f"Backup created: {backup_path}", xbmc.LOGINFO)
    except Exception as e:
        log(f"Error creating backup for {playlist_path}: {e}", xbmc.LOGERROR)