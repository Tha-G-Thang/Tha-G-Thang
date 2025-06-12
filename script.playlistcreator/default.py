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

# Initialiseer de StreamSetManager als een globale instantie
stream_set_manager = StreamSetManager()

def validate_settings_main():
    """Ensure essential directories exist and settings are valid for the main script."""
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
        log("Main: Invalid min_file_size reset to 1MB.", xbmc.LOGWARNING)

    if get_setting('enable_max_size', 'false') == 'true':
        try:
            max_size = int(get_setting('max_file_size', '0'))
            if max_size < 0:
                set_setting('max_file_size', '0')
                log("Main: Invalid max_file_size corrected to 0MB.", xbmc.LOGWARNING)
        except ValueError:
            set_setting('max_file_size', '0')
            log("Main: Invalid max_file_size reset to 0MB.", xbmc.LOGWARNING)

def show_explanation_dialog():
    """Shows a dialog explaining key features and usage."""
    dialog_text = """
    [B]Welkom bij Playlist Creator! Dit zijn de belangrijkste functies:[/B]

    [B]1. Nieuwe Afspeellijst Maken:[/B]
    Selecteer één of meerdere mappen. De addon scant deze op video's en genereert een .m3u afspeellijst in je Kodi 'video playlists' map. De sorteeropties in de instellingen bepalen de volgorde.

    [B]2. Beheer Afspeellijst Sets:[/B]
    Hiermee kun je 'sets' van mappen opslaan. Elke set kan met één klik een afspeellijst genereren. Handig voor vaak gebruikte collecties.

    [B]3. Update Alle Afspeellijst Sets:[/B]
    Genereert afspeellijsten voor alle opgeslagen sets. Dit kan ook automatisch op de achtergrond draaien via de service (zie instellingen).

    [B]4. Maak Favorieten Afspeellijst:[/B]
    Genereert een afspeellijst van al je 'Favorieten'.

    [B]5. Beheer Stream Sets:[/B]
    Hiermee kun je actieve (online) streams opslaan in sets en deze later direct afspelen. Ideaal voor DJ-sets, livestreams, etc.

    [B]6. Context Menu Opties (Druk op 'C' of lange druk op een item):[/B]
    - [B]Toevoegen/Verwijderen uit favorieten:[/B] Voeg een afgespeeld bestand toe aan/verwijder uit je favorietenlijst.
    - [B]Maak favorieten-afspeellijst:[/B] Direct een afspeellijst genereren van je favorieten.
    - [B]Sla Afspelende Stream op:[/B] Sla de URL van een actieve stream op in een stream set.
    - [B]Download:[/B] Download het afgespeelde video-bestand naar een lokale map.

    [B]7. Instellingen:[/B]
    Pas hier alle opties aan, inclusief scan-, sorteer-, download-, en serviceregels.
    """
    xbmcgui.Dialog().ok(f"{ADDON_NAME} - Toelichting & Help", dialog_text)


def show_main_menu():
    """Main menu for the addon."""
    dialog = xbmcgui.Dialog()
    options = [
        "Nieuwe Afspeellijst Maken",
        "Beheer Afspeellijst Sets",
        "Update Alle Afspeellijst Sets",
        "Maak Favorieten Afspeellijst",
        "Beheer Stream Sets",
        "Open Instellingen",
        "Toelichting & Help" # Nieuw menu-item
    ]
    
    choice = dialog.select(f"{ADDON_ID} - Hoofdmenu", options)
    
    if choice == 0:
        create_playlist()
    elif choice == 1:
        manage_sets()
    elif choice == 2:
        update_all_sets()
        xbmcgui.Dialog().notification(ADDON_NAME, "Alle Afspeellijst Sets Bijgewerkt!", xbmcgui.NOTIFICATION_INFO, 3000)
    elif choice == 3:
        create_favorites_playlist()
    elif choice == 4:
        stream_set_manager.manage_stream_sets_flow()
    elif choice == 5:
        ADDON.openSettings() # Gebruik ADDON object van constants
    elif choice == 6: # Handelt het nieuwe menu-item af
        show_explanation_dialog()


def parse_arguments():
    """Parse command line arguments for addon actions."""
    if len(sys.argv) <= 1:
        return 'main', None, None

    # sys.argv[1] is meestal de scriptnaam, sys.argv[2] bevat de query string
    args = dict(urllib.parse.parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 else {}
    action = args.get('action', '')
    
    if action == 'download_file':
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
    elif action == 'show_explanation': # Nieuwe actie voor de toelichting
        return 'show_explanation', None, None
    else:
        return 'main', None, None

# Hoofd uitvoering van de addon (NIET DE SERVICE)
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
        update_all_sets()
        xbmcgui.Dialog().notification(ADDON_NAME, "Alle Afspeellijst Sets Bijgewerkt!", xbmcgui.NOTIFICATION_INFO, 3000)
    elif command == 'save_playing_stream':
        stream_set_manager.save_playing_stream()
    elif command == 'manage_stream_sets':
        stream_set_manager.manage_stream_sets_flow()
    elif command == 'show_explanation': # Handelt de nieuwe actie af
        show_explanation_dialog()
    elif command == 'main':
        show_main_menu()
    else:
        log(f"Main: Onbekend commando of actie: {command}", xbmc.LOGWARNING)
        show_main_menu()