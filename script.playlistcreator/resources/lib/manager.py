import os
import xbmcgui
import xbmcvfs
import time
import xbmc  # Added for logging levels
import json
import xbmcaddon  # Added for settings manipulation

from resources.lib.utils import log, get_setting, set_setting, save_json, load_json, ADDON_PROFILE, PLAYLIST_DIR
from resources.lib.scanner import DAVSScanner
from resources.lib.creator import PlaylistCreator
from resources.lib.constants import CONFIG_FILE, ADDON_ID


class SetManager:
    def __init__(self):
        self.config_file_path = os.path.join(ADDON_PROFILE, CONFIG_FILE)
        # Ensure the profile directory exists
        if not xbmcvfs.exists(ADDON_PROFILE):
            try:
                xbmcvfs.mkdirs(ADDON_PROFILE)
                log(f"Created addon profile directory: {ADDON_PROFILE}", xbmc.LOGINFO)
            except Exception as e:
                log(f"Failed to create addon profile directory: {ADDON_PROFILE} - {e}", xbmc.LOGERROR)
                xbmcgui.Dialog().notification(get_setting('ADDON_NAME', 'Playlist Creator'), "Error: Could not create profile directory.", time=5000)

    def _get_set_name(self, default_name=""):
        """
        Prompts the user for a set name.
        """
        name = xbmcgui.Dialog().input("Enter Set Name:", defaultt=default_name)
        return name if name else None

    def _select_folders_dialog(self):
        """
        Allows the user to select multiple folders.
        """
        folders = []
        path = xbmcvfs.translatePath('special://video/')  # Default starting path
        dialog = xbmcgui.Dialog()

        # Select first folder
        folder = dialog.browse(0, "Select First Folder (Cancel to abort)", 'files', defaultt=path)
        if not folder:
            return None
        folders.append(folder)

        # Allow adding more folders
        while dialog.yesno("Add another folder?", "Do you want to add another folder to this set?"):
            folder = dialog.browse(0, "Select Additional Folder", 'files', defaultt=path)
            if folder and folder not in folders:
                folders.append(folder)
            elif folder:
                dialog.notification(get_setting('ADDON_NAME', 'Playlist Creator'), "Folder already added", xbmcgui.NOTIFICATION_WARNING)
        return folders

    def save_folder_set(self, name, folders):
        """
        Saves a folder set with its associated settings.
        """
        sets = self.load_folder_sets()
        if sets is None:
            sets = {}

        # Get current addon settings to save with the set
        current_settings = self._get_current_addon_settings()

        sets[name] = {'folders': folders, 'settings': current_settings}
        if save_json(sets, self.config_file_path):
            xbmcgui.Dialog().notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Folder set '{name}' saved successfully!", xbmcgui.NOTIFICATION_INFO)
            return True
        else:
            xbmcgui.Dialog().notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Failed to save folder set '{name}'.", xbmcgui.NOTIFICATION_ERROR)
            return False

    def load_folder_sets(self):
        """
        Loads all saved folder sets.
        """
        sets = load_json(self.config_file_path)
        if sets is None:
            log(f"No existing folder sets found at {self.config_file_path}.", xbmc.LOGINFO)
            return {}
        return sets

    def delete_folder_set(self, set_name):
        """
        Deletes a specific folder set and its associated playlist file.
        """
        sets = self.load_folder_sets()
        if set_name in sets:
            if xbmcgui.Dialog().yesno("Confirm Deletion", f"Are you sure you want to delete the set '{set_name}'? This will also delete the associated playlist file."):
                del sets[set_name]
                playlist_path = os.path.join(PLAYLIST_DIR, f"{set_name}.m3u")
                if xbmcvfs.exists(playlist_path):
                    xbmcvfs.delete(playlist_path)
                    log(f"Deleted playlist file: {playlist_path}", xbmc.LOGINFO)
                if save_json(sets, self.config_file_path):
                    xbmcgui.Dialog().notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Set '{set_name}' and its playlist deleted.", xbmcgui.NOTIFICATION_INFO)
                    return True
                else:
                    xbmcgui.Dialog().notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Failed to delete set '{set_name}'.", xbmcgui.NOTIFICATION_ERROR)
                    return False
        else:
            xbmcgui.Dialog().notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Set '{set_name}' not found.", xbmcgui.NOTIFICATION_WARNING)
        return False

    def _get_current_addon_settings(self):
        """
        Retrieves all current settings of the addon.
        This is a simplified approach; in a real scenario, you'd iterate through
        all setting IDs defined in your settings.xml. For now, we'll store a few key ones.
        """
        addon = xbmcaddon.Addon(ADDON_ID)
        settings = {}
        # Example: Collect a few important settings. Extend this based on your settings.xml
        settings['file_extensions'] = addon.getSetting('file_extensions')
        settings['exclude_pattern'] = addon.getSetting('exclude_pattern')
        settings['exclude_folders'] = addon.getSetting('exclude_folders')
        settings['min_file_size'] = addon.getSetting('min_file_size')
        settings['enable_max_size'] = addon.getSettingBool('enable_max_size')
        settings['max_file_size'] = addon.getSetting('max_file_size')
        settings['recursive_scan'] = addon.getSettingBool('recursive_scan')
        settings['scan_depth'] = addon.getSetting('scan_depth')
        settings['sort_mode'] = addon.getSetting('sort_mode')
        settings['randomize_files'] = addon.getSettingBool('randomize_files')
        settings['enable_file_limit_per_folder'] = addon.getSettingBool('enable_file_limit_per_folder')
        settings['file_count_per_folder'] = addon.getSetting('file_count_per_folder')
        settings['enable_global_file_limit'] = addon.getSettingBool('enable_global_file_limit')
        settings['global_file_count'] = addon.getSetting('global_file_count')
        settings['enable_backups'] = addon.getSettingBool('enable_backups')
        settings['show_folder_names'] = addon.getSettingBool('show_folder_names')
        settings['folder_name_color'] = addon.getSetting('folder_name_color')
        settings['show_metadata'] = addon.getSettingBool('show_metadata')
        settings['show_duration'] = addon.getSettingBool('show_duration')
        settings['show_file_size'] = addon.getSettingBool('show_file_size')
        settings['folder_sort_mode'] = addon.getSetting('folder_sort_mode')
        settings['custom_folder_order'] = addon.getSetting('custom_folder_order')

        # Add adult content settings if they exist and are relevant
        settings['adult_download_path'] = addon.getSetting('adult_download_path')
        settings['download_cleanup_adult_toggle'] = addon.getSettingBool('download_cleanup_adult_toggle')
        settings['download_delete_words_adult'] = addon.getSetting('download_delete_words_adult')
        settings['download_switch_words_adult'] = addon.getSetting('download_switch_words_adult')
        settings['download_regex_enable_adult'] = addon.getSettingBool('download_regex_enable_adult')
        settings['download_regex_pattern_adult'] = addon.getSetting('download_regex_pattern_adult')
        settings['download_regex_replace_with_adult'] = addon.getSetting('download_regex_replace_with_adult')

        return settings

    def apply_set_settings(self, set_name):
        """
        Applies the saved settings for a given set to the addon's current settings.
        """
        sets = self.load_folder_sets()
        if set_name in sets and 'settings' in sets[set_name]:
            set_settings = sets[set_name]['settings']
            addon = xbmcaddon.Addon(ADDON_ID)
            applied_count = 0
            for key, value in set_settings.items():
                try:
                    # setSetting handles different types automatically if the value is correct
                    if isinstance(value, bool):
                        addon.setSettingBool(key, value)
                    elif isinstance(value, int):
                        addon.setSettingInt(key, value)
                    elif isinstance(value, float):
                        addon.setSettingNumber(key, value)
                    else: # Treat as string for text, enum, path types
                        addon.setSetting(key, str(value))
                    applied_count += 1
                    log(f"Applied setting for set '{set_name}': {key} = {value}", xbmc.LOGDEBUG)
                except Exception as e:
                    log(f"Error applying setting '{key}' for set '{set_name}': {e}", xbmc.LOGWARNING)
            xbmcgui.Dialog().notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Settings for '{set_name}' applied ({applied_count} settings).", time=3000)
            return True
        else:
            xbmcgui.Dialog().notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"No saved settings found for set '{set_name}'.", xbmcgui.NOTIFICATION_WARNING)
            return False

    def create_playlist_from_set(self, set_name):
        """
        Creates a playlist from a saved folder set.
        Asks the user if saved settings for the set should be applied.
        """
        sets = self.load_folder_sets()
        if set_name not in sets:
            xbmcgui.Dialog().notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Set '{set_name}' not found.", xbmcgui.NOTIFICATION_ERROR)
            return False

        # Ask user if they want to apply saved settings
        if xbmcgui.Dialog().yesno(get_setting('ADDON_NAME', 'Playlist Creator'),
                                  f"Apply saved settings for '{set_name}' before creating playlist?",
                                  "Selecting 'No' will use current addon settings."):
            self.apply_set_settings(set_name)
            # Short delay to ensure settings are registered before proceeding
            time.sleep(0.5)

        folders = sets[set_name]['folders']
        creator = PlaylistCreator()
        if creator.create(set_name, folders, save_set=False):  # save_set=False as it's already saved
            xbmcgui.Dialog().notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Playlist '{set_name}' created successfully!", xbmcgui.NOTIFICATION_INFO)
            return True
        else:
            xbmcgui.Dialog().notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Failed to create playlist '{set_name}'. Check logs.", xbmcgui.NOTIFICATION_ERROR)
            return False

    def manage_sets_dialog(self):
        """
        Provides an interactive dialog for managing folder sets.
        """
        dialog = xbmcgui.Dialog()
        while True:
            sets = self.load_folder_sets()
            if not sets:
                dialog.notification(get_setting('ADDON_NAME', 'Playlist Creator'), "No folder sets found. Create one first.", time=3000)
                return

            set_names = sorted(sets.keys())
            # Add a "Back" option
            list_items = [f"{name} ({len(sets[name]['folders'])} folders)" for name in set_names]
            list_items.append("[COLOR grey].. Back[/COLOR]")

            selected_index = dialog.select("Manage Folder Sets", list_items)

            if selected_index == -1 or selected_index == len(list_items) - 1:  # Cancel or 'Back' selected
                break

            set_name = set_names[selected_index]

            # Options for the selected set
            action = dialog.select(f"Actions for Set: {set_name}", [
                "Create/Update Playlist",
                "Edit Set Name & Folders",
                "Apply Settings from Set",
                "Delete Set",
                "[COLOR grey].. Back[/COLOR]"
            ])

            if action == -1 or action == 4:  # Cancel or 'Back' selected
                continue
            elif action == 0:  # Create/Update Playlist
                self.create_playlist_from_set(set_name)
            elif action == 1:  # Edit Set Name & Folders
                new_name = self._get_set_name(default_name=set_name)
                if new_name and new_name != set_name:
                    if new_name in sets:
                        dialog.notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Set with name '{new_name}' already exists. Choose a different name.", xbmcgui.NOTIFICATION_ERROR)
                        continue
                    sets[new_name] = sets.pop(set_name) # Rename key
                    # Update playlist filename if it exists
                    old_playlist_path = os.path.join(PLAYLIST_DIR, f"{set_name}.m3u")
                    new_playlist_path = os.path.join(PLAYLIST_DIR, f"{new_name}.m3u")
                    if xbmcvfs.exists(old_playlist_path):
                        if xbmcvfs.rename(old_playlist_path, new_playlist_path):
                            log(f"Renamed playlist from {os.path.basename(old_playlist_path)} to {os.path.basename(new_playlist_path)}")
                        else:
                            log(f"Failed to rename playlist file from {os.path.basename(old_playlist_path)} to {os.path.basename(new_playlist_path)}", xbmc.LOGWARNING)

                    set_name = new_name # Update set_name for current loop iteration
                    dialog.notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Set renamed to '{set_name}'", xbmcgui.NOTIFICATION_INFO)

                # Always offer to re-select folders after name change or if just editing folders
                if dialog.yesno("Edit Folders?", f"Do you want to edit folders for '{set_name}'?"):
                    new_folders = self._select_folders_dialog()
                    if new_folders:
                        sets[set_name]['folders'] = new_folders
                        # Optionally, save current settings with the updated set as well
                        if dialog.yesno(get_setting('ADDON_NAME', 'Playlist Creator'), f"Save current addon settings with '{set_name}'?", "This will overwrite previously saved settings for this set."):
                            sets[set_name]['settings'] = self._get_current_addon_settings()

                        if save_json(sets, self.config_file_path):
                            dialog.notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Folders and settings updated for '{set_name}'. Updating playlist...", xbmcgui.NOTIFICATION_INFO)
                            # Directly update the playlist after editing folders/settings
                            self.create_playlist_from_set(set_name) # This will prompt for settings application
                        else:
                            dialog.notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Failed to save and update settings for: {set_name}", xbmcgui.NOTIFICATION_ERROR)
            elif action == 2: # Apply Settings from Set
                self.apply_set_settings(set_name)
            elif action == 3: # Delete Set
                if self.delete_folder_set(set_name):
                    # No need to pop from set_names here, the loop will reload sets and rebuild set_names
                    # and if no sets left, it will exit
                    pass # delete_folder_set already shows notification and logs


    def update_all_sets_dialog(self):
        """
        Updates all existing playlists based on their saved folder sets.
        Asks the user per set if saved settings should be applied.
        """
        dialog = xbmcgui.Dialog()
        sets = self.load_folder_sets()

        if not sets:
            dialog.notification(get_setting('ADDON_NAME', 'Playlist Creator'), "No folder sets to update.", xbmcgui.NOTIFICATION_INFO)
            return

        if not dialog.yesno(get_setting('ADDON_NAME', 'Playlist Creator'), "Confirm Update", "Do you want to update all existing playlists based on their folder sets?"):
            return

        success_count = 0
        fail_count = 0
        total_sets = len(sets)
        progress = xbmcgui.DialogProgress()
        progress.create(get_setting('ADDON_NAME', 'Playlist Creator'), "Updating all playlists...")

        for i, set_name in enumerate(sets.keys()):
            if progress.iscanceled():
                log("Update all sets cancelled by user.", xbmc.LOGINFO)
                break
            progress.update(int(i * 100 / total_sets), f"Updating set: {set_name}...")
            
            folders = sets[set_name]['folders']
            creator = PlaylistCreator()

            # Ask the user if set-specific settings should be applied for this update
            if dialog.yesno(get_setting('ADDON_NAME', 'Playlist Creator'),
                                      f"Apply saved settings for '{set_name}' before updating?",
                                      "Selecting 'No' will use current addon settings."):
                self.apply_set_settings(set_name)
                time.sleep(0.5) # Give Kodi a moment to apply settings

            if creator.create(set_name, folders, save_set=False):
                success_count += 1
            else:
                fail_count += 1
                log(f"Failed to update set: {set_name}", xbmc.LOGWARNING) 

        progress.close()
        dialog.notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Update complete: {success_count} succeeded, {fail_count} failed.", time=5000)