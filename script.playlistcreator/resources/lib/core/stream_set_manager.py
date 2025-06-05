import xbmcgui
import xbmc
import xbmcvfs
import os
import time
from resources.lib.core.base_utils import log, load_json, save_json, ADDON_PROFILE, ADDON
from resources.lib.constants import STREAM_SETS_FILE, PLAYLIST_DIR # PLAYLIST_DIR is hier niet strikt nodig, maar als er in de toekomst een relatie komt tussen stream sets en fysieke afspeellijsten, is het goed om het hier te hebben.

class StreamSetManager:
    def __init__(self):
        self.stream_sets_path = os.path.join(ADDON_PROFILE, STREAM_SETS_FILE)
        self._load_stream_sets()

    def _load_stream_sets(self):
        """
        Laadt de stream sets vanuit het JSON-bestand.
        """
        self.stream_sets = load_json(STREAM_SETS_FILE) or {}
        log(f"Stream Sets geladen: {len(self.stream_sets)} sets.", xbmc.LOGDEBUG)

    def _save_stream_sets(self):
        """
        Slaat de huidige stream sets op naar het JSON-bestand.
        """
        save_json(STREAM_SETS_FILE, self.stream_sets)
        log(f"Stream Sets opgeslagen: {len(self.stream_sets)} sets.", xbmc.LOGDEBUG)

    def save_playing_stream(self):
        """
        Slaat de momenteel afspelende stream op in een door de gebruiker gekozen set.
        """
        player = xbmc.Player()
        if not player.isPlaying():
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Geen stream actief.", xbmcgui.NOTIFICATION_WARNING, 3000)
            log("Geen stream actief om op te slaan.", xbmc.LOGINFO)
            return False

        playing_url = player.getPlayingFile()
        if not playing_url:
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Kan URL van actieve stream niet ophalen.", xbmcgui.NOTIFICATION_ERROR, 3000)
            log("Kan URL van actieve stream niet ophalen.", xbmc.LOGERROR)
            return False

        # Vraag om een naam voor de stream
        stream_name = xbmcgui.Dialog().input("Geef de stream een naam:", type=xbmcgui.INPUT_ALPHANUM)
        if not stream_name:
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Stream opslaan geannuleerd: geen naam ingevoerd.", xbmcgui.NOTIFICATION_WARNING, 3000)
            log("Stream opslaan geannuleerd: geen naam ingevoerd.", xbmc.LOGINFO)
            return False

        # Vraag de gebruiker om een bestaande set te kiezen of een nieuwe te maken
        sets = list(self.stream_sets.keys())
        choice = xbmcgui.Dialog().select("Selecteer een stream set of maak een nieuwe:", ["Nieuwe Set maken"] + sets)

        set_name = None
        if choice == -1: # Annuleer
            log("Gebruiker heeft opslaan van stream geannuleerd (set selectie).", xbmc.LOGINFO)
            return False
        elif choice == 0: # Nieuwe Set maken
            new_set_name = xbmcgui.Dialog().input("Voer een naam in voor de nieuwe stream set:", type=xbmcgui.INPUT_ALPHANUM)
            if new_set_name:
                set_name = new_set_name
                self.stream_sets[set_name] = [] # Initialiseer de nieuwe set
                log(f"Nieuwe stream set '{set_name}' aangemaakt.", xbmc.LOGINFO)
            else:
                xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Stream opslaan geannuleerd: geen naam voor nieuwe set ingevoerd.", xbmcgui.NOTIFICATION_WARNING, 3000)
                log("Stream opslaan geannuleerd: geen naam voor nieuwe set ingevoerd.", xbmc.LOGINFO)
                return False
        else: # Bestaande set gekozen
            set_name = sets[choice - 1] # -1 omdat "Nieuwe Set maken" op index 0 staat

        if set_name:
            # Voeg de stream toe aan de gekozen set
            # Controleer op duplicaten voordat u toevoegt
            if {'name': stream_name, 'url': playing_url} not in self.stream_sets[set_name]:
                self.stream_sets[set_name].append({'name': stream_name, 'url': playing_url})
                self._save_stream_sets()
                xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Stream '{stream_name}' opgeslagen in set '{set_name}'.", xbmcgui.NOTIFICATION_INFO, 3000)
                log(f"Stream '{stream_name}' (URL: {playing_url}) opgeslagen in set '{set_name}'.", xbmc.LOGINFO)
                return True
            else:
                xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Stream '{stream_name}' bestaat al in set '{set_name}'.", xbmcgui.NOTIFICATION_INFO, 3000)
                log(f"Stream '{stream_name}' bestaat al in set '{set_name}'.", xbmc.LOGINFO)
                return False
        return False

    def play_stream_set(self):
        """
        Laat de gebruiker een stream set kiezen en speelt vervolgens een stream af uit die set.
        """
        if not self.stream_sets:
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Geen stream sets gevonden.", xbmcgui.NOTIFICATION_INFO, 3000)
            log("Geen stream sets gevonden om af te spelen.", xbmc.LOGINFO)
            return False

        set_names = list(self.stream_sets.keys())
        set_choice = xbmcgui.Dialog().select("Selecteer een stream set:", set_names)

        if set_choice > -1:
            set_name = set_names[set_choice]
            streams = self.stream_sets[set_name]

            if not streams:
                xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Stream set '{set_name}' is leeg.", xbmcgui.NOTIFICATION_INFO, 3000)
                log(f"Stream set '{set_name}' is leeg. Kan niets afspelen.", xbmc.LOGINFO)
                return False

            stream_names = [s['name'] for s in streams]
            stream_choice = xbmcgui.Dialog().select(f"Selecteer een stream uit '{set_name}':", stream_names)

            if stream_choice > -1:
                selected_stream = streams[stream_choice]
                xbmc.Player().play(selected_stream['url'])
                xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Stream '{selected_stream['name']}' gestart.", xbmcgui.NOTIFICATION_INFO, 3000)
                log(f"Stream '{selected_stream['name']}' (URL: {selected_stream['url']}) gestart vanuit set '{set_name}'.", xbmc.LOGINFO)
                return True
            else:
                log("Gebruiker heeft stream selectie geannuleerd.", xbmc.LOGINFO)
        else:
            log("Gebruiker heeft stream set selectie geannuleerd.", xbmc.LOGINFO)
        return False

    def remove_stream_from_set(self):
        """
        Laat de gebruiker een stream kiezen uit een set en verwijdert deze.
        """
        if not self.stream_sets:
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Geen stream sets gevonden.", xbmcgui.NOTIFICATION_INFO, 3000)
            log("Geen stream sets gevonden om een stream uit te verwijderen.", xbmc.LOGINFO)
            return False

        set_names = list(self.stream_sets.keys())
        set_choice = xbmcgui.Dialog().select("Selecteer de set waarvan u een stream wilt verwijderen:", set_names)

        if set_choice > -1:
            set_name = set_names[set_choice]
            streams = self.stream_sets[set_name]

            if not streams:
                xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Stream set '{set_name}' is leeg.", xbmcgui.NOTIFICATION_INFO, 3000)
                log(f"Stream set '{set_name}' is leeg. Geen streams om te verwijderen.", xbmc.LOGINFO)
                return False

            stream_names = [s['name'] for s in streams]
            stream_choice = xbmcgui.Dialog().select(f"Selecteer de stream om te verwijderen uit '{set_name}':", stream_names)

            if stream_choice > -1:
                stream_to_remove = streams[stream_choice]
                if xbmcgui.Dialog().yesno(ADDON.getAddonInfo('name'), f"Weet u zeker dat u '{stream_to_remove['name']}' wilt verwijderen?", f"uit set '{set_name}'?"):
                    self.stream_sets[set_name].pop(stream_choice)
                    self._save_stream_sets()
                    xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Stream '{stream_to_remove['name']}' verwijderd uit set '{set_name}'.", xbmcgui.NOTIFICATION_INFO, 3000)
                    log(f"Stream '{stream_to_remove['name']}' verwijderd uit set '{set_name}'.", xbmc.LOGINFO)
                    return True
                else:
                    log("Gebruiker heeft verwijdering van stream geannuleerd.", xbmc.LOGINFO)
            else:
                log("Gebruiker heeft stream selectie geannuleerd voor verwijdering.", xbmc.LOGINFO)
        else:
            log("Gebruiker heeft stream set selectie geannuleerd voor verwijdering.", xbmc.LOGINFO)
        return False

    def delete_stream_set(self):
        """
        Laat de gebruiker een hele stream set verwijderen.
        """
        if not self.stream_sets:
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Geen stream sets gevonden om te verwijderen.", xbmcgui.NOTIFICATION_INFO, 3000)
            log("Geen stream sets gevonden om te verwijderen.", xbmc.LOGINFO)
            return False

        set_names = list(self.stream_sets.keys())
        choice = xbmcgui.Dialog().select("Selecteer stream set om te verwijderen:", set_names)

        if choice > -1:
            set_to_delete = set_names[choice]
            if xbmcgui.Dialog().yesno(ADDON.getAddonInfo('name'), f"Weet u zeker dat u set '{set_to_delete}' en alle daarin opgeslagen streams wilt verwijderen?"):
                del self.stream_sets[set_to_delete]
                self._save_stream_sets()
                xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Stream set '{set_to_delete}' verwijderd.", xbmcgui.NOTIFICATION_INFO, 3000)
                log(f"Stream set '{set_to_delete}' verwijderd.", xbmc.LOGINFO)
                return True
            else:
                log(f"Verwijdering van stream set '{set_to_delete}' geannuleerd door gebruiker.", xbmc.LOGINFO)
        return True

    def manage_stream_sets_flow(self):
        """
        Presenteert het beheermenu voor stream sets.
        """
        dialog = xbmcgui.Dialog()
        while True:
            menu_items = ["Stream Set Afspelen", "Verwijder Stream uit Set", "Verwijder Hele Stream Set"]
            
            choice = dialog.select("Beheer Stream Sets:", menu_items)

            if choice == -1: # Annuleer
                break
            elif choice == 0: # Stream Set Afspelen
                self.play_stream_set()
            elif choice == 1: # Verwijder Stream uit Set
                self.remove_stream_from_set()
            elif choice == 2: # Verwijder Hele Stream Set
                self.delete_stream_set()