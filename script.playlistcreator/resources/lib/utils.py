import os
import xbmc
import xbmcaddon
import xbmcvfs
import json
import re
import datetime
import xbmcgui
import time

# Attempt to import xbmc.VideoInfoTag for richer media info
try:
    import xbmc.VideoInfoTag
except ImportError:
    xbmc.log("WARNING: xbmc.VideoInfoTag not available. Media info might be limited.", xbmc.LOGWARNING)
    # Define a dummy class if not available to prevent crashes
    class VideoInfoTag:
        def __init__(self):
            self.duration = 0
            self.width = 0
            self.height = 0
            self.mediatype = ""
            self.year = 0
            self.art = {} # Ensure 'art' attribute exists if accessed
        def load(self, path): return False # Always fails for dummy
        def getduration(self): return self.duration
        def getwidth(self): return self.width
        def getheight(self): return self.height
        def getmediatype(self): return self.mediatype
        def getyear(self): return self.year
        def getart(self, key): return self.art.get(key, "") # Dummy getart

    xbmc.VideoInfoTag = VideoInfoTag


# Constants (assuming constants.py is available and correct)
# Zorg ervoor dat constants.py ook up-to-date is met de correcte ADDON_ID
from resources.lib.constants import ADDON_ID, CONFIG_FILE, VIDEO_EXTS
from resources.lib.profiles import NORMAL_PROFILE_SETTINGS, PRO_PROFILE_SETTINGS


addon = xbmcaddon.Addon(ADDON_ID)
log_prefix = f"[{ADDON_ID}]"
ADDON_PROFILE = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
# PLAYLIST_DIR wordt nu opgehaald via get_setting, dus deze regel is niet meer nodig als globale variabele
# PLAYLIST_DIR = xbmcvfs.translatePath(get_setting('playlist_output_path', 'special://home/playlists/'))

def log(msg, level=xbmc.LOGDEBUG):
    """Logs messages to the Kodi log file."""
    xbmc.log(f"{log_prefix} {msg}", level)

def get_setting(key, default_value=None):
    """Retrieves an addon setting, with a fallback default value."""
    try:
        value = addon.getSetting(str(key)) # Zorg dat key een string is voor addon.getSetting
        
        # Kodi returns 'true'/'false' for bools, convert to Python bool
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        return value
    except Exception as e:
        log(f"Error getting setting '{key}': {e}. Using default value: {default_value}", xbmc.LOGWARNING)
        return default_value

def get_bool_setting(key, default_value=False):
    """Retrieves a boolean addon setting and converts it to Python bool."""
    value = get_setting(key, str(default_value).lower()) # Ensure default is 'true' or 'false' string
    return str(value).lower() == 'true'

def get_int_setting(key, default_value=0):
    """Retrieves an integer addon setting."""
    try:
        return int(get_setting(key, str(default_value)))
    except (ValueError, TypeError):
        log(f"Error converting setting '{key}' to int. Using default: {default_value}", xbmc.LOGWARNING)
        return default_value

def get_text_setting(key, default_value=""):
    """Retrieves a text addon setting."""
    return get_setting(key, default_value)


def set_setting(key, value):
    """Sets an addon setting."""
    try:
        addon.setSetting(str(key), str(value)) # Zorg dat key een string is voor addon.setSetting
        log(f"Set setting '{key}' to '{value}'", xbmc.LOGDEBUG)
    except Exception as e:
        log(f"Error setting '{key}' to '{value}': {e}", xbmc.LOGERROR)

def get_string(string_id):
    """Retrieves a translated string from the addon."""
    return addon.getLocalizedString(string_id)

