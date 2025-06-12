import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import re
from resources.lib.core.base_utils import log, load_json, save_json, get_setting, set_setting, format_display_entry
from resources.lib.constants import ADDON, CONFIG_FILE, FAVORITES_FILE, SMART_FOLDERS_FILE # Importeer constanten
import sys

def load_favorites():
    return load_json(FAVORITES_FILE)

def save_favorites(favorites):
    save_json(favorites, FAVORITES_FILE)

def toggle_favorite(filepath, add=True):
    favorites = load_favorites()
    if add:
        if not any(f['path'] == filepath for f in favorites):
            favorites.append({'path': filepath})
            xbmcgui.Dialog().notification("Favorieten", "Bestand toegevoegd aan favorieten", xbmcgui.NOTIFICATION_INFO, 2000)
            log(f"Added {filepath} to favorites.")
        else:
            xbmcgui.Dialog().notification("Favorieten", "Bestand is al een favoriet", xbmcgui.NOTIFICATION_INFO, 2000)
            log(f"{filepath} is already a favorite.")
    else:
        initial_len = len(favorites)
        favorites = [f for f in favorites if f['path'] != filepath]
        if len(favorites) < initial_len:
            xbmcgui.Dialog().notification("Favorieten", "Bestand verwijderd uit favorieten", xbmcgui.NOTIFICATION_INFO, 2000)
            log(f"Removed {filepath} from favorites.")
        else:
            xbmcgui.Dialog().notification("Favorieten", "Bestand niet gevonden in favorieten", xbmcgui.NOTIFICATION_INFO, 2000)
            log(f"{filepath} not found in favorites to remove.")
    save_favorites(favorites)

def save_folder_set(name, folders):
    sets = load_json(CONFIG_FILE)
    sets[name] = folders
    save_json(sets, CONFIG_FILE)
    xbmcgui.Dialog().notification("Set Opgeslagen", f"Set '{name}' opgeslagen.", xbmcgui.NOTIFICATION_INFO, 2000)
    log(f"Saved set '{name}' with folders: {folders}")

def create_playlist_from_set(set_name):
    sets = load_json(CONFIG_FILE)
    if set_name in sets:
        folders = sets[set_name]
        from resources.lib.core.creator import create_playlist # Importeer lokaal om circulaire afhankelijkheid te voorkomen
        create_playlist(folders=folders, name=set_name, from_set=True)
    else:
        xbmcgui.Dialog().ok("Fout", f"Set '{set_name}' niet gevonden.")
        log(f"Attempted to create playlist from non-existent set: {set_name}", xbmc.LOGWARNING)

def update_all_sets():
    sets = load_json(CONFIG_FILE)
    if not sets:
        log("No sets found to update.", xbmc.LOGINFO)
        return
    
    dialog = xbmcgui.DialogProgress()
    dialog.create("Sets bijwerken", "Bezig met bijwerken van afspeellijsten...")
    
    total_sets = len(sets)
    for i, set_name in enumerate(sets):
        dialog.update(int((i / total_sets) * 100), f"Bijwerken van set: {set_name}")
        log(f"Updating set: {set_name}", xbmc.LOGINFO)
        create_playlist_from_set(set_name)
    
    dialog.close()
    xbmcgui.Dialog().notification("Sets Bijgewerkt", "Alle afspeellijsten zijn bijgewerkt.", xbmcgui.NOTIFICATION_INFO, 2000)
    log("All sets updated successfully.")

def manage_sets():
    sets = load_json(CONFIG_FILE)
    
    options = ["Nieuwe Set Maken"]
    for set_name in sets.keys():
        options.append(f"Afspeellijst maken van set: {set_name}")
    options.append("Verwijder een Set")
    options.append("Alle Sets Bijwerken")
    options.append("Beheer Smart Folders") # Optie voor beheer van Smart Folders

    dialog = xbmcgui.Dialog()
    selected_option_index = dialog.select("Beheer Afspeellijst Sets", options)

    if selected_option_index == -1: # Annuleren
        return
    
    if selected_option_index == 0: # Nieuwe Set Maken
        set_name = dialog.input('Voer nieuwe setnaam in', type=xbmcgui.INPUT_ALPHANUM)
        if not set_name:
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
        
        if folder_paths:
            save_folder_set(set_name, folder_paths)
        else:
            xbmcgui.Dialog().ok("Geen mappen geselecteerd", "Geen mappen geselecteerd voor de nieuwe set.")
            
    elif selected_option_index <= len(sets): # Afspeellijst maken van een bestaande set
        set_name = options[selected_option_index].replace("Afspeellijst maken van set: ", "")
        create_playlist_from_set(set_name)
    
    elif options[selected_option_index] == "Verwijder een Set":
        set_names = list(sets.keys())
        if not set_names:
            xbmcgui.Dialog().notification("Geen Sets", "Geen sets gevonden om te verwijderen.", xbmcgui.NOTIFICATION_INFO, 2000)
            return
        
        selected_set_index = dialog.select("Selecteer Set om te Verwijderen", set_names)
        if selected_set_index != -1:
            set_to_delete = set_names[selected_set_index]
            if dialog.yesno("Verwijder Set", f"Weet je zeker dat je '{set_to_delete}' wilt verwijderen?"):
                del sets[set_to_delete]
                save_json(sets, CONFIG_FILE)
                xbmcgui.Dialog().notification("Set Verwijderd", f"Set '{set_to_delete}' is verwijderd.", xbmcgui.NOTIFICATION_INFO, 2000)
                log(f"Deleted set: {set_to_delete}")
    
    elif options[selected_option_index] == "Alle Sets Bijwerken":
        update_all_sets()

    elif options[selected_option_index] == "Beheer Smart Folders":
        manage_smart_folders()

