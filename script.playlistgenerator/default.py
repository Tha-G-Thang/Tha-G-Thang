import sys
import os
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

from resources.lib import strm_scanner
from resources.lib import strm_creator
from resources.lib import strm_structure
from resources.lib import strm_utils
from resources.lib import menu_dl
from resources.lib import downloader

ADDON = xbmcaddon.Addon(id='script.playlistgenerator')
ADDON_NAME = ADDON.getAddonInfo('name')

def show_main_menu():
    menu_items = [
        "Scan Media & Create STRM Links", # Gebruiksvriendelijker
        "Manage Media Categories",        # Duidelijker label
        "Addon Settings"
    ]

    dialog = xbmcgui.Dialog()
    while True:
        choice = dialog.select(ADDON_NAME, menu_items)
        if choice == -1: # Terug-knop/Annuleren
            break

        if menu_items[choice] == "Scan Media & Create STRM Links":
            media_files = strm_scanner.get_media_files() # Geen argument meer
            if media_files:
                strm_creator.create_strm_from_list(media_files)
                dialog.notification(ADDON_NAME, f"Created STRM links for {len(media_files)} files.", xbmcgui.NOTIFICATION_INFO)
            else:
                dialog.notification(ADDON_NAME, "No media files found in source folder.", xbmcgui.NOTIFICATION_INFO)

        elif menu_items[choice] == "Manage Media Categories":
            # Als er in de toekomst meer functionaliteit komt dan alleen ensure_category_structure
            # zou hier een submenu of complexere logica komen.
            # Voor nu, als het alleen om 'ensure' gaat, kan dit een melding zijn.
            strm_structure.ensure_category_structure()
            dialog.notification(ADDON_NAME, "Media category folders ensured.", xbmcgui.NOTIFICATION_INFO)

        elif menu_items[choice] == "Addon Settings":
            ADDON.openSettings()

if __name__ == '__main__':
    strm_utils.log(f"{ADDON_NAME} starting...")

    if len(sys.argv) > 2:
        args = strm_utils.parse_url(sys.argv[2])
        mode = args.get('mode')

        if mode == 'add_to_playlist':
            file_url = args.get('file_url')
            if file_url:
                menu_dl.add_to_playlist_from_context(file_url)
        elif mode == 'download_video_file':
            file_url = args.get('file_url')
            if file_url:
                downloader.download_file_with_progress(file_url)
    else:
        show_main_menu()