import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import re
from resources.lib.core.base_utils import log, load_json, save_json, get_setting, set_setting, format_display_entry
from resources.lib.constants import ADDON, CONFIG_FILE, FAVORITES_FILE, SMART_FOLDERS_FILE

def create_smart_folder():
    dialog = xbmcgui.Dialog()
    sf_name = dialog.input("Naam van Smart Folder:", type=xbmcgui.INPUT_ALPHANUM)
    if not sf_name:
        return

    smart_folders = load_smart_folders()
    if sf_name in smart_folders:
        dialog.ok("Fout", f"Smart Folder '{sf_name}' bestaat al.")
        return

    folder_paths = []
    xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Selecteer mappen voor de Smart Folder (Annuleer om te stoppen).", xbmcgui.NOTIFICATION_INFO, 3000)
    
    while True:
        # Aangepast: start bij special://root/
        path = dialog.browse(3, 'Selecteer map', 'files', '', False, False, xbmcvfs.translatePath('special://root/'))
        if path:
            if xbmcvfs.isdir(path):
                folder_paths.append(path)
            else:
                xbmcgui.Dialog().ok("Ongeldige selectie", "Selecteer alstublieft een map, geen bestand.")
        else:
            break

    if not folder_paths:
        dialog.ok("Geen mappen geselecteerd", "Geen mappen geselecteerd voor de Smart Folder.")
        return

    smart_folders[sf_name] = {'paths': folder_paths}
    save_smart_folders(smart_folders)
    dialog.notification(ADDON.getAddonInfo('name'), f"Smart Folder '{sf_name}' aangemaakt.", xbmcgui.NOTIFICATION_INFO, 3000)
    log(f"Smart Folder '{sf_name}' aangemaakt met paden: {folder_paths}", xbmc.LOGINFO)
    
    if dialog.yesno("Afspeellijst Maken", f"Wilt u direct een afspeellijst aanmaken voor '{sf_name}'?"):
        create_playlist(folders=folder_paths, name=sf_name, from_set=True)


def edit_smart_folder():
    dialog = xbmcgui.Dialog()
    smart_folders = load_smart_folders()
    sf_names = list(smart_folders.keys())
    
    if not sf_names:
        dialog.notification(ADDON.getAddonInfo('name'), "Geen Smart Folders gevonden om te bewerken.", xbmcgui.NOTIFICATION_INFO, 2000)
        return

    selected_sf_index = dialog.select("Selecteer Smart Folder om te Bewerken:", sf_names)
    if selected_sf_index == -1:
        return

    sf_name = sf_names[selected_sf_index]
    current_folders = smart_folders[sf_name]['paths']

    options = ["Mappen Toevoegen", "Mappen Verwijderen", "Terug"]
    choice = dialog.select(f"Bewerk '{sf_name}':", options)

    if choice == -1 or choice == 2: # Annuleren of Terug
        return
    elif choice == 0: # Mappen Toevoegen
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Selecteer mappen om toe te voegen (Annuleer om te stoppen).", xbmcgui.NOTIFICATION_INFO, 3000)
        
        while True:
            # Aangepast: start bij special://root/
            path = dialog.browse(3, 'Selecteer map', 'files', '', False, False, xbmcvfs.translatePath('special://root/'))
            if path:
                if xbmcvfs.isdir(path) and path not in current_folders:
                    current_folders.append(path)
                elif not xbmcvfs.isdir(path):
                    xbmcgui.Dialog().ok("Ongeldige selectie", "Selecteer alstublieft een map, geen bestand.")
                else:
                    xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Map is al toegevoegd.", xbmcgui.NOTIFICATION_INFO, 2000)
            else:
                break
        smart_folders[sf_name]['paths'] = current_folders
        save_smart_folders(smart_folders)
        dialog.notification(ADDON.getAddonInfo('name'), f"Mappen toegevoegd aan '{sf_name}'.", xbmcgui.NOTIFICATION_INFO, 3000)
        log(f"Mappen toegevoegd aan Smart Folder '{sf_name}'. Nieuwe paden: {current_folders}", xbmc.LOGINFO)

    elif choice == 1: # Mappen Verwijderen
        if not current_folders:
            dialog.notification(ADDON.getAddonInfo('name'), "Geen mappen om te verwijderen uit deze Smart Folder.", xbmcgui.NOTIFICATION_INFO, 2000)
            return

        while True:
            display_paths = [os.path.basename(xbmcvfs.translatePath(p)) for p in current_folders] # Gebruik xbmcvfs.translatePath voor weergave
            if not display_paths:
                break
            
            remove_choice = dialog.select(f"Selecteer map om te verwijderen uit '{sf_name}':", display_paths + ["Klaar met verwijderen"])
            
            if remove_choice == -1 or remove_choice == len(display_paths): # Annuleren of "Klaar"
                break
            else:
                removed_path = current_folders.pop(remove_choice)
                dialog.notification(ADDON.getAddonInfo('name'), f"Map '{os.path.basename(removed_path)}' verwijderd.", xbmcgui.NOTIFICATION_INFO, 2000)
                log(f"Map '{removed_path}' verwijderd uit Smart Folder '{sf_name}'.", xbmc.LOGINFO)
        
        smart_folders[sf_name]['paths'] = current_folders
        save_smart_folders(smart_folders)
        dialog.notification(ADDON.getAddonInfo('name'), f"Smart Folder '{sf_name}' bijgewerkt.", xbmcgui.NOTIFICATION_INFO, 3000)
        log(f"Smart Folder '{sf_name}' bijgewerkt. Nieuwe paden: {current_folders}", xbmc.LOGINFO)


