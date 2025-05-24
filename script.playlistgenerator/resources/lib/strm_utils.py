import os
import xbmc
import xbmcaddon
import xbmcvfs # Zorg ervoor dat deze import aanwezig is
import json
from .constants import CONFIG_FILE

addon = xbmcaddon.Addon()
log_prefix = "[STRM Addon]"

# Aangepast: Gebruik xbmcvfs.translatePath in plaats van xbmc.translatePath
ADDON_PROFILE = xbmcvfs.translatePath(addon.getAddonInfo('profile')) 

def log(message, level=xbmc.LOGNOTICE):
    xbmc.log(f"{log_prefix} {message}", level)

def get_setting(id, default=None):
    return addon.getSetting(id) or default

def parse_exclude_folders():
    raw = get_setting('exclude_folders', '')
    return [x.strip() for x in raw.split(',') if x.strip()]

def is_valid_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    allowed_extensions_str = get_setting('file_extensions', '.mp4,.mkv,.avi,.mov,.wmv')
    allowed_extensions = [e.strip() for e in allowed_extensions_str.split(',') if e.strip()]
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

def clean_display_name(name):
    cleaned_name = os.path.basename(name)
    if '.' in cleaned_name:
        cleaned_name = os.path.splitext(cleaned_name)[0]
    return cleaned_name

def load_sets():
    config_path = os.path.join(ADDON_PROFILE, CONFIG_FILE)
    log(f"Checking for config file at: {config_path}")
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
        log(f"Error saving sets to {config_path}: {e}")
        return False