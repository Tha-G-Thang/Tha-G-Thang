import sys
import xbmcgui
import xbmcaddon
import xbmc
from resources.lib.downloader import Downloader
from resources.lib.utils import log, get_setting

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
        log(f"Missing action or URL in context menu call: {sys.LOGERROR}")
        xbmcgui.Dialog().notification(ADDON_NAME, "Context menu error: Invalid parameters.", xbmcgui.NOTIFICATION_ERROR)
        return

    downloader = Downloader()
    if action == 'download':
        downloader.download_file(url, is_adult_content_flag=False)
    elif action == 'download_adult':
        downloader.download_file(url, is_adult_content_flag=True)
    # elif action == 'play': # DEZE LIJN VERWIJDEREN
    #     xbmc.Player().play(url) # DEZE LIJN VERWIJDEREN
    else:
        log(f"Unknown context action: {action} for URL: {url}", xbmc.LOGWARNING)
        xbmcgui.Dialog().notification(ADDON_NAME, f"Unknown action: {action}", xbmcgui.NOTIFICATION_WARNING)

# Zorg ervoor dat de addon.xml nog steeds correct is en alleen de download acties bevat.
# Deze was al zo, dus geen aanpassing nodig hier, maar check voor de zekerheid:
# <item>
#     <label>Download with C-reator</label>
#     <file>plugin.video.playlistcreator/resources/lib/menu_handler.py</file>
#     <args>action=download&amp;url=$INFO[ListItem.Path]</args>
#     <visible>...</visible>
# </item>
# <item>
#     <label>Download Adult with C-reator</label>
#     <file>plugin.video.playlistcreator/resources/lib/menu_handler.py</file>
#     <args>action=download_adult&amp;url=$INFO[ListItem.Path]</args>
#     <visible>...</visible>
# </item>