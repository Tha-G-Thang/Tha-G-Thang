import sys
import urllib.parse
import xbmc
import xbmcgui
import xbmcvfs
import os # Import os for path manipulation

import resources.lib.utils as utils
from resources.lib.playlist_manager import PlaylistManager

def _view_files_in_directory(directory_path: str, title: str):
    dialog = xbmcgui.Dialog()
    files = []
    try:
        # List only files, not directories, in the specified directory
        # The listdir function returns (files, dirs) tuples
        file_names, _ = xbmcvfs.listdir(directory_path)
        # Filter out directories and only include actual files
        files = [f for f in file_names if xbmcvfs.isfile(os.path.join(directory_path, f))]
        files.sort() # Sort alphabetically
    except Exception as e:
        utils.log(f"Error listing files in {directory_path}: {e}", xbmc.LOGERROR)
        dialog.ok(utils.ADDON_NAME, f"Could not open {title} directory: {directory_path}")
        return

    if not files:
        dialog.ok(utils.ADDON_NAME, f"No files found in {title} directory.")
        return

    # Add a "Back" option to navigate back to the main menu
    list_items = ["[ Back ]"] + files

    while True:
        choice = dialog.select(title, list_items)

        if choice == -1: # Escape button pressed
            break
        elif choice == 0: # "[ Back ]" selected
            break
        else:
            selected_file = files[choice - 1]
            selected_path = os.path.join(directory_path, selected_file)
            # For .m3u files, offer to play or show info
            if selected_path.lower().endswith('.m3u'):
                options = ["Play Playlist", "Show Info"]
                option_choice = dialog.select(f"Playlist: {selected_file}", options)
                if option_choice == 0: # Play Playlist
                    xbmc.Player().play(selected_path)
                elif option_choice == 1: # Show Info (e.g., list contents)
                    playlist_content = []
                    try:
                        with xbmcvfs.File(selected_path, 'r') as f:
                            for line in f:
                                line = line.strip()
                                if not line.startswith('#') and line:
                                    playlist_content.append(os.path.basename(line)) # Show only filename from playlist
                    except Exception as e:
                        utils.log(f"Error reading playlist {selected_path}: {e}", xbmc.LOGERROR)
                        playlist_content = ["Error reading playlist content."]
                    
                    if playlist_content:
                        dialog.ok(f"Contents of {selected_file}", "\n".join(playlist_content[:20]) + ("\n..." if len(playlist_content) > 20 else ""))
                    else:
                        dialog.ok(f"Contents of {selected_file}", "Playlist is empty or could not be read.")
            else:
                # For other files (like .json for sets or general files), just show info or do nothing
                dialog.ok(utils.ADDON_NAME, f"Selected: {selected_file}")

if __name__ == '__main__':
    manager = PlaylistManager()

    if len(sys.argv) > 2:
        args = urllib.parse.parse_qs(sys.argv[2][1:])
    else:
        args = {}

    action = args.get('action', [None])[0]
    url = args.get('url', [None])[0]

    if action == 'download' and url:
        utils.log(f"Initiating download from context menu. URL: {url}", xbmc.LOGINFO)
        import resources.lib.downloader as downloader
        download_path = utils.get_setting('download_path', 'folder') # Use 'folder' type for settings retrieval
        adult_download_path = utils.get_setting('download_path_adult', 'folder')
        
        # Determine actual download path based on adult content indicator
        final_download_path = download_path
        if utils.get_setting('enable_adult_cleanup', 'bool') and utils.get_setting('download_path_adult', 'folder') and any(indicator in url.lower() for indicator in ['adult', 'xxx']):
             final_download_path = adult_download_path

        downloader.download_file(url, final_download_path) # Pass the determined path
    else:
        dialog = xbmcgui.Dialog()
        menu_items = [
            "Create New Playlist",
            "Manage Folder Sets",
            "View Playlists",
            "View Folder Sets",
            "Update All Folder Sets",
            "Settings",
            "Exit"
        ]
        choice = dialog.select(utils.ADDON_NAME, menu_items)

        if choice == 0:
            manager.create_playlist()
        elif choice == 1:
            manager.manage_sets()
        elif choice == 2:
            _view_files_in_directory(utils.PLAYLIST_DIR, "View Playlists")
        elif choice == 3:
            _view_files_in_directory(utils.SETS_DIR, "View Folder Sets")
        elif choice == 4:
            manager.update_all_sets()
        elif choice == 5:
            utils.ADDON.openSettings()
        elif choice in (6, -1):
            pass