import os
import xbmc
import xbmcaddon
import xbmcvfs
import json
from .constants import ADDON_ID, CONFIG_FILE

addon = xbmcaddon.Addon(ADDON_ID)
log_prefix = f"[{ADDON_ID}]"

ADDON_PROFILE = xbmcvfs.translatePath(addon.getAddonInfo('profile'))

def log(message, level=xbmc.LOGINFO):
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

    min_size_mb = float(get_setting('min_file_size', '50'))
    max_size_mb = float(get_setting('max_file_size', '0'))
    enable_max_size = get_setting('enable_max_size', 'false') == 'true'

    file_size_bytes = -1 # Default value

    try:
        file_size_bytes = xbmcvfs.size(filename)
    except AttributeError:
        # This should ideally not happen on Kodi 21.2. If it does, there's a deeper environment issue.
        log(f"CRITICAL WARNING: xbmcvfs.size is not available on this Kodi version for {filename}. Size checks will be skipped.", xbmc.LOGERROR)
        # If min_size is set and we can't get size, we must exclude to be safe.
        if min_size_mb > 0:
            log(f"Excluding {filename} (cannot determine size for min_size_mb check due to missing xbmcvfs.size).", xbmc.LOGINFO)
            return False
        file_size_bytes = 0 # Assume 0 size to pass max_size_mb if not strict min_size or if it can't be checked

    if file_size_bytes == -1: # xbmcvfs.size returns -1 if file doesn't exist or is inaccessible
        log(f"Warning: File {filename} not found or inaccessible via xbmcvfs.size(). Skipping size check.", xbmc.LOGWARNING)
        if min_size_mb > 0: # If min_size is required, and we can't get size, exclude
            log(f"Excluding {filename} (inaccessible for min_size_mb check).", xbmc.LOGINFO)
            return False
        # If size is -1 but min_size is 0, let it pass and continue with other checks
        file_size_bytes = 0 # Assume 0 size to pass max_size_mb if not strict min_size

    if min_size_mb > 0 and file_size_bytes < min_size_mb * 1024 * 1024:
        log(f"Excluding {filename} (size {file_size_bytes / (1024 * 1024):.2f} MB below min {min_size_mb} MB)", xbmc.LOGINFO)
        return False

    if enable_max_size and max_size_mb > 0 and file_size_bytes > max_size_mb * 1024 * 1024:
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
        except AttributeError:
            # This should also ideally not happen on Kodi 21.2.
            log(f"CRITICAL WARNING: xbmcvfs.stat is not available on this Kodi version for {filename}. Date checks will be skipped.", xbmc.LOGERROR)
            return True # If stat fails, assume valid for date purposes to not block other checks
        except Exception as e:
            log(f"Error checking file date for {filename}: {e}", xbmc.LOGWARNING)
            return True # If other date check fails, assume valid for date purposes to not block other checks

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
