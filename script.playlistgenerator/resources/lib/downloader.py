import xbmc
import xbmcgui
import xbmcvfs
import os
import requests
import re
from .strm_utils import log, get_setting, ADDON_PROFILE, clean_display_name

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
        original_filename = os.path.basename(file_url).split('?')[0]
        
        cleaned_filename = _clean_download_filename(original_filename, is_adult_content)
        file_path = os.path.join(download_dir, cleaned_filename)

        # Ensure unique filename to prevent overwriting
        counter = 1
        base_name, ext = os.path.splitext(cleaned_filename)
        while xbmcvfs.exists(file_path):
            file_path = os.path.join(download_dir, f"{base_name}_{counter}{ext}")
            counter += 1

        dialog = xbmcgui.DialogProgressBG()
        dialog.create("Downloading", f"Downloading: {os.path.basename(file_path)}")

        downloaded_size = 0
        chunk_size = 8192 # 8KB chunks
        with xbmcvfs.File(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if dialog.isFinished():
                    log(f"Download cancelled by user: {file_url}", xbmc.LOGINFO)
                    response.close()
                    xbmcvfs.delete(file_path) # Clean up partial file
                    dialog.close()
                    return

                f.write(chunk)
                downloaded_size += len(chunk)
                
                if total_size > 0:
                    percentage = int((downloaded_size / total_size) * 100)
                    dialog.update(percentage, f"Downloading: {os.path.basename(file_path)}", f"{round(downloaded_size / (1024 * 1024), 2)} MB / {round(total_size / (1024 * 1024), 2)} MB")
                else:
                    dialog.update(0, f"Downloading: {os.path.basename(file_path)}", f"{round(downloaded_size / (1024 * 1024), 2)} MB")

        dialog.close()
        log(f"Successfully downloaded: {file_path}", xbmc.LOGINFO)
        xbmcgui.Dialog().notification("Download Complete", f"Downloaded: {os.path.basename(file_path)}", xbmcgui.NOTIFICATION_INFO)

    except requests.exceptions.RequestException as e:
        log(f"Download request failed for {file_url}: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Download Error", "Could not download file.", xbmcgui.NOTIFICATION_ERROR)
    except Exception as e:
        log(f"An unexpected error occurred during download of {file_url}: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Download Error", "An unexpected error occurred.", xbmcgui.NOTIFICATION_ERROR)
    finally:
        if 'dialog' in locals() and not dialog.isFinished(): # Ensure dialog is closed in case of error
            dialog.close()

def _clean_download_filename(filename, is_adult_content):
    cleaned_name = os.path.basename(filename).split('?')[0] # Remove URL parameters

    if is_adult_content:
        if get_setting('adult_filename_remove_words', '') != '':
            remove_words = [w.strip() for w in get_setting('adult_filename_remove_words', '').split(',') if w.strip()]
            for word in remove_words:
                cleaned_name = re.sub(r'\b' + re.escape(word) + r'\b', '', cleaned_name, flags=re.IGNORECASE).strip()

        if get_setting('adult_filename_switch_words', '') != '':
            switch_pairs = [p.strip().split('=') for p in get_setting('adult_filename_switch_words', '').split(',') if p.strip() and '=' in p]
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
                cleaned_name = re.sub(r'\b' + re.escape(word) + r'\b', '', cleaned_name, flags=re.IGNORECASE).strip()

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
                log(f"Invalid regex pattern: {pattern} - {e}", xbmc.LOGERROR)

    return cleaned_name