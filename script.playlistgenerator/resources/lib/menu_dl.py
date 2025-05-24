import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs
import sys
import os 
import json # <-- DEZE IMPORT IS TOEGEVOEGD

from .strm_utils import log, ADDON_ID, clean_display_name, load_sets, save_sets, CONFIG_FILE   
from .strm_creator import create_playlist # Importeer create_playlist

def add_to_playlist_from_context(file_url):
    """
    Adds a file from a context menu selection to an existing or new playlist.
    """
    log(f"Context menu 'Add to Playlist' called for: {file_url}")
    dialog = xbmcgui.Dialog()

    display_name = clean_display_name(file_url)

    sets = load_sets() 
    if not sets:
        dialog.notification("Playlist Generator", "No existing folder sets. Create one first.", xbmcgui.NOTIFICATION_INFO)
        return

    set_names = list(sets.keys())
    set_names.append("[Create New Playlist]") 

    choice = dialog.select("Select Playlist / Folder Set", set_names)

    if choice == -1: # User cancelled
        return

    selected_set_name = set_names[choice]

    if selected_set_name == "[Create New Playlist]":
        new_playlist_name = dialog.input("Enter New Playlist Name")
        if not new_playlist_name:
            dialog.notification("Playlist Generator", "Playlist name cannot be empty.", xbmcgui.NOTIFICATION_WARNING)
            return
        
        # Nu roepen we create_playlist aan met is_single_file_mode=True
        if create_playlist([file_url], new_playlist_name, is_single_file_mode=True):
            dialog.notification("Playlist Generator", f"Created new playlist '{new_playlist_name}' and added '{display_name}'.", xbmcgui.NOTIFICATION_INFO)
        else:
            dialog.notification("Playlist Generator", f"Failed to create playlist '{new_playlist_name}'.", xbmcgui.NOTIFICATION_ERROR)
            
    else:
        # Add to existing playlist
        playlist_path = os.path.join(xbmc.translatePath('special://profile/playlists/video/'), f"{selected_set_name}.m3u")
            
        try:
            current_playlist_content = []
            if xbmcvfs.exists(playlist_path):
                with xbmcvfs.File(playlist_path, 'r') as f:
                    current_playlist_content = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if file_url not in current_playlist_content:
                with xbmcvfs.File(playlist_path, 'a') as f:
                    if not xbmcvfs.exists(playlist_path) or not current_playlist_content: 
                        f.write("#EXTM3U\\n")
                    f.write(f"{file_url}\\n")
                dialog.notification("Playlist Generator", f"Added '{display_name}' to '{selected_set_name}'.", xbmcgui.NOTIFICATION_INFO)
                log(f"Added {file_url} to playlist {selected_set_name}.m3u")
            else:
                dialog.notification("Playlist Generator", f"'{display_name}' is already in '{selected_set_name}'.", xbmcgui.NOTIFICATION_WARNING)

        except Exception as e:
            log(f"Error adding file to existing playlist: {e}", xbmc.LOGERROR)
            dialog.notification("Playlist Generator", "Error adding file to playlist.", xbmcgui.NOTIFICATION_ERROR)
        else:
            dialog.notification("Playlist Generator", "Selected set not found.", xbmcgui.NOTIFICATION_ERROR)

def show_sets_menu():
    """Shows a menu for managing saved settings sets."""
    dialog = xbmcgui.Dialog()
    sets = load_sets()
    
    menu_options = ["Add Current Settings as New Set", "[Delete Set]", "[Apply Set]"]
    if sets:
        menu_options.insert(1, "[Update Existing Set]") # Add update option if sets exist

    while True:
        choice = dialog.select("Manage Settings Sets", menu_options + list(sets.keys()))

        if choice == -1: # Cancel
            break
        
        selected_option = menu_options[choice] if choice < len(menu_options) else list(sets.keys())[choice - len(menu_options)]

        if selected_option == "Add Current Settings as New Set":
            new_set_name = dialog.input("Enter New Set Name")
            if new_set_name:
                if new_set_name in sets:
                    if not dialog.yesno("Overwrite Set?", f"Set '{new_set_name}' already exists. Overwrite?"):
                        continue
                add_current_settings_as_set(new_set_name, sets)
            else:
                dialog.notification(ADDON_ID, "Set name cannot be empty.", xbmcgui.NOTIFICATION_WARNING)
        
        elif selected_option == "[Update Existing Set]":
            if not sets:
                dialog.notification(ADDON_ID, "No sets to update.", xbmcgui.NOTIFICATION_INFO)
                continue
            update_choice = dialog.select("Select Set to Update", list(sets.keys()))
            if update_choice != -1:
                set_to_update = list(sets.keys())[update_choice]
                update_set_with_current_settings(set_to_update, sets)

        elif selected_option == "[Delete Set]":
            if not sets:
                dialog.notification(ADDON_ID, "No sets to delete.", xbmcgui.NOTIFICATION_INFO)
                continue
            delete_choice = dialog.select("Select Set to Delete", list(sets.keys()))
            if delete_choice != -1:
                set_to_delete = list(sets.keys())[delete_choice]
                if dialog.yesno("Confirm Delete", f"Are you sure you want to delete set '{set_to_delete}'?"):
                    delete_set(set_to_delete, sets)

        elif selected_option == "[Apply Set]":
            if not sets:
                dialog.notification(ADDON_ID, "No sets to apply.", xbmcgui.NOTIFICATION_INFO)
                continue
            apply_choice = dialog.select("Select Set to Apply", list(sets.keys()))
            if apply_choice != -1:
                set_to_apply = list(sets.keys())[apply_choice]
                if dialog.yesno("Apply Set?", f"Apply settings from set '{set_to_apply}'? This will change your current add-on settings."):
                    apply_set_settings(set_to_apply, sets)
        elif selected_option in sets: # User selected an existing set name
            # If a set name is directly selected, assume the user wants to apply it
            if dialog.yesno("Apply Set?", f"Apply settings from set '{selected_option}'?"):
                apply_set_settings(selected_option, sets)

