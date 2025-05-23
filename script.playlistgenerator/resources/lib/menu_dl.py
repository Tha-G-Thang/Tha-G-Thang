import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs
import sys
import os 

from .strm_utils import log, ADDON_ID, clean_display_name, load_sets, save_json, CONFIG_FILE   
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

    if choice == -1: 
        return

    selected_set_name = set_names[choice]

    if selected_set_name == "[Create New Playlist]":
        new_playlist_name = dialog.input("Enter New Playlist Name")
        if not new_playlist_name:
            dialog.notification("Playlist Generator", "Playlist name cannot be empty.", xbmcgui.NOTIFICATION_WARNING)
            return
        
        # Nu roepen we create_playlist aan met is_single_file_mode=True
        if create_playlist([file_url], new_playlist_name, is_single_file_mode=True): # Aangepast
            dialog.notification("Playlist Generator", f"File added to new playlist '{new_playlist_name}'.", xbmcgui.NOTIFICATION_INFO)
        else:
            dialog.notification("Playlist Generator", f"Failed to add file to new playlist '{new_playlist_name}'.", xbmcgui.NOTIFICATION_ERROR)
        
    else:
        # Add to an existing folder set (dit deel blijft ongewijzigd van de vorige iteratie)
        if selected_set_name in sets:
            playlist_path = os.path.join(xbmc.translatePath('special://profile/playlists/video/'), f"{selected_set_name}.m3u")
            
            try:
                current_playlist_content = []
                if xbmcvfs.exists(playlist_path):
                    with xbmcvfs.File(playlist_path, 'r') as f:
                        current_playlist_content = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
                if file_url not in current_playlist_content:
                    with xbmcvfs.File(playlist_path, 'a') as f:
                        if not xbmcvfs.exists(playlist_path) or not current_playlist_content: 
                            f.write("#EXTM3U\n")
                        f.write(f"{file_url}\n")
                    dialog.notification("Playlist Generator", f"Added '{display_name}' to '{selected_set_name}'.", xbmcgui.NOTIFICATION_INFO)
                    log(f"Added {file_url} to playlist {selected_set_name}.m3u")
                else:
                    dialog.notification("Playlist Generator", f"'{display_name}' is already in '{selected_set_name}'.", xbmcgui.NOTIFICATION_WARNING)

            except Exception as e:
                log(f"Error adding file to existing playlist: {e}", xbmc.LOGERROR)
                dialog.notification("Playlist Generator", "Error adding file to playlist.", xbmcgui.NOTIFICATION_ERROR)
        else:
            dialog.notification("Playlist Generator", "Selected set not found.", xbmcgui.NOTIFICATION_ERROR)