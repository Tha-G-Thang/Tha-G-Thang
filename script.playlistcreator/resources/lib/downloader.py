import xbmc
import xbmcgui
import xbmcvfs
import os
import requests
import re
from .utils import log, get_setting, ADDON_PROFILE, clean_display_name

def download_file_with_progress(file_url):
    """Downloads a file with a progress dialog, applying filename cleanup."""
    if not file_url:
        log("No file URL provided for download.", xbmc.LOGERROR)
        return

    # Determine if it's adult content based on settings
    is_adult_content = get_setting('enable_adult_content_filter', 'false') == 'true' and any(
        re.search(pattern.strip(), os.path.basename(file_url).split('?')[0], re.IGNORECASE)
        for pattern in get_setting('adult_content_keywords', '').split(',') if pattern.strip()
    )

    # Kies de juiste downloadmap op basis van contenttype
    if is_adult_content:
        # Gebruik adult_download_path, met fallback naar reguliere download_path
        download_dir = xbmcvfs.translatePath(get_setting('adult_download_path', get_setting('download_path', ADDON_PROFILE)))
    else:
        download_dir = xbmcvfs.translatePath(get_setting('download_path', ADDON_PROFILE))

    if not xbmcvfs.exists(download_dir):
        xbmcvfs.mkdirs(download_dir)

    try:
        response = requests.get(file_url, stream=True, timeout=30)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        chunk_size = 8192  # 8KB chunks
        downloaded_size = 0
        
        # Clean the filename before saving
        cleaned_filename = clean_display_name(os.path.basename(file_url).split('?')[0], is_adult_content)
        file_path = xbmcvfs.makeLegalFilename(os.path.join(download_dir, cleaned_filename))

        dialog = xbmcgui.DialogProgress()
        dialog.create("Downloading File", "Preparing to download...")

        with xbmcvfs.File(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if dialog.iscanceled():
                    log(f"Download cancelled by user: {file_url}", xbmc.LOGINFO)
                    dialog.close()
                    xbmcvfs.delete(file_path)  # Clean up partial download
                    xbmcgui.Dialog().notification("Download Cancelled", f"Download of '{cleaned_filename}' cancelled.", xbmcgui.NOTIFICATION_WARNING)
                    return False
                f.write(chunk)
                downloaded_size += len(chunk)
                if total_size > 0:
                    percent = int(downloaded_size * 100 / total_size)
                    dialog.update(percent, f"Downloading: {cleaned_filename}", f"{downloaded_size / (1024 * 1024):.2f} MB / {total_size / (1024 * 1024):.2f} MB")
                else:
                    dialog.update(0, f"Downloading: {cleaned_filename}", f"{downloaded_size / (1024 * 1024):.2f} MB (size unknown)")

        dialog.close()
        xbmcgui.Dialog().notification("Download Complete", f"'{cleaned_filename}' downloaded.", xbmcgui.NOTIFICATION_INFO)
        log(f"Successfully downloaded: {file_path}", xbmc.LOGINFO)
        return True

    except requests.exceptions.RequestException as e:
        log(f"Error downloading file {file_url}: {e}", xbmc.LOGERROR)
        dialog.close()
        xbmcgui.Dialog().notification("Download Failed", f"Failed to download '{cleaned_filename}'.", xbmcgui.NOTIFICATION_ERROR)
        return False
    except Exception as e:
        log(f"An unexpected error occurred during download: {e}", xbmc.LOGERROR)
        dialog.close()
        xbmcgui.Dialog().notification("Download Failed", f"An error occurred with '{cleaned_filename}'.", xbmcgui.NOTIFICATION_ERROR)
        return False

# This function remains in downloader.py as it's directly related to cleaning names for downloads.
def clean_downloaded_filename(original_name, is_adult=False):
    """
    Cleans up the filename of a downloaded file based on settings.
    Applies separate cleanup rules for adult content if enabled.
    """
    cleaned_name = original_name

    if is_adult:
        if get_setting('adult_remove_words', '') != '':
            remove_words = [w.strip() for w in get_setting('adult_remove_words', '').split('|') if w.strip()]
            for word in remove_words:
                cleaned_name = re.sub(r'\\b' + re.escape(word) + r'\\b', '', cleaned_name, flags=re.IGNORECASE).strip()

        if get_setting('adult_switch_words', '') != '':
            switch_pairs = [p.strip().split('=') for p in get_setting('adult_switch_words', '').split('|') if p.strip() and '=' in p]
            for old, new in switch_pairs:
                cleaned_name = re.sub(re.escape(old), new, cleaned_name, flags=re.IGNORECASE)
        
        if get_setting('adult_regex_enable', 'false') == 'true':
            pattern = get_setting('adult_regex_pattern', '(.*)')
            replace_with = get_setting('adult_regex_replace_with', '\\1')
            try:
                cleaned_name = re.sub(pattern, replace_with, cleaned_name, flags=re.IGNORECASE)
            except re.error as e:
                log(f"Invalid adult regex pattern: {pattern} - {e}", xbmc.LOGERROR)

    else:
        # Normal content cleanup
        if get_setting('download_remove_words', '') != '':
            remove_words = [w.strip() for w in get_setting('download_remove_words', '').split(',') if w.strip()]
            for word in remove_words:
                cleaned_name = re.sub(r'\\b' + re.escape(word) + r'\\b', '', cleaned_name, flags=re.IGNORECASE).strip()

        if get_setting('download_switch_words', '') != '':
            switch_pairs = [p.strip().split('=') for p in get_setting('download_switch_words', '').split(',') if p.strip() and '=' in p]
            for old, new in switch_pairs:
                cleaned_name = re.sub(re.escape(old), new, cleaned_name, flags=re.IGNORECASE)
        
        if get_setting('download_regex_enable', 'false') == 'true':
            pattern = get_setting('download_regex_pattern', '(.*)')
            replace_with = get_setting('download_regex_replace_with', '\\1')
            try:
                cleaned_name = re.sub(pattern, replace_with, cleaned_name, flags=re.IGNORECASE)
            except re.error as e:
                log(f"Invalid download regex pattern: {pattern} - {e}", xbmc.LOGERROR)
                
    return cleaned_name