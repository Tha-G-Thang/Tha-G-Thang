import sys
import xbmcgui
import xbmcaddon
import xbmc
from resources.lib.core.downloader import Downloader
from resources.lib.core.base_utils import log, ADDON
from resources.lib.core.stream_set_manager import StreamSetManager # NIEUW

ADDON_NAME = ADDON.getAddonInfo('name')

def handle_context_action():
    log(f"Context menu called with args: {sys.argv}", xbmc.LOGDEBUG)

    args = dict(arg.split('=') for arg in sys.argv[1:] if '=' in arg)
    action = args.get('action')
    url = args.get('url') # Kan leeg zijn voor sommige acties

    downloader = Downloader()
    stream_set_manager = StreamSetManager() # NIEUW

    match action:
        case 'download' | 'download_adult':
            if url:
                downloader.download_file(url, is_adult_content=(action == 'download_adult'))
            else:
                xbmcgui.Dialog().notification(ADDON_NAME, "Geen URL gevonden voor download.", xbmcgui.NOTIFICATION_WARNING, 3000)
        case 'save_playing_stream':
            stream_set_manager.save_playing_stream()
        case _:
            log(f"Unknown action: {action}", xbmc.LOGWARNING)
            xbmcgui.Dialog().notification(ADDON_NAME, "Onbekende contextmenu actie.", xbmcgui.NOTIFICATION_ERROR, 3000)