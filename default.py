import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import json
import urllib.parse
import re
import time
from datetime import datetime
import random
from typing import List, Dict, Optional, Union, Tuple
from collections import defaultdict

# Constants
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_PROFILE = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')
PLAYLIST_DIR = xbmcvfs.translatePath('special://profile/playlists/video/')
CONFIG_FILE = os.path.join(ADDON_PROFILE, 'folder_sets.json')
CHATBOT_ICON_PATH = os.path.join(ADDON_PATH, 'resources', 'media', 'chatbots', 'chatduo.jpg')

class SortModes:
    """Constants for sorting modes matching settings.xml values"""
    FOLDER_MODES = {
        '0': 'None',
        '1': 'Recently Modified',
        '2': 'A-Z',
        '3': 'Z-A',
        '4': 'Custom Order'
    }
    
    FILE_MODES = {
        '0': 'Newest First',
        '1': 'A-Z',
        '2': 'Z-A',
        '3': 'Random',
        '4': 'File Size (Smallest)',
        '5': 'File Size (Largest)',
        '6': 'Duration (Shortest)',
        '7': 'Duration (Longest)'
    }

class ImageUtils:
    """Handles image-related operations"""
    @staticmethod
    def get_chatbot_icon() -> Optional[str]:
        return CHATBOT_ICON_PATH if xbmcvfs.exists(CHATBOT_ICON_PATH) else None

    @staticmethod
    def create_listitem(label: str, icon_path: Optional[str] = None) -> xbmcgui.ListItem:
        li = xbmcgui.ListItem(label)
        if icon_path and xbmcvfs.exists(icon_path):
            li.setArt({'icon': icon_path, 'thumb': icon_path})
        return li

class Logger:
    """Centralized logging with Kodi integration"""
    @classmethod
    def log(cls, msg: str, level: int = xbmc.LOGINFO) -> None:
        xbmc.log(f"[{ADDON_ID}] {msg}", level)
    
    @classmethod
    def error(cls, msg: str) -> None:
        cls.log(msg, xbmc.LOGERROR)
    
    @classmethod
    def warning(cls, msg: str) -> None:
        cls.log(msg, xbmc.LOGWARNING)

class NotificationHandler:
    """Handles notifications based on operation mode"""
    @staticmethod
    def show(message: str, error: bool = False) -> None:
        mode = SettingsManager.get('operation_mode')
        if mode == "0" or (error and SettingsManager.get_bool('enable_error_popups')):
            icon = xbmcgui.NOTIFICATION_ERROR if error else xbmcgui.NOTIFICATION_INFO
            xbmcgui.Dialog().notification(ADDON_NAME, message, icon)
        elif mode == "1" and not error:
            xbmc.executebuiltin(f'Notification({ADDON_NAME}, {message})')

class SettingsManager:
    """Manages addon settings with type safety"""
    @staticmethod
    def get(setting_id: str, default: str = '') -> str:
        return ADDON.getSetting(setting_id) or default
    
    @staticmethod
    def get_int(setting_id: str, default: int = 0) -> int:
        try:
            return int(SettingsManager.get(setting_id, str(default)))
        except ValueError:
            return default
            
    @staticmethod
    def get_bool(setting_id: str) -> bool:
        return SettingsManager.get(setting_id).lower() == 'true'
    
    @staticmethod
    def set(setting_id: str, value: Union[str, int, bool]) -> None:
        ADDON.setSetting(setting_id, str(value))

class FileUtils:
    """File system operations with memory management"""
