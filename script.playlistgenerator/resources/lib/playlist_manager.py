import os
import re
import random
import xbmcvfs
import urllib.parse
from datetime import datetime
from functools import cmp_to_key
from typing import Dict, List, Any, Optional
import uuid

import xbmc
import xbmcgui
import xbmcaddon

import resources.lib.utils as utils
import resources.lib.downloader as downloader

class PlaylistManager:
    def __init__(self) -> None:
        self.sets: Dict[str, Any] = utils.load_json(utils.CONFIG_FILE)
        self.playlists_generated = 0
        self.files_processed_count = 0
        self.folders_processed_count = 0
        self.current_set_id: Optional[str] = None
        self.dialog = xbmcgui.Dialog()

    # Removed _get_setting method, now directly using utils.get_setting with type string

    def create_playlist(self) -> None:
        dialog = xbmcgui.Dialog()
        
        # Get set names for multiselect
        set_names = [name for name in self.sets.values()]
        # Kodi dialog.multiselect requires a list of strings, so use set names directly
        display_set_names = [s.get('name', k) for k, s in self.sets.items()] # Use set 'name' if available, otherwise key
        
        source_indices = dialog.multiselect("Select Folder Sets to Include", display_set_names)
        if not source_indices:
            return # User cancelled

        selected_set_ids = [list(self.sets.keys())[i] for i in source_indices]
        
        playlist_name = dialog.input("Enter Playlist Name", default="My Playlist") 
        if not playlist_name:
            return # User cancelled

        playlist_file = os.path.join(utils.PLAYLIST_DIR, f"{playlist_name}.m3u")

        # Retrieve settings using the new utils.get_setting
        sort_mode = utils.get_setting('sort_mode', 'enum') # 0: Random, 1: Creation Date Asc, 2: Creation Date Desc, etc.
        enable_limit = utils.get_setting('enable_playlist_limit', 'bool')
        limit_by_method = utils.get_setting('limit_by_method', 'enum') # 0: Max Files Playlist, 1: Max Total Size, 2: Max Files Folder, 3: Scan Depth
        max_files_playlist = utils.get_setting('max_files_playlist', 'number')
        max_total_size_playlist_mb = utils.get_setting('max_total_size_playlist', 'number')
        max_files_folder = utils.get_setting('max_files_folder', 'number')
        scan_depth_setting = utils.get_setting('scan_depth', 'number') # This will be passed to get_video_files_in_directory

        # General filters from settings
        file_extensions = [ext.strip() for ext in utils.get_setting('file_extensions', 'text').split(',') if ext.strip()]
        min_file_size_mb = utils.get_setting('min_file_size', 'number')
        exclude_pattern = utils.get_setting('exclude_pattern', 'text')
        
        playlist_entries = [] # List of dictionaries {path, size, ctime}

        for set_id in selected_set_ids:
            set_config = self.sets.get(set_id)
            if set_config:
                path = set_config.get('path', '')
                randomize_set = set_config.get('randomize', False)
                
                # Determine scan depth for this specific set
                # If 'Scan Depth' limit method is selected, use that value, otherwise use set's recursive or -1 (unlimited)
                current_set_scan_depth = -1 # Unlimited by default
                if enable_limit and limit_by_method == 3: # If 'Scan Depth' is chosen as the limit method
                    current_set_scan_depth = scan_depth_setting
                elif not set_config.get('recursive', False): # If not recursive in set config, limit to current folder only
                    current_set_scan_depth = 0

                # Use the new robust file collection function
                files_in_set = utils.get_video_files_in_directory(
                    path,
                    file_extensions,
                    min_file_size_mb,
                    exclude_pattern,
                    current_set_scan_depth
                )
                
                if randomize_set:
                    random.shuffle(files_in_set)
                
                # Apply 'Max Files Per Folder' limit if enabled and applicable
                if enable_limit and limit_by_method == 2 and max_files_folder > 0:
                    # Group files by their immediate parent folder to apply limit per folder
                    files_by_folder: Dict[str, List[Dict[str, Any]]] = {}
                    for f_info in files_in_set:
                        folder = os.path.dirname(f_info['path'])
                        if folder not in files_by_folder:
                            files_by_folder[folder] = []
                        files_by_folder[folder].append(f_info)
                    
                    limited_files_in_set = []
                    for folder, files_list in files_by_folder.items():
                        limited_files_in_set.extend(files_list[:max_files_folder])
                    playlist_entries.extend(limited_files_in_set)
                else:
                    playlist_entries.extend(files_in_set)

        # Apply overall sorting to the combined list of files
        self._apply_sorting(playlist_entries, sort_mode)

        with open(playlist_file, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            entry_count = 0
            total_size_bytes = 0
            
            # Display settings
            show_file_size_display = utils.get_setting('show_file_size_display', 'bool')
            path_display_level = utils.get_setting('path_display_level', 'enum') # 0: Full, 1: Relative, 2: Filename Only
            item_numbering_display = utils.get_setting('item_numbering_display', 'bool')

            for file_info in playlist_entries:
                file_path = file_info['path']
                file_size = file_info['size'] # in bytes

                if enable_limit:
                    if limit_by_method == 0 and entry_count >= max_files_playlist: # Max Files Per Playlist
                        utils.log(f"Playlist limit reached (max files): {entry_count}/{max_files_playlist}", xbmc.LOGDEBUG)
                        break
                    elif limit_by_method == 1 and total_size_bytes >= max_total_size_playlist_mb * 1024 * 1024: # Max Total Size (MB) Per Playlist
                        utils.log(f"Playlist limit reached (max size): {total_size_bytes / (1024*1024):.2f}MB/{max_total_size_playlist_mb}MB", xbmc.LOGDEBUG)
                        break
                    # Scan Depth and Max Files Per Folder are applied during file collection for the set

                display_name = self._format_playlist_entry_name(file_path, show_file_size_display, path_display_level)
                
                if item_numbering_display:
                    display_name = f"{entry_count + 1}. {display_name}"

                f.write(f"#EXTINF:-1,{display_name}\n")
                f.write(f"{file_path}\n")
                entry_count += 1
                total_size_bytes += file_size

        self.playlists_generated += 1
        utils.show_ok_dialog(utils.ADDON_NAME, f"Playlist '{playlist_name}.m3u' created in {utils.PLAYLIST_DIR}. Found {entry_count} files.")

    def _apply_sorting(self, playlist_entries: List[Dict[str, Any]], sort_mode: int) -> None:
        """Applies sorting to the list of file dictionaries."""
        if sort_mode == 0: # Random
            random.shuffle(playlist_entries)
        elif sort_mode == 1: # Creation Date Ascending
            playlist_entries.sort(key=lambda x: x['ctime'])
        elif sort_mode == 2: # Creation Date Descending
            playlist_entries.sort(key=lambda x: x['ctime'], reverse=True)
        elif sort_mode == 3: # File Size Ascending
            playlist_entries.sort(key=lambda x: x['size'])
        elif sort_mode == 4: # File Size Descending
            playlist_entries.sort(key=lambda x: x['size'], reverse=True)
        elif sort_mode == 5: # Name Ascending
            playlist_entries.sort(key=lambda x: os.path.basename(x['path']).lower())
        elif sort_mode == 6: # Name Descending
            playlist_entries.sort(key=lambda x: os.path.basename(x['path']).lower(), reverse=True)

    def _format_playlist_entry_name(self, file_path: str, show_file_size: bool, path_display_level: int) -> str:
        """Formats the display name for a playlist entry based on settings."""
        filename_with_ext = os.path.basename(file_path)
        filename_base, ext = os.path.splitext(filename_with_ext)
        
        display_name = filename_base

        if path_display_level == 0: # Full Path
            display_name = file_path
        elif path_display_level == 1: # Relative Path (relative to the set's base path for clarity, though not directly implemented here as a dynamic relative path)
            # For simplicity, will show parent folder + filename, or full path if no good relative base exists
            # A more robust relative path would need the set's base path to calculate
            parent_folder = os.path.basename(os.path.dirname(file_path))
            display_name = f"{parent_folder}/{filename_with_ext}" if parent_folder else filename_with_ext
        elif path_display_level == 2: # Filename Only
            display_name = filename_with_ext # Use filename with extension

        # Apply folder name prefixing (color, etc.)
        show_folder_name_in_playlist = utils.get_setting('show_foldername_in_playlist', 'bool')
        if show_folder_name_in_playlist:
            folder_name_prefix = ""
            if utils.get_setting('color_foldername', 'bool'):
                folder_name = os.path.basename(os.path.dirname(file_path))
                cleaned_folder_name = re.sub(r'\W+', ' ', folder_name).strip() # Clean folder name
                color_code = utils.get_setting('foldername_color', 'color')
                folder_name_prefix = f"[COLOR {color_code}]{cleaned_folder_name}[/COLOR] - "
            else:
                folder_name = os.path.basename(os.path.dirname(file_path))
                if folder_name: # Only add if folder name exists
                    folder_name_prefix = f"{folder_name} - "
            
            # Combine prefix with the chosen path display level
            if path_display_level == 0: # Full path
                # If showing full path, a separate folder name prefix makes less sense, so we will prepend to just the filename_base
                # Or, if path_display_level is full path, folder_name_prefix is redundant.
                # Let's adjust this: if full path, don't add the separate folder_name_prefix.
                pass # Already handled by full path display
            elif path_display_level == 1: # Relative path
                display_name = f"{folder_name_prefix}{filename_base}" if folder_name_prefix else filename_base
            else: # Filename Only (and default case)
                display_name = f"{folder_name_prefix}{filename_base}" if folder_name_prefix else filename_base
        
        # Apply download filename cleanup, but only the regex parts for display name consistency
        # Assuming the cleanup settings (delete_words, switch_words) are not intended for display names
        # We need to retrieve regex settings for display name if applicable, or assume they are for download only.
        # Based on original, `clean_filename_for_playlist` *was* calling `downloader.clean_download_filename`
        # Let's simplify this and only apply cleanup to the base filename for display purposes,
        # not the full path if that's what path_display_level dictates.

        # The existing logic `clean_filename_for_playlist` takes `file_path` and `show_folder_name`.
        # It then cleans `filename_with_ext` or `filename`.
        # I need to ensure the cleaning logic is applied to the *base* filename before display name formation.
        
        final_cleaned_filename = self._apply_filename_cleanup_for_display(filename_base, file_path) # Pass file_path for adult cleanup check
        
        if show_folder_name_in_playlist:
            folder_name_prefix = ""
            if utils.get_setting('color_foldername', 'bool'):
                folder_path_name = os.path.basename(os.path.dirname(file_path))
                cleaned_folder_name = re.sub(r'\W+', ' ', folder_path_name).strip()
                color_code = utils.get_setting('foldername_color', 'color')
                folder_name_prefix = f"[COLOR {color_code}]{cleaned_folder_name}[/COLOR] - "
            else:
                folder_path_name = os.path.basename(os.path.dirname(file_path))
                if folder_path_name:
                    folder_name_prefix = f"{folder_path_name} - "
            
            # Apply folder name prefix to the cleaned filename base
            if path_display_level == 0: # Full Path: folder name prefix is typically not prepended to full paths.
                display_name_content = file_path # Keep full path
            elif path_display_level == 1: # Relative Path: show parent folder + cleaned filename
                parent_folder_name = os.path.basename(os.path.dirname(file_path))
                display_name_content = f"{parent_folder_name}/{final_cleaned_filename}{ext}" if parent_folder_name else f"{final_cleaned_filename}{ext}"
            else: # Filename Only (path_display_level == 2 and default)
                display_name_content = f"{final_cleaned_filename}{ext}"

            # If folder name prefix is desired, add it now.
            if folder_name_prefix and path_display_level != 0: # Don't prepend folder prefix if full path is chosen
                display_name = f"{folder_name_prefix}{display_name_content}"
            else:
                display_name = display_name_content # Already includes full path or just filename with ext
        else:
            # If folder name not desired, use the chosen path display level directly on the cleaned filename
            if path_display_level == 0: # Full Path
                display_name = file_path
            elif path_display_level == 1: # Relative Path
                parent_folder_name = os.path.basename(os.path.dirname(file_path))
                display_name = f"{parent_folder_name}/{final_cleaned_filename}{ext}" if parent_folder_name else f"{final_cleaned_filename}{ext}"
            else: # Filename Only (path_display_level == 2 and default)
                display_name = f"{final_cleaned_filename}{ext}"


        if show_file_size:
            # Convert bytes to MB for display
            size_mb = file_size / (1024 * 1024)
            display_name = f"{display_name} ({size_mb:.2f} MB)"

        return display_name


    def _apply_filename_cleanup_for_display(self, filename_base: str, file_path: str) -> str:
        """Applies filename cleaning logic (subset of downloader.clean_download_filename) for display purposes."""
        cleaned_filename = filename_base

        # Only apply global cleanup if enabled (download_filename_cleanup)
        if utils.get_setting('download_filename_cleanup', 'bool'):
            delete_words_str = utils.get_setting('download_filename_delete_words', 'text')
            switch_words_str = utils.get_setting('download_filename_switch_words', 'text')
            use_regex = utils.get_setting('download_filename_regex', 'bool')
            regex_pattern = utils.get_setting('download_filename_regex_pattern', 'text')
            regex_replace_with = utils.get_setting('download_filename_regex_replace', 'text')

            # Delete words
            if delete_words_str:
                delete_words = [w.strip() for w in delete_words_str.split('|') if w.strip()]
                for word in delete_words:
                    cleaned_filename = re.sub(r'\b' + re.escape(word) + r'\b', '', cleaned_filename, flags=re.IGNORECASE).strip()
            
            # Switch words
            if switch_words_str:
                switch_pairs = {}
                for pair in switch_words_str.split('|'):
                    if '=' in pair:
                        old, new = pair.split('=', 1)
                        switch_pairs[old.strip()] = new.strip()
                
                for old_word, new_word in switch_pairs.items():
                    cleaned_filename = re.sub(r'\b' + re.escape(old_word) + r'\b', new_word, cleaned_filename, flags=re.IGNORECASE).strip()

            # Apply regex
            if use_regex and regex_pattern:
                try:
                    cleaned_filename = re.sub(regex_pattern, regex_replace_with, cleaned_filename).strip()
                except re.error as e:
                    utils.log(f"Invalid regex pattern for display cleanup '{regex_pattern}': {e}", xbmc.LOGERROR)

        # Adult content cleanup if enabled
        if utils.get_setting('enable_adult_cleanup', 'bool') and utils.get_setting('adult_content_indicator', 'text') in file_path.lower():
            adult_delete_words_str = utils.get_setting('adult_delete_words', 'text')
            adult_switch_words_str = utils.get_setting('adult_switch_words', 'text')

            if adult_delete_words_str:
                adult_delete_words = [w.strip() for w in adult_delete_words_str.split('|') if w.strip()]
                for word in adult_delete_words:
                    cleaned_filename = re.sub(r'\b' + re.escape(word) + r'\b', '', cleaned_filename, flags=re.IGNORECASE).strip()

            if adult_switch_words_str:
                adult_switch_pairs = {}
                for pair in adult_switch_words_str.split('|'):
                    if '=' in pair:
                        old, new = pair.split('=', 1)
                        adult_switch_pairs[old.strip()] = new.strip()
                
                for old_word, new_word in adult_switch_pairs.items():
                    cleaned_filename = re.sub(r'\b' + re.escape(old_word) + r'\b', new_word, cleaned_filename, flags=re.IGNORECASE).strip()
        
        return cleaned_filename.strip() # Final strip

    # quick_scan method has been removed as per plan

    def manage_sets(self) -> None:
        # Use existing set names for display, and map back to IDs
        current_set_ids = list(self.sets.keys())
        display_items = ["Create New Set"] + [f"Edit: {self.sets[key].get('name', key)}" for key in current_set_ids] + [f"Delete: {self.sets[key].get('name', key)}" for key in current_set_ids]
        
        choice = xbmcgui.Dialog().select("Manage Folder Sets", display_items)

        if choice == -1: # Escape button pressed
            return

        if choice == 0: # Create New Set
            self._create_or_edit_set()
        elif choice > 0 and choice <= len(current_set_ids): # Edit existing set
            set_id_to_edit = current_set_ids[choice - 1]
            self._create_or_edit_set(set_id_to_edit)
        elif choice > len(current_set_ids): # Delete existing set
            set_id_to_delete = current_set_ids[choice - 1 - len(current_set_ids)]
            set_name_to_delete = self.sets[set_id_to_delete].get('name', set_id_to_delete)
            if xbmcgui.Dialog().yesno("Delete Set", f"Are you sure you want to delete '{set_name_to_delete}'?"):
                del self.sets[set_id_to_delete]
                utils.save_json(utils.CONFIG_FILE, self.sets)
                utils.show_notification(utils.ADDON_NAME, f"Set '{set_name_to_delete}' deleted.")

    def _create_or_edit_set(self, set_id: Optional[str] = None) -> None:
        is_new_set = set_id is None
        current_set_data = {"name": "", "path": "", "recursive": False, "randomize": False}
        
        if not is_new_set:
            current_set_data = self.sets.get(set_id, current_set_data)
        
        initial_set_name = current_set_data.get('name', '')

        new_set_name = self.dialog.input("Enter Set Name", initial_set_name)
        
        if new_set_name:
            if not new_set_name.strip():
                utils.show_notification(utils.ADDON_NAME, "Set name cannot be empty.", time=1500)
                return

            # Check for duplicate names (excluding current set if editing)
            is_duplicate = False
            for existing_id, existing_data in self.sets.items():
                if existing_id != set_id and existing_data.get('name') == new_set_name:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                utils.show_notification(utils.ADDON_NAME, f"Set name '{new_set_name}' already exists. Please choose a different name.", time=3000)
                return

            current_set_data['name'] = new_set_name 

            selected_path = self.dialog.browse(3, "Select Folder Path", 'files', '', current_set_data.get('path', ''))
            
            if selected_path:
                current_set_data['path'] = selected_path
            else:
                utils.show_notification(utils.ADDON_NAME, "Folder selection cancelled. Set will not be saved without a path.", time=3000)
                return

            current_set_data['recursive'] = self.dialog.yesno("Scan Subfolders?", "Do you want to include files in subfolders?")
            current_set_data['randomize'] = self.dialog.yesno("Randomize Playback?", "Play files in this set randomly?")

            final_set_id = set_id if not is_new_set else str(uuid.uuid4())
            
            self.sets[final_set_id] = current_set_data
            utils.save_json(utils.CONFIG_FILE, self.sets)
            utils.show_notification(utils.ADDON_NAME, f"Set '{new_set_name}' saved.")
        else:
            utils.show_notification(utils.ADDON_NAME, "Set creation/edit cancelled or name was empty.", time=1500)


    def update_all_sets(self) -> None:
        utils.show_notification(utils.ADDON_NAME, "Updating all sets...", time=2000)
        file_extensions = [ext.strip() for ext in utils.get_setting('file_extensions', 'text').split(',') if ext.strip()]
        min_file_size_mb = utils.get_setting('min_file_size', 'number')
        exclude_pattern = utils.get_setting('exclude_pattern', 'text')

        # When updating all sets, typically we want to scan the full configured path of the set,
        # so scan_depth will be -1 (unlimited) unless the set itself is explicitly not recursive.
        for set_id, config in self.sets.items():
            name = config.get('name', set_id)
            path = config.get('path', '')
            recursive = config.get('recursive', False)
            
            # For update_all_sets, we apply the set's recursive setting as the scan_depth
            set_scan_depth = -1 if recursive else 0 # -1 for unlimited, 0 for current folder only

            files_in_set = utils.get_video_files_in_directory(
                path,
                file_extensions,
                min_file_size_mb,
                exclude_pattern,
                set_scan_depth
            )
            utils.log(f"Found {len(files_in_set)} files in set '{name}'.")
        utils.show_notification(utils.ADDON_NAME, "All sets updated (files re-indexed).", time=1500)

    # _collect_files_for_playlist method has been removed as its functionality is now in utils.get_video_files_in_directory
    # clean_filename_for_playlist is also removed as it's been integrated into _format_playlist_entry_name for display