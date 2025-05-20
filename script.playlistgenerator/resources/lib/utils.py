import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import json
import urllib.parse
import sys
import os
import re
from datetime import datetime
from typing import Any, List, Dict, Tuple, Optional # Added Optional here

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))

CONFIG_FILE = os.path.join(ADDON_PROFILE, 'settings.json')
PLAYLIST_DIR = os.path.join(ADDON_PROFILE, 'playlists')
SETS_DIR = os.path.join(ADDON_PROFILE, 'sets') # New directory for sets

# Ensure profile, playlists, and sets directories exist on addon import
if not xbmcvfs.exists(ADDON_PROFILE):
    xbmcvfs.mkdirs(ADDON_PROFILE)
if not xbmcvfs.exists(PLAYLIST_DIR):
    xbmcvfs.mkdirs(PLAYLIST_DIR)
if not xbmcvfs.exists(SETS_DIR): # Ensure sets directory exists
    xbmcvfs.mkdirs(SETS_DIR)

DIALOG = xbmcgui.Dialog()

def log(msg: str, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_NAME}] {msg}", level)

def show_notification(heading: str, message: str, time: int = 3000, icon: str = ADDON.getAddonInfo('icon')):
    DIALOG.notification(heading, message, icon, time)

def show_ok_dialog(heading: str, message: str):
    DIALOG.ok(heading, message)

def get_setting(setting_id: str, setting_type: str = 'text') -> Any:
    """
    Retrieves an addon setting and attempts to convert it to the specified type.
    Handles various setting types and provides default values if conversion fails.
    """
    value_str = ADDON.getSetting(setting_id)
    
    if setting_type == 'bool':
        return value_str.lower() == 'true'
    elif setting_type == 'number':
        try:
            return int(value_str)
        except ValueError:
            return 0 # Default for numbers
    elif setting_type == 'float':
        try:
            return float(value_str)
        except ValueError:
            return 0.0 # Default for floats
    elif setting_type == 'enum':
        try:
            return int(value_str) # Enums are stored as integers
        except ValueError:
            return 0 # Default for enums
    elif setting_type == 'folder':
        # xbmcvfs.translatePath is good for system paths, getSetting returns raw paths
        return value_str
    elif setting_type == 'date':
        # Date is returned as 'YYYY-MM-DD' string
        return value_str
    elif setting_type == 'color':
        # Color is returned as AARRGGBB string
        return value_str
    else: # 'text' or any other unhandled type
        return value_str

def set_setting(setting_id: str, value: Any):
    """Sets an addon setting."""
    ADDON.setSetting(setting_id, str(value)) # Settings API expects string

def load_json(file_path: str) -> Dict[str, Any]:
    try:
        if xbmcvfs.exists(file_path):
            with xbmcvfs.File(file_path, 'r') as f:
                content = f.read()
                if content:
                    return json.loads(content)
        return {}
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log(f"Error loading JSON from {file_path}: {e}", xbmc.LOGERROR)
        return {}
    except Exception as e:
        log(f"Unexpected error in load_json for {file_path}: {e}", xbmc.LOGERROR)
        return {}

def save_json(file_path: str, data: Dict[str, Any]):
    try:
        # Ensure parent directory exists for the file
        parent_dir = os.path.dirname(file_path)
        if not xbmcvfs.exists(parent_dir):
            xbmcvfs.mkdirs(parent_dir)

        with xbmcvfs.File(file_path, 'w') as f:
            f.write(json.dumps(data, indent=4))
    except IOError as e:
        log(f"Error saving JSON to {file_path}: {e}", xbmc.LOGERROR)
    except Exception as e:
        log(f"Unexpected error in save_json for {file_path}: {e}", xbmc.LOGERROR)


def parse_url(url: str) -> Dict[str, str]:
    args = {}
    if '?' in url:
        query_string = url.split('?', 1)[1]
        if query_string.startswith('&'): # Handle cases like "?&action=foo"
            query_string = query_string[1:]
        parsed_q = urllib.parse.parse_qs(query_string)
        for key, value_list in parsed_q.items():
            if value_list:
                args[key] = value_list[0]
    return args

