import os
import xbmc
import xbmcvfs
import json # Zorg dat deze import aanwezig is

from .strm_utils import log, translate_path, is_valid_file, get_setting # get_setting toegevoegd
from .strm_structure import ensure_category_structure
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
            # Voeg #EXTM3U toe als het een nieuw bestand is of als we overschrijven
            if mode == 'w' or not xbmcvfs.exists(playlist_path): # Check again for new file if mode was 'a' but file didn't exist
                f.write("#EXTM3U\\n")
            
            for file_url in file_list:
                f.write(f"{file_url}\\n")
        
        log(f"Created/updated playlist: {playlist_path}")
        return True
    except Exception as e:
        log(f"Failed to create or update playlist {playlist_name}: {e}", xbmc.LOGERROR)
        return False

def create_strm_from_list(media_files):
    """Genereert .strm bestanden voor de gegeven lijst van mediabestanden."""
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

    # Speciale categorieën op basis van trefwoorden in de bestandsnaam
    if any(keyword in filename for keyword in ['youtube.com', 'youtu.be']):
        return 'Youtube Clips'
    elif any(keyword in filename for keyword in ['trailer', 'teaser']):
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
    
    # Gedrag voor niet-gematchte bestanden
    default_behavior = get_setting('default_category_behavior', '1') # 0: parent folder, 1: Filename Only, 2: _

    if default_behavior == '0': # Categorize by Parent Folder Name
        parent_folder = os.path.basename(os.path.dirname(media_file))
        if parent_folder:
            # Controleer of de parent_folder overeenkomt met een van de CATEGORY_NAMES
            # Dit moet robuuster zijn, aangezien CATEGORY_NAMES kleurcodes kan bevatten
            for cat_name in CATEGORY_NAMES:
                # Vergelijk lowercase en zonder kleurcodes
                # xbmc.getCleanMovieTitle is een optie, maar niet altijd perfect
                cleaned_cat_name = xbmc.getCleanMovieTitle(cat_name).lower() if hasattr(xbmc, 'getCleanMovieTitle') else cat_name.lower().replace('[color black]', '').replace('[color gold]', '')
                if parent_folder.lower() == cleaned_cat_name:
                    return cat_name
            # Als het niet matcht met een vaste categorie, return dan de mapnaam zelf
            return parent_folder
        else:
            return 'Filename Only' # Of een andere fallback als geen parent map
    elif any(keyword in filename for keyword in ['adult']):
        for category_name in CATEGORY_NAMES:
            if 'adult' in category_name.lower(): # Find the "Adult" entry, ignoring case and color tags for the search
                return category_name
        return 'Adult' # Fallback, though it should find it in CATEGORY_NAMES
    else:
        # Check if "Filename Only" is a valid category or if a default exists
        if 'Filename Only' in CATEGORY_NAMES: # Ensure 'Filename Only' is a defined category
            return 'Filename Only'
        else:
            return '_' # Fallback to a generic folder if 'Filename Only' is not used