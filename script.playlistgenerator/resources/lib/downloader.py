import xbmc
import xbmcgui
import xbmcvfs
import urllib.request
import re
import os
from typing import List, Dict, Optional
import time
import ssl

import resources.lib.utils as utils

class VideoDownloader:
    def __init__(self):
        # No longer retrieving settings here.
        # Download paths and cleanup rules will be passed to download_file/clean_download_filename.
        pass

    def _download_file_with_progress(self, url: str, destination_path: str) -> bool:
        """
        Downloads a file with a progress dialog.
        Returns True on success, False on failure.
        """
        dialog_progress = xbmcgui.DialogProgress()
        dialog_progress.create(utils.ADDON_NAME, 'Starting download...')

        temp_destination_path = destination_path + ".part" # Use a temporary file for download

        try:
            # Create an SSL context that does not verify SSL certificates
            # This is often needed for various video streaming sites.
            # WARNING: This reduces security. Only use if absolutely necessary and understand the risks.
            ssl_context = ssl._create_unverified_context()

            # Using urllib.request for download
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req, context=ssl_context) as response:
                # Get total size if available (Content-Length header)
                total_size = int(response.getheader('Content-Length', 0))
                downloaded_size = 0
                chunk_size = 8192 # 8KB chunks for downloading

                # Open the temporary file for writing in binary mode
                with xbmcvfs.File(temp_destination_path, 'wb') as temp_file:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break # End of file
                        
                        temp_file.write(chunk)
                        downloaded_size += len(chunk)

                        # Update progress dialog
                        if total_size > 0:
                            percent = int((downloaded_size / total_size) * 100)
                            dialog_progress.update(
                                percent, 
                                'Downloading...', 
                                f'{os.path.basename(destination_path)} ({downloaded_size / (1024*1024):.2f} MB / {total_size / (1024*1024):.2f} MB)'
                            )
                        else:
                            dialog_progress.update(
                                -1, # Indeterminate progress if total size is unknown
                                'Downloading...', 
                                f'{os.path.basename(destination_path)} ({downloaded_size / (1024*1024):.2f} MB)'
                            )
                        
                        # Check if user cancelled
                        if dialog_progress.iscanceled(): # Corrected: lowercase 'c' for iscanceled()
                            utils.log("Download cancelled by user.", xbmc.LOGINFO)
                            temp_file.close() # Close file handle
                            xbmcvfs.delete(temp_destination_path) # Delete incomplete file
                            dialog_progress.close()
                            return False
                        
                        # Short delay to prevent UI freezing (adjust as needed)
                        time.sleep(0.01) # Sleep for 10ms

                # If download completes, rename the temporary file to the final destination
                xbmcvfs.rename(temp_destination_path, destination_path)
                utils.log(f"Download successful: {destination_path}", xbmc.LOGINFO)
                return True

        except Exception as e:
            utils.log(f"Download error: {e}", xbmc.LOGERROR)
            # Ensure temporary file is cleaned up on error
            if xbmcvfs.exists(temp_destination_path):
                xbmcvfs.delete(temp_destination_path)
            return False
        finally:
            dialog_progress.close()

    def clean_download_filename(
        self,
        filename: str,
        delete_words: List[str],
        switch_words_str: str,
        regex_pattern: str,
        regex_replace_with: str
    ) -> str:
        """
        Cleans up a filename based on provided rules.
        """
        cleaned_filename = filename

        # 1. Delete words
        for word in delete_words:
            # Case-insensitive replacement
            cleaned_filename = re.sub(re.escape(word), '', cleaned_filename, flags=re.IGNORECASE)

        # 2. Switch words (old:new)
        if switch_words_str:
            switch_pairs = [pair.split(':', 1) for pair in switch_words_str.split(',') if ':' in pair]
            for old_word, new_word in switch_pairs:
                # Case-insensitive replacement
                cleaned_filename = re.sub(re.escape(old_word), new_word, cleaned_filename, flags=re.IGNORECASE)

        # 3. Apply regex pattern if provided
        if regex_pattern:
            try:
                cleaned_filename = re.sub(regex_pattern, regex_replace_with, cleaned_filename)
            except re.error as e:
                utils.log(f"Regex error in filename cleanup: {e}. Skipping regex.", xbmc.LOGERROR)

        # 4. Clean up multiple spaces and remove leading/trailing spaces
        cleaned_filename = re.sub(r'\s+', ' ', cleaned_filename).strip()
        
        # 5. Make sure filename is valid for the filesystem (replace common invalid characters)
        # Using a safer set of characters to replace, typically avoided in filenames
        invalid_chars_pattern = r'[<>:"/\\|?*]'
        cleaned_filename = re.sub(invalid_chars_pattern, '_', cleaned_filename)
        
        return cleaned_filename

# For external calls from other modules (like PlaylistManager)
def download_file(url: str, destination_path: str) -> bool:
    """Initiates a download. Returns True on success, False on failure."""
    downloader_instance = VideoDownloader()
    return downloader_instance._download_file_with_progress(url, destination_path)

def clean_download_filename(
    filename: str, 
    delete_words: List[str], 
    switch_words_str: str, 
    regex_pattern: str, 
    regex_replace_with: str
) -> str:
    """
    Calls the VideoDownloader's clean_download_filename method.
    This function is a wrapper for external modules to call the cleanup logic.
    """
    downloader_instance = VideoDownloader() # Create instance for method access
    return downloader_instance.clean_download_filename(
        filename, delete_words, switch_words_str, regex_pattern, regex_replace_with
    )
