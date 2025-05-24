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
    
    while dialog.yesno(ADDON_NAME, "Add another folder?", nolabel="No", yeslabel="Yes"):
        folder = dialog.browse(0, "Select Additional Folder", 'files', defaultt=path)
        if folder and folder not in folders:
            folders.append(folder)
        elif folder:
            dialog.notification(ADDON_NAME, "Folder already added", xbmcgui.NOTIFICATION_WARNING)
    
    return folders

def create_backup(playlist_path):
    backup_dir = os.path.join(PLAYLIST_DIR, "backups")
    if not xbmcvfs.exists(backup_dir):
        xbmcvfs.mkdirs(backup_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{os.path.basename(playlist_path)}.bak.{timestamp}"
    backup_path = os.path.join(backup_dir, backup_file)
    xbmcvfs.copy(playlist_path, backup_path)
    
    # Clean up old backups if needed
    max_backups = int(get_setting('max_backups', '3'))
    if max_backups > 0:
        try:
            _, files = xbmcvfs.listdir(backup_dir)
            base_name = os.path.basename(playlist_path)
            matching_backups = [f for f in files if f.startswith(f"{base_name}.bak.")]
            matching_backups.sort(reverse=True)  # Newest first
            
            for old_backup in matching_backups[max_backups:]:
                xbmcvfs.delete(os.path.join(backup_dir, old_backup))
        except Exception as e:
            log(f"Backup cleanup error: {str(e)}", xbmc.LOGERROR)

def create_playlist(folders=None, name=None, from_set=False):
    if folders is None:
        folders = select_folders()
        if not folders:
            return False
            
    if name is None:
        name = xbmcgui.Dialog().input("Enter Playlist Name:")
        if not name:
            return False

    progress = xbmcgui.DialogProgress()
    progress.create(ADDON_NAME, "Collecting media files...")
    
    all_files = []
    total_folders = len(folders)
    for i, folder in enumerate(folders):
        if progress.iscanceled(): # Allow cancellation during folder scanning
            progress.close()
            return False
        progress.update(int(i * 100 / total_folders), f"Scanning {os.path.basename(folder)}...")
        files = get_media_files(folder)
        all_files.extend(files)
        
    # Apply all sorting rules
    progress.update(90, "Applying sorting...")
    all_files = apply_sorting(all_files)
    
    # Apply total limit if enabled
    if get_setting('limit_mode', '0') == '1': # Total files
        all_files = all_files[:int(get_setting('total_file_count', '100'))]
    
    progress.update(95, "Creating playlist...")
    
    if not xbmcvfs.exists(PLAYLIST_DIR):
        xbmcvfs.mkdirs(PLAYLIST_DIR)
    
    playlist_path = os.path.join(PLAYLIST_DIR, f"{name}.m3u")
    
    # Create backup if enabled
    if get_setting('enable_backups') == 'true' and xbmcvfs.exists(playlist_path):
        create_backup(playlist_path)
    
    try:
        with xbmcvfs.File(playlist_path, 'w') as f:
            f.write("#EXTM3U\n")
            for file in all_files:
                f.write(f"#EXTINF:-1,{format_display_entry(file)}\n")
                f.write(f"{file}\n")
        
        progress.close()
        
        # If not from a preset, ask to save as set
        if not from_set and xbmcgui.Dialog().yesno(ADDON_NAME, "Playlist created successfully. Save as folder set?"):
            save_folder_set(name, folders)
        else:
            xbmcgui.Dialog().notification(ADDON_NAME, f"Created playlist: {name}", xbmcgui.NOTIFICATION_INFO)
        
        return True
    except Exception as e:
        progress.close()
        log(f"Playlist creation failed: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, "Failed to create playlist", xbmcgui.NOTIFICATION_ERROR)
        return False

def save_folder_set(name, folders):
    """Save folder set with all current settings"""
    sets = load_json(CONFIG_FILE) or {}
    
    # Save all relevant settings
    sets[name] = {
        'folders': folders,
        'timestamp': time.time(),
        'settings': {
            # File Selection
            'file_extensions': get_setting('file_extensions'),
            'exclude_pattern': get_setting('exclude_pattern'),
            'exclude_folders': get_setting('exclude_folders'), 
            'min_file_size': get_setting('min_file_size'),
            'enable_max_size': get_setting('enable_max_size'),
            'max_file_size': get_setting('max_file_size'),
            'recursive_scan': get_setting('recursive_scan'),
            
            # Sorting
            'sort_mode': get_setting('sort_mode'),
            'folder_sort_mode': get_setting('folder_sort_mode'),
            'custom_folder_order': get_setting('custom_folder_order'),
            'newest_files': get_setting('newest_files'),
            'limit_mode': get_setting('limit_mode'),
            'file_count': get_setting('file_count'),
            'total_file_count': get_setting('total_file_count'),
            
            # Display
            'show_folder_names': get_setting('show_folder_names'),
            'show_metadata': get_setting('show_metadata'),
            'show_duration': get_setting('show_duration')
        }
    }
    save_json(sets, CONFIG_FILE)
    xbmcgui.Dialog().notification(ADDON_NAME, f"Saved set: {name}", xbmcgui.NOTIFICATION_INFO)

def create_playlist_from_set(set_name):
    sets = load_json(CONFIG_FILE) or {}
    if set_name not in sets:
        log(f"Set '{set_name}' not found.", xbmc.LOGWARNING)
        return False
    
    # Apply settings from this set
    set_data = sets[set_name]
    
    # Store current settings to restore later
    original_settings = {}
    for key in set_data.get('settings', {}):
        original_settings[key] = get_setting(key)
    
    # Apply set-specific settings
    for key, value in set_data.get('settings', {}).items():
        set_setting(key, value)
    
    folders = set_data['folders']
    result = create_playlist(folders, set_name, from_set=True)
    
    # Update timestamp
    if result:
        sets[set_name]['timestamp'] = time.time()
        save_json(sets, CONFIG_FILE)
    
    # Restore original settings
    for key, value in original_settings.items():
        set_setting(key, value)
        
    return result

def update_all_sets():
    sets = load_json(CONFIG_FILE) or {}
    if not sets:
        xbmcgui.Dialog().notification(ADDON_NAME, "No sets found", xbmcgui.NOTIFICATION_WARNING)
        return False # Changed to return False if no sets
    
    progress = xbmcgui.DialogProgress()
    progress.create(ADDON_NAME, "Updating playlists...")
    
    success = 0
    total = len(sets)
    for i, set_name in enumerate(sets):
        if progress.iscanceled(): # Allow cancellation during update
            break
        progress.update(int(i * 100 / total), f"Updating {set_name}...")
        if create_playlist_from_set(set_name):
            success += 1
    
    progress.close()
    
    xbmcgui.Dialog().notification(
        ADDON_NAME, 
        f"Updated {success}/{total} sets", 
        xbmcgui.NOTIFICATION_INFO if success > 0 else xbmcgui.NOTIFICATION_WARNING
    )
    return success > 0

def manage_sets():
    sets = load_json(CONFIG_FILE) or {}
    dialog = xbmcgui.Dialog()
    
    while True:
        if not sets:
            choices = ["Create New Set", "Back"]
        else:
            choices = list(sets.keys()) + ["Create New Set", "Back"]
            
        choice = dialog.select("Manage Folder Sets", choices)
        
        if choice == -1 or choice == len(choices)-1:  # Back
            break
        elif choice == len(choices)-2:  # Create New
            name = dialog.input("Set Name:")
            if name:
                folders = select_folders()
                if folders:
                    save_folder_set(name, folders)
                    sets = load_json(CONFIG_FILE) or {} # Reload sets after saving
        else:  # Existing set
            set_name = choices[choice]
            action = dialog.select(f"Set: {set_name}", ["Update Now", "Edit Folders", "Edit Settings", "Delete"])
            
            if action == 0:  # Update
                if create_playlist_from_set(set_name):
                    dialog.notification(ADDON_NAME, f"Updated {set_name}", xbmcgui.NOTIFICATION_INFO)
            elif action == 1:  # Edit Folders
                folders = select_folders()
                if folders:
                    sets[set_name]['folders'] = folders
                    save_json(sets, CONFIG_FILE)
            elif action == 2:  # Edit Settings
                # Apply set settings first
                apply_set_settings(set_name)
                # Open settings dialog
                ADDON.openSettings()
                # Save settings back to set
                if dialog.yesno(ADDON_NAME, "Save changes to set settings?"):
                    temp_folders = sets[set_name]['folders'] # Preserve folders as settings dialog doesn't change them
                    save_folder_set(set_name, temp_folders)
                # Re-load sets to reflect any changes if settings were saved/not saved
                sets = load_json(CONFIG_FILE) or {} 
            elif action == 3:  # Delete
                if dialog.yesno("Confirm", f"Delete {set_name}?"):
                    del sets[set_name]
                    xbmcvfs.delete(os.path.join(PLAYLIST_DIR, f"{set_name}.m3u")) # Delete associated playlist file
                    save_json(sets, CONFIG_FILE)
                    sets = load_json(CONFIG_FILE) or {} # Reload sets after deletion


def save_json(data, file_path):
    try:
        if not xbmcvfs.exists(ADDON_PROFILE):
            xbmcvfs.mkdirs(ADDON_PROFILE)
        with xbmcvfs.File(file_path, 'w') as f:
            f.write(json.dumps(data, indent=2))
        return True
    except Exception as e:
        log(f"Save failed: {str(e)}", xbmc.LOGERROR)
        return False

def load_json(file_path):
    try:
        if xbmcvfs.exists(file_path):
            with xbmcvfs.File(file_path, 'r') as f:
                content = f.read()
                return json.loads(content)
    except Exception as e:
        log(f"Load failed: {str(e)}", xbmc.LOGERROR)
    return {}

def show_main_menu():
    dialog = xbmcgui.Dialog()
    while True:
        choice = dialog.select(ADDON_NAME, [
            "Create Playlist", 
            "Quick Scan (No Playlist)",
            "Manage Folder Sets",
            "Update All Sets",
            "Settings",
            "Exit"
        ])
        
        if choice == 0:
            create_playlist()
        elif choice == 1:
            quick_scan()
        elif choice == 2:
            manage_sets()
        elif choice == 3:
            update_all_sets()
        elif choice == 4:
            ADDON.openSettings()
        elif choice in (5, -1):
            break

if __name__ == '__main__':
    log(f"{ADDON_NAME} starting")
    if not xbmcvfs.exists(ADDON_PROFILE):
        xbmcvfs.mkdirs(ADDON_PROFILE)
    if not xbmcvfs.exists(PLAYLIST_DIR):
        xbmcvfs.mkdirs(PLAYLIST_DIR)

    show_main_menu()