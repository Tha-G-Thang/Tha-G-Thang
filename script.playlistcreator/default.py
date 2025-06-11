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

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PROFILE = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')
CONFIG_FILE = os.path.join(ADDON_PROFILE, 'playlist_sets.json')
PLAYLIST_DIR = xbmcvfs.translatePath('special://profile/playlists/video/')

# Cache for file durations to improve performance
duration_cache = {}

def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] {msg}", level)

def get_setting(setting_id, default=''):
    return ADDON.getSetting(setting_id) or default

def set_setting(setting_id, value):
    ADDON.setSetting(setting_id, str(value))

def validate_settings():
    """Validate critical settings to prevent conflicts"""
    try:
        min_size = int(get_setting('min_file_size', '50'))
        max_size = int(get_setting('max_file_size', '0'))
        if get_setting('enable_max_size') == 'true' and max_size > 0 and max_size <= min_size:
            log("Warning: Max file size should be larger than min file size", xbmc.LOGWARNING)

        # Validate time format
        update_time = get_setting('update_time', '03:00')
        if not re.match(r'^\d{2}:\d{2}$', update_time):
            set_setting('update_time', '03:00')
            log("Fixed invalid update time format", xbmc.LOGWARNING)
    except ValueError as e:
        log(f"Settings validation error: {e}", xbmc.LOGERROR)

def apply_set_settings(set_name):
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
    except Exception:
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
    if filepath in duration_cache:
        return duration_cache[filepath]
    try:
        if filepath.startswith('special://') or not xbmcvfs.exists(filepath):
            duration_cache[filepath] = 0
            return 0
        item = xbmcgui.ListItem(path=filepath)
        duration = int(item.getDuration())
        duration_cache[filepath] = duration
        return duration
    except Exception:
        duration_cache[filepath] = 0
        return 0

def get_media_files(folder, depth=0, max_depth=8):
    """Get media files with improved error handling and depth limiting"""
    extensions = [ext.strip().lower() for ext in get_setting('file_extensions', '.mp4,.mkv,.avi,.mov,.wmv').split(',') if ext.strip()]
    exclude = [word.strip().lower() for word in get_setting('exclude_pattern', 'sample,trailer').split(',') if word.strip()]
    exclude_folders = [f.strip().lower() for f in get_setting('exclude_folders', '').split(',') if f.strip()]
    min_size = int(get_setting('min_file_size', '50')) * 1024 * 1024
    max_size = int(get_setting('max_file_size', '0')) * 1024 * 1024 if get_setting('enable_max_size') == 'true' else 0
    files = []

    try:
        dirs, filenames = xbmcvfs.listdir(folder)
        dirs = [d for d in dirs if d.lower() not in exclude_folders]

        for filename in filenames:
            file_lower = filename.lower()
            filepath = os.path.join(folder, filename)

            try:
                file_size = xbmcvfs.Stat(filepath).st_size()
            except Exception:
                continue  # Skip files we can't access

            valid_ext = any(file_lower.endswith(ext) for ext in extensions)
            valid_exclude = not any(word in file_lower for word in exclude)
            valid_min_size = (min_size <= 0 or file_size >= min_size)
            valid_max_size = (max_size <= 0 or file_size <= max_size)

            if valid_ext and valid_exclude and valid_min_size and valid_max_size:
                files.append(filepath)

        if get_setting('limit_mode', '0') == '0':
            file_count = int(get_setting('file_count', '20'))
            files = files[:file_count]

        if get_setting('recursive_scan') and depth < max_depth:
            for dir_name in dirs:
                files.extend(get_media_files(os.path.join(folder, dir_name), depth + 1, max_depth))
    except Exception as e:
        log(f"Error scanning {folder}: {str(e)}", xbmc.LOGERROR)
    
    return files

def get_folder_sort_key(folder_path):
    folder_mode = get_setting('folder_sort_mode', '0')
    custom_order = [f.strip().lower() for f in get_setting('custom_folder_order', '').split(',') if f.strip()]
    folder_name = os.path.basename(folder_path).lower()

    if folder_mode == '1':  # A-Z
        return (0, folder_name)
    elif folder_mode == '2':  # Z-A
        return (0, folder_name)  # Reverse happens later
    elif folder_mode == '3' and custom_order:  # Custom
        try:
            return (custom_order.index(folder_name), folder_name)
        except ValueError:
            return (len(custom_order), folder_name)
    else:  # None
        return (0, folder_path)

