import os
import xbmc
import xbmcvfs

from .strm_utils import log, translate_path, is_valid_file, get_setting # get_setting toegevoegd
from .strm_structure import ensure_category_structure
from .constants import CATEGORY_NAMES

def create_playlist(file_list, playlist_name, is_single_file_mode=False):
    """
    Create a playlist from a list of files
    This is a wrapper/alternative to create_strm_from_list for playlist creation
    """
    try:
        if is_single_file_mode:
            # Handle single file addition to playlist
            playlist_path = xbmcvfs.translatePath(f'special://profile/playlists/video/{playlist_name}.m3u')
            
            # Ensure directory exists
            playlist_dir = os.path.dirname(playlist_path)
            if not xbmcvfs.exists(playlist_dir):
                xbmcvfs.mkdirs(playlist_dir)
            
            # Create or append to playlist
            mode = 'a' if xbmcvfs.exists(playlist_path) else 'w'
            with open(playlist_path, mode) as f:
                if mode == 'w':
                    f.write("#EXTM3U\n")
                for file_url in file_list:
                    f.write(f"{file_url}\n")
            
            log(f"Created/updated playlist: {playlist_path}")
            return True
        else:
            # This is for creating a playlist from a list of files, overwriting if it exists
            playlist_path = xbmcvfs.translatePath(f'special://profile/playlists/video/{playlist_name}.m3u')
            
            # Ensure directory exists
            playlist_dir = os.path.dirname(playlist_path)
            if not xbmcvfs.exists(playlist_dir):
                xbmcvfs.mkdirs(playlist_dir)
            
            # Write the new playlist
            with open(playlist_path, 'w') as f:
                f.write("#EXTM3U\n")
                for file_url in file_list:
                    f.write(f"{file_url}\n")
            
            log(f"Created/updated playlist with multiple files: {playlist_path}")
            return True
            
    except Exception as e:
        log(f"Error creating playlist: {e}", xbmc.LOGERROR)
        return False

def create_strm_from_list(media_files):
    """Maakt STRM-bestanden voor de opgegeven media-bestanden."""
    ensure_category_structure()  # Zorgt ervoor dat de mappenstructuur bestaat
    for media_file in media_files:
        category = categorize_file(media_file)
        if category:
            strm_file = os.path.join(translate_path(get_setting('streams_target_root')), category, os.path.basename(media_file) + '.strm')
            if not xbmcvfs.exists(strm_file):
                try:
                    with xbmcvfs.File(strm_file, 'w') as f:
                        f.write(media_file)
                    log(f"Created STRM file for {media_file} in category {category}")
                except Exception as e:
                    log(f"Failed to create STRM file for {media_file}: {e}", xbmc.LOGERROR)
            else:
                log(f"STRM file for {media_file} already exists.", xbmc.LOGINFO)

def categorize_file(media_file):
    """Bepaal de categorie voor een bestand op basis van naam of extensie."""
    filename = os.path.basename(media_file).lower()

    if any(keyword in filename for keyword in ['trailer', 'teaser']):
        return 'Trailers'
    elif any(keyword in filename for keyword in ['compilation', 'best of']):
        return 'Compilations'
    elif any(keyword in filename for keyword in ['music video', 'song']):
        return 'Music Videos'
    elif any(keyword in filename for keyword in ['short']):
        return 'Shorts'
    elif any(keyword in filename for keyword in ['adult']):
        for category_name in CATEGORY_NAMES:
            if 'adult' in category_name.lower(): # Find the "Adult" entry, ignoring case and color tags for the search
                return category_name
        return 'Adult' # Fallback, though it should find it in CATEGORY_NAMES
    else:
        return 'Filename Only'