def add_current_settings_as_set(set_name, sets_data):
    """Saves the current addon settings as a new named set."""
    addon = xbmcaddon.Addon(id=ADDON_ID)
    current_settings = {}
    
    # List of all settings IDs that should be saved
    settings_to_save = [
        'set_source_root_1', 'set_exclude_folders_1',
        'set_source_root_2', 'set_exclude_folders_2',
        'set_source_root_3', 'set_exclude_folders_3',
        'set_source_root_4', 'set_exclude_folders_4',
        'set_source_root_5', 'set_exclude_folders_5',
        'streams_target_root', 'file_extensions', 'recursive_scan',
        'scan_depth_limit', 'min_file_size_mb', 'exclude_hidden_files',
        'enable_adult_content_filter', 'adult_content_keywords',
        'adult_category_name', 'default_category_behavior',
        'download_path', 'enable_direct_download', 'download_remove_words',
        'download_switch_words', 'download_regex_enable',
        'download_regex_pattern', 'download_regex_replace_with',
        'adult_download_path', 'adult_remove_words', 'adult_switch_words',
        'adult_regex_enable', 'adult_regex_pattern',
        'download_regex_replace_with_adult', 'log_level'
    ]
    
    for setting_id in settings_to_save:
        current_settings[setting_id] = addon.getSetting(setting_id)

    sets_data[set_name] = {'settings': current_settings}
    if save_sets(sets_data):
        log(f"Set '{set_name}' added/updated successfully.")
        xbmcgui.Dialog().notification(ADDON_ID, f"Set '{set_name}' saved.", xbmcgui.NOTIFICATION_INFO)
    else:
        log(f"Failed to add/update set '{set_name}'.", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_ID, f"Failed to save set '{set_name}'.", xbmcgui.NOTIFICATION_ERROR)

def update_set_with_current_settings(set_name, sets_data):
    """Updates an existing set with the current addon settings."""
    add_current_settings_as_set(set_name, sets_data) # Hergebruik de add functie om bij te werken

def apply_set_settings(set_name, sets_data):
    """Apply settings from a saved set to the addon settings."""
    addon = xbmcaddon.Addon(id=ADDON_ID) # Haal de addon instance opnieuw op
    if set_name not in sets_data or 'settings' not in sets_data[set_name]:
        log(f"Set '{set_name}' not found or has no settings.", xbmc.LOGWARNING)
        return False
    
    settings_to_apply = sets_data[set_name]['settings']
    for setting_id, value in settings_to_apply.items():
        addon.setSetting(setting_id, value)
        log(f"Applied setting '{setting_id}': '{value}' from set '{set_name}'.")

    xbmcgui.Dialog().notification(ADDON_ID, f"Settings from set '{set_name}' applied.", xbmcgui.NOTIFICATION_INFO)
    log(f"Successfully applied settings from set: {set_name}")
    return True

def delete_set(set_name, sets_data):
    """Deletes a saved settings set."""
    if set_name in sets_data:
        del sets_data[set_name]
        if save_sets(sets_data):
            log(f"Set '{set_name}' deleted successfully.")
            xbmcgui.Dialog().notification(ADDON_ID, f"Set '{set_name}' deleted.", xbmcgui.NOTIFICATION_INFO)
        else:
            log(f"Failed to delete set '{set_name}'.", xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_ID, f"Failed to delete set '{set_name}'.", xbmcgui.NOTIFICATION_ERROR)
    else:
        log(f"Attempted to delete non-existent set: {set_name}", xbmc.LOGWARNING)
        xbmcgui.Dialog().notification(ADDON_ID, f"Set '{set_name}' not found.", xbmcgui.NOTIFICATION_WARNING)