def apply_sorting(files):
    folder_groups = {}
    for file in files:
        folder = os.path.dirname(file)
        if folder not in folder_groups:
            folder_groups[folder] = []
        folder_groups[folder].append(file)

    sorted_folders = sorted(folder_groups.keys(), key=get_folder_sort_key)
    if get_setting('folder_sort_mode') == '2':  # Z-A
        sorted_folders.reverse()

    result = []
    for folder in sorted_folders:
        folder_files = folder_groups[folder]
        sort_mode = get_setting('sort_mode', '0') # Correctie: overtollig sluithaakje verwijderd

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
                folder_files.sort(key=lambda x: get_file_duration(x))
            elif sort_mode == '7':  # Duration (Longest first)
                folder_files.sort(key=lambda x: get_file_duration(x), reverse=True)
            else:  # Newest first (default)
                folder_files.sort(key=lambda x: xbmcvfs.Stat(x).st_mtime(), reverse=True)
        except Exception as e:
            import traceback
            log(f"Error: {str(e)}\n{traceback.format_exc()}", xbmc.LOGERROR)

        result.extend(folder_files)

    newest_count = int(get_setting('newest_files', '0'))
    if newest_count > 0:
        try:
            newest = sorted(result, key=lambda x: xbmcvfs.Stat(x).st_mtime(), reverse=True)[:newest_count]
            remaining = [f for f in result if f not in newest]
            result = newest + remaining
        except Exception as e:
            import traceback
            log(f"Error: {str(e)}\n{traceback.format_exc()}", xbmc.LOGERROR)

    return result

