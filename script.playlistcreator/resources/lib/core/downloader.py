import xbmc
import xbmcgui
import xbmcvfs
import os
import urllib.parse
from resources.lib.core.base_utils import log, get_setting, clean_display_name
import re
import time

def clean_filename(filename):
    """ Cleans a filename by removing illegal characters for file systems. """
    cleaned_filename = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', filename)
    cleaned_filename = cleaned_filename.replace(' ', '_')
    cleaned_filename = cleaned_filename.replace("'", "")
    cleaned_filename = cleaned_filename.replace("&", "and")
    cleaned_filename = cleaned_filename[:200]
    return cleaned_filename

def download_file(path, download_type='standard'):
    log(f"Attempting to download: {path} (type: {download_type})", xbmc.LOGINFO)

    if not path:
        xbmcgui.Dialog().ok("Download Fout", "Geen bestandspad opgegeven voor download.")
        return

    if download_type == 'adult':
        download_path_setting = get_setting('download_path_adult')
    else:
        download_path_setting = get_setting('download_path')

    if not download_path_setting:
        xbmcgui.Dialog().ok("Download Fout", "Geen downloadpad ingesteld in de addon instellingen.")
        return

    if not xbmcvfs.exists(download_path_setting):
        xbmcvfs.mkdirs(download_path_setting)
        log(f"Created download directory: {download_path_setting}", xbmc.LOGINFO)

    original_filename = os.path.basename(urllib.parse.urlparse(path).path)
    if get_setting('enable_auto_clean', 'true') == 'true':
        target_filename = clean_filename(original_filename)
        log(f"Cleaned filename from '{original_filename}' to '{target_filename}'", xbmc.LOGINFO)
    else:
        target_filename = original_filename
        log(f"Auto-clean filenames is disabled. Using original filename: {original_filename}", xbmc.LOGINFO)
        
    destination_path = xbmcvfs.translatePath(os.path.join(download_path_setting, target_filename))

    if xbmcvfs.exists(destination_path):
        if not xbmcgui.Dialog().yesno("Bestand Bestaat Al", f"'{target_filename}' bestaat al. Overschrijven?"):
            xbmcgui.Dialog().notification("Download Geannuleerd", "Download geannuleerd.", xbmcgui.NOTIFICATION_INFO, 2000)
            log(f"Download of {path} cancelled: file already exists.", xbmc.LOGINFO)
            return

    dialog = xbmcgui.DialogProgress()
    dialog.create("Bestand Downloaden", "Bezig met downloaden...")

    try:
        log(f"Starting download from '{path}' to '{destination_path}'", xbmc.LOGINFO)
        xbmcvfs.copy(path, destination_path)
        
        for i in range(101):
            dialog.update(i, "Downloaden...", f"{i}% voltooid")
            time.sleep(0.01)
        
        dialog.close()
        xbmcgui.Dialog().notification("Download Voltooid", f"'{target_filename}' gedownload.", xbmcgui.NOTIFICATION_INFO, 2000)
        log(f"Successfully downloaded: {path} to {destination_path}", xbmc.LOGINFO)

    except Exception as e:
        dialog.close()
        xbmcgui.Dialog().ok("Download Fout", f"Fout tijdens downloaden: {str(e)}")
        log(f"Download error: {e}", xbmc.LOGERROR)