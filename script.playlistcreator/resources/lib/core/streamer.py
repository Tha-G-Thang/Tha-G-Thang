import xbmcgui
import xbmc
import xbmcvfs
import os
import time
from resources.lib.core.base_utils import log, load_json, save_json, get_setting # Importeer get_setting
from resources.lib.constants import ADDON_PROFILE, PLAYLIST_DIR, ADDON_NAME, STREAM_SETS_FILE # Importeer benodigde constanten

class StreamSetManager:
    def __init__(self):
        self.stream_sets_path = self._get_stream_sets_storage_path()
        self._ensure_storage_path_exists()
        self._load_stream_sets()

    def _get_stream_sets_storage_path(self):
        """
        Bepaalt de opslaglocatie voor stream_sets.json op basis van de addon-instellingen.
        """
        location_type = get_setting('stream_sets_location_type', '0')
        base_dir = ADDON_PROFILE # Standaard is addon profielmap

        if location_type == '1': # Binnen Standaard Downloadmap (/Streams/)
            download_path = get_setting('download_path', '')
            if download_path and xbmcvfs.exists(download_path):
                base_dir = os.path.join(download_path, 'Streams')
            else:
                log("Standaard downloadmap niet gevonden of ingesteld, valt terug op addon profielmap voor streams.", xbmc.LOGWARNING)
        elif location_type == '2': # Binnen Adult Downloadmap (/Streams/)
            download_path_adult = get_setting('download_path_adult', '')
            if download_path_adult and xbmcvfs.exists(download_path_adult):
                base_dir = os.path.join(download_path_adult, 'Streams')
            else:
                log("Adult downloadmap niet gevonden of ingesteld, valt terug op addon profielmap voor streams.", xbmc.LOGWARNING)
        elif location_type == '3': # Aangepaste Map
            custom_path = get_setting('custom_stream_sets_path', '')
            if custom_path and xbmcvfs.exists(custom_path):
                base_dir = custom_path
            else:
                log("Aangepaste stream sets map niet gevonden of ingesteld, valt terug op addon profielmap voor streams.", xbmc.LOGWARNING)
        
        return os.path.join(base_dir, STREAM_SETS_FILE)

    def _ensure_storage_path_exists(self):
        """
        Zorgt ervoor dat de map voor stream_sets.json bestaat.
        """
        storage_dir = os.path.dirname(self.stream_sets_path)
        if not xbmcvfs.exists(storage_dir):
            xbmcvfs.mkdirs(storage_dir)
            log(f"Map voor stream sets aangemaakt: {storage_dir}", xbmc.LOGINFO)


    def _load_stream_sets(self):
        """
        Laadt de stream sets vanuit het JSON-bestand.
        """
        # load_json verwacht het volledige pad
        self.stream_sets = load_json(self.stream_sets_path) or {}
        log(f"Stream Sets geladen: {len(self.stream_sets)} sets vanuit {self.stream_sets_path}.", xbmc.LOGDEBUG)

    def _save_stream_sets(self):
        """
        Slaat de huidige stream sets op naar het JSON-bestand.
        """
        # save_json verwacht het volledige pad
        save_json(self.stream_sets, self.stream_sets_path)
        log(f"Stream Sets opgeslagen: {len(self.stream_sets)} sets naar {self.stream_sets_path}.", xbmc.LOGDEBUG)

    def save_playing_stream(self):
        """
        Slaat de momenteel afspelende stream op in een door de gebruiker gekozen set.
        """
        player = xbmc.Player()
        if not player.isPlaying():
            xbmcgui.Dialog().notification(ADDON_NAME, "Geen media wordt momenteel afgespeeld.", xbmcgui.NOTIFICATION_INFO, 3000)
            log("Geen media wordt momenteel afgespeeld om op te slaan.", xbmc.LOGINFO)
            return

        current_playing_file = player.getPlayingFile()
        if not current_playing_file:
            xbmcgui.Dialog().notification(ADDON_NAME, "Kon afspelend bestandspad niet ophalen.", xbmcgui.NOTIFICATION_INFO, 3000)
            log("Kon afspelend bestandspad niet ophalen.", xbmc.LOGWARNING)
            return
            
        dialog = xbmcgui.Dialog()
        set_names = list(self.stream_sets.keys())
        
        options = ["Nieuwe Stream Set Aanmaken"] + set_names
        
        choice = dialog.select("Kies of maak een Stream Set:", options)

        if choice == -1:
            log("Opslaan stream geannuleerd door gebruiker.", xbmc.LOGINFO)
            return

        set_name = ""
        if choice == 0:
            set_name = dialog.input('Voer nieuwe Stream Set naam in', type=xbmcgui.INPUT_ALPHANUM)
            if not set_name:
                log("Geen set naam ingevoerd, opslaan stream geannuleerd.", xbmc.LOGINFO)
                return
            if set_name in self.stream_sets:
                xbmcgui.Dialog().notification(ADDON_NAME, f"Stream Set '{set_name}' bestaat al. Kies een andere naam of bewerk de bestaande set.", xbmcgui.NOTIFICATION_WARNING, 4000)
                log(f"Stream Set '{set_name}' bestaat al.", xbmc.LOGWARNING)
                return
            self.stream_sets[set_name] = []

        else:
            set_name = set_names[choice - 1]

        if current_playing_file in self.stream_sets[set_name]:
            xbmcgui.Dialog().notification(ADDON_NAME, f"Stream is al opgeslagen in '{set_name}'.", xbmcgui.NOTIFICATION_INFO, 3000)
            log(f"Stream '{current_playing_file}' is al opgeslagen in '{set_name}'.", xbmc.LOGINFO)
            return

        self.stream_sets[set_name].append(current_playing_file)
        self._save_stream_sets()
        xbmcgui.Dialog().notification(ADDON_NAME, f"Stream opgeslagen in set '{set_name}'.", xbmcgui.NOTIFICATION_INFO, 3000)
        log(f"Stream '{current_playing_file}' opgeslagen in set '{set_name}'.", xbmc.LOGINFO)


    def play_stream_set(self):
        """
        Presenteert een lijst van stream sets en speelt de gekozen set af.
        """
        if not self.stream_sets:
            xbmcgui.Dialog().notification(ADDON_NAME, "Geen stream sets gevonden.", xbmcgui.NOTIFICATION_INFO, 3000)
            log("Geen stream sets gevonden om af te spelen.", xbmc.LOGINFO)
            return

        dialog = xbmcgui.Dialog()
        set_names = list(self.stream_sets.keys())
        choice = dialog.select("Kies een Stream Set om af te spelen:", set_names)

        if choice == -1:
            log("Afspelen stream set geannuleerd door gebruiker.", xbmc.LOGINFO)
            return

        selected_set_name = set_names[choice]
        streams_to_play = self.stream_sets.get(selected_set_name, [])

        if not streams_to_play:
            xbmcgui.Dialog().notification(ADDON_NAME, f"Stream set '{selected_set_name}' bevat geen streams.", xbmcgui.NOTIFICATION_INFO, 3000)
            log(f"Stream set '{selected_set_name}' bevat geen streams.", xbmc.LOGWARNING)
            return

        if xbmcgui.Dialog().yesno(ADDON_NAME, "Stream Set Shufflen?", yeslabel="Ja", nolabel="Nee"):
            import random
            random.shuffle(streams_to_play)

        xbmcgui.Dialog().notification(ADDON_NAME, f"Start afspelen van stream set '{selected_set_name}'.", xbmcgui.NOTIFICATION_INFO, 3000)
        
        xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
        for stream_url in streams_to_play:
            list_item = xbmcgui.ListItem(path=stream_url)
            if not list_item.getLabel():
                list_item.setLabel(os.path.basename(stream_url.split('?')[0]) or stream_url)
            xbmc.PlayList(xbmc.PLAYLIST_VIDEO).add(stream_url, list_item)
        
        xbmc.Player().play(xbmc.PlayList(xbmc.PLAYLIST_VIDEO))
        log(f"Afspelen van stream set '{selected_set_name}' gestart met {len(streams_to_play)} streams.", xbmc.LOGINFO)


    def remove_stream_from_set(self):
        """
        Verwijder een specifieke stream uit een gekozen set.
        """
        if not self.stream_sets:
            xbmcgui.Dialog().notification(ADDON_NAME, "Geen stream sets gevonden om te bewerken.", xbmcgui.NOTIFICATION_INFO, 3000)
            log("Geen stream sets gevonden om te bewerken.", xbmc.LOGINFO)
            return
        
        dialog = xbmcgui.Dialog()
        set_names = list(self.stream_sets.keys())
        set_choice = dialog.select("Kies de Stream Set om te bewerken:", set_names)

        if set_choice == -1:
            log("Verwijderen stream uit set geannuleerd door gebruiker.", xbmc.LOGINFO)
            return

        selected_set_name = set_names[set_choice]
        streams_in_set = self.stream_sets.get(selected_set_name, [])

        if not streams_in_set:
            xbmcgui.Dialog().notification(ADDON_NAME, f"Stream set '{selected_set_name}' bevat geen streams.", xbmcgui.NOTIFICATION_INFO, 3000)
            log(f"Stream set '{selected_set_name}' bevat geen streams om te verwijderen.", xbmc.LOGWARNING)
            return

        stream_display_names = [os.path.basename(s.split('?')[0]) if os.path.basename(s.split('?')[0]) else s for s in streams_in_set]
        
        stream_choice = dialog.select(f"Kies een stream om te verwijderen uit '{selected_set_name}':", stream_display_names)

        if stream_choice == -1:
            log("Verwijderen stream uit set geannuleerd door gebruiker.", xbmc.LOGINFO)
            return

        stream_to_remove = streams_in_set[stream_choice]
        
        if dialog.yesno(ADDON_NAME, f"Weet u zeker dat u '{stream_display_names[stream_choice]}' wilt verwijderen uit set '{selected_set_name}'?"):
            self.stream_sets[selected_set_name].pop(stream_choice)
            self._save_stream_sets()
            xbmcgui.Dialog().notification(ADDON_NAME, f"Stream verwijderd uit set '{selected_set_name}'.", xbmcgui.NOTIFICATION_INFO, 3000)
            log(f"Stream '{stream_to_remove}' verwijderd uit set '{selected_set_name}'.", xbmc.LOGINFO)
        else:
            log("Verwijdering stream geannuleerd door gebruiker.", xbmc.LOGINFO)

    def remove_whole_stream_set(self):
        """
        Verwijder een hele stream set.
        """
        if not self.stream_sets:
            xbmcgui.Dialog().notification(ADDON_NAME, "Geen stream sets gevonden om te verwijderen.", xbmcgui.NOTIFICATION_INFO, 3000)
            log("Geen stream sets gevonden om te verwijderen.", xbmc.LOGINFO)
            return
        
        dialog = xbmcgui.Dialog()
        set_names = list(self.stream_sets.keys())
        choice = dialog.select("Selecteer stream set om te verwijderen:", set_names)

        if choice == -1:
            log("Verwijdering hele stream set geannuleerd door gebruiker.", xbmc.LOGINFO)
            return

        set_to_delete = set_names[choice]
        if dialog.yesno(ADDON_NAME, f"Weet u zeker dat u set '{set_to_delete}' en alle daarin opgeslagen streams wilt verwijderen?"):
            del self.stream_sets[set_to_delete]
            self._save_stream_sets()
            xbmcgui.Dialog().notification(ADDON_NAME, f"Stream set '{set_to_delete}' verwijderd.", xbmcgui.NOTIFICATION_INFO, 3000)
            log(f"Stream set '{set_to_delete}' verwijderd.", xbmc.LOGINFO)
            return True
        else:
            log(f"Verwijdering van stream set '{set_to_delete}' geannuleerd door gebruiker.", xbmc.LOGINFO)
        return False

    def manage_stream_sets_flow(self):
        """
        Presenteert het beheermenu voor stream sets.
        """
        dialog = xbmcgui.Dialog()
        while True:
            menu_items = [
                "Nieuwe Stream Set Maken (of voeg stream toe aan bestaande)",
                "Stream Set Afspelen",
                "Verwijder Stream uit Set",
                "Verwijder Hele Stream Set"
            ]
            
            choice = dialog.select("Beheer Stream Sets:", menu_items)

            if choice == -1:
                break
            elif choice == 0:
                self.save_playing_stream()
            elif choice == 1:
                self.play_stream_set()
            elif choice == 2:
                self.remove_stream_from_set()
            elif choice == 3:
                self.remove_whole_stream_set()
        log("Beheer stream sets menu afgesloten.", xbmc.LOGINFO)