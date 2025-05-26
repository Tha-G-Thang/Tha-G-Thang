import sys
import xbmcgui
import xbmcaddon
import xbmc
from resources.lib.downloader import Downloader
from resources.lib.utils import log, get_string # get_string toegevoegd

# Haal ADDON_NAME hier op, zoals in default.py
ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')

def handle_context_action():
    log(f"Menu handler starting (sys.argv: {sys.argv})")
    
    args = {}
    for arg_str in sys.argv[1:]: # sys.argv[0] is de scriptnaam
        if '=' in arg_str:
            key, value = arg_str.split('=', 1)
            args[key] = value

    action = args.get('action')
    url = args.get('url')

    if not action or not url:
        log(f"Missing action or URL in context menu call: {sys.argv}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, get_string(3021), xbmcgui.NOTIFICATION_ERROR) # "Context menu error: Invalid parameters."
        return

    downloader = Downloader()
    if action == 'download':
        downloader.download_file(url, is_adult_content_flag=False)
    elif action == 'download_adult':
        downloader.download_file(url, is_adult_content_flag=True)
    # elif action == 'play': # DEZE LIJN VERWIJDERD
    #     xbmc.Player().play(url) # DEZE LIJN VERWIJDERD
    else:
        log(f"Unknown context action: {action} for URL: {url}", xbmc.LOGWARNING)
        xbmcgui.Dialog().notification(ADDON_NAME, get_string(3022).format(action), xbmcgui.NOTIFICATION_WARNING) # "Unknown action: {}"