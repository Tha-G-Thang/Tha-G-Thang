import os
import xbmc
import xbmcaddon
import xbmcvfs
import json
import re
import datetime
import xbmcgui
import time
from resources.lib.constants import ADDON_ID, CONFIG_FILE, VIDEO_EXTS
from resources.lib.constants import ADDON_ID

def get_addon():
    try:
        return xbmcaddon.Addon(ADDON_ID)
    except Exception as e:
        xbmc.log(f"Critical: Addon init failed - {str(e)}", xbmc.LOGERROR)
        raise SystemExit  # Stop als de addon-ID niet klopt
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
            self.art = {}
        def load(self, path): return False
        def getduration(self): return self.duration
        def getwidth(self): return self.width
        def getheight(self): return self.height
        def getmediatype(self): return self.mediatype
        def getyear(self): return self.year
        def getart(self, key): return self.art.get(key, "")

    xbmc.VideoInfoTag = VideoInfoTag

def clean_filename(filename):
    # Basis cleaning zonder AI
    return re.sub(r'[._-]', ' ', filename).strip()

def log(msg, level=xbmc.LOGINFO):
    if get_bool_setting('debug_logging', False) or level == xbmc.LOGERROR:
        xbmc.log(f"{log_prefix} {msg}", level)

def ai_log(msg, level=xbmc.LOGINFO):
    if get_bool_setting('debug_logging', False) and is_ai_enabled(): # Only log AI if AI debug is enabled and AI is globally enabled
        xbmc.log(f"{log_prefix} [AI] {msg}", level)

def get_setting(setting_id, default=None):
    return addon.getSetting(setting_id) if addon.getSetting(setting_id) != '' else default

def get_int_setting(setting_id, default=0):
    try:
        return int(addon.getSetting(setting_id))
    except ValueError:
        return default

def get_bool_setting(setting_id, default=False):
    return addon.getSettingBool(setting_id) if hasattr(addon, 'getSettingBool') else addon.getSetting(setting_id) == 'true'

def set_setting(setting_id, value):
    addon.setSetting(setting_id, str(value))

def translate_path(path):
    return xbmcvfs.translatePath(path)

def save_json(data, filename):
    full_path = os.path.join(ADDON_PROFILE, filename)
    try:
        with xbmcvfs.File(full_path, 'w') as f:
            f.write(json.dumps(data, indent=4))
        log(f"Successfully saved {filename} to {full_path}")
        return True
    except Exception as e:
        log(f"Failed to save {filename} to {full_path}: {e}", xbmc.LOGERROR)
        return False

def load_json(filename):
    full_path = os.path.join(ADDON_PROFILE, filename)
    if xbmcvfs.exists(full_path):
        try:
            with xbmcvfs.File(full_path, 'r') as f:
                data = f.read()
            log(f"Successfully loaded {filename} from {full_path}")
            return json.loads(data)
        except Exception as e:
            log(f"Failed to load {filename} from {full_path}: {e}", xbmc.LOGERROR)
            return None
    log(f"{filename} does not exist at {full_path}")
    return None

def apply_profile_settings():
    current_profile = get_setting('user_profile_mode', '0') # '0' for Normal, '1' for Pro

    if current_profile == '0': # Normal Profile
        target_settings = NORMAL_PROFILE_SETTINGS
        log("Applying 'Normal' profile settings.")
    else: # Pro Profile
        target_settings = PRO_PROFILE_SETTINGS
        log("Applying 'Pro' profile settings.")

    for setting_id, default_value in target_settings.items():
        # Only apply if the setting is not currently set by the user (or is default for the *other* profile)
        # This logic is simplified; a more robust system might store defaults or use a dedicated reset
        current_value = get_setting(setting_id)
        if current_value == '' or (current_value != default_value and not (setting_id in addon.getSetting('user_customized_settings', '').split(','))):
             # This checks if the user has explicitly changed this setting.
             # For now, we'll just set it if it's empty or doesn't match the profile default.
            set_setting(setting_id, default_value)
            log(f"Set {setting_id} to {default_value} for profile {current_profile}")

    xbmcgui.Dialog().notification(addon.getAddonInfo('name'), f"Profile '{'Pro' if current_profile == '1' else 'Normal'}' settings applied.", time=3000)

