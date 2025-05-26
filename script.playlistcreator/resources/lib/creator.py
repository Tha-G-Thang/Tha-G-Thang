import os
import xbmcvfs
import xbmcgui
import xbmc
from resources.lib.utils import log, get_setting, ADDON_PROFILE, PLAYLIST_DIR, create_backup, format_display_entry, get_bool_setting, is_ai_enabled, ai_log # Added is_ai_enabled, ai_log
from resources.lib.scanner import DAVSScanner
from resources.lib.sorter import Sorter

# Import AI components
from resources.lib.ai_tagger import AITagger # New import
from resources.lib.ai_sorter import AISorter # New import


class PlaylistCreator:
    def create(self, name, folders, save_set=True):
        log(f"Initiating playlist creation for '{name}' from {len(folders)} folders.")
        scanner = DAVSScanner()
        sorter = Sorter()
        dialog = xbmcgui.Dialog()
        progress = xbmcgui.DialogProgress()
        progress.create(get_setting('ADDON_NAME', 'Playlist Creator'), "Collecting media files...")

        all_files_info = []
        total_folders = len(folders)
        for i, folder in enumerate(folders):
            if progress.iscanceled():
                log("Playlist creation cancelled by user during scan.")
                progress.close()
                return False
            progress.update(int(i * 100 / total_folders), f"Scanning {os.path.basename(folder)}...")
            
            if folder.startswith(('davs://', 'dav://')) and not folder.endswith('/'):
                folder = folder + '/'
                log(f"Normalized WebDAV path: {folder}")
            
            files_in_folder = scanner.scan([folder])
            all_files_info.extend(files_in_folder)
            log(f"Found {len(files_in_folder)} files in {folder}. Total files so far: {len(all_files_info)}")
        
        progress.update(100, "Scan complete. Processing files...")
        xbmc.sleep(500) # Give UI a moment to update


        # --- AI Integration Section ---
        if is_ai_enabled():
            ai_tagger = None
            ai_sorter = None

            # Initialize AITagger
            if get_bool_setting('enable_ai_auto_tagging', False):
                try:
                    ai_tagger = AITagger()
                    ai_log("AITagger initialized.")
                except Exception as e:
                    log(f"Failed to initialize AITagger: {e}", xbmc.LOGERROR)

            # Initialize AISorter
            if get_bool_setting('enable_ai_smart_playlists', False):
                try:
                    ai_sorter = AISorter()
                    ai_log("AISorter initialized.")
                except Exception as e:
                    log(f"Failed to initialize AISorter: {e}", xbmc.LOGERROR)

            if ai_tagger or ai_sorter:
                progress.create(get_setting('ADDON_NAME', 'Playlist Creator'), "Applying AI enhancements...")
                total_files = len(all_files_info)

                for i, file_info in enumerate(all_files_info):
                    if progress.iscanceled():
                        log("AI processing cancelled by user.")
                        break
                    progress.update(int(i * 100 / total_files), f"Processing AI for {os.path.basename(file_info['path'])}...")
                    
                    filename_for_ai = os.path.splitext(os.path.basename(file_info['path']))[0] # Use filename without extension

                    # AI Auto-Tagging
                    if ai_tagger:
                        try:
                            tags = ai_tagger.generate_tags(filename_for_ai)
                            file_info['ai_tags'] = [tag[0] for tag in tags] # Store only the keyword
                            ai_log(f"Generated AI tags for {filename_for_ai}: {file_info['ai_tags']}")
                        except Exception as e:
                            log(f"Error during AI tagging for {filename_for_failure}: {e}", xbmc.LOGWARNING)

                # AI Smart Playlists (Clustering)
                if ai_sorter and not progress.iscanceled():
                    try:
                        titles = [os.path.splitext(os.path.basename(f['path']))[0] for f in all_files_info]
                        n_clusters = get_int_setting('ai_cluster_count', 3)
                        
                        # Only cluster if there are enough titles and clusters make sense
                        if len(titles) > 0 and n_clusters > 1 and len(set(titles)) >= n_clusters: # Ensure diverse enough titles
                            clusters = ai_sorter.cluster_titles(titles, n_clusters=n_clusters)
                            
                            # Assign cluster labels back to file_info dictionaries
                            for file_info in all_files_info:
                                filename_no_ext = os.path.splitext(os.path.basename(file_info['path']))[0]
                                if filename_no_ext in clusters:
                                    file_info['ai_cluster_id'] = clusters[filename_no_ext]
                                else:
                                    # Handle cases where a title might not be in clusters (e.g., empty string)
                                    file_info['ai_cluster_id'] = -1 # Or a unique identifier
                            ai_log(f"AI Clustering complete. Example cluster IDs: {[f.get('ai_cluster_id') for f in all_files_info[:5]]}")
                        else:
                            ai_log("Not enough unique titles or clusters for effective AI clustering.")
                            for file_info in all_files_info:
                                file_info['ai_cluster_id'] = -1 # Assign default if no clustering
                    except Exception as e:
                        log(f"Error during AI clustering: {e}", xbmc.LOGERROR)
                progress.close()
        # --- End AI Integration Section ---

        log(f"Total files collected before sorting: {len(all_files_info)}")
        
        # Apply sorting
        sorted_files_info = sorter.apply_sorting(all_files_info)
        log(f"Total files after sorting: {len(sorted_files_info)}")

        # Create M3U playlist
        playlist_path = os.path.join(PLAYLIST_DIR, f"{name}.m3u")
        log(f"Attempting to write playlist to: {playlist_path}")

        if xbmcvfs.exists(playlist_path):
            create_backup(playlist_path)

        try:
            with xbmcvfs.File(playlist_path, 'w') as f:
                f.write("#EXTM3U\n")
                for file_info in sorted_files_info:
                    try:
                        display_name = format_display_entry(file_info)
                        f.write(f"#EXTINF:-1,{display_name}\\n")
                        f.write(f"{file_info['path']}\\n")
                        log(f"Added to M3U: {display_name} -> {file_info['path']}", xbmc.LOGDEBUG)
                    except Exception as entry_e:
                        log(f"Error adding file {file_info.get('path', 'Unknown')} to playlist: {entry_e}",
                            xbmc.LOGWARNING)
                        f.write(f"#EXTINF:-1,{os.path.basename(file_info['path'])}\\n")
                        f.write(f"{file_info['path']}\\n")
            log(f"M3U playlist successfully written to {playlist_path}", xbmc.LOGINFO)
            return True
        except Exception as e:
            log(f"Failed to write M3U playlist {playlist_path}: {e}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Error writing playlist: {e}", time=5000)
            return False