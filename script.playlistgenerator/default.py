import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import json
import random
import urllib.parse
from datetime import datetime
import re
import time
import sys
from functools import cmp_to_key

# Addon Setup
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PROFILE = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')
CONFIG_FILE = os.path.join(ADDON_PROFILE, 'playlist_sets.json')
PLAYLIST_DIR = xbmcvfs.translatePath('special://profile/playlists/video/')

def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] {msg}", level)

def get_setting(setting_id, default=''):
    return ADDON.getSetting(setting_id) or default

def set_setting(setting_id, value):
    ADDON.setSetting(setting_id, str(value))

def apply_set_settings(set_name):
    """Apply settings from a saved set to the addon settings"""
    sets = load_json(CONFIG_FILE) or {}
    if set_name not in sets or 'settings' not in sets[set_name]:
        return False
        
    settings = sets[set_name]['settings']
    for key, value in settings.items():
        set_setting(key, value)
    return True

def clean_display_name(path):
    try:
        decoded_path = urllib.parse.unquote(path)
        if any(path.startswith(p) for p in ('smb://', 'dav://', 'davs://', 'http://', 'nfs://')):
            basename = os.path.basename(decoded_path)
            return basename.split('?')[0]
        return os.path.basename(decoded_path)
    except:
        return os.path.basename(path)

def format_display_entry(filepath):
    name = os.path.splitext(clean_display_name(filepath))[0]
    
    if get_setting('show_metadata') == 'true':
        clean_name = urllib.parse.unquote(name)
        if year_match := re.search(r'\((\d{4})\)', clean_name):
            name += f" [COLOR gray]({year_match.group(1)})[/COLOR]"
        if res_match := re.search(r'(\d{3,4}[pP]|4[kK])', clean_name):
            name += f" [COLOR blue]{res_match.group(1)}[/COLOR]"
        if get_setting('show_duration') == 'true':
            duration = get_file_duration(filepath)
            if duration > 0:
                mins = duration // 60
                secs = duration % 60
                name += f" [COLOR yellow]{mins}:{secs:02d}[/COLOR]"
    
    if get_setting('show_folder_names') == 'true':
        folder = os.path.basename(os.path.dirname(filepath))
        folder = urllib.parse.unquote(folder)
        return f"[COLOR green]{folder}[/COLOR] {name}"
    return name

def get_file_duration(filepath):
    try:
        # Check if the file actually exists before trying to get duration
        if not xbmcvfs.exists(filepath):
            log(f"File does not exist, cannot get duration: {filepath}", xbmc.LOGWARNING)
            return 0
        
        # xbmc.Player().isPlaying() context is not relevant here.
        # We need to use ListItem and getInfoLabel for file properties.
        item = xbmcgui.ListItem(path=filepath)
        # getDuration() as a method on ListItem is deprecated or not directly providing int.
        # xbmc.getInfoLabel can extract information from various properties of an item.
        # The 'VideoPlayer.Duration' is typically used when a video is *playing*.
        # For a file's duration property, Kodi's internal info label for a ListItem should be used.
        # As per recent Kodi versions, ListItem.getMusicInfoTag().getDuration() for music
        # and ListItem.getVideoInfoTag().getDuration() for video are more direct, 
        # but often xbmc.getInfoLabel('ListItem.Duration') works universally if the item is set up correctly.
        # A simpler way for existing files is just to use ListItem.getDuration() which often returns a numeric string.
        
        # Try to get duration using ListItem.getDuration() directly (common for local files)
        duration_str = item.getDuration() 
        if duration_str and duration_str.isdigit(): # Check if it returns a numeric string
            return int(duration_str)
        
        # Fallback/alternative attempt if ListItem.getDuration() isn't reliable for all sources
        # (This is more complex and usually not needed if getDuration works for the ListItem object)
        # We assume ListItem.getDuration() is the intended and most direct way.
        
        return 0 # If duration could not be determined
    except Exception as e:
        log(f"Error getting duration for {filepath}: {e}", xbmc.LOGWARNING)
        return 0