def clean_filename_for_display(filename):
    """
    Applies basic cleaning for display purposes (removes common separators).
    """
    cleaned = re.sub(r"[._-]", " ", filename)
    # Remove double spaces, strip leading/trailing spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def format_display_entry(file_info):
    """
    Format the display entry for the playlist, including folder name, metadata, and cleaning.
    """
    filename = os.path.basename(file_info['path'])
    
    # Check cleaning scope for playlist creation
    cleaning_scope_settings = get_setting('cleaning_scope', '0').split(',')
    apply_playlist_cleaning = '0' in cleaning_scope_settings # '0' is Playlist Creation Process

    clean_filename = filename
    if apply_playlist_cleaning:
        # Hier kun je de cleaning logica implementeren die ook in downloader zit,
        # of een aparte CleaningUtility klasse maken die herbruikbaar is.
        # Voor nu, als voorbeeld, gebruiken we een basisvervanging.
        # Je zou de algemene cleaning settings (remove_words, switch_words, regex) hiervoor kunnen hergebruiken.
        
        # Voorbeeld eenvoudige cleaning voor playlist weergave:
        temp_filename = filename
        if get_bool_setting('download_cleanup_toggle', False): # Gebruik de algemene cleaning toggle
            remove_words = [w.strip() for w in get_setting('download_delete_words', '').split(',') if w.strip()]
            switch_words = [w.strip() for w in get_setting('download_switch_words', '').split(',') if w.strip()]
            regex_enable = get_bool_setting('download_regex_enable', False)
            regex_pattern = get_setting('download_regex_pattern', '')
            regex_replace = get_setting('download_regex_replace_with', '')
            
            clean_filename = _apply_simple_cleaning_rules(
                temp_filename, 
                remove_words, 
                switch_words, 
                regex_enable, 
                regex_pattern, 
                regex_replace
            )
        else: # Als cleaning niet is ingeschakeld, nog steeds basis cleanup voor weergave
            clean_filename = clean_filename_for_display(filename)
    else:
        clean_filename = clean_filename_for_display(filename)


    metadata_string = ""
    if get_bool_setting('show_metadata', True):
        parts = []
        if get_bool_setting('metadata_include_duration', True) and 'duration' in file_info and file_info['duration'] > 0:
            minutes, seconds = divmod(file_info['duration'], 60)
            hours, minutes = divmod(minutes, 60)
            if hours > 0:
                parts.append(f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
            else:
                parts.append(f"{int(minutes):02d}:{int(seconds):02d}")
        if get_bool_setting('metadata_include_size', True) and 'size' in file_info and file_info['size'] > 0:
            size_mb = file_info['size'] / (1024 * 1024)
            parts.append(f"{size_mb:.1f}MB")
        if get_bool_setting('metadata_include_resolution', False) and 'width' in file_info and 'height' in file_info and file_info['width'] > 0 and file_info['height'] > 0:
            parts.append(f"{file_info['width']}x{file_info['height']}")
        if get_bool_setting('metadata_include_year', False) and 'year' in file_info and file_info['year'] > 0:
            parts.append(str(file_info['year']))

        if parts:
            metadata_string = f" ({', '.join(parts)})"

    folder_name_part = ""
    if get_bool_setting('show_folder_names', True):
        folder_path = os.path.dirname(file_info['path'])
        folder_name = os.path.basename(folder_path.rstrip(os.sep))
        if folder_name:
            folder_color = get_setting('folder_name_color', 'gold')
            folder_name_part = f"[COLOR {folder_color}]{folder_name}[/COLOR]"
    
    display_name = ""
    if folder_name_part:
        folder_position = get_setting('folder_name_position', 'after') # Changed to get_setting, as it's not a boolean
        if folder_position == 'before':
            display_name = f"{folder_name_part} {clean_filename}{metadata_string}"
        else: # 'after' or any other value
            display_name = f"{clean_filename}{metadata_string} {folder_name_part}"
    else:
        display_name = f"{clean_filename}{metadata_string}"

    return display_name.strip()

# Hulpfunctie voor cleaning, kan hergebruikt worden
def _apply_simple_cleaning_rules(text, remove_words, switch_words, regex_enable, regex_pattern, regex_replace):
    temp_text = text

    for word in remove_words:
        if word:
            temp_text = re.sub(r'\b' + re.escape(word) + r'\b', '', temp_text, flags=re.IGNORECASE).strip()
    
    for switch_pair in switch_words:
        if '=' in switch_pair:
            old, new = switch_pair.split('=', 1)
            temp_text = re.sub(re.escape(old), re.escape(new), temp_text, flags=re.IGNORECASE)
    
    if regex_enable and regex_pattern:
        try:
            temp_text = re.sub(regex_pattern, regex_replace, temp_text, flags=re.IGNORECASE)
        except re.error as e:
            log(f"Regex error in cleaning: {e}", xbmc.LOGERROR)
            # Fallback to non-regex cleaned text in case of regex error
            pass # Keep temp_text as is if regex fails

    return temp_text

def get_file_duration_from_kodi(filepath):
    """
    Haalt de duur van een videobestand op via Kodi's VideoInfoTag.
    Geeft 0 terug als de duur niet bepaald kan worden.
    """
    try:
        if hasattr(xbmc, 'VideoInfoTag'):
            video_info = xbmc.VideoInfoTag()
            if video_info.load(filepath):
                return video_info.getduration()
        
        list_item = xbmcgui.ListItem(path=filepath)
        xbmc.Player().play(filepath, listitem=list_item, subfolder=False, offitems=0) # Only play for duration, don't show UI
        
        # Give Kodi a moment to load the media info
        for _ in range(20): # Try for up to 2 seconds
            if xbmc.Player().isPlaying():
                duration = xbmc.Player().getTotalTime()
                xbmc.Player().stop()
                if duration > 0:
                    return duration
            time.sleep(0.1)

    except Exception as e:
        log(f"Error getting duration for {filepath}: {e}", xbmc.LOGERROR)
    return 0

def create_backup(original_path):
    """Creates a timestamped backup of the original file."""
    if get_bool_setting('enable_backups', False):
        try:
            backup_dir = os.path.join(os.path.dirname(original_path), "backups")
            if not xbmcvfs.exists(backup_dir):
                xbmcvfs.mkdirs(backup_dir)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            backup_filename = f"{os.path.basename(original_path).split('.')[0]}_{timestamp}.m3u.bak"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            xbmcvfs.copy(original_path, backup_path)
            log(f"Backup created: {backup_path}", xbmc.LOGINFO)
        except Exception as e:
            log(f"Failed to create backup for {original_path}: {e}", xbmc.LOGERROR)

def is_ai_enabled():
    """
    Controleert of AI-functies globaal zijn ingeschakeld via de add-on instellingen.
    """
    user_profile_mode = get_setting('user_profile_mode', '0')
    enable_ai_features = get_bool_setting('enable_ai_features', False)
    
    # AI features are only available and enabled in 'Pro' mode if the specific setting is true.
    return user_profile_mode == '1' and enable_ai_features