import os
import xbmc
import xbmcaddon
import xbmcvfs
import json
from .constants import ADDON_ID, CONFIG_FILE

addon = xbmcaddon.Addon(ADDON_ID)
log_prefix = f"[{ADDON_ID}]"

ADDON_PROFILE = xbmcvfs.translatePath(addon.getAddonInfo('profile'))

def log(message, level=xbmc.LOGNOTICE):
    xbmc.log(f"{log_prefix} {message}", level)

def get_setting(id, default=None):
    return addon.getSetting(id) or default

def translate_path(path):
    """Translates a special path (like special://) to a system path."""
    return xbmcvfs.translatePath(path)

def is_valid_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    allowed_extensions_str = get_setting('file_extensions', '.mp4,.mkv,.avi,.mov,.wmv')
    allowed_extensions = [e.strip() for e in allowed_extensions_str.split(',') if e.strip()]
    
    if ext not in allowed_extensions:
        return False

    # Check minimum file size
    min_size_mb = float(get_setting('min_file_size', '50'))
    if min_size_mb > 0:
        file_size_bytes = xbmcvfs.size(filename)
        if file_size_bytes == -1: # -1 indicates file not found or inaccessible by xbmcvfs.size
            log(f"Warning: Could not get size for file: {filename}. Skipping size check.", xbmc.LOGWARNING)
            # Decide if you want to include or exclude if size cannot be determined.
            # For now, let's assume it's invalid if size can't be checked for min_size > 0
            return False 
        if file_size_bytes < min_size_mb * 1024 * 1024:
            log(f"Excluding {filename} (size {file_size_bytes / (1024 * 1024):.2f} MB below min {min_size_mb} MB)", xbmc.LOGINFO)
            return False

    # Check maximum file size (if enabled)
    if get_setting('enable_max_size', 'false') == 'true':
        max_size_mb = float(get_setting('max_file_size', '0'))
        if max_size_mb > 0:
            file_size_bytes = xbmcvfs.size(filename)
            if file_size_bytes == -1: # Same check as above
                log(f"Warning: Could not get size for file: {filename}. Skipping max size check.", xbmc.LOGWARNING)
                return False
            if file_size_bytes > max_size_mb * 1024 * 1024:
                log(f"Excluding {filename} (size {file_size_bytes / (1024 * 1024):.2f} MB above max {max_size_mb} MB)", xbmc.LOGINFO)
                return False

    # Check exclude pattern in filename (e.g., "sample", "trailer")
    exclude_pattern_str = get_setting('exclude_pattern', 'sample,trailer')
    exclude_patterns = [p.strip().lower() for p in exclude_pattern_str.split(',') if p.strip()]
    
    file_name_lower = os.path.basename(filename).lower()
    if any(pattern in file_name_lower for pattern in exclude_patterns):
        log(f"Excluding {filename} (matches exclude pattern)", xbmc.LOGINFO)
        return False

    # Check date filter (if enabled)
    if get_setting('enable_date_filter', 'false') == 'true':
        try:
            file_stat = xbmcvfs.stat(filename)
            file_mtime = file_stat['st_mtime'] # Modification time
            
            min_date_str = get_setting('min_file_date', '2000-01-01')
            max_date_str = get_setting('max_file_date', '2100-01-01')

            from datetime import datetime
            min_timestamp = datetime.strptime(min_date_str, '%Y-%m-%d').timestamp()
            max_timestamp = datetime.strptime(max_date_str, '%Y-%m-%d').timestamp()

            if not (min_timestamp <= file_mtime <= max_timestamp):
                log(f"Excluding {filename} (modification date outside range)", xbmc.LOGINFO)
                return False
        except Exception as e:
            log(f"Error checking file date for {filename}: {e}", xbmc.LOGWARNING)
            # If date check fails, decide whether to include or exclude. Default to exclude for safety.
            return False

    return True

def clean_display_name(filename_or_url):
    """
    Extracts the base filename without extension from a path or URL.
    This function currently does NOT apply any cleaning rules (like removing words or regex).
    Full cleaning logic will be handled later, potentially for metadata display.
    """
    # Handles both local paths and URLs
    if "://" in filename_or_url: # Likely a URL
        base_name = filename_or_url.split('/')[-1].split('?')[0] # Get last part, remove query params
    else: # Likely a local path
        base_name = os.path.basename(filename_or_url)
    
    name_without_extension = os.path.splitext(base_name)[0]
    return name_without_extension.strip()

def load_sets():
    config_path = os.path.join(ADDON_PROFILE, CONFIG_FILE)
    log(f"Loading sets from: {config_path}")
    if xbmcvfs.exists(config_path):
        try:
            f = xbmcvfs.File(config_path, 'r')
            content = f.read()
            f.close()
            if content:
                try:
                    sets_data = json.loads(content)
                    log("Sets loaded successfully.")
                    return sets_data
                except (json.JSONDecodeError, TypeError) as e:
                    log(f"Error decoding JSON from {config_path}: {e}")
                    return {}
            else:
                log(f"Config file {config_path} is empty.")
                return {}
        except Exception as e:
            log(f"Error reading config file {config_path}: {e}")
            return {}
    else:
        log(f"Config file not found: {config_path}")
        return {}

def save_sets(sets_data):
    config_path = os.path.join(ADDON_PROFILE, CONFIG_FILE)
    log(f"Saving sets to: {config_path}")
    try:
        if not xbmcvfs.exists(ADDON_PROFILE):
            if not xbmcvfs.mkdirs(ADDON_PROFILE):
                log(f"Error creating directory: {ADDON_PROFILE}")
                return False
        
        f = xbmcvfs.File(config_path, 'w')
        json_data = json.dumps(sets_data, indent=4)
        f.write(json_data)
        f.close()
        log("Sets saved successfully.")
        return True
    except Exception as e:
        log(f"Error saving sets to {config_path}: {e}", xbmc.LOGERROR)
        return False