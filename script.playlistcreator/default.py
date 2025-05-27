import sys
import xbmcgui
import xbmcaddon
import xbmcvfs
from resources.lib.manager import SetManager
from resources.lib.utils import log, get_setting, ADDON_PROFILE, PLAYLIST_DIR, apply_profile_settings # Added apply_profile_settings
from resources.lib.constants import ADDON_ID


ADDON = xbmcaddon.Addon(ADDON_ID)
ADDON_NAME = ADDON.getAddonInfo('name')


def create_playlist():
    manager = SetManager()
    
    # Get the name for the set
    name = manager._get_set_name()
    if not name:
        xbmcgui.Dialog().notification(ADDON_NAME, "Playlist creation cancelled: No set name provided.", time=3000)
        return

    # Select folders
    folders = manager._select_folders_dialog()
    if not folders:
        xbmcgui.Dialog().notification(ADDON_NAME, "Playlist creation cancelled: No folders selected.", time=3000)
        return

    # Ask the user if they want to save the set
    if xbmcgui.Dialog().yesno(ADDON_NAME, "Do you want to save this as a new folder set?"):
        if not manager.save_folder_set(name, folders):
            # save_folder_set already shows a notification, so only log here
            log(f"Failed to save folder set '{name}'.", xbmc.LOGERROR)
    
    # Create the playlist (this will also use the addon's settings)
    # create_playlist_from_set in manager.py will ask if set-settings should be applied
    manager.create_playlist_from_set(name) # This will use the settings of the set


def quick_scan():
    manager = SetManager()
    folders = manager._select_folders_dialog()
    if not folders:
        xbmcgui.Dialog().notification(ADDON_NAME, "Quick scan cancelled: No folders selected.", time=3000)
        return
    
    # Perform scan using current settings, no playlist creation
    # The scanner itself reads settings, so nothing explicit needed here besides selection.
    xbmcgui.Dialog().notification(ADDON_NAME, "Scanning folders...", time=2000)
    # In a real scenario, you might want to instantiate DAVSScanner and run its scan method,
    # then display results or just log the files found.
    log(f"Quick scan initiated for folders: {folders}", xbmc.LOGINFO)
    xbmcgui.Dialog().notification(ADDON_NAME, "Quick scan complete (no playlist created).", time=3000)


def manage_sets():
    manager = SetManager()
    while True:
        sets = manager.load_folder_sets()
        if not sets:
            xbmcgui.Dialog().notification(ADDON_NAME, "No folder sets saved yet.", time=3000)
            break

        set_names = list(sets.keys())
        choice = _show_menu("Manage Folder Sets", set_names + ["Update All Playlists", "Delete All Sets"])

        if choice is None: # Back or Cancel
            break
        elif choice == len(set_names): # "Update All Playlists" option
            manager.update_all_sets()
        elif choice == len(set_names) + 1: # "Delete All Sets" option
            if xbmcgui.Dialog().yesno(ADDON_NAME, "Are you sure you want to delete ALL folder sets?", "This action cannot be undone."):
                manager.delete_all_folder_sets()
                xbmcgui.Dialog().notification(ADDON_NAME, "All folder sets deleted.", time=3000)
        else:
            selected_set_name = set_names[choice]
            # Menu for selected set
            set_actions = ["Create Playlist from this Set", "Delete this Set"]
            action_choice = _show_menu(f"Actions for '{selected_set_name}'", set_actions)

            if action_choice is None:
                continue # Go back to set list
            elif action_choice == 0:
                # Create playlist from this set, applying its saved settings if chosen
                manager.create_playlist_from_set(selected_set_name)
            elif action_choice == 1:
                if xbmcgui.Dialog().yesno(ADDON_NAME, f"Delete set '{selected_set_name}'?", "This cannot be undone."):
                    manager.delete_folder_set(selected_set_name)
                    xbmcgui.Dialog().notification(ADDON_NAME, f"Set '{selected_set_name}' deleted.", time=3000)

def update_all_sets():
    manager = SetManager()
    manager.update_all_sets()

def open_settings():
    ADDON.openSettings()
    # After settings are closed, apply the new profile settings if the profile was changed.
    # This ensures that the Python logic immediately reflects the selected profile.
    current_profile = get_setting('user_profile_mode') # 'Normal' or 'Pro'
    apply_profile_settings(current_profile)
    log(f"Addon settings closed. Applied profile: {current_profile}")


def _show_menu(title, items):
    """
    Shows a menu and returns the chosen index or None if the user cancels/goes back.
    """
    dialog = xbmcgui.Dialog()
    menu_items = items + ["Back"]
    
    while True:
        choice = dialog.select(title, menu_items)
        if choice == -1 or choice == len(menu_items) - 1: # -1 is escape, last item is "Back"
            return None
        else:
            return choice

def show_main_menu():
    while True:
        menu_options = [
            "Create New Playlist", 
            # "Quick Scan (No Playlist Creation)", # DEZE LIJN VERWIJDEREN
            "Manage Existing Folder Sets",
            "Update All Playlists",
        ]
        
        # Voeg AI Features toe als de gebruiker in 'Pro' modus zit
        if get_setting('user_profile_mode') == '1':
            menu_options.append("AI Features")
        
        menu_options.append("Addon Settings") # Altijd als laatste optie

        choice = _show_menu(ADDON_NAME, menu_options)
        
        if choice is None: # Back of Exit
            break
        elif choice == 0: # Create New Playlist (was 0)
            create_playlist()
        elif choice == 1: # Manage Existing Folder Sets (was 2)
            manage_sets()
        elif choice == 2: # Update All Playlists (was 3)
            update_all_sets()
        elif choice == 3 and get_setting('user_profile_mode') == '1': # Als AI Features zichtbaar is (was 4)
            show_ai_menu()
        elif (choice == 3 and get_setting('user_profile_mode') == '0') or \
             (choice == 4 and get_setting('user_profile_mode') == '1'): # Addon Settings (was 4 of 5)
            open_settings()

if __name__ == '__main__':
    log(f"{ADDON_NAME} starting")
    if not xbmcvfs.exists(ADDON_PROFILE):
        try:
            xbmcvfs.mkdirs(ADDON_PROFILE)
            log(f"Created addon profile directory: {ADDON_PROFILE}", xbmc.LOGINFO)
        except Exception as e:
            log(f"Failed to create addon profile directory: {ADDON_PROFILE} - {e}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification(get_setting('ADDON_NAME', 'Playlist Creator'), "Error: Could not create profile directory.", time=5000)
    
    # Apply settings based on the currently selected profile at addon startup
    current_profile = get_setting('user_profile_mode') # 'Normal' or 'Pro'
    apply_profile_settings(current_profile) # Apply settings once at startup
    
    show_main_menu()