def get_media_files(folder, depth=0):
    extensions = [ext.strip().lower() for ext in get_setting('file_extensions', '.mp4,.mkv,.avi,.mov,.wmv').split(',')]
    exclude = [word.strip().lower() for word in get_setting('exclude_pattern', 'sample,trailer').split(',') if word.strip()]
    exclude_folders = [f.strip().lower() for f in get_setting('exclude_folders', '').split(',') if f.strip()]
    min_size = int(get_setting('min_file_size', '50')) * 1024 * 1024
    max_size = int(get_setting('max_file_size', '0')) * 1024 * 1024 if get_setting('enable_max_size') == 'true' else 0
    files = []
    
    try:
        log(f"Scanning directory: {folder}")
        # xbmcvfs.listdir returns (dirs, files)
        dirs, filenames = xbmcvfs.listdir(folder)
        log(f"Found {len(dirs)} subdirectories and {len(filenames)} files in {folder}")
        
        # Filter excluded folders from the directory list
        dirs = [d for d in dirs if os.path.basename(d.rstrip(os.sep)).lower() not in exclude_folders]
        
        for filename in filenames:
            filepath = os.path.join(folder, filename)
            
            # Better handling for WebDAV and network paths
            is_directory = False
            # Skip directory check for known file extensions
            file_lower = filename.lower()
            if any(file_lower.endswith(ext) for ext in extensions):
                is_directory = False
            else:
                try:
                    # Try to list contents - if this works, it's a directory
                    test_dirs, test_files = xbmcvfs.listdir(filepath)
                    is_directory = True
                    log(f"Identified as directory: {filepath}")
                except:
                    # Not a directory or can't access
                    is_directory = False
            
            if is_directory:
                continue
            
            # Get file size using xbmcvfs.Stat().st_size()
            try:
                file_stat = xbmcvfs.Stat(filepath)
                file_size = file_stat.st_size()
                
                # Skip if file size is 0 (likely not a real file)
                if file_size == 0:
                    log(f"Skipping zero-size file: {filepath}")
                    continue
                    
            except Exception as stat_e:
                log(f"Could not get file size for {filepath}: {stat_e}", xbmc.LOGWARNING)
                file_size = 0
                if min_size > 0:
                    continue
            
            valid_ext = any(file_lower.endswith(ext) for ext in extensions)
            valid_exclude = not any(word in file_lower for word in exclude)
            valid_min_size = (min_size <= 0 or file_size >= min_size)
            valid_max_size = (max_size <= 0 or file_size <= max_size)
            
            if valid_ext and valid_exclude and valid_min_size and valid_max_size:
                log(f"Adding file: {filepath}")
                files.append(filepath)
            else:
                log(f"Skipping file (filters): {filepath} - ext:{valid_ext} excl:{valid_exclude} minsize:{valid_min_size} maxsize:{valid_max_size}")
        
        # Apply per-folder limit only if not recursive and not total limit mode
        if get_setting('limit_mode', '0') == '0' and get_setting('recursive_scan', 'true') == 'false':
            files = files[:int(get_setting('file_count', '20'))]
        
        # Recursive scan
        if get_setting('recursive_scan', 'true') == 'true' and depth < 8:
            for dir_name in dirs:
                dir_path = os.path.join(folder, dir_name)
                log(f"Recursively scanning: {dir_path}")
                files.extend(get_media_files(dir_path, depth + 1))
                
    except Exception as e:
        log(f"Scan error {folder}: {str(e)}", xbmc.LOGERROR)
        
    log(f"Total files found in {folder} and subdirs: {len(files)}")
    return files


def apply_sorting(files):
    """Apply all sorting rules to files"""
    log(f"Sorting {len(files)} files")
    if not files:
        log("No files to sort, returning empty list")
        return []
        
    try:
        # Group by folder first
        folder_groups = {}
        for file in files:
            folder = os.path.dirname(file)
            if folder not in folder_groups:
                folder_groups[folder] = []
            folder_groups[folder].append(file)
        
        log(f"Files grouped into {len(folder_groups)} folders")
        
        # Sort folders
        sorted_folders = sorted(folder_groups.keys(), key=get_folder_sort_key)
        
        # Sort files within folders
        result = []
        for folder in sorted_folders:
            folder_files = folder_groups[folder]
            sort_mode = get_setting('sort_mode', '0')
            
            try:
                if sort_mode == '1':  # A-Z
                    folder_files.sort(key=lambda x: x.lower())
                elif sort_mode == '2':  # Z-A
                    folder_files.sort(key=lambda x: x.lower(), reverse=True)
                elif sort_mode == '3':  # Random
                    random.shuffle(folder_files)
                elif sort_mode == '4':  # File Size (Smallest first)
                    folder_files.sort(key=lambda x: xbmcvfs.Stat(x).st_size())
                elif sort_mode == '5':  # File Size (Largest first)
                    folder_files.sort(key=lambda x: xbmcvfs.Stat(x).st_size(), reverse=True)
                elif sort_mode == '6':  # Duration (Shortest first)
                    folder_files.sort(key=lambda x: get_file_duration(x) or 0)  # Added or 0 to handle None
                elif sort_mode == '7':  # Duration (Longest first)
                    folder_files.sort(key=lambda x: get_file_duration(x) or 0, reverse=True)  # Added or 0
                else:  # Newest first (default)
                    # Safer sort with exception handling
                    def get_mtime_safe(path):
                        try:
                            return xbmcvfs.Stat(path).st_mtime()
                        except:
                            return 0
                    folder_files.sort(key=get_mtime_safe, reverse=True)
            except Exception as sort_e:
                log(f"Error sorting files in {folder}: {sort_e}", xbmc.LOGWARNING)
                # Fall back to simple alphabetical sort if sorting fails
                folder_files.sort(key=lambda x: x.lower())
            
            # Apply per-folder limit if enabled and recursive scan is off
            if get_setting('limit_mode', '0') == '0': # Per folder
                folder_files = folder_files[:int(get_setting('file_count', '20'))]

            result.extend(folder_files)
        
        # Apply newest files to top if enabled for the total list
        newest_count = int(get_setting('newest_files', '0'))
        if newest_count > 0:
            try:
                def get_mtime_safe(path):
                    try:
                        return xbmcvfs.Stat(path).st_mtime()
                    except:
                        return 0
                newest = sorted(result, key=get_mtime_safe, reverse=True)[:newest_count]
                remaining = [f for f in result if f not in newest]
                result = newest + remaining
            except Exception as newest_e:
                log(f"Error extracting newest files: {newest_e}", xbmc.LOGWARNING)
        
        log(f"Sorting complete, returning {len(result)} files")
        return result
    except Exception as e:
        log(f"Overall sorting error: {e}", xbmc.LOGERROR)
        return files  # Return original files on error


