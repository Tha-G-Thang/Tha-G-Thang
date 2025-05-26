import os
import re
import random
import xbmcvfs
import xbmc 

from resources.lib.utils import get_setting, log, get_bool_setting, ai_log # Added get_bool_setting, ai_log

class Sorter:
    def apply_sorting(self, files_info): 
        log(f"Applying sorting to {len(files_info)} files.")
        if not files_info:
            return []

        try:
            # Group by folder first
            folder_groups = {}
            for file_info in files_info:
                folder_path = os.path.dirname(file_info['path'])
                if folder_path not in folder_groups:
                    folder_groups[folder_path] = []
                folder_groups[folder_path].append(file_info)

            # Sort folders
            sorted_folder_paths = sorted(folder_groups.keys(), key=self._get_folder_sort_key, reverse=get_setting('folder_sort_mode', '0') == '2')

            result_files = []
            for folder_path in sorted_folder_paths:
                files_in_current_folder = folder_groups[folder_path]

                # Apply exclude patterns for files within folders
                exclude_pattern = get_setting('exclude_pattern', '')
                exclude_patterns = [p.strip().lower() for p in exclude_pattern.split(',') if p.strip()]\

                filtered_files = []
                for file_info in files_in_current_folder:
                    filename = os.path.basename(file_info['path']).lower()
                    if not any(excluded in filename for excluded in exclude_patterns):
                        # Apply AI-based filtering here if a setting like 'filter_by_ai_tags' existed
                        # Example: if 'ai_tags' in file_info and 'unwanted_tag' in file_info['ai_tags']: continue
                        filtered_files.append(file_info)
                
                # Apply file-specific sorting within each folder
                file_sort_mode = get_setting('file_sort_mode', '0')
                if file_sort_mode == '0': # Original (A-Z)
                    files_in_current_folder_sorted = sorted(filtered_files, key=lambda f: os.path.basename(f['path']).lower())
                elif file_sort_mode == '1': # Newest (by modification date)
                    files_in_current_folder_sorted = sorted(filtered_files, key=lambda f: f.get('modification_date', 0), reverse=True)
                elif file_sort_mode == '2': # Oldest (by modification date)
                    files_in_current_folder_sorted = sorted(filtered_files, key=lambda f: f.get('modification_date', 0))
                elif file_sort_mode == '3': # Random
                    random.shuffle(filtered_files)
                    files_in_current_folder_sorted = filtered_files
                elif file_sort_mode == '4': # AI Cluster (New Sorting Mode)
                    if get_bool_setting('enable_ai_smart_playlists', False): # Only if AI clustering is enabled
                        ai_log(f"Sorting files in folder {folder_path} by AI Cluster ID.")
                        # Sort by AI cluster ID first, then alphabetically by filename for stability
                        files_in_current_folder_sorted = sorted(filtered_files, key=lambda f: (f.get('ai_cluster_id', -1), os.path.basename(f['path']).lower()))
                    else:
                        ai_log(f"AI Smart Playlists not enabled, falling back to A-Z for AI Cluster mode.")
                        files_in_current_folder_sorted = sorted(filtered_files, key=lambda f: os.path.basename(f['path']).lower())
                else: # Default to A-Z
                    files_in_current_folder_sorted = sorted(filtered_files, key=lambda f: os.path.basename(f['path']).lower())

                # Apply 'newest files per folder to top' if enabled
                newest_count = get_int_setting('newest_files_per_folder_to_top_count', 0)
                if newest_count > 0:
                    # Sort files by modification date in reverse for this specific feature
                    temp_sorted_by_date = sorted(files_in_current_folder_sorted, key=lambda f: f.get('modification_date', 0), reverse=True)
                    top_n_newest = temp_sorted_by_date[:newest_count]
                    # Filter out top N from the rest of the list without changing their relative order
                    rest_of_files = [f for f in files_in_current_folder_sorted if f not in top_n_newest]
                    files_in_current_folder_sorted = top_n_newest + rest_of_files

                result_files.extend(files_in_current_folder_sorted)

            # Apply global file limit
            enable_global_file_limit = get_bool_setting('enable_global_file_limit', False)
            global_file_count = get_int_setting('global_file_count', 0)
            if enable_global_file_limit and global_file_count > 0:
                result_files = result_files[:global_file_count]

            log(f"Total files after sorting and limiting: {len(result_files)}")
            return result_files

        except Exception as e:
            log(f"Error in Sorter.apply_sorting: {e}", xbmc.LOGERROR)
            return files_info 


    def _get_folder_sort_key(self, folder_path):
        folder_mode = get_setting('folder_sort_mode', '0') # 0: None (A-Z), 1: A-Z, 2: Z-A, 3: Custom
        folder_name = os.path.basename(folder_path.rstrip(os.sep)).lower()

        if folder_mode == '1': # A-Z
            return (0, folder_name) # Tuple for stable sorting
        elif folder_mode == '2': # Z-A
            return (0, folder_name) 
        elif folder_mode == '3': # Custom
            custom_order = [f.strip().lower() for f in get_setting('custom_folder_order', '').split(',') if f.strip()]
            try:
                return (custom_order.index(folder_name), folder_name) # Sort by index, then alphabetically
            except ValueError:
                # If folder not in custom order, place it at the end (large index)
                return (len(custom_order), folder_name)
        else: # Default or 'None' (A-Z)
            return (0, folder_name)