def select_folders():
    dialog = xbmcgui.Dialog()
    folders = []
    last_folder = folders[-1] if folders else xbmcvfs.translatePath('special://video/')

    folder = dialog.browse(0, "Select First Folder (Cancel to abort)", 'files', defaultt=path)
    if not folder:
        return None

    folders.append(folder)

    while dialog.yesno(ADDON_NAME, "Add another folder?", nolabel="No", yeslabel="Yes"):
        folder = dialog.browse(0, "Select Additional Folder", 'files', defaultt=last_folder)
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

    try:
        xbmcvfs.copy(playlist_path, backup_path)
    except Exception as e:
        import traceback
        log(f"Error: {str(e)}\n{traceback.format_exc()}", xbmc.LOGERROR)
        return False

    max_backups = int(get_setting('max_backups', '3'))
    if max_backups > 0:
        try:
            _, files = xbmcvfs.listdir(backup_dir)
            base_name = os.path.basename(playlist_path)
            matching_backups = [f for f in files if f.startswith(f"{base_name}.bak.")]
            matching_backups.sort(reverse=True)

            for old_backup in matching_backups[max_backups:]:
                xbmcvfs.delete(os.path.join(backup_dir, old_backup))
        except Exception as e:
            import traceback
            log(f"Error: {str(e)}\n{traceback.format_exc()}", xbmc.LOGERROR)

    return True

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
    try:
        for i, folder in enumerate(folders):
            if progress.iscanceled():
                progress.close()
                return False

            progress.update(int(i * 100 / total_folders), f"Scanning {os.path.basename(folder)}...")
            files = get_media_files(folder)
            all_files.extend(files)

        progress.update(90, "Applying sorting...")
        all_files = apply_sorting(all_files)

        if get_setting('limit_mode') == '1':
            total_count = int(get_setting('total_file_count', '100'))
            all_files = all_files[:total_count]

        progress.update(95, "Creating playlist...")

        if not xbmcvfs.exists(PLAYLIST_DIR):
            xbmcvfs.mkdirs(PLAYLIST_DIR)

        playlist_path = os.path.join(PLAYLIST_DIR, f"{name}.m3u")

        if get_setting('enable_backups') == 'true' and xbmcvfs.exists(playlist_path):
            create_backup(playlist_path)

        try:
            with xbmcvfs.File(playlist_path, 'w') as f:
                f.write("#EXTM3U\n")
                for file in all_files:
                    f.write(f"#EXTINF:-1,{format_display_entry(file)}\n")
                    f.write(f"{file}\n")

            progress.close()

            if not from_set and xbmcgui.Dialog().yesno(ADDON_NAME, "Playlist created successfully.\nSave as folder set?"):
                save_folder_set(name, folders)
            else:
                xbmcgui.Dialog().notification(ADDON_NAME, f"Created playlist: {name}", xbmcgui.NOTIFICATION_INFO)

            return True
        except Exception as e:
            progress.close()
            log(f"Playlist creation failed: {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, "Failed to create playlist", xbmcgui.NOTIFICATION_ERROR)
            return False
    except Exception as e:
        progress.close()
        log(f"Error creating playlist: {str(e)}", xbmc.LOGERROR)
        return False

def save_folder_set(name, folders):
    sets = load_json(CONFIG_FILE) or {}

    sets[name] = {
        'folders': folders,
        'timestamp': time.time(),
        'settings': {
            'file_extensions': get_setting('file_extensions'),
            'exclude_pattern': get_setting('exclude_pattern'),
            'exclude_folders': get_setting('exclude_folders'),
            'min_file_size': get_setting('min_file_size'),
            'enable_max_size': get_setting('enable_max_size'),
            'max_file_size': get_setting('max_file_size'),
            'recursive_scan': get_setting('recursive_scan'),
            'sort_mode': get_setting('sort_mode'),
            'folder_sort_mode': get_setting('folder_sort_mode'),
            'custom_folder_order': get_setting('custom_folder_order'),
            'newest_files': get_setting('newest_files'),
            'limit_mode': get_setting('limit_mode'),
            'file_count': get_setting('file_count'),
            'total_file_count': get_setting('total_file_count'),
            'show_folder_names': get_setting('show_folder_names'),
            'show_metadata': get_setting('show_metadata'),
            'show_duration': get_setting('show_duration')
        }
    }
    save_json(sets, CONFIG_FILE)
    xbmcgui.Dialog().notification(ADDON_NAME, f"Saved set: {name}", xbmcgui.NOTIFICATION_INFO) # Gecorrigeerd

def create_playlist_from_set(set_name):
    sets = load_json(CONFIG_FILE) or {}
    if set_name not in sets:
        return False

    set_data = sets[set_name]
    original_settings = {}
    for key in set_data.get('settings', {}):
        original_settings[key] = get_setting(key)

    for key, value in set_data.get('settings', {}).items():
        set_setting(key, value)

    folders = set_data['folders']
    result = create_playlist(folders, set_name, from_set = True)

    if result:
        sets[set_name]['timestamp'] = time.time()
        save_json(sets, CONFIG_FILE)

    for key, value in original_settings.items():
        set_setting(key, value)

    return result

def update_all_sets():
    sets = load_json(CONFIG_FILE) or {}
    if not sets:
        xbmcgui.Dialog().notification(ADDON_NAME, "No sets found", xbmcgui.NOTIFICATION_WARNING)
        return False

    progress = xbmcgui.DialogProgress()
    progress.create(ADDON_NAME, "Updating playlists...")

    success = 0
    total = len(sets)
    for i, set_name in enumerate(sets):
        if progress.iscanceled():
            break

        progress.update(int(i * 100 / total), f"Updating {set_name}...") # Gecorrigeerd
        if create_playlist_from_set(set_name):
            success += 1

    progress.close()
    record_update_time()

    xbmcgui.Dialog().notification(
        ADDON_NAME,
        f"Updated {success}/{total} sets", # Gecorrigeerd
        xbmcgui.NOTIFICATION_INFO if success > 0 else xbmcgui.NOTIFICATION_WARNING
    )
    return success > 0

def manage_sets():
    sets = load_json(CONFIG_FILE) or {}
    dialog = xbmcgui.Dialog()

    while True:
        set_names = sorted(list(sets.keys()))
        choices = set_names + ["Create New Set", "Back"]

        choice_idx = dialog.select("Manage Folder Sets", choices)

        if choice_idx == -1 or choice_idx == len(choices) - 1: # Back
            break
        elif choice_idx == len(choices) - 2: # Create New
            name = dialog.input("Set Name:")
            if name:
                folders = select_folders()
                if folders:
                    save_folder_set(name, folders)
                    sets = load_json(CONFIG_FILE) or {}
        else: # Note: 'else' moet hier staan om de 'set_name' te definiëren voor de rest van de acties.
            set_name = choices[choice_idx]
            action = dialog.select(f"Set: {set_name}", ["Update Now", "Edit Folders", "Edit Settings", "Delete"]) # Gecorrigeerd

            if action == 0: # Update
                if create_playlist_from_set(set_name):
                    dialog.notification(ADDON_NAME, f"Updated {set_name}", xbmcgui.NOTIFICATION_INFO) # Gecorrigeerd
            elif action == 1: # Edit Folders
                folders = select_folders()
                if folders:
                    sets[set_name]['folders'] = folders
                    save_json(sets, CONFIG_FILE)
            elif action == 2: # Edit Settings
                apply_set_settings(set_name)
                ADDON.openSettings()
                if dialog.yesno(ADDON_NAME, "Save changes to this set's settings?"):
                    temp_folders = sets[set_name]['folders']
                    save_folder_set(set_name, temp_folders)
            elif action == 3: # Delete
                if dialog.yesno("Confirm", f"Delete set '{set_name}'?"): # Gecorrigeerd
                    del sets[set_name]
                    save_json(sets, CONFIG_FILE)

def save_json(data, file_path):
    try:
        if not xbmcvfs.exists(ADDON_PROFILE):
            xbmcvfs.mkdirs(ADDON_PROFILE)
        with xbmcvfs.File(file_path, 'w') as f:
            f.write(json.dumps(data, indent = 2))
        return True
    except Exception as e:
        import traceback
        log(f"Error: {str(e)}\n{traceback.format_exc()}", xbmc.LOGERROR) # Gecorrigeerd
        return False

def load_json(file_path):
    try:
        if xbmcvfs.exists(file_path):
            with xbmcvfs.File(file_path, 'r') as f:
                content = f.read()
                return json.loads(content)
    except Exception as e:
        import traceback
        log(f"Error: {str(e)}\n{traceback.format_exc()}", xbmc.LOGERROR) # Gecorrigeerd
    return {}

def check_scheduled_updates():
    if get_setting('enable_timer') != 'true':
        return False

    interval = get_setting('update_interval', '1')
    last_update_str = get_setting('last_update', '')

    try:
        last_update = datetime.strptime(last_update_str, "%Y-%m-%d %H:%M:%S") if last_update_str else None
    except ValueError:
        last_update = None

    now = datetime.now()

    if interval == '0': # Hourly
        return not last_update or (now - last_update).total_seconds() >= 3600
    elif interval == '1': # Daily
        update_time = get_setting('update_time', '03:00')
        try:
            hour, minute = map(int, update_time.split(':'))
        except ValueError:
            hour, minute = 3, 0

        today = now.replace(hour = hour, minute = minute, second = 0, microsecond = 0)
        return not last_update or (now >= today and last_update.date() < now.date())
    elif interval == '2': # Weekly
        update_time = get_setting('update_time', '03:00')
        try:
            hour, minute = map(int, update_time.split(':'))
        except ValueError:
            hour, minute = 3, 0

        is_sunday = now.weekday() == 6
        past_update_time = now.hour >= hour and now.minute >= minute

        if not last_update:
            return is_sunday and past_update_time

        days_since_update = (now.date() - last_update.date()).days
        return is_sunday and past_update_time and days_since_update >= 1

    return False

def record_update_time():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    set_setting('last_update', now)

def show_timer_settings():
    dialog = xbmcgui.Dialog()

    while True:
        enable_timer = get_setting('enable_timer') == 'true'
        interval_idx = int(get_setting('update_interval', '1'))
        update_time = get_setting('update_time', '03:00')
        last_update = get_setting('last_update', 'Never')

        interval_names = ['Hourly', 'Daily', 'Weekly']
        interval_name = interval_names[interval_idx] if 0 <= interval_idx < len(interval_names) else 'Daily'

        options = [
            f"Enable scheduled updates: {'Yes' if enable_timer else 'No'}", # Gecorrigeerd
            f"Update interval: {interval_name}", # Gecorrigeerd
            f"Update time: {update_time}", # Gecorrigeerd
            f"Last update: {last_update}", # Gecorrigeerd
            "Run update now",
            "Back"
        ]

        choice = dialog.select("Scheduled Updates", options)

        if choice == 0:
            enable_timer = not enable_timer
            set_setting('enable_timer', 'true' if enable_timer else 'false')

        elif choice == 1:
            new_idx = dialog.select("Update Interval", interval_names, preselect = interval_idx)
            if new_idx >= 0:
                set_setting('update_interval', str(new_idx))

        elif choice == 2:
            new_time = dialog.numeric(2, "Update Time (HH:MM)", update_time)
            if new_time and re.match(r'^\d{2}:\d{2}$', new_time):
                set_setting('update_time', new_time)

        elif choice == 4:
            if update_all_sets():
                pass # Success notification already shown

        elif choice == 5 or choice == -1:
            break

def clean_filename(filename):
    """Clean filename for download with better pattern matching"""
    cleaned_filename = re.sub(r'[^\w\-_\.]', '_', filename)
    cleaned_filename = re.sub(r'_{2,}', '_', cleaned_filename)
    return cleaned_filename.strip('_')

def download_file(path, download_type = 'standard'):
    """Download file with improved error handling and validation"""
    dialog = xbmcgui.Dialog()

    if not path:
        dialog.notification(ADDON_NAME, "No file path provided for download.", xbmcgui.NOTIFICATION_ERROR)
        return False

    target_dir = get_setting('download_path') if download_type == 'standard' else get_setting('download_path_adult')
    if not target_dir:
        dialog.notification(ADDON_NAME, "Download path not configured in settings.", xbmcgui.NOTIFICATION_ERROR)
        return False

    if not xbmcvfs.exists(target_dir):
        try:
            xbmcvfs.mkdirs(target_dir)
        except Exception as e:
            import traceback
            log(f"Error: {str(e)}\n{traceback.format_exc()}", xbmc.LOGERROR) # Gecorrigeerd
            dialog.notification(ADDON_NAME, f"Failed to create download directory", xbmcgui.NOTIFICATION_ERROR)
            return False

    base_filename = os.path.basename(path)
    if get_setting('enable_auto_clean') == 'true':
        base_filename = clean_filename(base_filename)

    target_path = os.path.join(target_dir, base_filename)

    if xbmcvfs.exists(target_path):
        if not dialog.yesno(ADDON_NAME, f"File already exists. Overwrite '{base_filename}'?"): # Gecorrigeerd
            return False

    progress = xbmcgui.DialogProgress()
    progress.create(ADDON_NAME, f"Downloading: {base_filename}") # Gecorrigeerd

    try:
        if not xbmcvfs.copy(path, target_path):
            raise Exception("xbmcvfs.copy failed")

        progress.close()
        dialog.notification(ADDON_NAME, f"Downloaded: {base_filename}", xbmcgui.NOTIFICATION_INFO) # Gecorrigeerd
        return True
    except Exception as e:
        progress.close()
        log(f"Download failed for {path}: {e}", xbmc.LOGERROR) # Gecorrigeerd
        dialog.notification(ADDON_NAME, f"Download failed for {base_filename}", xbmcgui.NOTIFICATION_ERROR) # Gecorrigeerd
        return False

def show_main_menu():
    dialog = xbmcgui.Dialog()
    while True:
        choice = dialog.select(ADDON_NAME, [
            "Create Playlist",
            "Manage Folder Sets",
            "Update All Sets",
            "Scheduled Updates",
            "Settings",
            "Exit"
        ])

        if choice == 0:
            create_playlist()
        elif choice == 1:
            manage_sets()
        elif choice == 2:
            update_all_sets()
        elif choice == 3:
            show_timer_settings()
        elif choice == 4:
            ADDON.openSettings()
        elif choice in (5, -1):
            break

class PlaylistService:
    def __init__(self):
        self.monitor = xbmc.Monitor()
        self.last_check = time.time()

    def run(self):
        while not self.monitor.abortRequested():
            if self.monitor.waitForAbort(300): # Check every 5 minutes
                break

            if check_scheduled_updates():
                log("Running scheduled update")
                update_all_sets()

            self.last_check = time.time()

def parse_arguments():
    """Parse command line arguments with better validation"""
    if len(sys.argv) <= 1:
        return 'main', None, None

    command = sys.argv[1]

    if command == 'service':
        return 'service', None, None
    elif command == 'action=download_file':
        path = urllib.parse.unquote(sys.argv[2]) if len(sys.argv) > 2 else ''
        download_type = sys.argv[3] if len(sys.argv) > 3 else 'standard'
        return 'download', path, download_type
    elif command.startswith('debug='):
        return 'debug', command.split('=')[1], None
    else :
        return 'main', None, None

if __name__ == '__main__':
    log(f"{ADDON_NAME} starting") # Gecorrigeerd

    # Ensure directories exist
    if not xbmcvfs.exists(ADDON_PROFILE):
        xbmcvfs.mkdirs(ADDON_PROFILE)
    if not xbmcvfs.exists(PLAYLIST_DIR):
        xbmcvfs.mkdirs(PLAYLIST_DIR)

    # Validate settings on startup
    validate_settings()

    # Parse arguments and execute appropriate action
    action, path, download_type = parse_arguments()

    if action == 'service':
        service = PlaylistService()
        service.run()
    elif action == 'download':
        download_file(path, download_type)
    elif action == 'debug':
        # Debug mode handling
        pass
    else :
        if get_setting('auto_update') == 'true':
            update_all_sets()

        show_main_menu()