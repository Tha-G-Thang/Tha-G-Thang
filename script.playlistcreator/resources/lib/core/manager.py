import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import json
import random
import urllib.parse
from datetime import datetime, timedelta
import re

# Importeer utility functies
from resources.lib.core.base_utils import log, get_setting, set_setting, ADDON_PROFILE, PLAYLIST_DIR, load_json, save_json, show_busy_dialog, hide_busy_dialog, get_progress_dialog_mode, show_text_dialog
# Import AI modules conditionally (niet hier in manager.py direct, maar later in creator.py als nodig)

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')

class SetManager:
    def __init__(self):
        self.sets_file = xbmcvfs.translatePath(os.path.join(ADDON_PROFILE, 'playlist_sets.json'))
        self.sets = self.load_sets()
        log("SetManager initialized.", xbmc.LOGDEBUG)

    def load_sets(self):
        """Laadt de playlist sets vanuit het JSON-bestand."""
        log(f"Attempting to load sets from: {self.sets_file}", xbmc.LOGDEBUG)
        try:
            if xbmcvfs.exists(self.sets_file):
                data = load_json(self.sets_file)
                if isinstance(data, dict):
                    log(f"Successfully loaded {len(data)} sets.", xbmc.LOGDEBUG)
                    return data
                else:
                    log("Loaded sets data is not a dictionary. Initializing empty sets.", xbmc.LOGWARNING)
                    return {}
            else:
                log("Playlist sets file does not exist. Initializing empty sets.", xbmc.LOGINFO)
                return {}
        except Exception as e:
            log(f"Error loading sets: {e}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok(ADDON_NAME, f"Error loading playlist sets: {e}\nInitializing empty sets.")
            return {}

    def save_sets(self):
        """Slaat de playlist sets op naar het JSON-bestand."""
        log(f"Attempting to save {len(self.sets)} sets to: {self.sets_file}", xbmc.LOGDEBUG)
        try:
            save_json(self.sets_file, self.sets)
            log("Sets saved successfully.", xbmc.LOGDEBUG)
            return True
        except Exception as e:
            log(f"Error saving sets: {e}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok(ADDON_NAME, f"Error saving playlist sets: {e}")
            return False

    def get_sets(self):
        """Retourneert alle geladen sets als een dictionary."""
        log("Returning all sets.", xbmc.LOGDEBUG)
        return self.sets # De sets zijn al geladen in __init__ en worden bijgehouden

    def get_set_names(self):
        """Retourneert een lijst met de namen van alle sets."""
        log("Returning set names.", xbmc.LOGDEBUG)
        return list(self.sets.keys())

    def get_set_by_name(self, name):
        """Retourneert een specifieke set op basis van de naam."""
        log(f"Getting set by name: {name}", xbmc.LOGDEBUG)
        return self.sets.get(name)

    def set_active_set(self, set_name):
        """Stelt de actieve set in via een add-on instelling."""
        log(f"Setting active set to: {set_name}", xbmc.LOGINFO)
        set_setting('active_set', set_name)

    def get_active_set_name(self):
        """Haalt de naam van de actieve set op."""
        name = get_setting('active_set')
        log(f"Retrieved active set name: {name}", xbmc.LOGDEBUG)
        return name

    def create_new_set_flow(self):
        """Doorloop het proces voor het aanmaken van een nieuwe playlist set."""
        log("Starting new set creation flow.", xbmc.LOGINFO)
        dialog = xbmcgui.Dialog()

        set_name = dialog.input("Enter a name for the new Playlist Set:")
        if not set_name:
            log("Set creation cancelled by user (no name entered).", xbmc.LOGINFO)
            return

        if set_name in self.sets:
            dialog.ok(ADDON_NAME, f"A playlist set with the name '{set_name}' already exists.")
            log(f"Set creation aborted: name '{set_name}' already exists.", xbmc.LOGWARNING)
            return

        set_data = {
            "name": set_name,
            "folders": [],
            "include_subfolders": False,
            "file_extensions": "",
            "exclude_folders": "",
            "exclude_files": "",
            "folder_sort_order": "Alphabetical",
            "file_sort_order": "Alphabetical",
            "content_filter_mode": "None",
            "content_filter_keywords": "",
            "enable_ai_title_cleaning": False,
            "enable_ai_content_grouping": False,
            "enable_ai_auto_tagging": False,
            "enable_ai_metadata_enhancement": False,
            "playlist_folder_name_color": "None",
            "playlist_folder_name_position": "Before Name",
            "metadata_display_mode": "None",
            "progress_dialog_mode": "Determinate", # Nieuwe setting
            "last_updated": ""
        }
        
        # Initialiseer de AI instellingen op basis van globale AI setting
        if get_setting('enable_ai') == 'true':
            set_data["enable_ai_title_cleaning"] = True
            set_data["enable_ai_content_grouping"] = True
            set_data["enable_ai_auto_tagging"] = True
            set_data["enable_ai_metadata_enhancement"] = True

        self.sets[set_name] = set_data
        self.save_sets()
        dialog.notification(ADDON_NAME, f"Playlist Set '{set_name}' created successfully!", xbmcgui.NOTIFICATION_INFO, 3000)
        log(f"New playlist set '{set_name}' created and saved.", xbmc.LOGINFO)

        # Direct bewerken na creatie
        self.edit_set_settings(set_name)


    def manage_sets(self):
        """Toon een menu voor het beheren van sets (bewerken, verwijderen, uitvoeren)."""
        log("Entering manage_sets() menu.", xbmc.LOGINFO)
        dialog = xbmcgui.Dialog()
        
        while True:
            set_names = self.get_set_names()
            if not set_names:
                dialog.ok(ADDON_NAME, "No playlist sets to manage.")
                log("No sets found for management.", xbmc.LOGINFO)
                return

            options = [name for name in set_names]
            options.append("[ Create New Set ]")
            options.append("[ Back ]")
            
            selected_index = dialog.select("Manage Playlist Sets", options)

            if selected_index == -1 or options[selected_index] == "[ Back ]":
                log("Exiting manage_sets() menu.", xbmc.LOGDEBUG)
                break
            elif options[selected_index] == "[ Create New Set ]":
                self.create_new_set_flow()
                # Na creatie direct de menu's refresh-en
                self.sets = self.load_sets() # herlaad de sets na creatie
                continue # Blijf in de loop
            else:
                selected_set_name = options[selected_index]
                log(f"Selected set for management: {selected_set_name}", xbmc.LOGDEBUG)
                self._show_set_action_menu(selected_set_name)
                # Na actie, herlaad sets voor het geval er wijzigingen zijn
                self.sets = self.load_sets()


    def _show_set_action_menu(self, set_name):
        """Toon acties voor een specifieke set."""
        log(f"Showing action menu for set: {set_name}", xbmc.LOGDEBUG)
        dialog = xbmcgui.Dialog()
        actions = ["Run Set", "Edit Settings", "Delete Set", "Back"]
        
        action_choice = dialog.select(f"Actions for '{set_name}'", actions)

        if action_choice == 0: # Run Set
            from resources.lib.core.creator import PlaylistCreator # Importeer hier om circulaire afhankelijkheid te vermijden
            pc = PlaylistCreator()
            pc.create_playlist_from_set(set_name)
        elif action_choice == 1: # Edit Settings
            self.edit_set_settings(set_name)
        elif action_choice == 2: # Delete Set
            self.delete_set(set_name)
        log(f"Action '{actions[action_choice]}' for set '{set_name}' completed or cancelled.", xbmc.LOGDEBUG)

    def edit_set_settings(self, set_name):
        """Bewerkt de instellingen voor een specifieke set."""
        log(f"Editing settings for set: {set_name}", xbmc.LOGINFO)
        current_set = self.sets.get(set_name)
        if not current_set:
            xbmcgui.Dialog().ok(ADDON_NAME, f"Set '{set_name}' not found.")
            log(f"Attempted to edit non-existent set: {set_name}", xbmc.LOGWARNING)
            return

        settings_to_edit = [
            ("Folders (separated by |)", "text", "folders"),
            ("Include Subfolders", "bool", "include_subfolders"),
            ("File Extensions (e.g., .mp4|.mkv|.avi)", "text", "file_extensions"),
            ("Exclude Folders (separated by |)", "text", "exclude_folders"),
            ("Exclude Files (separated by |)", "text", "exclude_files"),
            ("Folder Sort Order", "select", "folder_sort_order", ["Alphabetical", "Newest", "Oldest", "Random"]),
            ("File Sort Order", "select", "file_sort_order", ["Alphabetical", "Newest", "Oldest", "Random", "AI Content Grouping"]), # AI optie toegevoegd
            ("Content Filter Mode", "select", "content_filter_mode", ["None", "Include Keywords", "Exclude Keywords"]),
            ("Content Filter Keywords (separated by |)", "text", "content_filter_keywords"),
            ("Enable AI Title Cleaning", "bool", "enable_ai_title_cleaning"),
            ("Enable AI Content Grouping", "bool", "enable_ai_content_grouping"),
            ("Enable AI Auto Tagging", "bool", "enable_ai_auto_tagging"),
            ("Enable AI Metadata Enhancement", "bool", "enable_ai_metadata_enhancement"),
            ("Playlist Folder Name Color", "select", "playlist_folder_name_color", ["None", "Red", "Green", "Blue", "Yellow", "Cyan", "Magenta", "White", "Black", "Orange", "Pink", "Purple", "Brown", "Gray", "Light Blue", "Dark Green"]),
            ("Playlist Folder Name Position", "select", "playlist_folder_name_position", ["Before Name", "After Name", "Hidden"]),
            ("Metadata Display Mode", "select", "metadata_display_mode", ["None", "All Metadata", "Selected Metadata"]),
            ("Progress Dialog Mode", "select", "progress_dialog_mode", ["Determinate", "Indeterminate"])
        ]

        # Filter AI settings als globale AI setting is uitgeschakeld
        if get_setting('enable_ai') == 'false':
            settings_to_edit = [s for s in settings_to_edit if not s[0].startswith("Enable AI")]
            # Verwijder "AI Content Grouping" uit file_sort_order als AI is uitgeschakeld
            for i, setting in enumerate(settings_to_edit):
                if setting[2] == "file_sort_order":
                    settings_to_edit[i] = (setting[0], setting[1], setting[2], [o for o in setting[3] if o != "AI Content Grouping"])
                    break

        new_values = {}
        for setting_name, setting_type, key, *args in settings_to_edit:
            current_value = current_set.get(key)
            log(f"Editing '{setting_name}'. Current value: '{current_value}'", xbmc.LOGDEBUG)

            if setting_type == "text":
                new_value = dialog.input(f"Enter {setting_name}:", defaultt=str(current_value) if current_value is not None else "")
                if new_value is not None: # Indien gebruiker op 'Cancel' drukt, blijft de waarde ongewijzigd
                    new_values[key] = new_value
            elif setting_type == "bool":
                choice = dialog.yesno(ADDON_NAME, f"Enable {setting_name}?", yeslabel="Yes", nolabel="No", autoclose=5000, defaultt=current_value)
                new_values[key] = choice
            elif setting_type == "select":
                options = args[0]
                try:
                    default_index = options.index(current_value) if current_value in options else 0
                except ValueError:
                    default_index = 0 # Fallback indien de oude waarde niet meer bestaat in de opties
                choice_index = dialog.select(f"Select {setting_name}:", options)
                if choice_index != -1:
                    new_values[key] = options[choice_index]
            log(f"New value for '{setting_name}': '{new_values.get(key, 'No change')}'", xbmc.LOGDEBUG)

        # Update de set met de nieuwe waarden
        for key, value in new_values.items():
            current_set[key] = value
        
        current_set["last_updated"] = datetime.now().isoformat()
        self.save_sets()
        dialog.notification(ADDON_NAME, f"Settings for '{set_name}' saved successfully!", xbmcgui.NOTIFICATION_INFO, 3000)
        log(f"Settings for set '{set_name}' updated and saved.", xbmc.LOGINFO)

    def delete_set(self, set_name):
        """Verwijdert een playlist set."""
        log(f"Attempting to delete set: {set_name}", xbmc.LOGINFO)
        dialog = xbmcgui.Dialog()
        if dialog.yesno(ADDON_NAME, f"Are you sure you want to delete the set '{set_name}'? This cannot be undone."):
            if set_name in self.sets:
                del self.sets[set_name]
                self.save_sets()
                dialog.notification(ADDON_NAME, f"Set '{set_name}' deleted.", xbmcgui.NOTIFICATION_INFO, 3000)
                log(f"Set '{set_name}' deleted.", xbmc.LOGINFO)
            else:
                dialog.ok(ADDON_NAME, f"Set '{set_name}' not found.")
                log(f"Attempted to delete non-existent set: {set_name}", xbmc.LOGWARNING)
        else:
            log(f"Deletion of set '{set_name}' cancelled by user.", xbmc.LOGINFO)

    def update_all_sets(self):
        """Werkt alle bestaande playlist sets bij."""
        log("Starting update for all playlist sets.", xbmc.LOGINFO)
        from resources.lib.core.creator import PlaylistCreator # Importeer hier om circulaire afhankelijkheid te vermijden
        pc = PlaylistCreator()
        
        if not self.sets:
            xbmcgui.Dialog().notification(ADDON_NAME, "No sets to update.", xbmcgui.NOTIFICATION_INFO, 3000)
            log("No sets found for update_all_sets().", xbmc.LOGINFO)
            return

        dialog_mode = get_progress_dialog_mode()
        
        if dialog_mode == "Determinate":
            p_dialog = xbmcgui.DialogProgress()
            p_dialog.create(ADDON_NAME, "Updating all playlist sets...")
        else: # Indeterminate
            show_busy_dialog(f"Updating all playlist sets...")
        
        total_sets = len(self.sets)
        for i, set_name in enumerate(list(self.sets.keys())): # Maak een kopie van keys om wijzigingen tijdens iteratie te voorkomen
            if dialog_mode == "Determinate":
                percentage = int((i / total_sets) * 100)
                if p_dialog.isCancelled():
                    log("Update cancelled by user.", xbmc.LOGINFO)
                    break
                p_dialog.update(percentage, f"Updating set: {set_name}", "Please wait...")
            else:
                show_busy_dialog(f"Updating set: {set_name}") # Update de busy dialog tekst

            try:
                pc.create_playlist_from_set(set_name)
                current_set = self.sets.get(set_name)
                if current_set:
                    current_set["last_updated"] = datetime.now().isoformat()
                    self.save_sets() # Sla elke set afzonderlijk op na update
                log(f"Successfully updated set: {set_name}", xbmc.LOGINFO)
            except Exception as e:
                log(f"Error updating set '{set_name}': {e}", xbmc.LOGERROR)
                xbmcgui.Dialog().ok(ADDON_NAME, f"Error updating set '{set_name}':\n{e}")
        
        if dialog_mode == "Determinate":
            p_dialog.close()
        else:
            hide_busy_dialog()

        xbmcgui.Dialog().notification(ADDON_NAME, "All selected sets updated!", xbmcgui.NOTIFICATION_INFO, 3000)
        log("Finished updating all playlist sets.", xbmc.LOGINFO)