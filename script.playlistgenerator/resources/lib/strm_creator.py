import os
import xbmc
import xbmcvfs
import json

from .strm_utils import log, translate_path, get_setting
from .strm_structure import ensure_category_structure # Keep this for category management
from .constants import CATEGORY_NAMES

def create_playlist(file_list, playlist_name, is_single_file_mode=False):
    """
    Create a playlist from a list of files.
    When is_single_file_mode is True, it appends to an existing playlist or creates a new one.
    Otherwise, it overwrites an existing playlist or creates a new one from the list.
    """
    try:
        playlist_path = xbmcvfs.translatePath(f'special://profile/playlists/video/{playlist_name}.m3u')
        
        # Ensure directory exists
        playlist_dir = os.path.dirname(playlist_path)
        if not xbmcvfs.exists(playlist_dir):
            xbmcvfs.mkdirs(playlist_dir)
        
        mode = 'a' if is_single_file_mode and xbmcvfs.exists(playlist_path) else 'w'
        
        with xbmcvfs.File(playlist_path, mode) as f:
            # Add #EXTM3U if it's a new file or if we're overwriting
            if mode == 'w' or not xbmcvfs.exists(playlist_path):
                f.write("#EXTM3U\n")
            
            for file_path in file_list:
                # For playlists, we simply write the path to the STRM file.
                # The display name will be handled by Kodi's scraper if an NFO is present,
                # or will default to the STRM filename.
                f.write(f"{file_path}\n")
        
        log(f"Playlist '{playlist_name}' created/updated successfully at {playlist_path}", xbmc.LOGINFO)
        return True
    except Exception as e:
        log(f"Failed to create/update playlist '{playlist_name}': {e}", xbmc.LOGERROR)
        return False

def get_category_for_file(filename):
    """
    Determines the category folder based on addon settings or file path.
    """
    use_parent_folder_as_category = get_setting('use_parent_folder_as_category', 'false') == 'true'

    if use_parent_folder_as_category:
        parent_folder = os.path.basename(os.path.dirname(filename))
        if parent_folder:
            # Check if the parent_folder matches any of the CATEGORY_NAMES
            for cat_name in CATEGORY_NAMES:
                # Compare lowercase and without color codes for a robust match
                # xbmc.getCleanMovieTitle is not suitable here for exact string comparison
                # We'll just compare cleaned up versions
                clean_cat_name = cat_name.lower().replace('[color black]', '').replace('[color gold]', '')
                if parent_folder.lower() == clean_cat_name:
                    return cat_name
            # If it doesn't match a fixed category, return the folder name itself
            return parent_folder
        else:
            # Fallback if no parent folder (e.g., file directly in root of source)
            # Or if "Filename Only" is configured as a fallback
            if 'Filename Only' in CATEGORY_NAMES:
                return 'Filename Only'
            else:
                return '_' # Generic fallback
    else:
        # Default behavior if not using parent folder as category
        if 'Filename Only' in CATEGORY_NAMES:
            return 'Filename Only'
        else:
            return '_' # Fallback to a generic folder if 'Filename Only' is not used

def create_strm_from_list(media_files):
    """
    Creates STRM files for each media file in the list.
    The STRM files are now named using the original base filename.
    """
    if not media_files:
        log("No media files provided to create STRM links.", xbmc.LOGINFO)
        return False

    strm_output_root = translate_path(get_setting('streams_target_root'))
    strm_file_extension = get_setting('strm_file_extension', '.strm')

    if not xbmcvfs.exists(strm_output_root):
        if not xbmcvfs.mkdirs(strm_output_root):
            log(f"Failed to create output folder: {strm_output_root}", xbmc.LOGERROR)
            return False

    # Ensure category structure exists if `use_parent_folder_as_category` is enabled
    # We call this here to ensure all potential category folders are ready.
    ensure_category_structure()

    successful_creations = 0
    for media_file in media_files:
        try:
            # Get the category path for the STRM file
            category_name = get_category_for_file(media_file)
            strm_target_dir = os.path.join(strm_output_root, category_name)
            
            if not xbmcvfs.exists(strm_target_dir):
                if not xbmcvfs.mkdirs(strm_target_dir):
                    log(f"Failed to create category folder: {strm_target_dir}", xbmc.LOGERROR)
                    continue # Skip this file if folder creation fails

            # Use original base filename for the .strm file
            strm_base_name = os.path.splitext(os.path.basename(media_file))[0]
            strm_file_path = os.path.join(strm_target_dir, f"{strm_base_name}{strm_file_extension}")

            # Write the original media file path (URL) into the .strm file
            with xbmcvfs.File(strm_file_path, 'w') as f:
                f.write(media_file) # Write the actual URL/path to the media file

            log(f"Created STRM: {strm_file_path} -> {media_file}", xbmc.LOGINFO)
            successful_creations += 1

        except Exception as e:
            log(f"Error creating STRM for {media_file}: {e}", xbmc.LOGERROR)
            continue

    if successful_creations > 0:
        log(f"Successfully created {successful_creations} STRM links.", xbmc.LOGINFO)
        return True
    else:
        log("No STRM links were successfully created.", xbmc.LOGWARNING)
        return False