import xbmc
import xbmcvfs
import urllib.request
import os
import re
from typing import List, Optional # <--- THIS LINE WAS ADDED

import resources.lib.utils as utils

def download_file(url: str, destination_path: str) -> None:
    """Downloads a file from a URL to the specified destination."""
    if not destination_path:
        utils.show_notification(utils.ADDON_NAME, "Download path not set in addon settings.", time=3000)
        return

    # Extract filename from URL
    filename_from_url = os.path.basename(urllib.parse.urlparse(url).path)
    
    # Get cleanup settings
    enable_cleanup = utils.get_setting('download_filename_cleanup', 'bool')
    delete_words_str = utils.get_setting('download_filename_delete_words', 'text')
    switch_words_str = utils.get_setting('download_filename_switch_words', 'text')
    use_regex = utils.get_setting('download_filename_regex', 'bool')
    regex_pattern = utils.get_setting('download_filename_regex_pattern', 'text')
    regex_replace_with = utils.get_setting('download_filename_regex_replace', 'text')

    # Apply cleanup
    cleaned_filename = clean_download_filename(
        filename_from_url,
        enable_cleanup,
        delete_words_str,
        switch_words_str,
        use_regex,
        regex_pattern,
        regex_replace_with
    )
    
    final_destination = os.path.join(destination_path, cleaned_filename)

    try:
        utils.log(f"Attempting to download '{url}' to '{final_destination}'", xbmc.LOGINFO)
        xbmcvfs.mkdirs(os.path.dirname(final_destination)) # Ensure directory exists
        
        # Check if file already exists
        if xbmcvfs.exists(final_destination):
            utils.log(f"File '{final_destination}' already exists. Skipping download.", xbmc.LOGWARNING)
            utils.show_notification(utils.ADDON_NAME, f"File already exists: {cleaned_filename}", time=3000)
            return

        # Perform the download
        urllib.request.urlretrieve(url, final_destination)
        utils.show_notification(utils.ADDON_NAME, f"Download successful: {cleaned_filename}")
        utils.log(f"Download completed for '{cleaned_filename}'", xbmc.LOGINFO)
    except Exception as e:
        utils.log(f"Error downloading '{url}' to '{final_destination}': {e}", xbmc.LOGERROR)
        utils.show_notification(utils.ADDON_NAME, f"Download failed: {cleaned_filename}")

def clean_download_filename(
    filename: str,
    enable_cleanup: bool,
    delete_words_str: str,
    switch_words_str: str,
    use_regex: bool,
    regex_pattern: str,
    regex_replace_with: str
) -> str:
    """
    Cleans a filename by removing unwanted words, switching words, and applying regex.
    This function is now self-contained with all necessary parameters.
    """
    if not enable_cleanup:
        return filename # Return original if cleanup is disabled

    cleaned_filename = filename

    # Delete words
    if delete_words_str:
        delete_words = [w.strip() for w in delete_words_str.split('|') if w.strip()]
        for word in delete_words:
            # Use regex for whole word matching to avoid partial replacements (e.g., 'sample' in 'supersample')
            cleaned_filename = re.sub(r'\b' + re.escape(word) + r'\b', '', cleaned_filename, flags=re.IGNORECASE).strip()
            
    # Switch words
    if switch_words_str:
        switch_pairs = {}
        for pair in switch_words_str.split('|'):
            if '=' in pair:
                old, new = pair.split('=', 1)
                switch_pairs[old.strip()] = new.strip()
        
        # Apply switch words using regex for whole word matching
        for old_word, new_word in switch_pairs.items():
            cleaned_filename = re.sub(r'\b' + re.escape(old_word) + r'\b', new_word, cleaned_filename, flags=re.IGNORECASE).strip()

    # Apply regex
    if use_regex and regex_pattern:
        try:
            cleaned_filename = re.sub(regex_pattern, regex_replace_with, cleaned_filename, flags=re.IGNORECASE).strip()
        except re.error as e:
            utils.log(f"Invalid regex pattern for download filename cleanup '{regex_pattern}': {e}", xbmc.LOGERROR)

    return cleaned_filename.strip() # Final strip