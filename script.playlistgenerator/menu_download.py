import sys
import xbmc
import urllib.parse

# Ensure necessary modules are imported.
# It's good practice to wrap imports in a try-except block in Kodi addons
# to catch issues if files are missing or corrupted.
try:
    import resources.lib.utils as utils
    from resources.lib.playlist_manager import PlaylistManager
except ImportError as e:
    # Log the error and exit gracefully if essential modules can't be imported.
    xbmc.log(f"[Playlist Generator] menu_download.py: Failed to import internal modules: {e}", xbmc.LOGERROR)
    sys.exit(1) # Exit immediately if essential modules can't be imported

if __name__ == '__main__':
    # Initialize addon globals and the PlaylistManager.
    # This is crucial because menu_download.py is now the direct entry point
    # for download actions from context menus, and it needs access to these utilities.
    utils.init_addon_globals()
    manager = PlaylistManager()

    # Parse arguments from Kodi.
    # For context menu items, sys.argv[1] typically contains the query string (e.g., "action=download&url=path/to/file").
    if len(sys.argv) > 1:
        args_str = sys.argv[1]
        
        # urllib.parse.parse_qs expects the string to not start with '?' for parsing
        # but context menu args sometimes include it, sometimes not.
        # Ensure it starts with '?' before parsing to get consistent behavior.
        if not args_str.startswith('?'):
            args_str = '?' + args_str
            
        # Parse the query string into a dictionary.
        # We slice from index 1 to remove the leading '?' for parse_qs.
        args = urllib.parse.parse_qs(args_str[1:])

        # Extract 'action' and 'url' from the parsed arguments.
        # .get('key', [None])[0] safely gets the first value from the list returned by parse_qs, or None.
        action = args.get('action', [None])[0]
        url = args.get('url', [None])[0]

        # Log received arguments for debugging
        utils.log(f"[Playlist Generator] menu_download.py received action: {action}, URL: {url}", xbmc.LOGDEBUG)

        # Execute the download action if both action and URL are present.
        if action == 'download' and url:
            manager.run_download_action(url)
        else:
            utils.log(f"[Playlist Generator] menu_download.py: Unknown action or missing URL. Action: {action}, URL: {url}", xbmc.LOGWARNING)
    else:
        # Log if no arguments were passed, which shouldn't happen for context menu calls.
        utils.log("[Playlist Generator] menu_download.py: No arguments received. Exiting.", xbmc.LOGWARNING)