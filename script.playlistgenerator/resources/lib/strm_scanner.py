import os
import xbmc
import xbmcvfs
from .strm_utils import log, parse_exclude_folders, is_valid_file, get_setting, translate_path
from .constants import CATEGORY_NAMES

def get_media_files():
    """Scant de opgegeven mappen en haalt alle geldige media-bestanden op."""
    media_files = []
    
    # Haal alle 5 mogelijke bronmappen op uit de instellingen
    source_roots = []
    for i in range(1, 6): # Voor set_source_root_1 t/m set_source_root_5
        setting_id = f'set_source_root_{i}'
        root_path = get_setting(setting_id)
        if root_path: # Voeg alleen niet-lege paden toe
            source_roots.append(translate_path(root_path))

    if not source_roots:
        log("No source folders configured in settings. Please check your add-on settings.", xbmc.LOGWARNING)
        return []

    excluded_folders = parse_exclude_folders()
    
    for root_path in source_roots:
        log(f"Scanning source folder: {root_path}", xbmc.LOGINFO)
        if not xbmcvfs.exists(root_path):
            log(f"Source folder does not exist or is not accessible: {root_path}", xbmc.LOGWARNING)
            continue

        recursive_scan = get_setting('recursive_scan', 'true') == 'true'
        scan_depth_limit = int(get_setting('scan_depth_limit', '3'))
        
        # Gebruik os.walk voor het doorlopen van mappen
        for dirpath, dirnames, filenames in os.walk(root_path):
            current_depth = dirpath[len(root_path):].count(os.sep)
            
            if scan_depth_limit > 0 and current_depth >= scan_depth_limit and recursive_scan:
                del dirnames[:] # Voorkom dieper scannen als limiet bereikt is
                continue

            # Filter excluded folders (dit moet gebeuren voordat we dirnames manipuleren voor recursie)
            dirnames[:] = [d for d in dirnames if not any(excluded_folder.lower() in d.lower() for excluded_folder in excluded_folders)]
            
            if any(excluded_folder.lower() in os.path.basename(dirpath).lower() for excluded_folder in excluded_folders):
                log(f"Excluding folder: {dirpath}", xbmc.LOGINFO)
                del dirnames[:] # Sla submappen van deze uitgesloten map over
                continue

            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                if is_valid_file(full_path): # is_valid_file controleert bestandsextensies
                    media_files.append(full_path)

    if media_files:
        log(f"Found {len(media_files)} media files across all configured source folders.")
    else:
        log("No media files found in any configured source folder.", xbmc.LOGINFO)
    
    return media_files