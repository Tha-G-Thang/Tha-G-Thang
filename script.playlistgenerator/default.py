import xbmcaddon
import xbmcgui
import xbmcplugin
import sys

from resources.lib import playlist_manager
from resources.lib import utils

# Get addon info
ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_PATH = ADDON.getAddonInfo('path')

# Initialize playlist manager
manager = playlist_manager.PlaylistManager()

# Safely get the plugin handle from sys.argv
# This is crucial for xbmcplugin functions to work correctly.
try:
    PLUGIN_HANDLE = int(sys.argv[1])
except (IndexError, ValueError):
    # If sys.argv[1] is not present or not an integer, it means the addon
    # is likely not being launched as a proper Kodi plugin.
    # We log a warning and set PLUGIN_HANDLE to 0 as a fallback.
    # Some xbmcplugin functions might not work as expected with a 0 handle.
    PLUGIN_HANDLE = 0 
    utils.log(f"Warning: Could not get valid plugin handle from sys.argv. Using 0. sys.argv: {sys.argv}", xbmc.LOGWARNING)


def display_main_menu():
    """Displays the main menu of the addon."""
    # Use the globally defined PLUGIN_HANDLE for all xbmcplugin calls
    xbmcplugin.setPluginCategory(PLUGIN_HANDLE, ADDON_NAME)

    # Main menu items
    menu_items = [
        ("Manage Playlists Sets", "manage_sets"),
        ("Create Playlist", "create_playlist"),
        ("Settings", "open_settings"),
    ]

    # Only show 'Generate All Playlists' if there are existing sets
    if manager.sets: 
        menu_items.insert(1, ("Generate All Playlists", "generate_all_playlists"))

    for item_name, action_id in menu_items:
        list_item = xbmcgui.ListItem(label=item_name)
        url = utils.build_url({'action': action_id})
        xbmcplugin.addDirectoryItem(PLUGIN_HANDLE, url, list_item, isFolder=True) # Use PLUGIN_HANDLE

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE) # Use PLUGIN_HANDLE

def create_playlist_action():
    """Handles the create playlist action."""
    # The set_id is passed as an argument from the main menu (if applicable),
    # but for initial calls, it might not be present.
    # The manager's create_playlist method likely handles this by itself
    # or expects to be called with a specific set_id if it's not a generic call.
    # For now, it's called without args in main_menu, which is fine for its internal logic.
    manager.create_playlist("") # Pass an empty string for the default action to create new playlist

def generate_all_playlists_action():
    """Handles generating all playlists."""
    manager.generate_all_playlists()

def manage_sets_action():
    """Handles managing playlist sets."""
    manager.manage_sets()

def open_settings_action():
    """Opens the addon settings."""
    ADDON.openSettings()

# Main entry point
if __name__ == '__main__':
    args = utils.parse_argv(sys.argv)
    action = args.get('action')
    set_id_arg = args.get('set_id') # Get set_id if passed in URL

    if action == 'create_playlist':
        # If set_id is passed, it means we are trying to create a specific playlist
        # Otherwise, the manager's create_playlist will handle the new playlist creation flow
        manager.create_playlist(set_id_arg) 
    elif action == 'generate_all_playlists':
        manager.generate_all_playlists()
    elif action == 'manage_sets':
        manager.manage_sets()
    elif action == 'open_settings':
        open_settings_action()
    else:
        # Default action when the addon is first launched
        display_main_menu()