def build_url(query: Dict[str, str], handle: Optional[int] = None) -> str:
    base_url = sys.argv[0]

    if handle is None:
        try:
            # sys.argv[1] is the handle if it's a context menu or similar call
            handle = int(sys.argv[1])
        except (IndexError, ValueError):
            handle = 0 # Default handle if not provided
            log(f"Warning: build_url called without explicit handle and sys.argv[1] is missing/invalid. Using 0. sys.argv: {sys.argv}", xbmc.LOGWARNING)

    encoded_query = urllib.parse.urlencode(query)
    full_url = f"{base_url}?{handle}&{encoded_query}"
    log(f"Building URL: {full_url}", xbmc.LOGDEBUG)
    return full_url

def get_video_files_in_directory(
    path: str,
    file_extensions: List[str],
    min_file_size_mb: int,
    exclude_pattern: str,
    scan_depth: int,
    current_depth: int = 0
) -> List[Dict[str, Any]]:
    """
    Recursively collects video files from a directory based on filters.
    Returns a list of dictionaries, each containing file_path, size, and ctime.
    """
    found_files = []
    
    # Compile regex pattern for exclusion if provided
    exclude_regex = None
    if exclude_pattern:
        try:
            exclude_regex = re.compile(exclude_pattern, re.IGNORECASE)
        except re.error as e:
            log(f"Invalid exclude regex pattern '{exclude_pattern}': {e}", xbmc.LOGERROR)
            exclude_regex = None

    try:
        if not xbmcvfs.exists(path):
            log(f"Path does not exist: {path}", xbmc.LOGWARNING)
            return []
        
        # List contents of the current directory
        # xbmcvfs.listdir returns (files, dirs) where files are filenames and dirs are dirnames
        dir_contents, _ = xbmcvfs.listdir(path) 

        # Separate files and directories
        files_in_current_dir = [os.path.join(path, f) for f in dir_contents if xbmcvfs.isfile(os.path.join(path, f))]
        dirs_in_current_dir = [os.path.join(path, d) for d in dir_contents if xbmcvfs.isdir(os.path.join(path, d))]

        for file_path in files_in_current_dir:
            file_name = os.path.basename(file_path)

            # Check file extension
            if not any(file_name.lower().endswith(ext) for ext in file_extensions):
                continue

            # Check exclude pattern
            if exclude_regex and exclude_regex.search(file_name):
                log(f"Excluding file by pattern: {file_name}", xbmc.LOGDEBUG)
                continue

            # Get file stats for size and ctime
            try:
                stat = xbmcvfs.Stat(file_path)
                file_size_bytes = stat.st_size()
                file_ctime = stat.st_ctime() # Creation time (timestamp)
                
                # Check minimum file size
                if file_size_bytes < min_file_size_mb * 1024 * 1024:
                    log(f"Excluding file by size (too small): {file_name} ({file_size_bytes / (1024*1024):.2f}MB)", xbmc.LOGDEBUG)
                    continue

                found_files.append({
                    'path': file_path,
                    'size': file_size_bytes,
                    'ctime': file_ctime
                })
            except Exception as stat_e:
                log(f"Error getting stat for {file_path}: {stat_e}", xbmc.LOGWARNING)
                continue

        # Recurse into subdirectories if recursive is true and depth limit not reached
        if scan_depth == -1 or current_depth < scan_depth: # -1 means unlimited depth
            for sub_dir_path in dirs_in_current_dir:
                found_files.extend(get_video_files_in_directory(
                    sub_dir_path,
                    file_extensions,
                    min_file_size_mb,
                    exclude_pattern,
                    scan_depth,
                    current_depth + 1
                ))

    except Exception as e:
        log(f"Error collecting files in {path}: {e}", xbmc.LOGERROR)
    
    return found_files

def get_base_dir_from_path(file_path: str, levels_up: int = 1) -> str:
    """
    Gets the base directory name from a file path, going up 'levels_up' directories.
    e.g., /path/to/folder/file.mp4, levels_up=0 -> folder
          /path/to/folder/file.mp4, levels_up=1 -> to
    """
    current_path = os.path.dirname(file_path)
    for _ in range(levels_up):
        current_path = os.path.dirname(current_path)
    return os.path.basename(current_path)