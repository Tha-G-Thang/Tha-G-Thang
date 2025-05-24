import sys
import os
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

from resources.lib import strm_scanner
from resources.lib import strm_creator
from resources.lib import strm_structure
from resources.lib import strm_utils
from resources.lib import menu_dl

ADDON = xbmcaddon.Addon(id='script.playlistgenerator')
ADDON_NAME = ADDON.getAddonInfo('name')

def create_playlist_from_selection():
    """
    Handles the 'Create Playlist' menu option.
    Scans for media files and creates STRM links, then asks for playlist name.
    """
    dialog = xbmcgui.Dialog()
    media_files = strm_scanner.get_media_files()

    if not media_files:
        dialog.notification(ADDON_NAME, "No media files found to create a playlist.", xbmcgui.NOTIFICATION_INFO)
        return

    # Create STRM files first (flat structure, no categories)
    strm_success = strm_creator.create_strm_from_list(media_files)
    if not strm_success:
        dialog.notification(ADDON_NAME, "Failed to create STRM links.", xbmcgui.NOTIFICATION_ERROR)
        return

    # Ask for playlist name
    playlist_name = dialog.input("Enter Playlist Name", type=xbmcgui.INPUT_ALPHANUM)
    if not playlist_name:
        dialog.notification(ADDON_NAME, "Playlist creation cancelled (no name provided).", xbmcgui.NOTIFICATION_WARNING)
        return

    # Use the paths to the newly created STRM files for the playlist
    strm_output_path = strm_utils.translate_path(strm_utils.get_setting('streams_target_root'))
    strm_file_paths = []
    for media_file in media_files:
        filename_base = os.path.splitext(os.path.basename(media_file))[0]
        strm_file_paths.append(os.path.join(strm_output_path, filename_base + '.strm'))

    # Create the playlist using the STRM file paths
    if strm_creator.create_playlist(strm_file_paths, playlist_name):
        dialog.notification(ADDON_NAME, f"Playlist '{playlist_name}' created successfully.", xbmcgui.NOTIFICATION_INFO)
    else:
        dialog.notification(ADDON_NAME, f"Failed to create playlist '{playlist_name}'.", xbmcgui.NOTIFICATION_ERROR)

def quick_scan_selected_folder():
    """
    Handles the 'Quick Scan (No Playlist)' menu option.
    Scans for media files and creates STRM links without making a playlist.
    """
    dialog = xbmcgui.Dialog()
    media_files = strm_scanner.get_media_files() # This will scan all configured source folders

    if media_files:
        strm_success = strm_creator.create_strm_from_list(media_files)
        if strm_success:
            dialog.notification(ADDON_NAME, f"Quick Scan: Created STRM links for {len(media_files)} files.", xbmcgui.NOTIFICATION_INFO)
        else:
            dialog.notification(ADDON_NAME, "Quick Scan: Failed to create STRM links.", xbmcgui.NOTIFICATION_ERROR)
    else:
        dialog.notification(ADDON_NAME, "Quick Scan: No media files found in source folders.", xbmcgui.NOTIFICATION_INFO)

def update_all_sets():
    """
    Handles the 'Update All Sets' menu option.
    Iterates through all saved sets, applies their settings, and updates their content.
    """
    dialog = xbmcgui.Dialog()
    sets_data = strm_utils.load_sets()

    if not sets_data:
        dialog.notification(ADDON_NAME, "No folder sets saved to update.", xbmcgui.NOTIFICATION_INFO)
        return

    updated_count = 0
    failed_sets = []

    for set_name, set_info in sets_data.items():
        dialog.notification(ADDON_NAME, f"Updating set: {set_name}", xbmcgui.NOTIFICATION_INFO)
        strm_utils.log(f"Applying settings for set: {set_name}")

        # Apply settings from the current set
        if not menu_dl.apply_set_settings(set_name, sets_data):
            strm_utils.log(f"Failed to apply settings for set: {set_name}. Skipping update.", xbmc.LOGERROR)
            failed_sets.append(set_name)
            continue

        # Perform the scan based on the applied settings
        media_files = strm_scanner.get_media_files()

        if media_files:
            strm_utils.log(f"Found {len(media_files)} media files for set '{set_name}'. Creating STRM links.")
            strm_success = strm_creator.create_strm_from_list(media_files)

            if strm_success:
                # If a playlist needs to be generated, get the STRM file paths
                strm_output_path = strm_utils.translate_path(strm_utils.get_setting('streams_target_root'))
                strm_file_paths = []
                for media_file in media_files:
                    filename_base = os.path.splitext(os.path.basename(media_file))[0]
                    strm_file_paths.append(os.path.join(strm_output_path, filename_base + '.strm'))

                # Update the playlist for the set
                if strm_creator.create_playlist(strm_file_paths, set_name): # Using set_name as playlist name
                    strm_utils.log(f"Successfully updated STRM links and playlist for set: {set_name}", xbmc.LOGINFO)
                    updated_count += 1
                else:
                    strm_utils.log(f"Failed to update playlist for set: {set_name}", xbmc.LOGERROR)
                    failed_sets.append(set_name)
            else:
                strm_utils.log(f"Failed to create STRM links for set: {set_name}", xbmc.LOGERROR)
                failed_sets.append(set_name)
        else:
            strm_utils.log(f"No media files found for set: {set_name}. Skipping STRM creation.", xbmc.LOGWARNING)
            dialog.notification(ADDON_NAME, f"No files for set: {set_name}", xbmcgui.NOTIFICATION_INFO)

    if updated_count > 0:
        dialog.notification(ADDON_NAME, f"Updated {updated_count} sets.", xbmcgui.NOTIFICATION_INFO)
    if failed_sets:
        dialog.notification(ADDON_NAME, f"Failed to update: {', '.join(failed_sets)}", xbmcgui.NOTIFICATION_ERROR)
    elif updated_count == 0:
        dialog.notification(ADDON_NAME, "All sets already up to date or no files found.", xbmcgui.NOTIFICATION_INFO)


def show_main_menu():
    dialog = xbmcgui.Dialog()
    while True:
        choice = dialog.select(ADDON_NAME, [
            "Create Playlist",
            "Quick Scan (No Playlist)",
            "Manage Folder Sets",
            "Update All Sets",
            "Settings",
            "Exit"
        ])

        if choice == 0: # Create Playlist
            create_playlist_from_selection()
        elif choice == 1: # Quick Scan (No Playlist)
            quick_scan_selected_folder()
        elif choice == 2: # Manage Folder Sets
            menu_dl.manage_sets() # This function will be implemented in menu_dl.py
        elif choice == 3: # Update All Sets
            update_all_sets()
        elif choice == 4: # Addon Settings
            ADDON.openSettings()
        elif choice in (5, -1): # Exit or Cancel
            break

if __name__ == '__main__':
    strm_utils.log(f"{ADDON_NAME} starting...")

    # Initial call to ensure logging is set up if not already
    log = strm_utils.log # Use the logging function from strm_utils

    if len(sys.argv) > 1:
        args = strm_utils.parse_url(sys.argv[0]) # Use sys.argv[0] for context menu args
        mode = args.get('mode')

        if mode == 'add_to_playlist':
            file_url = args.get('file_url')
            if file_url:
                menu_dl.add_to_playlist_from_context(file_url)
        # Removed 'download_video_file' mode as per user's request
        else:
            show_main_menu()
    else:
        show_main_menu() # Show main menu if no arguments are passed (addon started normally)