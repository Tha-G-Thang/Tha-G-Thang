import os
import urllib.parse
from resources.lib.core.base_utils import get_setting, log, get_file_duration
import xbmc
import xbmcvfs # Nodig voor mtime

def get_folder_sort_key(folder_path):
    # This function is used to sort folders based on custom settings.
    # It assumes the folder name is the last part of the path.
    folder_name = os.path.basename(urllib.parse.unquote(folder_path)).lower()
    return folder_name

def sort_files_for_playlist(files):
    """
    Applies sorting and 'new_to_top' logic to a list of file paths.
    This function processes files *within* a folder or a concatenated list if no folder sorting is applied beforehand.
    """
    file_sort_order = get_setting('file_sort_order_within_folders', '0') # 0: None, 1: Newest First, 2: Oldest First, 3: A-Z, 4: Z-A, 5: Duration Longest, 6: Duration Shortest
    
    # 1. Pas de primaire bestandssortering toe
    if file_sort_order == '1': # Newest First (gebaseerd op modificatietijd)
        log("Applying file sort: Newest First.", xbmc.LOGINFO)
        files.sort(key=lambda x: xbmcvfs.File(x).mtime() if xbmcvfs.exists(x) else 0, reverse=True)
    elif file_sort_order == '2': # Oldest First (gebaseerd op modificatietijd)
        log("Applying file sort: Oldest First.", xbmc.LOGINFO)
        files.sort(key=lambda x: xbmcvfs.File(x).mtime() if xbmcvfs.exists(x) else 0)
    elif file_sort_order == '3': # A-Z (Filename)
        log("Applying file sort: A-Z (Filename).", xbmc.LOGINFO)
        files.sort(key=lambda x: os.path.basename(x).lower())
    elif file_sort_order == '4': # Z-A (Filename)
        log("Applying file sort: Z-A (Filename).", xbmc.LOGINFO)
        files.sort(key=lambda x: os.path.basename(x).lower(), reverse=True)
    elif file_sort_order == '5': # Duration (Longest First)
        log("Applying file sort: Duration (Longest First).", xbmc.LOGINFO)
        try:
            files.sort(key=get_file_duration, reverse=True)
        except Exception as e:
            log(f"Error applying duration sort: {e}", xbmc.LOGERROR)
    elif file_sort_order == '6': # Duration (Shortest First)
        log("Applying file sort: Duration (Shortest First).", xbmc.LOGINFO)
        try:
            files.sort(key=get_file_duration)
        except Exception as e:
            log(f"Error applying duration sort: {e}", xbmc.LOGERROR)
    # Als file_sort_order == '0' (None), blijft de volgorde zoals hij is (vaak filesystem-order)

    # 2. Pas 'Newest to Top' logica toe, indien ingeschakeld
    new_to_top_enabled = get_setting('new_to_top', 'false') == 'true'
    if new_to_top_enabled:
        new_to_top_count = int(get_setting('new_to_top_count', '2'))
        if new_to_top_count > 0:
            log(f"Applying 'Newest {new_to_top_count} to Top' logic.", xbmc.LOGINFO)
            
            # Sorteer de bestanden op modificatietijd om de 'nieuwste' te vinden
            temp_files_sorted_by_mtime = sorted(files, key=lambda x: xbmcvfs.File(x).mtime() if xbmcvfs.exists(x) else 0, reverse=True)
            
            newest_files = temp_files_sorted_by_mtime[:new_to_top_count]
            remaining_files = [f for f in files if f not in newest_files] # Behoud originele volgorde voor de rest

            # Combineer: nieuwste bestanden bovenaan, gevolgd door de rest
            files = newest_files + remaining_files
            log(f"Newest {len(newest_files)} files moved to top.", xbmc.LOGINFO)

    return files