def save_json(data, file_path):
    """Saves data to a JSON file."""
    try:
        with xbmcvfs.File(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        log(f"Data saved to {file_path}", xbmc.LOGDEBUG)
        return True
    except Exception as e:
        log(f"Error saving JSON to {file_path}: {e}", xbmc.LOGERROR)
        return False

def load_json(file_path):
    """Loads data from a JSON file."""
    if xbmcvfs.exists(file_path):
        try:
            with xbmcvfs.File(file_path, 'r') as f:
                data = json.load(f)
            log(f"Data loaded from {file_path}", xbmc.LOGDEBUG)
            return data
        except Exception as e:
            log(f"Error loading JSON from {file_path}: {e}", xbmc.LOGERROR)
    else:
        log(f"File not found: {file_path}", xbmc.LOGDEBUG)
    return None

def translate_path(path):
    """Translates a Kodi special path."""
    return xbmcvfs.translatePath(path)

def create_backup(file_path):
    """Creates a backup of a file if backups are enabled."""
    if get_bool_setting('30601', False): # 'enable_backups'
        backup_path = file_path + ".bak"
        try:
            if xbmcvfs.exists(file_path):
                xbmcvfs.copy(file_path, backup_path)
                log(f"Created backup: {backup_path}", xbmc.LOGINFO)
                return True
        except Exception as e:
            log(f"Failed to create backup for {file_path}: {e}", xbmc.LOGERROR)
    return False

def apply_profile_settings(profile_mode):
    """Applies settings based on the selected user profile (Normal/Pro)."""
    settings_to_apply = {}
    if profile_mode == '0': # Normal
        settings_to_apply = NORMAL_PROFILE_SETTINGS
        log("Applying Normal profile settings.", xbmc.LOGINFO)
    elif profile_mode == '1': # Pro
        settings_to_apply = PRO_PROFILE_SETTINGS
        log("Applying Pro profile settings.", xbmc.LOGINFO)
    
    for key, value in settings_to_apply.items():
        set_setting(key, value)
    xbmc.executebuiltin("Addon.OpenSettings(script.playlistcreator)") # Refresh settings UI if open
    xbmc.executebuiltin("SetFocus(0)") # Set focus away from settings to apply changes


def get_file_duration_from_kodi(filepath):
    """
    Haalt de duur van een videobestand op via Kodi's VideoInfoTag.
    Geeft 0 terug als de duur niet bepaald kan worden.
    """
    try:
        # Probeer eerst met xbmc.VideoInfoTag als beschikbaar
        if hasattr(xbmc, 'VideoInfoTag'):
            video_info = xbmc.VideoInfoTag()
            if video_info.load(filepath):
                return video_info.getduration()
        
        # Fallback voor oudere Kodi versies of als VideoInfoTag niet werkt
        # Deze fallback is minder betrouwbaar en kan in sommige Kodi-versies problemen geven
        # Aangezien we een dummy class hebben voor VideoInfoTag, zou dit pad minder vaak nodig moeten zijn.
        list_item = xbmcgui.ListItem(path=filepath)
        # Kodi v20+ heeft list_item.getVideoInfoTag() in Python, maar het is niet altijd gevuld.
        # Voor v19 en ouder is de info vaak al beschikbaar via ListItem.
        info = list_item.getVideoInfoTag() # Dit retourneert een xbmc.VideoInfoTag object (of None)
        if info:
            return info.getDuration() # Gebruik getDuration() van het VideoInfoTag object
    except Exception as e:
        log(f"Error getting duration for {filepath} using Kodi: {e}", xbmc.LOGWARNING)
    return 0


def format_display_entry(file_info):
    """
    Format the display entry for the playlist, including folder name, metadata, and cleaning.
    """
    filename = os.path.basename(file_info['path'])
    
    # Check cleaning scope for playlist creation
    cleaning_scope_settings = get_setting('30801', '0').split(',') # '0' is Playlist Creation Process
    apply_playlist_cleaning = '0' in cleaning_scope_settings 

    clean_filename = filename
    if apply_playlist_cleaning:
        temp_filename = filename
        if get_bool_setting('30807', False): # Use the general cleaning toggle
            remove_words = [w.strip() for w in get_setting('30810', '').split(',') if w.strip()]
            switch_words = [w.strip() for w in get_setting('30813', '').split(',') if w.strip()]
            regex_enable = get_bool_setting('30816', False)
            regex_pattern = get_setting('30819', '')
            regex_replace = get_setting('30822', '')

            temp_filename = _apply_simple_cleaning_rules(
                temp_filename, 
                remove_words, 
                switch_words, 
                regex_enable, 
                regex_pattern, 
                regex_replace
            )
        clean_filename = temp_filename


    metadata_string = ""
    if get_bool_setting('30412', False): # 'show_metadata'
        year = file_info.get('year', 0)
        resolution = file_info.get('resolution', '')
        if year > 0:
            metadata_string += f" ({year})"
        if resolution:
            metadata_string += f" [{resolution}]"
    
    if get_bool_setting('30415', False): # 'show_duration'
        duration_seconds = file_info.get('duration', 0)
        if duration_seconds > 0:
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            metadata_string += f" [{minutes:02d}:{seconds:02d}]"

    if get_bool_setting('30418', False): # 'show_file_size'
        size_bytes = file_info.get('size', 0)
        if size_bytes > 0:
            size_mb = size_bytes / (1024 * 1024)
            metadata_string += f" [{size_mb:.1f}MB]"

    folder_name_part = ""
    if get_bool_setting('30401', True): # 'show_folder_names'
        folder_path = os.path.dirname(file_info['path'])
        folder_name = os.path.basename(folder_path.rstrip(os.sep))
        if folder_name:
            folder_color = get_setting('30404', 'gold') # 'folder_name_color'
            folder_name_part = f"[COLOR {folder_color}]{folder_name}[/COLOR]"
    
    display_name = ""
    # We hadden geen setting voor 'folder_name_position' in settings.xml, voeg deze toe in de settings.xml
    # en zorg dat de default waarde 'after' is als de setting ontbreekt.
    # Ik zal deze toevoegen aan de settings.xml hierboven.
    folder_position = get_text_setting('30421', 'after') # Nieuwe setting ID voor 'folder_name_position'
    
    if folder_name_part:
        if folder_position == 'before':
            display_name = f"{folder_name_part} {clean_filename}{metadata_string}"
        else: # 'after' or any other value
            display_name = f"{clean_filename}{metadata_string} {folder_name_part}"
    else:
        display_name = f"{clean_filename}{metadata_string}"

    return display_name.strip()

# Helper function for cleaning, can be reused
def _apply_simple_cleaning_rules(text, remove_words, switch_words, regex_enable, regex_pattern, regex_replace):
    temp_text = text

    for word in remove_words:
        if word:
            temp_text = re.sub(r'\b' + re.escape(word) + r'\b', '', temp_text, flags=re.IGNORECASE).strip()
    
    for switch_pair in switch_words:
        if '=' in switch_pair:
            old, new = switch_pair.split('=', 1)
            temp_text = re.sub(re.escape(old), new, temp_text, flags=re.IGNORECASE)
    
    if regex_enable and regex_pattern:
        try:
            temp_text = re.sub(regex_pattern, regex_replace, temp_text, flags=re.IGNORECASE)
        except re.error as regex_e:
            log(f"Regex error during cleaning: {regex_e}", xbmc.LOGERROR)
    return temp_text.strip()