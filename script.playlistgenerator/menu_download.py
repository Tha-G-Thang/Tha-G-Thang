import sys
import xbmc
import urllib.parse
import os # Added for os.path.basename

# Import necessary modules
try:
    import resources.lib.utils as utils
    import resources.lib.downloader as downloader
except ImportError as e:
    xbmc.log(f"[Playlist Generator] menu_download.py: Failed to import necessary modules: {e}", xbmc.LOGERROR)
    sys.exit()

if __name__ == '__main__':
    # No need for utils.init_addon_globals() as global vars are initialized on utils import
    
    # sys.argv[0] is the script path, sys.argv[1] is handle, sys.argv[2] is the query string
    args = utils.parse_url(sys.argv[2]) # Use the updated parse_url from utils

    action = args.get('action')
    url = args.get('url')

    if action == 'download' and url:
        # Check if download is enabled in settings
        if not utils.get_setting('enable_download', 'bool'):
            utils.show_notification(utils.ADDON_NAME, "Download feature is disabled in settings.", time=3000)
            utils.log("[Playlist Generator] Download action attempted but feature is disabled.", xbmc.LOGWARNING)
            sys.exit()

        utils.log(f"Initiating download from context menu in menu_download.py. URL: {url}", xbmc.LOGINFO)
        
        download_path = utils.get_setting('download_path', 'folder')
        adult_download_path = utils.get_setting('download_path_adult', 'folder')
        
        # Determine actual download path based on adult content indicator
        final_download_path = download_path
        # Check for adult content indicator in the URL itself (common for direct download links)
        if utils.get_setting('enable_adult_cleanup', 'bool') and adult_download_path and utils.get_setting('adult_content_indicator', 'text') in url.lower():
             final_download_path = adult_download_path
        
        # Also check if adult_content_indicator is present in the filename part of the URL path
        filename_from_url = os.path.basename(urllib.parse.urlparse(url).path)
        if utils.get_setting('enable_adult_cleanup', 'bool') and adult_download_path and utils.get_setting('adult_content_indicator', 'text') in filename_from_url.lower():
            final_download_path = adult_download_path

        if not final_download_path:
            utils.show_ok_dialog(utils.ADDON_NAME, "Download path is not set in addon settings. Please configure it.")
            utils.log("[Playlist Generator] Download failed: Download path is not configured.", xbmc.LOGERROR)
            sys.exit()

        downloader.download_file(url, final_download_path)
    else:
        utils.log(f"[Playlist Generator] menu_download.py: Unknown action or missing URL. Action: {action}, URL: {url}", xbmc.LOGWARNING)