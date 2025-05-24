import os
import xbmc
import xbmcaddon
import xbmcvfs
import json
from .constants import ADDON_ID, CONFIG_FILE # <-- DEZE IMPORTS ZIJN TOEGEVOEGD

addon = xbmcaddon.Addon(ADDON_ID) # Gebruik ADDON_ID hier voor initialisatie
log_prefix = f"[{ADDON_ID}]" # Gebruik ADDON_ID voor log prefix

# Aangepast: Gebruik xbmcvfs.translatePath in plaats van xbmc.translatePath
ADDON_PROFILE = xbmcvfs.translatePath(addon.getAddonInfo('profile')) 

def log(message, level=xbmc.LOGNOTICE):
    xbmc.log(f"{log_prefix} {message}", level)

def get_setting(id, default=None):
    return addon.getSetting(id) or default

def parse_exclude_folders():
    # Deze functie wordt niet meer direct gebruikt door strm_scanner.py voor de hoofdscan
    # maar kan blijven bestaan voor compatibiliteit of andere doeleinden.
    raw = get_setting('exclude_folders', '')
    return [x.strip() for x in raw.split(',') if x.strip()]

def is_valid_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    allowed_extensions_str = get_setting('file_extensions', '.mp4,.mkv,.avi,.mov,.wmv')
    allowed_extensions = [e.strip() for e in allowed_extensions_str.split(',') if e.strip()]
    
    # Controleer ook minimum bestandsgrootte
    min_size_mb = float(get_setting('min_file_size_mb', '0'))
    if min_size_mb > 0:
        file_size_bytes = xbmcvfs.FStat(filename).size()
        if file_size_bytes < (min_size_mb * 1024 * 1024):
            log(f"Excluding {filename} due to size ({file_size_bytes / (1024 * 1024):.2f} MB < {min_size_mb} MB)", xbmc.LOGINFO)
            return False

    return ext in allowed_extensions

def translate_path(path):
    # Aangepast: Gebruik xbmcvfs.translatePath in plaats van xbmc.translatePath
    return xbmcvfs.translatePath(path)

def parse_url(url):
    params = {}
    if url:
        if url.startswith("plugin://"):
            url = url[len("plugin://"):]
        
        parts = url.split('/')
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                params[key] = value
    return params

def clean_display_name(filename, is_adult=False):
    """
    Cleans up a filename for display purposes, removing unwanted words and applying regex.
    Applies separate cleanup rules for adult content if enabled.
    """
    cleaned_name = os.path.splitext(os.path.basename(filename))[0]

    if is_adult:
        # Use adult-specific cleanup settings
        if get_setting('adult_remove_words', '') != '':
            remove_words = [w.strip() for w in get_setting('adult_remove_words', '').split('|') if w.strip()]
            for word in remove_words:
                cleaned_name = re.sub(r'\b' + re.escape(word) + r'\b', '', cleaned_name, flags=re.IGNORECASE).strip()

        if get_setting('adult_switch_words', '') != '':
            switch_pairs = [p.strip().split('=') for p in get_setting('adult_switch_words', '').split('|') if p.strip() and '=' in p]
            for old, new in switch_pairs:
                cleaned_name = re.sub(re.escape(old), new, cleaned_name, flags=re.IGNORECASE)
        
        if get_setting('adult_regex_enable', 'false') == 'true':
            pattern = get_setting('adult_regex_pattern', '(.*)')
            replace_with = get_setting('adult_regex_replace_with', '\\1')
            try:
                cleaned_name = re.sub(pattern, replace_with, cleaned_name, flags=re.IGNORECASE)
            except re.error as e:
                log(f"Invalid adult regex pattern in settings: {pattern} - {e}", xbmc.LOGERROR)

    else:
        # Use general cleanup settings
        if get_setting('download_remove_words', '') != '':
            remove_words = [w.strip() for w in get_setting('download_remove_words', '').split(',') if w.strip()]
            for word in remove_words:
                cleaned_name = re.sub(r'\b' + re.escape(word) + r'\b', '', cleaned_name, flags=re.IGNORECASE).strip()

        if get_setting('download_switch_words', '') != '':
            switch_pairs = [p.strip().split('=') for p in get_setting('download_switch_words', '').split(',') if p.strip() and '=' in p]
            for old, new in switch_pairs:
                cleaned_name = re.sub(re.escape(old), new, cleaned_name, flags=re.IGNORECASE)
        
        if get_setting('download_regex_enable', 'false') == 'true':
            pattern = get_setting('download_regex_pattern', '(.*)')
            replace_with = get_setting('download_regex_replace_with', '\\1')
            try:
                cleaned_name = re.sub(pattern, replace_with, cleaned_name, flags=re.IGNORECASE)
            except re.error as e:
                log(f"Invalid download regex pattern in settings: {pattern} - {e}", xbmc.LOGERROR)

    # Remove any leading/trailing hyphens or spaces left from cleanup
    cleaned_name = cleaned_name.strip(' -')
    return cleaned_name

def load_sets():
    config_path = os.path.join(ADDON_PROFILE, CONFIG_FILE)
    log(f"Loading sets from: {config_path}")
    if xbmcvfs.exists(config_path):
        try:
            f = xbmcvfs.File(config_path, 'r')
            content = f.read()
            f.close()
            if content:
                try:
                    sets_data = json.loads(content)
                    log("Sets loaded successfully.")
                    return sets_data
                except (json.JSONDecodeError, TypeError) as e:
                    log(f"Error decoding JSON from {config_path}: {e}")
                    return {}
            else:
                log(f"Config file {config_path} is empty.")
                return {}
        except Exception as e:
            log(f"Error reading config file {config_path}: {e}")
            return {}
    else:
        log(f"Config file not found: {config_path}")
        return {}

def save_sets(sets_data):
    config_path = os.path.join(ADDON_PROFILE, CONFIG_FILE)
    log(f"Saving sets to: {config_path}")
    try:
        if not xbmcvfs.exists(ADDON_PROFILE):
            # Create the directory if it doesn't exist
            if not xbmcvfs.mkdirs(ADDON_PROFILE):
                log(f"Error creating directory: {ADDON_PROFILE}")
                return False
        
        f = xbmcvfs.File(config_path, 'w')
        json_data = json.dumps(sets_data, indent=4)
        f.write(json_data)
        f.close()
        log("Sets saved successfully.")
        return True
    except Exception as e:
        log(f"Error saving config file {config_path}: {e}", xbmc.LOGERROR)
        return False