def create_playlist(folders=None, name=None, from_set=False):
    if folders is None:
        folders = select_folders()
        if not folders:
            return False
            
    if name is None:
        name = xbmcgui.Dialog().input("Enter Playlist Name:")
        if not name:
            return False

    log(f"Creating playlist '{name}' from {len(folders)} folders")
    
    progress = xbmcgui.DialogProgress()
    progress.create(ADDON_NAME, "Collecting media files...")
    
    all_files = []
    total_folders = len(folders)
    for i, folder in enumerate(folders):
        if progress.iscanceled():
            progress.close()
            return False
        progress.update(int(i * 100 / total_folders), f"Scanning {os.path.basename(folder)}...")
        log(f"Scanning folder: {folder}")
        
        # WebDAV specific handling
        if folder.startswith(('davs://', 'dav://')):
            log(f"WebDAV path detected: {folder}")
            # Ensure path ends with slash for WebDAV
            if not folder.endswith('/'):
                folder = folder + '/'
                log(f"Added trailing slash for WebDAV: {folder}")
        
        files = get_media_files(folder)
        log(f"Found {len(files)} files in {folder}")
        all_files.extend(files)
    
    log(f"Total files found before sorting/filtering: {len(all_files)}")
    
    if not all_files:
        progress.close()
        xbmcgui.Dialog().notification(ADDON_NAME, "No media files found", xbmcgui.NOTIFICATION_WARNING)
        return False
    
    # Apply all sorting rules
    progress.update(90, "Applying sorting...")
    all_files = apply_sorting(all_files)
    log(f"Files after sorting: {len(all_files)}")
    
    # Apply total limit if enabled
    if get_setting('limit_mode', '0') == '1': # Total files
        limit = int(get_setting('total_file_count', '100'))
        all_files = all_files[:limit]
        log(f"Applied total limit of {limit}, remaining files: {len(all_files)}")
    
    progress.update(95, "Creating playlist...")
    
    if not xbmcvfs.exists(PLAYLIST_DIR):
        xbmcvfs.mkdirs(PLAYLIST_DIR)
    
    playlist_path = os.path.join(PLAYLIST_DIR, f"{name}.m3u")
    log(f"Writing playlist to: {playlist_path}")
    
    # Create backup if enabled
    if get_setting('enable_backups', 'false') == 'true' and xbmcvfs.exists(playlist_path):
        create_backup(playlist_path)
    
    try:
        with xbmcvfs.File(playlist_path, 'w') as f:
            f.write("#EXTM3U\n")
            for file in all_files:
                try:
                    display_name = format_display_entry(file)
                    log(f"Adding file to playlist: {file}")
                    f.write(f"#EXTINF:-1,{display_name}\n")
                    f.write(f"{file}\n")
                except Exception as entry_e:
                    log(f"Error adding file to playlist: {file} - {entry_e}", xbmc.LOGWARNING)
                    # Write a simple entry if formatting fails
                    f.write(f"#EXTINF:-1,{os.path.basename(file)}\n")
                    f.write(f"{file}\n")
        
        log(f"Playlist created with {len(all_files)} entries")
        progress.close()
        
        # If not from a preset, ask to save as set
        if not from_set and xbmcgui.Dialog().yesno(ADDON_NAME, "Playlist created successfully. Save as folder set?"):
            save_folder_set(name, folders)
        else:
            xbmcgui.Dialog().notification(ADDON_NAME, f"Created playlist: {name} ({len(all_files)} items)", xbmcgui.NOTIFICATION_INFO)
        
        return True
    except Exception as e:
        progress.close()
        log(f"Playlist creation failed: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, "Failed to create playlist", xbmcgui.NOTIFICATION_ERROR)
        return False

def quick_scan():
    """Perform a quick scan of selected folders and show results."""
    dialog = xbmcgui.Dialog()
    folders = select_folders()
    if not folders:
        return
    
    # Show scanning notification
    xbmcgui.Dialog().notification(
        ADDON_NAME, 
        "Scanning folders...", 
        xbmcgui.NOTIFICATION_INFO,
        sound=False
    )
    
    total_files = 0
    for folder in folders:
        files = get_media_files(folder)
        total_files += len(files)
    
    # Show results
    dialog.notification(
        ADDON_NAME,
        f"Found {total_files} media files",
        xbmcgui.NOTIFICATION_INFO,
        5000  # Show for 5 seconds
    )

def get_folder_sort_key(folder_path):
    """Generate sort key based on folder sorting settings"""
    folder_mode = get_setting('folder_sort_mode', '0')
    custom_order = [f.strip().lower() for f in get_setting('custom_folder_order', '').split(',') if f.strip()]
    folder_name = os.path.basename(folder_path).lower()
    
    if folder_mode == '1':  # A-Z
        return (0, folder_name)
    elif folder_mode == '2':  # Z-A
        return (0, folder_name)
    elif folder_mode == '3' and custom_order:  # Custom
        try:
            return (custom_order.index(folder_name), folder_name)
        except ValueError:
            return (len(custom_order), folder_name)
    else:  # None
        return (0, folder_path)

def apply_sorting(files):
    """Apply all sorting rules to files"""
    # Group by folder first
    folder_groups = {}
    for file in files:
        folder = os.path.dirname(file)
        if folder not in folder_groups:
            folder_groups[folder] = []
        folder_groups[folder].append(file)
    
    # Sort folders
    sorted_folders = sorted(folder_groups.keys(), key=get_folder_sort_key)
    
    # Sort files within folders
    result = []
    for folder in sorted_folders:
        folder_files = folder_groups[folder]
        sort_mode = get_setting('sort_mode', '0')
        
        if sort_mode == '1':  # A-Z
            folder_files.sort(key=lambda x: x.lower())
        elif sort_mode == '2':  # Z-A
            folder_files.sort(key=lambda x: x.lower(), reverse=True)
        elif sort_mode == '3':  # Random
            random.shuffle(folder_files)
        elif sort_mode == '4':  # File Size (Smallest first)
            folder_files.sort(key=lambda x: xbmcvfs.Stat(x).st_size())
        elif sort_mode == '5':  # File Size (Largest first)
            folder_files.sort(key=lambda x: xbmcvfs.Stat(x).st_size(), reverse=True)
        elif sort_mode == '6':  # Duration (Shortest first)
            folder_files.sort(key=lambda x: get_file_duration(x))
        elif sort_mode == '7':  # Duration (Longest first)
            folder_files.sort(key=lambda x: get_file_duration(x), reverse=True)
        else:  # Newest first (default)
            folder_files.sort(key=lambda x: xbmcvfs.Stat(x).st_mtime(), reverse=True)
        
        # Apply per-folder limit if enabled and recursive scan is off
        if get_setting('limit_mode', '0') == '0': # Per folder
            folder_files = folder_files[:int(get_setting('file_count', '20'))]

        result.extend(folder_files)
    
    # Apply newest files to top if enabled for the total list
    newest_count = int(get_setting('newest_files', '0'))
    if newest_count > 0:
        newest = sorted(result, key=lambda x: xbmcvfs.Stat(x).st_mtime(), reverse=True)[:newest_count]
        remaining = [f for f in result if f not in newest]
        result = newest + remaining
    
    return result

def select_folders():
    dialog = xbmcgui.Dialog()
    folders = []
    path = xbmcvfs.translatePath('special://video/')
    
    folder = dialog.browse(0, "Select First Folder (Cancel to abort)", 'files', defaultt=path)
    if not folder:
        return None
        
    folders.append(folder)
    
    while dialog.yesno(ADDON_NAME, "Add another folder?", no            pass