def delete_smart_folder():
    dialog = xbmcgui.Dialog()
    smart_folders = load_smart_folders()
    sf_names = list(smart_folders.keys())

    if not sf_names:
        dialog.notification(ADDON.getAddonInfo('name'), "Geen Smart Folders gevonden om te verwijderen.", xbmcgui.NOTIFICATION_INFO, 2000)
        return

    selected_sf_index = dialog.select("Selecteer Smart Folder om te Verwijderen:", sf_names)
    if selected_sf_index == -1:
        return

    sf_to_delete = sf_names[selected_sf_index]
    if dialog.yesno("Verwijder Smart Folder", f"Weet u zeker dat u '{sf_to_delete}' wilt verwijderen? Dit verwijdert ook de bijbehorende afspeellijst."):
        del smart_folders[sf_to_delete]
        save_smart_folders(smart_folders)
        
        # Verwijder ook de .m3u afspeellijst als deze bestaat
        playlist_file_path = xbmcvfs.translatePath(os.path.join(get_setting('playlist_dir'), f"{sf_to_delete}.m3u"))
        if xbmcvfs.exists(playlist_file_path):
            try:
                xbmcvfs.delete(playlist_file_path)
                log(f"Verwijderde afspeellijst: {playlist_file_path}", xbmc.LOGINFO)
            except Exception as e:
                log(f"Fout bij verwijderen afspeellijst {playlist_file_path}: {e}", xbmc.LOGERROR)

        dialog.notification(ADDON.getAddonInfo('name'), f"Smart Folder '{sf_to_delete}' verwijderd.", xbmcgui.NOTIFICATION_INFO, 3000)
        log(f"Deleted Smart Folder: {sf_to_delete}", xbmc.LOGINFO)

def update_all_sets(create_playlist_func): 
    smart_folders = load_smart_folders()
    if not smart_folders:
        log("Geen Smart Folders gevonden om bij te werken.", xbmc.LOGINFO)
        return

    dialog_progress = xbmcgui.DialogProgress()
    dialog_progress.create("Smart Folders Bijwerken", "Bezig met bijwerken van alle afspeellijst sets...")

    for i, (sf_name, sf_data) in enumerate(smart_folders.items()):
        current_progress = int((i / len(smart_folders)) * 100)
        dialog_progress.update(current_progress, f"Bijwerken: {sf_name}", "Even geduld...")
        log(f"Bijwerken van Smart Folder: {sf_name}", xbmc.LOGINFO)
        
        # Roep de doorgegeven functie aan in plaats van direct create_playlist
        create_playlist_func(folders=sf_data['paths'], name=sf_name, from_set=True)
        
        if dialog_progress.isCancelled():
            log("Bijwerken geannuleerd door gebruiker.", xbmc.LOGINFO)
            break
    
    dialog_progress.close()
    xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Alle Afspeellijst Sets Bijgewerkt!", xbmcgui.NOTIFICATION_INFO, 3000)
    log("Alle Smart Folders bijgewerkt.", xbmc.LOGINFO)