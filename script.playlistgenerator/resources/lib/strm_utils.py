import os
import xbmc
import xbmcaddon
import xbmcvfs # Zorg ervoor dat deze import aanwezig is

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