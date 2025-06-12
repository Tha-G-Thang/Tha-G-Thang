import xbmc
import xbmcgui
import xbmcvfs
import os
import urllib.parse
from resources.lib.core.base_utils import log, get_setting, clean_display_name # Importeer benodigde functies
import re

def clean_filename(filename):
    """ Cleans a filename by removing illegal characters for file systems. """
    # Remove characters that are illegal in Windows, macOS, and Linux filenames
    cleaned_filename = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', filename)
    # Replace common illegal characters with a safe alternative (e.g., underscore)
    cleaned_filename = cleaned_filename.replace(' ', '_')
    cleaned_filename = cleaned_filename.replace("'", "")
    cleaned_filename = cleaned_filename.replace("&", "and")
    # Limit length to avoid issues with some file systems (e.g., 255 chars)
    cleaned_filename = cleaned_filename[:200] # Arbitrary limit, adjust as needed
    return cleaned_filename

def download_file(path, download_type='standard'):
    log(f"Attempting to download: {path} (type: {download_type})", xbmc.LOGINFO)

    if not path:
        xbmcgui.Dialog().ok("Download Fout", "Geen bestandspad opgegeven voor download.")
        return

    # Determine destination folder based on download_type
    if download_type == 'adult':
        download_path_setting = get_setting('download_path_adult')
    else:
        download_path_setting = get_setting('download_path')

    if not download_path_setting:
        xbmcgui.Dialog().ok("Download Fout", "Geen downloadmap ingesteld in de addon instellingen.")
        return

    # Ensure the destination directory exists
    if not xbmcvfs.exists(download_path_setting):
        xbmcvfs.mkdirs(download_path_setting)
        if not xbmcvfs.exists(download_path_setting): # Check again if creation was successful
            xbmcgui.Dialog().ok("Download Fout", f"Kon downloadmap niet aanmaken: {download_path_setting}")
            return

    original_filename = os.path.basename(urllib.parse.unquote(path))
    
    # Auto-clean filename if setting is enabled
    if get_setting('enable_auto_clean', 'true') == 'true':
        filename_without_ext, file_ext = os.path.splitext(original_filename)
        cleaned_filename_without_ext = clean_filename(filename_without_ext)
        target_filename = f"{cleaned_filename_without_ext}{file_ext}"
    else:
        target_filename = original_filename
        
    destination_path = xbmcvfs.translatePath(os.path.join(download_path_setting, target_filename))

    if xbmcvfs.exists(destination_path):
        if not xbmcgui.Dialog().yesno("Bestand Bestaat Al", f"'{target_filename}' bestaat al. Overschrijven?"):
            xbmcgui.Dialog().notification("Download Geannuleerd", "Download geannuleerd.", xbmcgui.NOTIFICATION_INFO, 2000)
            log(f"Download of {path} cancelled: file already exists.", xbmc.LOGINFO)
            return

    dialog = xbmcgui.DialogProgress()
    dialog.create("Bestand Downloaden", "Bezig met downloaden...")

    try:
        # xbmcvfs.copy does not provide progress, so we use a dummy progress for UX
        log(f"Starting download from '{path}' to '{destination_path}'", xbmc.LOGINFO)
        xbmcvfs.copy(path, destination_path)
        
        # Simulate progress for better UX as xbmcvfs.copy is blocking
        for i in range(101):
            dialog.update(i, "Downloaden...", f"{i}% voltooid")
            time.sleep(0.01) # Small delay to show progress
        
        dialog.close()
        xbmcgui.Dialog().notification("Download Voltooid", f"'{target_filename}' gedownload.", xbmcgui.NOTIFICATION_INFO, 2000)
        log(f"Successfully downloaded: {path} to {destination_path}", xbmc.LOGINFO)

    except Exception as e:
        dialog.close()
        xbmcgui.Dialog().ok("Download Fout", f"Fout bij downloaden van '{target_filename}': {e}")
        log(f"Error downloading {path}: {e}", xbmc.LOGERROR)