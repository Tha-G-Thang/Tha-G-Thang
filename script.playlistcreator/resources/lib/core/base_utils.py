import xbmc
import xbmcgui
import xbmcvfs
import os
import json
import urllib.parse
import re # Nodig voor metadata parsing

from resources.lib.constants import ADDON, ADDON_ID, ADDON_NAME

# Cache for file durations to improve performance
_duration_cache = {}

def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] {msg}", level)

def get_setting(setting_id, default=''):
    return ADDON.getSetting(setting_id) or default

def set_setting(setting_id, value):
    ADDON.setSetting(setting_id, str(value))

def load_json(file_path):
    try:
        # file_path might be just a filename, so ensure it's in ADDON_PROFILE
        full_path = os.path.join(xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/'), file_path)
        if xbmcvfs.exists(full_path):
            with xbmcvfs.File(full_path, 'r') as f:
                content = f.read()
                return json.loads(content)
    except Exception as e:
        import traceback
        log(f"Error loading JSON from {file_path}: {str(e)}\n{traceback.format_exc()}", xbmc.LOGERROR)
    return {}

def save_json(data, file_path):
    try:
        # file_path might be just a filename, so ensure it's in ADDON_PROFILE
        full_path = os.path.join(xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/'), file_path)
        
        # Ensure the directory exists
        dir_name = os.path.dirname(full_path)
        if not xbmcvfs.exists(dir_name):
            xbmcvfs.mkdirs(dir_name)

        with xbmcvfs.File(full_path, 'w') as f:
            f.write(json.dumps(data, indent=4))
    except Exception as e:
        import traceback
        log(f"Error saving JSON to {file_path}: {str(e)}\n{traceback.format_exc()}", xbmc.LOGERROR)

def clean_display_name(filepath):
    """ Cleans a filename for display by removing illegal characters or unwanted patterns. """
    # Haal de bestandsnaam op zonder extensie
    filename_without_ext = os.path.splitext(os.path.basename(filepath))[0]
    
    # Decode URL-encoded karakters
    cleaned_name = urllib.parse.unquote(filename_without_ext)

    # Verwijder veelvoorkomende bracket-patterns en overtollige spaties
    cleaned_name = re.sub(r'\[.*?\]|\(.*?\)|\{.*?\}', '', cleaned_name)
    
    # Vervang underscores en punten door spaties, behalve in getallenreeksen
    cleaned_name = re.sub(r'([a-zA-Z0-9])[\._]([a-zA-Z0-9])', r'\1 \2', cleaned_name)
    cleaned_name = cleaned_name.replace('_', ' ').replace('.', ' ').strip()
    
    # Meerdere spaties vervangen door enkele spatie
    cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()

    return cleaned_name

def get_file_duration(filepath):
    """
    Returns the duration of a video file in seconds.
    Uses a cache to avoid repeated calls for the same file.
    """
    if filepath in _duration_cache:
        return _duration_cache[filepath]
    try:
        if filepath.startswith('special://') or not xbmcvfs.exists(filepath):
            _duration_cache[filepath] = 0
            return 0
        
        # xbmc.Player().getPlayingFile() must be called to get ListItem properties.
        # This function is typically called for files that are not currently playing.
        # So we use xbmcgui.ListItem to get properties.
        item = xbmcgui.ListItem(path=filepath)
        duration = int(item.getDuration()) # getDuration returns duration in seconds
        _duration_cache[filepath] = duration
        return duration
    except Exception as e:
        log(f"Error getting duration for {filepath}: {e}", xbmc.LOGWARNING)
        _duration_cache[filepath] = 0
        return 0

def format_display_entry(filepath, original_folder_path=None):
    """
    Formats the display entry for a playlist item, optionally including folder name and metadata.
    """
    display_name = clean_display_name(filepath)

    # Voeg foldernamen toe indien ingesteld
    show_folder_names = get_setting('show_folder_names_in_playlist', 'true') == 'true'
    if show_folder_names and original_folder_path:
        folder_name = os.path.basename(original_folder_path)
        folder_name_position = get_setting('playlist_folder_name_position', '0') # 0: Prefix, 1: Suffix

        if folder_name_position == '0': # Prefix
            display_name = f"[{folder_name}] {display_name}"
        else: # Suffix
            display_name = f"{display_name} [{folder_name}]"

    # Voeg metadata toe indien ingesteld
    if get_setting('show_metadata', 'true') == 'true':
        clean_name_for_regex = urllib.parse.unquote(os.path.basename(filepath)) # Gebruik ongeparseerde naam voor regex
        
        # Jaar
        if year_match := re.search(r'(\d{4})', clean_name_for_regex): # Zoek gewoon naar 4 cijfers, flexibeler
            display_name += f" [COLOR gray]({year_match.group(1)})[/COLOR]"
        
        # Resolutie
        if res_match := re.search(r'(\d{3,4}[pP]|4[kK])', clean_name_for_regex, re.IGNORECASE):
            display_name += f" [COLOR blue]{res_match.group(1).upper()}[/COLOR]"
        
        # Duur
        if get_setting('show_duration', 'true') == 'true':
            duration = get_file_duration(filepath)
            if duration > 0:
                mins = duration // 60
                secs = duration % 60
                display_name += f" [COLOR yellow]{mins}:{secs:02d}[/COLOR]"

    return display_name