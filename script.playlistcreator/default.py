import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import sys
import re
import urllib.parse

from resources.lib.constants import ADDON_ID, ADDON_PROFILE, PLAYLIST_DIR, ADDON_NAME, ADDON

from resources.lib.core.base_utils import log, get_setting, set_setting
from resources.lib.core.creator import create_playlist, create_favorites_playlist
from resources.lib.core.set_manager import toggle_favorite, manage_sets, update_all_sets
from resources.lib.core.downloader import download_file
from resources.lib.core.streamer import StreamSetManager

stream_set_manager = StreamSetManager()

def validate_settings_main():
    if not xbmcvfs.exists(ADDON_PROFILE):
        xbmcvfs.mkdirs(ADDON_PROFILE)
        log(f"Main: Created addon profile directory: {ADDON_PROFILE}", xbmc.LOGINFO)
    if not xbmcvfs.exists(PLAYLIST_DIR):
        xbmcvfs.mkdirs(PLAYLIST_DIR)
        log(f"Main: Created playlist directory: {PLAYLIST_DIR}", xbmc.LOGINFO)

    try:
        min_size = int(get_setting('min_file_size', '1'))
        if min_size < 0:
            set_setting('min_file_size', '1')
            log("Main: Invalid min_file_size corrected to 1MB.", xbmc.LOGWARNING)
    except ValueError:
        set_setting('min_file_size', '1')
        log("Main: min_file_size is not a valid number, corrected to 1MB.", xbmc.LOGWARNING)

    if get_setting('enable_max_size', 'false') == 'true':
        try:
            max_size = int(get_setting('max_file_size', '0'))
            if max_size < 0:
                set_setting('max_file_size', '0')
                log("Main: Invalid max_file_size corrected to 0MB.", xbmc.LOGWARNING)
        except ValueError:
            set_setting('max_file_size', '0')
            log("Main: max_file_size is not a valid number, corrected to 0MB.", xbmc.LOGWARNING)

def show_explanation_dialog():
    dialog = xbmcgui.Dialog()
    message = (
        "Welkom bij Playlist Creator!\n\n"
        "Deze addon is speciaal ontworpen om afspeellijsten te maken van video's die moeilijk te 'scrapen' zijn met Kodi's standaardbibliotheek. Denk aan verzamelde video's, DJ-sets, YouTube-video's, of andere niet-standaard content (geen films of tv-series).\n\n"
        "Belangrijkste functies:\n"
        "- **Afspeellijsten maken**: Selecteer mappen met videobestanden en genereer afspeellijsten (.m3u).\n"
        "- **Smart Folders**: Definieer sets van mappen die automatisch worden bijgewerkt naar een afspeellijst.\n"
        "- **Favorieten**: Voeg individuele video's toe aan een favorietenlijst en creëer er een afspeellijst van.\n"
        "- **Downloads**: Download de momenteel afspelende video direct naar een door jou gekozen map.\n"
        "- **Stream Sets**: Sla streams op in sets en speel ze later eenvoudig af.\n"
        "- **Geplande updates**: Laat de addon automatisch je Smart Folders bijwerken op gezette tijden.\n\n"
        "Navigeer via het contextmenu in Kodi (op video's) voor snelle acties, of start de addon via Programma's > Video add-ons voor de hoofdinterface."
    )
    dialog.ok(ADDON_NAME, message)

def show_main_menu():
    dialog = xbmcgui.Dialog()
    menu_items = [
        "Afspeellijst Maken",
        "Favorieten Afspeellijst Maken",
        "Beheer Smart Folders (Sets)",
        "Bijwerken van Alle Smart Folder Sets",
        "Stream Sets Beheren",
        "Toon Uitleg Addon"
    ]
    
    # Voeg een optie toe om de instellingen te openen
    menu_items.append("Instellingen Addon")

    choice = dialog.select(ADDON_NAME, menu_items)

    if choice == -1: # Annuleren
        return False # Geeft aan dat de lus moet stoppen

    if choice == 0:
        create_playlist()
    elif choice == 1:
        create_favorites_playlist()
    elif choice == 2:
        manage_sets()
    elif choice == 3:
        update_all_sets()
        xbmcgui.Dialog().notification(ADDON_NAME, "Alle Afspeellijst Sets Bijgewerkt!", xbmcgui.NOTIFICATION_INFO, 3000)
    elif choice == 4:
        stream_set_manager.manage_stream_sets_flow()
    elif choice == 5:
        show_explanation_dialog()
    elif choice == 6: # Instellingen openen
        ADDON.openSettings()
        
    return True # Geeft aan dat de lus moet doorgaan

def parse_arguments():
    if len(sys.argv) <= 1:
        return 'main', None, None

    # sys.argv[1] bevat de "action" string, bijvoorbeeld "action=add_favorite"
    # of de string "service"
    
    # We moeten sys.argv[1] parsen als het een 'action=' string is.
    # Anders is het waarschijnlijk de string 'service'.
    
    # Eerst, check of het een 'service' call is (deze heeft geen 'action=')
    if sys.argv[1] == 'service':
        return 'service', None, None

    # Voor andere acties, parse de query string
    args = dict(urllib.parse.parse_qsl(sys.argv[1]))

    action = args.get('action', '')
    
    if action == 'download_file':
        # Voor download_file, de 'path' en 'download_type' komen ook uit de args
        path = args.get('path', '')
        download_type = args.get('download_type', 'standard')
        return 'download', path, download_type
    elif action == 'add_favorite':
        path = args.get('path', '')
        return 'add_favorite', path, None
    elif action == 'remove_favorite':
        path = args.get('path', '')
        return 'remove_favorite', path, None
    elif action == 'create_favorites':
        return 'create_favorites', None, None
    elif action == 'create_playlist':
        return 'create_playlist', None, None
    elif action == 'manage_sets':
        return 'manage_sets', None, None
    elif action == 'update_all_sets':
        return 'update_all_sets', None, None
    elif action == 'save_playing_stream':
        return 'save_playing_stream', None, None
    elif action == 'manage_stream_sets':
        return 'manage_stream_sets', None, None
    elif action == 'show_explanation':
        return 'show_explanation', None, None
    else:
        # Als er geen specifieke actie is herkend, val terug op het hoofdmenu
        return 'main', None, None

if __name__ == '__main__':
    validate_settings_main()

    command, param1, param2 = parse_arguments()

    if command == 'download':
        download_file(param1, param2)
    elif command == 'add_favorite':
        toggle_favorite(param1, add=True)
    elif command == 'remove_favorite':
        toggle_favorite(param1, add=False)
    elif command == 'create_favorites':
        create_favorites_playlist()
    elif command == 'create_playlist':
        create_playlist()
    elif command == 'manage_sets':
        manage_sets()
    elif command == 'update_all_sets':
        update_all_sets(create_playlist_func=create_playlist): geef create_playlist mee
        xbmcgui.Dialog().notification(ADDON_NAME, "Alle Afspeellijst Sets Bijgewerkt!", xbmcgui.NOTIFICATION_INFO, 3000)
    elif command == 'save_playing_stream':
        stream_set_manager.save_playing_stream()
    elif command == 'manage_stream_sets':
        stream_set_manager.manage_stream_sets_flow()
    elif command == 'show_explanation':
        show_explanation_dialog()
    elif command == 'service':
        # Service wordt gestart via de service.py, deze code wordt niet direct uitgevoerd.
        log("default.py: Service command received, but service is handled by service.py.", xbmc.LOGDEBUG)
    elif command == 'main':
        # Toon het hoofdmenu in een lus totdat de gebruiker annuleert
        while show_main_menu():
            pass # Blijf in de lus