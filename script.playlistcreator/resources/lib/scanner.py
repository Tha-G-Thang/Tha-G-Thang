import os
import xbmcvfs
import xbmc
from resources.lib.utils import log, get_setting, ADDON_PROFILE, get_file_duration_from_kodi, is_ai_enabled, ai_log # Added is_ai_enabled, ai_log
from resources.lib.constants import VIDEO_EXTS

# Import AI components
from resources.lib.ai_metadata import AIMetadata # New import


class DAVSScanner:
    def scan(self, folders):
        files_info = []
        for folder in folders:
            try:
                files_info.extend(self._scan_folder(folder, 0)) # Start depth at 0
            except Exception as e:
                log(f"Error scanning {folder}: {e}", xbmc.LOGERROR)
        return files_info
    
    def _scan_folder(self, folder, current_depth):
        files_info = []
        recursive_scan = get_setting('recursive_scan', 'true') == 'true'
        
        try:
            scan_depth_limit = int(get_setting('scan_depth', '0'))
        except ValueError:
            log("Invalid 'scan_depth' setting. Using default 0 (unlimited).", xbmc.LOGWARNING)
            scan_depth_limit = 0

        exclude_folders_setting = [f.strip().lower() for f in get_setting('exclude_folders', '').split(',') if f.strip()]
        
        if scan_depth_limit > 0 and current_depth >= scan_depth_limit:
            log(f"Reached max scan depth at: {folder}", xbmc.LOGDEBUG)
            return []

        try:
            dirs, filenames = xbmcvfs.listdir(folder)
        except Exception as e:
            log(f"Failed to list directory {folder}: {e}", xbmc.LOGERROR)
            return []

        # Initialize AI Metadata Extractor if enabled and in Pro mode
        ai_metadata_extractor = None
        if is_ai_enabled() and get_bool_setting('enable_ai_metadata_extraction', False):
            try:
                ai_metadata_extractor = AIMetadata()
                ai_log("AIMetadata initialized in scanner.")
            except Exception as e:
                log(f"Failed to initialize AIMetadata: {e}", xbmc.LOGERROR)
                ai_metadata_extractor = None # Disable if initialization fails

        for filename in filenames:
            if any(filename.lower().endswith(ext) for ext in VIDEO_EXTS):
                filepath = os.path.join(folder, filename)
                file_stat = None
                try:
                    file_stat = xbmcvfs.Stat(filepath)
                except Exception as e:
                    log(f"Failed to stat file {filepath}: {e}", xbmc.LOGWARNING)
                    continue

                duration = get_file_duration_from_kodi(filepath)

                file_info = {
                    'path': filepath,
                    'size': file_stat.st_size() if file_stat else 0,
                    'creation_date': file_stat.st_ctime() if file_stat else 0,
                    'modification_date': file_stat.st_mtime() if file_stat else 0,
                    'duration': duration,
                    'year': 0, # Placeholder
                    'resolution': '' # Placeholder
                }

                # AI Metadata Extraction for audio files (and placeholder for video)
                if ai_metadata_extractor:
                    try:
                        if any(filename.lower().endswith(ext) for ext in [".mp3", ".flac", ".ogg", ".wav"]): # Example audio extensions
                            audio_meta = ai_metadata_extractor.extract_audio_metadata(filepath)
                            file_info.update(audio_meta) # Merge audio metadata
                            ai_log(f"Extracted AI audio metadata for {filename}")
                        # For video metadata (e.g., using yt-dlp for online content, or more advanced local analysis)
                        # This part would be more complex and require yt-dlp integration.
                        # if get_bool_setting('enable_ai_yt_dlp_metadata', False):
                        #    video_meta = ai_metadata_extractor.extract_video_metadata(filepath) # Needs implementation in AIMetadata
                        #    file_info.update(video_meta)
                    except Exception as e:
                        log(f"Error during AI metadata extraction for {filepath}: {e}", xbmc.LOGWARNING)

                files_info.append(file_info)
        
        if recursive_scan:
            for dirname in dirs:
                if dirname.lower() in exclude_folders_setting:
                    log(f"Excluding folder: {dirname}", xbmc.LOGDEBUG)
                    continue
                subdir = os.path.join(folder, dirname)
                files_info.extend(self._scan_folder(subdir, current_depth + 1))
            
        return files_info