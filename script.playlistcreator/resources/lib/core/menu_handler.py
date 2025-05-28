import sys
import xbmcgui
import xbmcaddon
from resources.lib.core.downloader import Downloader
from resources.lib.utils import log

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')

def handle_context_action():
    log(f"Context menu called with args: {sys.argv}", xbmc.LOGDEBUG)
    
    # Argument parsing
    args = dict(arg.split('=') for arg in sys.argv[1:] if '=' in arg)
    action, url = args.get('action'), args.get('url')
    
    if not all((action, url)):
        xbmcgui.Dialog().notification(
            ADDON_NAME, 
            "Missing parameters", 
            xbmcgui.NOTIFICATION_ERROR
        )
        return

    # Action routing
    downloader = Downloader()
    match action:
        case 'download' | 'download_adult':
            ddownloader.download_file(url, is_adult_content=(action == 'download_adult'))
            )
        case _:
            log(f"Unknown action: {action}", xbmc.LOGWARNING)