@staticmethod
def _is_valid_file(filepath: str, extensions: List[str], 
                  exclude: List[str], min_size: int, max_size: int) -> bool:
    """Validate if file meets all criteria"""
    filename = os.path.basename(filepath).lower()
    return (any(filename.endswith(ext) for ext in extensions) and \
           not any(excl in filename for excl in exclude) and \
           FileUtils._check_file_size(filepath, min_size, max_size)

@staticmethod
def _check_file_size(filepath: str, min_size: int, max_size: int) -> bool:
    """Validate if file size meets minimum and maximum requirements"""
    try:
        size = xbmcvfs.File(filepath).size()
        return size >= min_size and (max_size <= 0 or size <= max_size)
    except Exception:
        return False

@staticmethod
    def get_media_files(folder: str, depth: int = 0) -> List[str]:
        """Scan folder for media files with memory management"""
        settings = {
            'extensions': SettingsManager.get('file_extensions', '.mp4,.mkv,.avi,.mov,.wmv'),
            'exclude': SettingsManager.get('exclude_pattern', 'sample,trailer'),
            'exclude_folders': SettingsManager.get('exclude_folders', ''),
            'min_size': SettingsManager.get_int('min_file_size', 50) * 1024 * 1024,
            'max_size': SettingsManager.get_int('max_file_size', 0) * 1024 * 1024 
                       if SettingsManager.get_bool('enable_max_size') else 0,
            'batch_size': {0: 50, 1: 100, 2: 200}.get(
                SettingsManager.get_int('file_batch_size', 0), 50)
        }

        extensions = [ext.strip().lower() for ext in settings['extensions'].split(',')]
        exclude = [word.strip().lower() for word in settings['exclude'].split(',') if word]
        exclude_folders = [f.strip().lower() for f in settings['exclude_folders'].split(',') if f]
        
        return FileUtils._scan_folder(
            folder, depth, extensions, exclude, exclude_folders,
            settings['min_size'], settings['max_size'], settings['batch_size']
        )

    @staticmethod
    def _scan_folder(folder: str, depth: int, extensions: List[str],
                    exclude: List[str], exclude_folders: List[str],
                    min_size: int, max_size: int, batch_size: int) -> List[str]:
        files = []
        try:
            dirs, filenames = xbmcvfs.listdir(folder)
            
            for i in range(0, len(filenames), batch_size):
                if xbmc.Monitor().abortRequested():
                    return []
                    
                batch = filenames[i:i + batch_size]
                files.extend(
                    os.path.join(folder, f) for f in batch
                    if FileUtils._is_valid_file(
                        os.path.join(folder, f), extensions, exclude, min_size, max_size
                    )
                )
                
                if SettingsManager.get('limit_mode') == '1' and \
                   len(files) >= SettingsManager.get_int('total_file_count', 100):
                    return files

            if depth < SettingsManager.get_int('max_scan_depth', 2) and \
               SettingsManager.get_bool('recursive_scan'):
                for dir_name in (d for d in dirs if d.lower() not in exclude_folders):
                    if xbmc.Monitor().abortRequested():
                        break
                    files.extend(FileUtils._scan_folder(
                        os.path.join(folder, dir_name), depth + 1,
                        extensions, exclude, exclude_folders,
                        min_size, max_size, batch_size
                    ))
                    
        except Exception as e:
            Logger.error(f"Scan error in {folder}: {str(e)}")
            
        return files

class PlaylistManager:
    """Handles playlist creation and management"""
    @staticmethod
    def create_backup(playlist_path: str) -> None:
        if not SettingsManager.get_bool('enable_backups'):
            return
            
        backup_dir = os.path.join(PLAYLIST_DIR, "backups")
        if not xbmcvfs.exists(backup_dir):
            xbmcvfs.mkdirs(backup_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"{os.path.basename(playlist_path)}.bak.{timestamp}")
        xbmcvfs.copy(playlist_path, backup_path)
        PlaylistManager._cleanup_backups(backup_dir, os.path.basename(playlist_path))

    @staticmethod
    def _cleanup_backups(backup_dir: str, base_name: str) -> None:
        max_backups = SettingsManager.get_int('max_backups', 3)
        if max_backups <= 0:
            return
            
        try:
            _, files = xbmcvfs.listdir(backup_dir)
            backups = sorted(
                (f for f in files if f.startswith(f"{base_name}.bak.")),
                key=lambda x: x.split('.')[-1],
                reverse=True
            )
            for old_backup in backups[max_backups:]:
                xbmcvfs.delete(os.path.join(backup_dir, old_backup))
        except Exception as e:
            Logger.error(f"Backup cleanup error: {str(e)}")

@staticmethod
    def select_folders() -> Optional[List[str]]:
        dialog = xbmcgui.Dialog()
        path = xbmcvfs.translatePath('special://video/')
        folders = []
        
        while True:
            folder = dialog.browse(0, "Select Folder (Cancel when done)", 'files', defaultt=path)
            if not folder:
                return folders if folders else None
            if folder not in folders:
                folders.append(folder)
            else:
                NotificationHandler.show("Folder already added", error=True)

    @staticmethod
    def _get_folder_sort_key(folder_path: str) -> Tuple[int, str]:
        mode = SettingsManager.get('folder_sort_mode', '0')
        folder_name = os.path.basename(folder_path).lower()
        
        if mode == '1':  # Recently Modified
            try:
                return (-xbmcvfs.Stat(folder_path).st_mtime(), folder_name)
            except Exception as e:
                Logger.warning(f"Couldn't get mtime for {folder_path}: {str(e)}")
                return (0, folder_name)
        elif mode == '3':  # Z-A
            return (0, folder_name[::-1])
        elif mode == '4':  # Custom Order
            custom_order = [
                f.strip().lower() for f in 
                SettingsManager.get('custom_folder_order', '').split(',') if f.strip()
            ]
            if custom_order:
                return (custom_order.index(folder_name) if folder_name in custom_order 
                       else len(custom_order), folder_name)
        return (0, folder_name)  # Default (0 or 2)

    @staticmethod
    def apply_sorting(files: List[str]) -> List[str]:
        if not files:
            return []

        # Cache metadata for all files first
        metadata = {
            file: {
                'name': os.path.basename(file),
                'size': xbmcvfs.Stat(file).st_size(),
                'mtime': xbmcvfs.Stat(file).st_mtime(),
                'duration': 0  # Placeholder - would use actual duration in full implementation
            } for file in files
        }

        # Group by folder and sort folders
        folder_groups = defaultdict(list)
        for file in files:
            folder_groups[os.path.dirname(file)].append(file)
            
        sorted_folders = sorted(
            folder_groups.keys(),
            key=PlaylistManager._get_folder_sort_key
        )

        # Sort files within each folder
        result = []
        file_sort_mode = SettingsManager.get('file_sort_mode', '0')
        
        for folder in sorted_folders:
            folder_files = sorted(
                folder_groups[folder],
                key=lambda x: PlaylistManager._get_file_sort_key(x, metadata, file_sort_mode)
            )
            result.extend(folder_files)

        # Apply newest files to top if enabled
        newest_count = SettingsManager.get_int('newest_files', 0)
        if 0 < newest_count < len(result):
            result.sort(key=lambda x: -metadata[x]['mtime'])
            result = result[:newest_count] + [f for f in result if f not in result[:newest_count]]

        return result

    @staticmethod
    def _get_file_sort_key(file: str, metadata: dict, mode: str) -> tuple:
        """Helper method for file sorting"""
        if mode == '1':  # A-Z
            return metadata[file]['name'].lower()
        elif mode == '2':  # Z-A
            return metadata[file]['name'].lower()[::-1]
        elif mode == '4':  # Size (Smallest)
            return metadata[file]['size']
        elif mode == '5':  # Size (Largest)
            return -metadata[file]['size']
        elif mode == '6':  # Duration (Shortest)
            return metadata[file]['duration']
        elif mode == '7':  # Duration (Longest)
            return -metadata[file]['duration']
        else:  # Newest first (0) or other
            return -metadata[file]['mtime']

    @staticmethod
    def create_playlist(folders: Optional[List[str]] = None, 
                       name: Optional[str] = None,
                       from_set: bool = False) -> bool:
        """Main playlist creation method"""
        if not from_set:
            ChatbotManager.start_chat(SettingsManager.get("scan_as", "Regular Files"))
            
        folders = folders or PlaylistManager.select_folders()
        if not folders:
            return False
            
        name = name or xbmcgui.Dialog().input("Enter Playlist Name:")
        if not name:
            return False

        with ProgressDialog("Creating Playlist") as progress:
            all_files = PlaylistManager._collect_files(folders, progress)
            if not all_files:
                return False
                
            all_files = PlaylistManager.apply_sorting(all_files)
            
            # Apply total limit if enabled
            if SettingsManager.get('limit_mode', '0') == '1':
                all_files = all_files[:SettingsManager.get_int('total_file_count', 100)]
            
            return PlaylistManager._write_playlist(name, all_files, from_set)

    @staticmethod
    def _collect_files(folders: List[str], progress) -> List[str]:
        """Collect files from folders with progress updates"""
        all_files = []
        total = len(folders)
        
        for i, folder in enumerate(folders):
            progress.update(int(i * 100 / total), f"Scanning {os.path.basename(folder)}...")
            all_files.extend(FileUtils.get_media_files(folder))
            
            if progress.is_canceled():
                return []
                
        return all_files

    @staticmethod
    def _write_playlist(name: str, files: List[str], from_set: bool) -> bool:
        """Write the playlist file and handle post-creation actions"""
        if not xbmcvfs.exists(PLAYLIST_DIR):
            xbmcvfs.mkdirs(PLAYLIST_DIR)
            
        playlist_path = os.path.join(PLAYLIST_DIR, f"{name}.m3u")
        
        if xbmcvfs.exists(playlist_path):
            PlaylistManager.create_backup(playlist_path)
        
        try:
            with xbmcvfs.File(playlist_path, 'w') as f:
                f.write("#EXTM3U\n")
                for file in files:
                    f.write(f"#EXTINF:-1,{os.path.basename(file)}\n")
                    f.write(f"{file}\n")
            
            if not from_set and xbmcgui.Dialog().yesno(
                ADDON_NAME, "Save as folder set?"
            ):
                FolderSetManager.save_folder_set(name, [os.path.dirname(f) for f in files])
            else:
                NotificationHandler.show(f"Created playlist: {name}")
                
            return True
        except Exception as e:
            Logger.error(f"Playlist creation failed: {str(e)}")
            NotificationHandler.show("Failed to create playlist", error=True)
            return False

class ProgressDialog:
    """Context manager for progress dialogs"""
    def __init__(self, title: str):
        self.dialog = xbmcgui.DialogProgress()
        self.title = title
        
    def __enter__(self):
        self.dialog.create(ADDON_NAME, self.title)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dialog.close()
        
    def update(self, percent: int, message: str) -> None:
        self.dialog.update(percent, message)
        
    def is_canceled(self) -> bool:
        return self.dialog.iscanceled()

class JsonManager:
    """Handles JSON file operations with proper error handling"""
    @staticmethod
    def save(data: Union[dict, list], file_path: str) -> bool:
        """Save data to JSON file with atomic write pattern"""
        temp_path = f"{file_path}.tmp"
        try:
            # Create parent directory if needed
            parent_dir = os.path.dirname(file_path)
            if not xbmcvfs.exists(parent_dir):
                xbmcvfs.mkdirs(parent_dir)
            
            # Write to temporary file first
            with xbmcvfs.File(temp_path, 'w') as f:
                if not f.write(json.dumps(data, indent=2)):
                    raise IOError("Failed to write JSON data")
            
            # Atomic rename
            if xbmcvfs.exists(file_path):
                xbmcvfs.delete(file_path)
            xbmcvfs.rename(temp_path, file_path)
            return True
            
        except Exception as e:
            Logger.error(f"JSON save failed for {file_path}: {str(e)}")
            # Clean up temp file if it exists
            if xbmcvfs.exists(temp_path):
                xbmcvfs.delete(temp_path)
            return False

    @staticmethod
    def load(file_path: str) -> Optional[Union[dict, list]]:
        """Load JSON data with robust error handling"""
        try:
            if xbmcvfs.exists(file_path):
                with xbmcvfs.File(file_path, 'r') as f:
                    content = f.read()
                    if content:
                        return json.loads(content)
            return None
        except json.JSONDecodeError as e:
            Logger.error(f"Invalid JSON in {file_path}: {str(e)}")
            return None
        except Exception as e:
            Logger.error(f"Failed to load {file_path}: {str(e)}")
            return None

    @staticmethod
    def load(file_path: str) -> Optional[Union[dict, list]]:
        """Load JSON data with robust error handling"""
        try:
            if xbmcvfs.exists(file_path):
                with xbmcvfs.File(file_path, 'r') as f:
                    content = f.read()
                    if content:
                        return json.loads(content)
        except json.JSONDecodeError as e:
            Logger.error(f"Invalid JSON in {file_path}: {str(e)}")
        except Exception as e:
            Logger.error(f"Failed to load {file_path}: {str(e)}")
        return None


class FolderSetManager:
    """Manages folder sets with settings preservation"""
    @staticmethod
    def save_folder_set(name: str, folders: List[str]) -> None:
        """Save a complete folder set with all current settings"""
        sets = JsonManager.load(CONFIG_FILE) or {}
        
        # Capture all relevant settings
        settings = {
            setting_id: SettingsManager.get(setting_id)
            for setting_id in SettingsGroups.FOLDER_SET
        }
        
        sets[name] = {
            'folders': folders,
            'timestamp': int(time.time()),
            'settings': settings
        }
        
        if JsonManager.save(sets, CONFIG_FILE):
            NotificationHandler.show(f"Saved set: {name}")
        else:
            NotificationHandler.show("Failed to save set", error=True)

    @staticmethod
    def apply_set_settings(set_name: str) -> bool:
        """Apply settings from a saved set"""
        sets = JsonManager.load(CONFIG_FILE) or {}
        if not sets or set_name not in sets or 'settings' not in sets[set_name]:
            return False
            
        for key, value in sets[set_name]['settings'].items():
            if key in SettingsGroups.FOLDER_SET:
                SettingsManager.set(key, value)
        return True

    @staticmethod
    def create_playlist_from_set(set_name: str) -> bool:
        """Create playlist from a saved set with settings restoration"""
        sets = JsonManager.load(CONFIG_FILE) or {}
        if set_name not in sets:
            return False
            
        # Backup current settings
        original_settings = {
            key: SettingsManager.get(key)
            for key in SettingsGroups.FOLDER_SET
        }
        
        try:
            # Apply set settings
            FolderSetManager.apply_set_settings(set_name)
            
            # Create playlist
            result = PlaylistManager.create_playlist(
                sets[set_name]['folders'],
                set_name,
                from_set=True
            )
            
            # Update timestamp if successful
            if result:
                sets[set_name]['timestamp'] = int(time.time())
                JsonManager.save(sets, CONFIG_FILE)
                
            return result
        finally:
            # Restore original settings
            for key, value in original_settings.items():
                SettingsManager.set(key, value)

    @staticmethod
    def manage_sets() -> None:
        """Interactive folder set management UI"""
        sets = JsonManager.load(CONFIG_FILE) or {}
        dialog = xbmcgui.Dialog()
        
        while True:
            choices = list(sets.keys()) if sets else []
            choices.extend(["Create New Set", "Back"])
            
            choice = dialog.select("Manage Folder Sets", choices)
            if choice == -1 or choice == len(choices) - 1:  # Back
                break
                
            if choice == len(choices) - 2:  # Create New
                FolderSetManager._create_new_set()
                sets = JsonManager.load(CONFIG_FILE) or {}  # Refresh
            else:  # Existing set
                FolderSetManager._manage_existing_set(choices[choice], sets)

    @staticmethod
    def _create_new_set() -> None:
        """Handle new set creation flow"""
        name = xbmcgui.Dialog().input("Set Name:")
        if not name:
            return
            
        folders = PlaylistManager.select_folders()
        if folders:
            FolderSetManager.save_folder_set(name, folders)

    @staticmethod
    def _manage_existing_set(set_name: str, sets: dict) -> None:
        """Handle actions for existing sets"""
        dialog = xbmcgui.Dialog()
        action = dialog.select(
            f"Set: {set_name}",
            ["Update Now", "Edit Folders", "Edit Settings", "Delete"]
        )
        
        if action == 0:  # Update
            if FolderSetManager.create_playlist_from_set(set_name):
                NotificationHandler.show(f"Updated {set_name}")
        elif action == 1:  # Edit Folders
            folders = PlaylistManager.select_folders()
            if folders:
                sets[set_name]['folders'] = folders
                JsonManager.save(sets, CONFIG_FILE)
        elif action == 2:  # Edit Settings
            FolderSetManager._edit_set_settings(set_name)
        elif action == 3:  # Delete
            if dialog.yesno("Confirm", f"Delete {set_name}?"):
                del sets[set_name]
                JsonManager.save(sets, CONFIG_FILE)

    @staticmethod
    def _edit_set_settings(set_name: str) -> None:
        """Handle set settings editing flow"""
        # Apply set settings first
        FolderSetManager.apply_set_settings(set_name)
        
        # Open settings dialog
        ADDON.openSettings()
        
        # Prompt to save changes
        if xbmcgui.Dialog().yesno(ADDON_NAME, "Save changes to set settings?"):
            sets = JsonManager.load(CONFIG_FILE) or {}
            if set_name in sets:
                temp_folders = sets[set_name]['folders']
                FolderSetManager.save_folder_set(set_name, temp_folders)


class UpdateManager:
    """Handles playlist updates and scheduling"""
    @staticmethod
    def record_update_time() -> None:
        """Record current time as last update"""
        SettingsManager.set('last_update', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @staticmethod
    def update_playlists_with_mode() -> bool:
        """Update all playlists according to operation mode"""
        sets = JsonManager.load(CONFIG_FILE) or {}
        if not sets:
            NotificationHandler.show("No playlists found", error=True)
            return False
            
        mode = SettingsManager.get('operation_mode')
        
        # Background mode (silent)
        if mode == "1":
            success = sum(
                1 for set_name in sets
                if FolderSetManager.create_playlist_from_set(set_name)
            )
            UpdateManager.record_update_time()
            return success > 0
        
        # Foreground mode with progress
        with ProgressDialog("Updating Playlists") as progress:
            total = len(sets)
            success = 0
            
            for i, set_name in enumerate(sets):
                progress.update(int(i * 100 / total), f"Updating {set_name}...")
                if FolderSetManager.create_playlist_from_set(set_name):
                    success += 1
                if progress.is_canceled():
                    break
                    
            UpdateManager.record_update_time()
            
            message = f"Updated {success}/{total} playlists"
            if mode == "Background Notify":
                xbmc.executebuiltin(f'Notification({ADDON_NAME}, {message})')
            else:
                NotificationHandler.show(message)
                
            return success > 0

    @staticmethod
    def show_timer_settings() -> None:
        """Interactive timer settings management"""
        dialog = xbmcgui.Dialog()
        interval_names = ['Hourly', 'Daily', 'Weekly']
        
        # Initialize settings
        settings = {
            'enable_timer': SettingsManager.get_bool('enable_timer'),
            'interval_idx': SettingsManager.get_int('update_interval', 1),
            'update_time': SettingsManager.get('update_time', '03:00'),
            'last_update': SettingsManager.get('last_update', 'Never')
        }
        
        while True:
            # Build menu options
            options = [
                f"Enable scheduled updates: {'Yes' if settings['enable_timer'] else 'No'}",
                f"Update interval: {interval_names[settings['interval_idx']}",
                f"Update time: {settings['update_time']}",
                f"Last update: {settings['last_update']}",
                "Run update now",
                "Back"
            ]
            
            choice = dialog.select("Scheduled Updates", options)
            if choice == -1 or choice == len(options) - 1:  # Back
                break
                
            elif choice == 0:  # Toggle timer
                settings['enable_timer'] = not settings['enable_timer']
                SettingsManager.set('enable_timer', settings['enable_timer'])
                
            elif choice == 1:  # Change interval
                new_idx = dialog.select(
                    "Update Interval", 
                    interval_names, 
                    preselect=settings['interval_idx']
                )
                if new_idx >= 0:
                    settings['interval_idx'] = new_idx
                    SettingsManager.set('update_interval', new_idx)
                    
            elif choice == 2:  # Change time
                new_time = dialog.numeric(2, "Update Time (HH:MM)", settings['update_time'])
                if new_time:
                    settings['update_time'] = new_time
                    SettingsManager.set('update_time', new_time)
                    
            elif choice == 4:  # Run update now
                if UpdateManager.update_playlists_with_mode():
                    settings['last_update'] = SettingsManager.get('last_update', 'Never')


class ChatbotManager:
    """Manages chatbot personalities and interactions"""
    PERSONALITIES = {
        "bot_g": {
            "name": "G",
            "scan_as": ["Youtube Videos", "Regular Files"],
            "greetings": {
                "default": "Yo, let's find those fire videos",
                "Youtube Videos": "A'ight, let's hunt down those YouTube bangers",
                "Regular Files": "I see you workin' with local files - let's organize this"
            }
        },
        # ... other personalities ...
    }

    @staticmethod
    def get_personality_for_scan_mode(scan_mode: str) -> dict:
        """Get appropriate chatbot personality for content type"""
        return next(
            (p for p in ChatbotManager.PERSONALITIES.values() 
             if scan_mode in p["scan_as"]),
            list(ChatbotManager.PERSONALITIES.values())[0]  # Default
        )

    @staticmethod
    def start_chat(scan_mode: Optional[str] = None) -> None:
        """Start chatbot interaction"""
        persona = ChatbotManager.get_personality_for_scan_mode(scan_mode or "Regular Files")
        greeting = persona["greetings"].get(scan_mode, persona["greetings"]["default"])
        
        choice = xbmcgui.Dialog().select(
            persona["name"],
            [greeting, "Help with search", "Create playlist", "Exit"]
        )
        
        if choice == 0:
            ChatbotManager._handle_greeting_response(persona, scan_mode)
        elif choice == 1:
            ChatbotManager._provide_help(scan_mode)

    @staticmethod
    def _handle_greeting_response(persona: dict, scan_mode: str) -> None:
        """Handle greeting selection"""
        if scan_mode == "Adult Content":
            xbmcgui.Dialog().ok(persona["name"], "I'll help you browse privately...")
        elif scan_mode == "Music Videos":
            xbmcgui.Dialog().ok(persona["name"], "Let's mix up your music video collection!")
        else:
            xbmcgui.Dialog().ok(persona["name"], "Let's get started!")

    @staticmethod
    def _provide_help(scan_mode: str) -> None:
        """Provide context-sensitive help"""
        help_text = {
            "Adult Content": "Private browsing tips...",
            "Music Videos": "Music organization tips...",
            # ... other modes ...
        }.get(scan_mode, "General help information")
        
        xbmcgui.Dialog().ok("Help", help_text)


class MainMenu:
    """Main application menu controller"""
    @staticmethod
    def show() -> None:
        """Display and handle main menu"""
        options = [
            "Create Playlist",
            "Manage Folder Sets",
            "Update Playlists",
            "Scheduled Updates",
            "Settings",
            "Chat with AI",
            "Exit"
        ]
        
        dialog = xbmcgui.Dialog()
        while True:
            choice = dialog.select(ADDON_NAME, options)
            if choice == -1 or choice == len(options) - 1:  # Exit
                break
                
            if choice == 0:
                PlaylistManager.create_playlist()
            elif choice == 1:
                FolderSetManager.manage_sets()
            elif choice == 2:
                UpdateManager.update_playlists_with_mode()
            elif choice == 3:
                UpdateManager.show_timer_settings()
            elif choice == 4:
                ADDON.openSettings()
            elif choice == 5:
                ChatbotManager.start_chat()


class PlaylistService:
    """Background service for scheduled updates"""
    def __init__(self):
        self.monitor = xbmc.Monitor()
        self.interval = 300  # 5 minutes check interval
        self.memory_watchdog = MemoryWatchdog(threshold=85)  # 85% RAM threshold

    def run(self) -> None:
        """Main service loop"""
        Logger.log("Service started")
        while not self.monitor.abortRequested():
            if self.memory_watchdog.is_safe():
                if self._should_run_update():
                    self._safe_update()
            else:
                Logger.warning("Memory threshold exceeded - skipping scan")
                
            if self.monitor.waitForAbort(self.interval):
                break

    def _should_run_update(self) -> bool:
        """Check if scheduled update should run"""
        if not SettingsManager.get_bool('enable_timer'):
            return False
            
        now = datetime.now()
        update_time = SettingsManager.get('update_time', '03:00')
        
        try:
            hour, minute = map(int, update_time.split(':'))
            last_update = SettingsManager.get('last_update')
            
            # Check if current time matches scheduled time
            time_matches = now.hour == hour and now.minute == minute
            
            # Check interval
            interval = SettingsManager.get_int('update_interval', 1)
            if interval == 0:  # Hourly
                return time_matches and (
                    not last_update or 
                    (now - datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S")).seconds >= 3600
                )
            elif interval == 1:  # Daily
                return time_matches and (
                    not last_update or 
                    (now - datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S")).days >= 1
                )
            elif interval == 2:  # Weekly
                return time_matches and now.weekday() == 0 and (
                    not last_update or 
                    (now - datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S")).days >= 7
                )
        except Exception as e:
            Logger.error(f"Schedule check error: {str(e)}")
        return False

    def _safe_update(self) -> None:
        """Run update with memory safety"""
        try:
            UpdateManager.update_playlists_with_mode()
        except MemoryError:
            Logger.error("MemoryError - skipping update")
        except Exception as e:
            Logger.error(f"Update error: {str(e)}")


class MemoryWatchdog:
    """Tracks memory usage and prevents overload"""
    def __init__(self, threshold=85):
        self.threshold = threshold
        
    def is_safe(self):
        try:
            used_mem = xbmc.getInfoLabel('System.Memory(free.percent)')
            return float(used_mem) < self.threshold
        except:
            return True  # Fail-safe

class PlaylistService:
    def __init__(self):
        self.monitor = xbmc.Monitor()
        self.watchdog = MemoryWatchdog(threshold=85)
        self.update_interval = 300  # 5 minutes
        
    def run(self):
        """Main service loop"""
        from default import UpdateManager, Logger, NotificationHandler, SettingsManager
        
        Logger.log("Service started")
        while not self.monitor.abortRequested():
            try:
                if self._should_run_update():
                    UpdateManager.update_playlists_with_mode()
            except Exception as e:
                Logger.error(f"Service error: {str(e)}")
                if SettingsManager.get('operation_mode') == '0':
                    NotificationHandler.show(f"Service error: {str(e)}", error=True)
            
            if self.monitor.waitForAbort(self.update_interval):
                break
    
    def _should_run_update(self):
        from default import SettingsManager
        if not self.watchdog.is_safe():
            return False
            
        if not SettingsManager.get_bool('enable_timer'):
            return False
            
        now = datetime.now()
        interval = SettingsManager.get_int('update_interval', 1)
        update_time = SettingsManager.get('update_time', '03:00')
        
        try:
            hour, minute = map(int, update_time.split(':'))
            last_update_str = SettingsManager.get('last_update')
            last_update = (datetime.strptime(last_update_str, "%Y-%m-%d %H:%M:%S") 
                          if last_update_str and last_update_str != 'Never' else None)
            
            if interval == 0:  # Hourly
                return now.minute == minute and (
                    not last_update or (now - last_update).total_seconds() >= 3600)
            elif interval == 1:  # Daily
                return (now.hour == hour and now.minute == minute and 
                       (not last_update or (now - last_update).total_seconds() >= 86400))
            elif interval == 2:  # Weekly
                return (now.weekday() == 0 and now.hour == hour and now.minute == minute and 
                       (not last_update or (now - last_update).total_seconds() >= 604800))
        except Exception as e:
            from default import Logger
            Logger.error(f"Schedule check error: {str(e)}")
            return False

if __name__ == '__main__':
    service = PlaylistService()
    service.run()