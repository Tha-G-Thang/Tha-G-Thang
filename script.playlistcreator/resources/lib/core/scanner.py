import xbmc
import xbmcvfs
import os
from resources.lib.core.base_utils import log, get_setting

def get_media_files(folder, depth=0, max_depth=8):
    file_extensions = [ext.strip().lower() for ext in get_setting('file_extensions', '.mp4,.mkv,.avi,.mov,.wmv').split(',')]
    exclude_patterns = [p.strip().lower() for p in get_setting('exclude_pattern', 'sample').split(',')]
    exclude_folders = [f.strip().lower() for f in get_setting('exclude_folders', 'XTRA').split(',')]
    min_file_size = int(get_setting('min_file_size', '1')) * 1024 * 1024
    enable_max_size = get_setting('enable_max_size', 'false') == 'true'
    max_file_size = int(get_setting('max_file_size', '0')) * 1024 * 1024 if enable_max_size else 0

    log(f"Scanning folder: {folder} at depth {depth}")
    files = []
    dirs, contents = xbmcvfs.listdir(folder)
    
    contents = [c for c in contents if not c.startswith('.')]

    for item in contents:
        full_path = xbmcvfs.translatePath(os.path.join(folder, item))
        if xbmcvfs.File(full_path).exists() and not xbmcvfs.validatePath(full_path):
            log(f"Invalid path encountered, skipping: {full_path}", xbmc.LOGWARNING)
            continue
            
        if xbmcvfs.isdir(full_path):
            folder_name = os.path.basename(full_path).lower()
            if folder_name in exclude_folders:
                log(f"Excluding folder: {full_path}", xbmc.LOGINFO)
                continue
            if get_setting('recursive_scan', 'true') == 'true' and depth < max_depth:
                files.extend(get_media_files(full_path, depth + 1, max_depth))
        else:
            filename, file_extension = os.path.splitext(item)
            file_extension = file_extension.lower()

            if file_extension not in file_extensions:
                continue

            file_size = xbmcvfs.File(full_path).size()
            if file_size < min_file_size:
                continue
            if enable_max_size and max_file_size > 0 and file_size > max_file_size:
                continue

            if any(p in filename.lower() for p in exclude_patterns if p):
                log(f"Excluding file due to pattern: {full_path}", xbmc.LOGINFO)
                continue

            files.append(full_path)
    return files