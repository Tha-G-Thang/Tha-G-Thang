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
        xbmcgui.Dialog().notification(ADDON_NAME, get_string(3001), time=3000) # "Playlist creation cancelled: No set name provided."
        return

    # Select folders
    folders = manager._select_folders_dialog()
    if not folders:
        xbmcgui.Dialog().notification(ADDON_NAME, get_string(3002), time=3000) # "Playlist creation cancelled: No folders selected."
        return

    # Ask the user if they want to save the set
    if xbmcgui.Dialog().yesno(ADDON_NAME, get_string(3003)): # "Do you want to save this as a new folder set?"
        if not manager.save_folder_set(name, folders):
            # save_folder_set already shows a notification, so only log here
            log(f"Failed to save folder set '{name}'.", xbmc.LOGERROR)
    
    # Create the playlist (this will also use the addon's settings)
    # create_playlist_from_set in manager.py will ask if set-settings should be applied
    manager.create_playlist_from_set(name, folders)

def manage_sets():
    manager = SetManager()
    manager.show_manager_menu()

def update_all_sets():
    manager = SetManager()
    manager.update_all_sets()

def open_settings():
    ADDON.openSettings()
    # Apply settings based on the currently selected profile after settings dialog is closed
    current_profile = get_setting('30001') # Use the new ID for 'user_profile_mode'
    apply_profile_settings(current_profile)

def show_ai_menu():
    dialog = xbmcgui.Dialog()
    ai_menu_options = [
        get_string(3004), # "AI Metadata Extraction"
        get_string(3005), # "AI Filename Cleaning"
        get_string(3006), # "AI Auto-Tagging"
        get_string(3007), # "AI Smart Playlists"
        get_string(3008), # "AI Natural Language Search"
    ]
    
    while True:
        choice = _show_menu(get_string(3009), ai_menu_options) # "AI Features"
        
        if choice is None: # Back
            break
        elif choice == 0:
            dialog.notification(ADDON_NAME, get_string(3010), time=3000) # "AI Metadata Extraction not yet implemented."
        elif choice == 1:
            dialog.notification(ADDON_NAME, get_string(3011), time=3000) # "AI Filename Cleaning not yet implemented."
        elif choice == 2:
            dialog.notification(ADDON_NAME, get_string(3012), time=3000) # "AI Auto-Tagging not yet implemented."
        elif choice == 3:
            dialog.notification(ADDON_NAME, get_string(3013), time=3000) # "AI Smart Playlists not yet implemented."
        elif choice == 4:
            dialog.notification(ADDON_NAME, get_string(3014), time=3000) # "AI Natural Language Search not yet implemented."


def _show_menu(title, items):
    """
    Displays a Kodi menu and returns the chosen index or None if the user cancels/goes back.
    """
    dialog = xbmcgui.Dialog()
    menu_items = items + [get_string(3015)] # "Back"
    
    while True:
        choice = dialog.select(title, menu_items)
        if choice == -1 or choice == len(menu_items) - 1: # -1 is escape, laatste item is "Back"
            return None
        else:
            return choice

def show_main_menu():
    while True:
        menu_options = [
            get_string(3016), # "Create New Playlist"
            get_string(3017), # "Manage Existing Folder Sets"
            get_string(3018), # "Update All Playlists"
        ]
        
        # Add AI Features if the user is in 'Pro' mode
        if get_setting('30001') == '1': # Use the new ID for 'user_profile_mode'
            menu_options.append(get_string(3009)) # "AI Features"
        
        menu_options.append(get_string(3019)) # "Addon Settings" # Always as last option

        choice = _show_menu(ADDON_NAME, menu_options)
        
        if choice is None: # Back or Exit
            break
        elif choice == 0: # Create New Playlist
            create_playlist()
        elif choice == 1: # Manage Existing Folder Sets
            manage_sets()
        elif choice == 2: # Update All Playlists
            update_all_sets()
        elif choice == 3 and get_setting('30001') == '1': # If AI Features is visible
            show_ai_menu()
        elif (choice == 3 and get_setting('30001') == '0') or \
             (choice == 4 and get_setting('30001') == '1'): # Addon Settings
            open_settings()

# Function to get translated string from Kodi
def get_string(string_id):
    return ADDON.getLocalizedString(string_id)

if __name__ == '__main__':
    log(f"{ADDON_NAME} starting")
    if not xbmcvfs.exists(ADDON_PROFILE):
        try:
            xbmcvfs.mkdirs(ADDON_PROFILE)
            log(f"Created addon profile directory: {ADDON_PROFILE}", xbmc.LOGINFO)
        except Exception as e:
            log(f"Failed to create addon profile directory: {ADDON_PROFILE} - {e}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, get_string(3020), time=5000) # "Error: Could not create profile directory."
    
    # Apply settings based on the currently selected profile at addon startup
    current_profile = get_setting('30001') # Use the new ID for 'user_profile_mode'
    apply_profile_settings(current_profile)
    
    show_main_menu()