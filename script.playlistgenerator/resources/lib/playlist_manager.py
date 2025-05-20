import os
import re
import random
import xbmcvfs
import urllib.parse
from datetime import datetime
from functools import cmp_to_key
# from typing import Dict, List, Any, Optional, Union # Removed type hint import
import uuid 

import xbmc
import xbmcgui
import xbmcaddon
import json 

import resources.lib.utils as utils
import resources.lib.downloader as downloader

class PlaylistManager:
    def __init__(self):
        self.sets = utils.load_json(utils.CONFIG_FILE)
        self.playlists_generated = 0
        self.files_processed_count = 0
        self.folders_processed_count = 0

    def _get_setting(self, setting_id, default = ''):
        return utils.get_setting(setting_id, default)

    def _get_setting_bool(self, setting_id):
        return self._get_setting(setting_id) == 'true'

    def _get_setting_int(self, setting_id):
        try:
            return int(self._get_setting(setting_id))
        except ValueError:
            return 0

    def _get_setting_float(self, setting_id):
        try:
            return float(self._get_setting(setting_id))
        except ValueError:
            return 0.0

    def _get_current_addon_settings(self):
        return utils.get_all_addon_settings()

    def _show_progress_dialog(self, heading, message):
        dialog = xbmcgui.DialogProgress()
        dialog.create(utils.ADDON_NAME, heading, message)
        return dialog

    def _close_progress_dialog(self, dialog):
        if dialog.iscancelled():
            utils.show_notification(utils.ADDON_NAME, "Operation cancelled.", time=2000)
        dialog.close()

    def _get_file_details(self, path):
        return utils.get_file_details(path)
    
    def _get_folder_content(self, path, scan_depth, exclude_folders, current_depth = 0):
        all_files = []
        try:
            folders, files = xbmcvfs.listdir(path)
            
            # Add files from current directory
            for f in files:
                full_path = xbmcvfs.validatePath(os.path.join(path, f))
                all_files.append(full_path)
                self.files_processed_count += 1
            
            # Recursively scan subfolders
            if scan_depth == 0 or current_depth < scan_depth: # 0 means unlimited depth
                for folder in folders:
                    folder_name = os.path.basename(xbmcvfs.validatePath(os.path.join(path, folder)))
                    if folder_name not in exclude_folders:
                        full_folder_path = xbmcvfs.validatePath(os.path.join(path, folder))
                        self.folders_processed_count += 1
                        all_files.extend(self._get_folder_content(full_folder_path, scan_depth, exclude_folders, current_depth + 1))
        except Exception as e:
            utils.log(f"Error listing directory {path}: {e}", xbmc.LOGERROR)
        return all_files

    def _filter_and_sort_files(self, files, set_settings):
        file_extensions = [ext.strip().lower() for ext in set_settings.get('file_extensions', '.mp4|.mkv|.avi|.mov|.wmv').split('|') if ext.strip()]
        exclude_pattern = set_settings.get('exclude_pattern', 'sample|trailer|bonus').lower()
        min_file_size_mb = self._get_setting_int('min_file_size')
        enable_max_size = self._get_setting_bool('enable_max_size')
        max_file_size_mb = self._get_setting_int('max_file_size')
        enable_date_filter = self._get_setting_bool('enable_date_filter')
        min_file_date_str = self._get_setting('min_file_date', '2000-01-01')
        sort_mode = self._get_setting_int('sort_mode') # 0:Newest, 1:Oldest, 2:A-Z, 3:Z-A, 4:Random, 5:Smallest, 6:Largest, 7:Shortest, 8:Longest

        min_file_date_timestamp = 0
        if enable_date_filter:
            try:
                min_file_date_dt = datetime.strptime(min_file_date_str, '%Y-%m-%d')
                min_file_date_timestamp = min_file_date_dt.timestamp()
            except ValueError:
                utils.log(f"Invalid min_file_date format: {min_file_date_str}", xbmc.LOGWARNING)
                enable_date_filter = False # Disable filter if date is invalid

        filtered_files = []
        for f in files:
            file_name = os.path.basename(f).lower()
            file_ext = os.path.splitext(file_name)[1]

            # Extension filter
            if file_ext not in file_extensions:
                continue
            
            # Exclude pattern filter
            if exclude_pattern and re.search(exclude_pattern, file_name):
                continue
            
            # Get file details for size/date filters
            details = self._get_file_details(f)
            file_size_mb = details['size'] / (1024 * 1024) if details['size'] is not None else 0
            file_creation_time = details['creation_time']

            # Size filter
            if min_file_size_mb > 0 and file_size_mb < min_file_size_mb:
                continue
            if enable_max_size and max_file_size_mb > 0 and file_size_mb > max_file_size_mb:
                continue
            
            # Date filter
            if enable_date_filter and file_creation_time < min_file_date_timestamp:
                continue
            
            filtered_files.append((f, details)) # Store full
            
        # Sort files based on sort_mode
        if sort_mode == 0: # Newest First (creation_time)
            filtered_files.sort(key=lambda x: x[1]['creation_time'], reverse=True)
        elif sort_mode == 1: # Oldest First (creation_time)
            filtered_files.sort(key=lambda x: x[1]['creation_time'])
        elif sort_mode == 2: # A-Z (filename)
            filtered_files.sort(key=lambda x: os.path.basename(x[0]).lower())
        elif sort_mode == 3: # Z-A (filename)
            filtered_files.sort(key=lambda x: os.path.basename(x[0]).lower(), reverse=True)
        elif sort_mode == 4: # Random
            random.shuffle(filtered_files)
        elif sort_mode == 5: # Smallest First (size)
            filtered_files.sort(key=lambda x: x[1]['size'])
        elif sort_mode == 6: # Largest First
            filtered_files.sort(key=lambda x: x[1]['size'], reverse=True)
        elif sort_mode == 7: # Shortest First (duration)
            filtered_files.sort(key=lambda x: x[1]['duration'])
        elif sort_mode == 8: # Longest First (duration)
            filtered_files.sort(key=lambda x: x[1]['duration'], reverse=True)

        return [f[0] for f in filtered_files] # Return only file paths

    def _apply_playlist_limit_and_rotation(self, files):
        enable_playlist_limit = self._get_setting_bool('enable_playlist_limit')
        limit_mode = self._get_setting_int('limit_mode') # 0:Number of files, 1:Total file count (bytes)
        file_count_limit = self._get_setting_int('file_count')
        total_file_count_limit = self._get_setting_int('total_file_count') # in bytes
        enable_rotation = self._get_setting_bool('enable_rotation')
        rotation_offset = self._get_setting_int('rotation_offset')

        if not enable_playlist_limit:
            return files

        limited_files = []
        if limit_mode == 0: # Number of files
            limited_files = files[:file_count_limit]
        elif limit_mode == 1: # Total file count (bytes)
            current_size = 0
            for f in files:
                details = self._get_file_details(f)
                file_size = details['size'] if details['size'] is not None else 0
                if current_size + file_size <= total_file_count_limit:
                    limited_files.append(f)
                    current_size += file_size
                else:
                    break
        
        if enable_rotation and len(limited_files) > 0:
            offset = rotation_offset % len(limited_files)
            limited_files = limited_files[offset:] + limited_files[:offset]

        return limited_files

    def _create_playlist_file(self, set_name, playlist_files, folder_name_color_enabled, folder_name_color):
        playlist_filename = utils.generate_playlist_filename(set_name)
        playlist_full_path = os.path.join(utils.PLAYLIST_DIR, playlist_filename)
        
        # Ensure playlist directory exists
        if not xbmcvfs.exists(utils.PLAYLIST_DIR):
            xbmcvfs.mkdirs(utils.PLAYLIST_DIR)

        # Write to M3U8 format
        with xbmcvfs.File(playlist_full_path, 'w') as f:
            f.write("#EXTM3U\n")
            for file_path in playlist_files:
                display_name = os.path.basename(file_path)
                folder_path = os.path.dirname(file_path)
                folder_name = os.path.basename(folder_path)

                # Apply folder name color if enabled
                if folder_name_color_enabled and folder_name_color:
                    display_name = f"[{folder_name_color}]{folder_name}[/{folder_name_color}] {display_name}"
                
                # Use JSON-RPC to get duration if available and prepend to display name
                details = self._get_file_details(file_path)
                duration_seconds = details.get('duration')
                if duration_seconds is not None:
                    # Convert seconds to HH:MM:SS format
                    minutes, seconds = divmod(duration_seconds, 60)
                    hours, minutes = divmod(minutes, 60)
                    duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"
                    display_name = f"#EXTINF:{duration_seconds},{display_name} [{duration_str}]\n"
                else:
                    display_name = f"#EXTINF:-1,{display_name}\n" # -1 for unknown duration

                f.write(display_name)
                f.write(f"{file_path}\n")
        utils.log(f"Playlist '{playlist_filename}' created at '{playlist_full_path}' with {len(playlist_files)} files.", xbmc.LOGINFO)

    def create_playlist(self, set_id):
        if set_id not in self.sets:
            utils.show_ok_dialog(utils.ADDON_NAME, "Folder Set not found.")
            return

        current_set = self.sets[set_id]
        set_name = current_set.get("name", "Unknown Set")
        paths_to_scan = current_set.get("paths", [])
        
        if not paths_to_scan:
            utils.show_ok_dialog(utils.ADDON_NAME, f"Folder Set '{set_name}' has no paths defined. Please add paths via 'Manage Folder Sets'.")
            return

        progress_dialog = self._show_progress_dialog("Generating Playlist", f"Scanning files for '{set_name}'...")
        self.files_processed_count = 0
        self.folders_processed_count = 0
        
        try:
            # Gather all files from specified paths
            all_raw_files = []
            scan_depth_setting = self._get_setting_int('scan_depth')
            exclude_folders_raw = self._get_setting('exclude_folders', '')
            exclude_folders_list = [f.strip() for f in exclude_folders_raw.split('|') if f.strip()]

            for i, path in enumerate(paths_to_scan):
                if progress_dialog.iscancelled():
                    break
                progress_dialog.update(int((i / len(paths_to_scan)) * 50), f"Scanning folder {i+1}/{len(paths_to_scan)}", path)
                all_raw_files.extend(self._get_folder_content(path, scan_depth_setting, exclude_folders_list))

            if progress_dialog.iscancelled():
                return
            
            progress_dialog.update(50, "Filtering and Sorting Files", f"Found {len(all_raw_files)} raw files.")

            # Filter and sort files
            filtered_sorted_files = self._filter_and_sort_files(all_raw_files, self._get_current_addon_settings())

            progress_dialog.update(75, "Applying Limits and Rotation", f"Filtered to {len(filtered_sorted_files)} files.")

            # Apply playlist limits and rotation
            final_playlist_files = self._apply_playlist_limit_and_rotation(filtered_sorted_files)

            if not final_playlist_files:
                utils.show_ok_dialog(utils.ADDON_NAME, f"No files found matching criteria for Folder Set '{set_name}'.")
                return

            progress_dialog.update(90, "Creating Playlist File", f"Generating playlist with {len(final_playlist_files)} files.")

            # Get display settings
            folder_name_color_enabled = self._get_setting_bool('enable_display_name_color')
            folder_name_color = self._get_setting('folder_name_color', 'blue')

            # Create playlist file
            self._create_playlist_file(set_name, final_playlist_files, folder_name_color_enabled, folder_name_color)
            utils.show_notification(utils.ADDON_NAME, f"Playlist '{set_name}' created successfully!", time=3000)
            self.playlists_generated += 1

        except Exception as e:
            utils.log(f"Error creating playlist for '{set_name}': {e}", xbmc.LOGERROR)
            utils.show_ok_dialog(utils.ADDON_NAME, f"An error occurred: {e}")
        finally:
            self._close_progress_dialog(progress_dialog)
            utils.log(f"Playlist generation finished for '{set_name}'. Files processed: {self.files_processed_count}, Folders processed: {self.folders_processed_count}", xbmc.LOGINFO)

    def quick_scan(self):
        """Performs a quick scan without creating a playlist."""
        utils.show_notification(utils.ADDON_NAME, "Quick Scan initiated...", time=2000)
        progress_dialog = self._show_progress_dialog("Quick Scan", "Scanning files...")
        self.files_processed_count = 0
        self.folders_processed_count = 0

        try:
            # Get all active sets
            active_sets = [s for s in self.sets.values() if s.get('active', True)]
            if not active_sets:
                utils.show_ok_dialog(utils.ADDON_NAME, "No active Folder Sets to scan.")
                return

            all_raw_files = []
            scan_depth_setting = self._get_setting_int('scan_depth')
            exclude_folders_raw = self._get_setting('exclude_folders', '')
            exclude_folders_list = [f.strip() for f in exclude_folders_raw.split('|') if f.strip()]

            total_paths = sum(len(s.get('paths', [])) for s in active_sets)
            current_path_idx = 0

            for s_idx, current_set in enumerate(active_sets):
                set_name = current_set.get("name", "Unknown Set")
                paths_to_scan = current_set.get("paths", [])
                
                for p_idx, path in enumerate(paths_to_scan):
                    if progress_dialog.iscancelled():
                        break
                    current_path_idx += 1
                    progress = int((current_path_idx / total_paths) * 100)
                    progress_dialog.update(progress, f"Scanning set '{set_name}' ({s_idx+1}/{len(active_sets)})", path)
                    
                    all_raw_files.extend(self._get_folder_content(path, scan_depth_setting, exclude_folders_list))
                if progress_dialog.iscancelled():
                    break
            
            if progress_dialog.iscancelled():
                return
            
            utils.show_ok_dialog(utils.ADDON_NAME, f"Quick Scan Complete!\\nFound {len(all_raw_files)} files in {len(active_sets)} active sets.\\nProcessed {self.files_processed_count} files and {self.folders_processed_count} folders.")

        except Exception as e:
            utils.log(f"Error during quick scan: {e}", xbmc.LOGERROR)
            utils.show_ok_dialog(utils.ADDON_NAME, f"An error occurred during Quick Scan: {e}")
        finally:
            self._close_progress_dialog(progress_dialog)
            utils.log(f"Quick Scan finished. Files processed: {self.files_processed_count}, Folders processed: {self.folders_processed_count}", xbmc.LOGINFO)

    def update_all_sets(self):
        """Updates all active playlists."""
        utils.show_notification(utils.ADDON_NAME, "Updating all active playlists...", time=2000)
        progress_dialog = self._show_progress_dialog("Updating All Playlists", "Initializing...")

        active_sets = [s_id for s_id, s in self.sets.items() if s.get('active', True)]
        if not active_sets:
            utils.show_ok_dialog(utils.ADDON_NAME, "No active Folder Sets to update.")
            return

        try:
            for i, set_id in enumerate(active_sets):
                if progress_dialog.iscancelled():
                    utils.show_notification(utils.ADDON_NAME, "Update all playlists cancelled.", time=2000)
                    break
                
                set_name = self.sets[set_id].get("name", "Unknown Set")
                progress_dialog.update(int((i / len(active_sets)) * 100), f"Updating playlist: {set_name}", f"Set {i+1} of {len(active_sets)}")
                self.create_playlist(set_id) # Call individual playlist creation
            
            if not progress_dialog.iscancelled():
                utils.show_ok_dialog(utils.ADDON_NAME, "All active playlists updated successfully!")

        except Exception as e:
            utils.log(f"Error updating all playlists: {e}", xbmc.LOGERROR)
            utils.show_ok_dialog(utils.ADDON_NAME, f"An error occurred while updating all playlists: {e}")
        finally:
            self._close_progress_dialog(progress_dialog)

    def manage_sets(self):
        while True:
            # Refresh sets list
            self.sets = utils.load_json(utils.CONFIG_FILE) # Always load fresh
            
            set_choices = [f"{s['name']}{' (Active)' if s.get('active', True) else ' (Inactive)'}" for s in self.sets.values()]
            
            # Add option to create a new set if there are existing ones, or just show create if empty
            if not set_choices:
                menu_options = ["Create New Folder Set"]
            else:
                menu_options = ["Create New Folder Set"] + set_choices

            set_selection = utils.DIALOG.select(utils.ADDON_NAME, menu_options)
            
            if set_selection == -1: # User cancelled
                break # Exit manage_sets

            if set_selection == 0: # Create New Set
                self._create_or_edit_set() # This will handle creation
            else:
                # Adjust index for "Create New Set" option at index 0
                selected_set_id = list(self.sets.keys())[set_selection - 1] 
                self._create_or_edit_set(set_id=selected_set_id)
            
        utils.log("Exiting manage_sets menu", xbmc.LOGINFO)

    def _create_or_edit_set(self, set_id = None):
        is_new_set = set_id is None
        current_set = self.sets.get(set_id, {"name": "", "paths": [], "active": True})

        set_name = current_set["name"]
        if is_new_set or not set_name:
            # Prompt for new set name
            keyboard = xbmc.Keyboard(set_name, "Enter Folder Set Name")
            keyboard.doModal()
            if keyboard.isConfirmed():
                set_name = keyboard.getText().strip() # Strip whitespace
                if not set_name:
                    utils.show_ok_dialog(utils.ADDON_NAME, "Folder Set name cannot be empty.")
                    return
                
                # Check for duplicate name if creating a new set or renaming existing one
                existing_names = [s['name'] for s_id_temp, s in self.sets.items() if s_id_temp != set_id]
                if set_name in existing_names:
                    utils.show_ok_dialog(utils.ADDON_NAME, "A Folder Set with this name already exists. Please choose a different name.")
                    return 
            else:
                return 
        
        # Ensure set_id exists for new sets and update name for current set
        if is_new_set:
            set_id = str(uuid.uuid4())
            current_set["id"] = set_id
        current_set["name"] = set_name 

        # Ensure active status is set for new sets (if not already present)
        if "active" not in current_set:
            curr
