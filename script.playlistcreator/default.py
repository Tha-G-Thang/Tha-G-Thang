import xbmcgui
import xbmcaddon
import xbmcvfs
from resources.lib.core.creator import PlaylistCreator
from resources.lib.core.manager import SetManager
from resources.lib.core.downloader import Downloader
from resources.lib.utils import log, get_setting, ADDON_PROFILE

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')

def _show_menu(heading, items):
    return xbmcgui.Dialog().select(heading, [item[0] for item in items])

def main():
    manager = SetManager()
    creator = PlaylistCreator()
    downloader = Downloader()

    while True:
        choice = _show_menu(ADDON_NAME, [
            ("Create playlist", "create"),
            ("Manage sets", "manage"),
            ("Downloads", "download"),
            ("Settings", "settings")
        ])
        
        if choice == -1: break
        action = menu_items[choice][1]
        
        if action == "create":
            if folder := manager.select_folder():
                creator.generate(folder)
        elif action == "manage":
            manager.manage_sets()
        elif action == "download":
            downloader.show_dialog()
        elif action == "settings":
            ADDON.openSettings()

if __name__ == '__main__':
    if not xbmcvfs.exists(ADDON_PROFILE):
        xbmcvfs.mkdirs(ADDON_PROFILE)
    main()