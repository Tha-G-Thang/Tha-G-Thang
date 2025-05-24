import os
import xbmc
import xbmcvfs
import json
from .utils import log, translate_path, get_setting

def create_playlist(file_list, playlist_name, is_single_file_mode=False):

    try:
        playlist_path = xbmcvfs.translatePath(f'special://profile/playlists/video/{playlist_name}.m3u')
        
        # Ensure directory exists
        playlist_dir = os.path.dirname(playlist_path)
        if not xbmcvfs.exists(playlist_dir):
            xbmcvfs.mkdirs(playlist_dir)
        
        mode = 'a' if is_single_file_mode and xbmcvfs.exists(playlist_path) else 'w'
        
        with xbmcvfs.File(playlist_path, mode) as f:

            if mode == 'w' or not xbmcvfs.exists(playlist_path):
                f.write("#EXTM3U\n")
            
            for file_path in file_list:
                f.write(f"{file_path}\n")
        
        log(f"Playlist '{playlist_name}' created/updated successfully at {playlist_path}", xbmc.LOGINFO)
        return True
    except Exception as e:
        log(f"Failed to create/update playlist '{playlist_name}': {e}", xbmc.LOGERROR)
        return False