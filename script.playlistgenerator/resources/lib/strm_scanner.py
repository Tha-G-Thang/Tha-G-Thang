import os
import xbmc
import xbmcvfs
from .strm_utils import log, is_valid_file, get_setting, translate_path
from .constants import CATEGORY_NAMES # Deze is niet direct nodig in deze functie, maar kan blijven staan

def get_media_files():
    """Scant de opgegeven mappen en haalt alle geldige media-bestanden op, met pad-specifieke uitsluitingsregels."""
    media_files = []
    
    # Haal alle 5 mogelijke bronmappen op uit de instellingen
    source_configs = []
    for i in range(1, 6): # Voor set_source_root_1 t/m set_source_root_5
        root_path_setting_id = f'set_source_root_{i}'
        exclude_folders_setting_id = f'set_exclude_folders_{i}'
        
        root_path = get_setting(root_path_setting_id)
        if root_path: # Voeg alleen niet-lege paden toe
            translated_root_path = translate_path(root_path)
            raw_excluded_folders = get_setting(exclude_folders_setting_id, '')
            
            # Converteer de comma-separated string naar een lijst van schone, lowercase namen
            # Filter ook lege strings die kunnen ontstaan door dubbele komma's
            specific_excluded_folders = [f.strip().lower() for f in raw_excluded_folders.split(',') if f.strip()]
            
            source_configs.append({
                'root_path': translated_root_path,
                'excluded_folders': specific_excluded_folders
            })

    if not source_configs:
        log("No source folders configured in settings. Please check your add-on settings.", xbmc.LOGWARNING)
        return []

    for config in source_configs:
        root_path = config['root_path']
        excluded_folders = config['excluded_folders']
        
        log(f"Scanning source folder: {root_path} with exclusions: {excluded_folders}", xbmc.LOGINFO)
        if not xbmcvfs.exists(root_path):
            log(f"Source folder does not exist or is not accessible: {root_path}", xbmc.LOGWARNING)
            continue

        recursive_scan = get_setting('recursive_scan', 'true') == 'true'
        scan_depth_limit = int(get_setting('scan_depth_limit', '3'))
        exclude_hidden_files = get_setting('exclude_hidden_files', 'true') == 'true'
        
        # Gebruik os.walk voor het doorlopen van mappen
        for dirpath, dirnames, filenames in os.walk(root_path):
            current_depth = dirpath[len(root_path):].count(os.sep)
            
            if scan_depth_limit > 0 and current_depth >= scan_depth_limit and recursive_scan:
                del dirnames[:] # Voorkom dieper scannen als limiet bereikt is
                continue

            # Filter hidden folders and excluded folders for recursion
            dirnames_to_keep = []
            for dname in dirnames:
                if exclude_hidden_files and dname.startswith('.'):
                    log(f"Excluding hidden folder: {os.path.join(dirpath, dname)}", xbmc.LOGINFO)
                    continue
                if dname.lower() in excluded_folders: # Controleer of deze map volledig moet worden overgeslagen
                    log(f"Excluding subfolder and its contents: {os.path.join(dirpath, dname)}", xbmc.LOGINFO)
                else:
                    dirnames_to_keep.append(dname)
            dirnames[:] = dirnames_to_keep # Update dirnames in-place voor os.walk

            # Controleer of de *huidige* map (dirpath) zelf uitgesloten is
            # Dit is voor het geval een pad in de uitsluitingslijst een map is die je al scant
            current_folder_name = os.path.basename(dirpath).lower()
            if current_folder_name in excluded_folders and dirpath != root_path: # Voorkom dat de root zelf wordt uitgesloten als deze toevallig dezelfde naam heeft als een uitgesloten map
                 log(f"Excluding current folder: {dirpath}", xbmc.LOGINFO)
                 continue # Sla alle bestanden in deze map over en ga naar de volgende

            for fname in filenames:
                if exclude_hidden_files and fname.startswith('.'):
                    log(f"Excluding hidden file: {os.path.join(dirpath, fname)}", xbmc.LOGINFO)
                    continue
                full_path = os.path.join(dirpath, fname)
                if is_valid_file(full_path): # is_valid_file controleert bestandsextensies en grootte
                    media_files.append(full_path)

    if media_files:
        log(f"Found {len(media_files)} media files across all configured source folders.")
    else:
        log("No media files found in any configured source folder.", xbmc.LOGINFO)
    
    return media_files