def manage_smart_folders():
    smart_folders = load_json(SMART_FOLDERS_FILE)

    options = ["Nieuwe Smart Folder Maken"]
    for sf_name in smart_folders.keys():
        options.append(f"Bewerk Smart Folder: {sf_name}")
    options.append("Verwijder Smart Folder")

    dialog = xbmcgui.Dialog()
    selected_option_index = dialog.select("Beheer Smart Folders", options)

    if selected_option_index == -1: # Annuleren
        return

    if selected_option_index == 0: # Nieuwe Smart Folder Maken
        sf_name = dialog.input('Voer nieuwe Smart Folder naam in', type=xbmcgui.INPUT_ALPHANUM)
        if not sf_name:
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
        
        if folder_paths:
            save_json({**smart_folders, sf_name: folder_paths}, SMART_FOLDERS_FILE) # Gebruik dictionary unpacking om de smart_folders te updaten
            xbmcgui.Dialog().notification("Smart Folder Opgeslagen", f"Smart Folder '{sf_name}' opgeslagen.", xbmcgui.NOTIFICATION_INFO, 2000)
            log(f"Saved Smart Folder '{sf_name}' with folders: {folder_paths}")
        else:
            xbmcgui.Dialog().ok("Geen mappen geselecteerd", "Geen mappen geselecteerd voor de nieuwe Smart Folder.")
    
    elif "Bewerk Smart Folder:" in options[selected_option_index]: # Bewerk Smart Folder
        sf_name = options[selected_option_index].replace("Bewerk Smart Folder: ", "")
        current_folders = smart_folders.get(sf_name, [])
        
        # Display current folders and allow modification
        edit_options = ["Voeg map toe"] + [f"Verwijder: {f}" for f in current_folders]

        while True:
            selected_edit_index = dialog.select(f"Bewerk '{sf_name}'", edit_options)
            if selected_edit_index == -1: # Annuleren
                break
            
            if selected_edit_index == 0: # Voeg map toe
                path = dialog.browse(3, 'Selecteer map om toe te voegen', 'files', '', False, False, xbmc.translatePath('special://home/'))
                if path and xbmcvfs.isdir(path) and path not in current_folders:
                    current_folders.append(path)
                    edit_options = ["Voeg map toe"] + [f"Verwijder: {f}" for f in current_folders]
                elif path and path in current_folders:
                    xbmcgui.Dialog().notification("Map bestaat al", "Deze map is al opgenomen in de Smart Folder.", xbmcgui.NOTIFICATION_INFO, 2000)
                elif path and not xbmcvfs.isdir(path):
                    xbmcgui.Dialog().ok("Ongeldige selectie", "Selecteer alstublieft een map, geen bestand.")
            else: # Verwijder map
                folder_to_remove = current_folders[selected_edit_index - 1] # -1 omdat "Voeg map toe" index 0 is
                if dialog.yesno("Verwijder Map", f"Weet je zeker dat je '{os.path.basename(folder_to_remove)}' wilt verwijderen uit deze Smart Folder?"):
                    current_folders.pop(selected_edit_index - 1)
                    edit_options = ["Voeg map toe"] + [f"Verwijder: {f}" for f in current_folders]
        
        # Sla de gewijzigde Smart Folder op
        save_json({**smart_folders, sf_name: current_folders}, SMART_FOLDERS_FILE)
        xbmcgui.Dialog().notification("Smart Folder Bijgewerkt", f"Smart Folder '{sf_name}' bijgewerkt.", xbmcgui.NOTIFICATION_INFO, 2000)
        log(f"Updated Smart Folder '{sf_name}' to: {current_folders}")
        
    elif options[selected_option_index] == "Verwijder Smart Folder":
        sf_names = list(smart_folders.keys())
        if not sf_names:
            xbmcgui.Dialog().notification("Geen Smart Folders", "Geen Smart Folders gevonden om te verwijderen.", xbmcgui.NOTIFICATION_INFO, 2000)
            return
        
        selected_sf_index = dialog.select("Selecteer Smart Folder om te Verwijderen", sf_names)
        if selected_sf_index != -1:
            sf_to_delete = sf_names[selected_sf_index]
            if dialog.yesno("Verwijder Smart Folder", f"Weet je zeker dat je '{sf_to_delete}' wilt verwijderen?"):
                del smart_folders[sf_to_delete]
                save_json(smart_folders, SMART_FOLDERS_FILE)
                xbmcgui.Dialog().notification("Smart Folder Verwijderd", f"Smart Folder '{sf_to_delete}' is verwijderd.", xbmcgui.NOTIFICATION_INFO, 2000)
                log(f"Deleted Smart Folder: {sf_to_delete}")

def apply_set_settings(set_name):
    # Dit is een placeholder voor logica die instellingen van een specifieke set toepast.
    # Dit kan in de toekomst worden uitgebreid met set-specifieke settings in de JSON.
    log(f"Applying settings for set: {set_name} (Not implemented yet)", xbmc.LOGWARNING)
    pass