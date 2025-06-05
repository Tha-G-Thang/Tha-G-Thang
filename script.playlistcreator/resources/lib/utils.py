import xbmcaddon
import xbmc
import json
import os
import datetime # Import datetime for date formatting

from resources.lib.core.cleaner import Cleaner 
from resources.lib.core.base_utils import (
    log, get_setting, get_bool_setting, get_int_setting,
    ADDON_PROFILE, ADDON, load_json, save_json
)

# Oude AI-gerelateerde imports en initialisatie zijn verwijderd.
# De import van AICleaner en AIMetadataEnhancer wordt nu direct in
# cleaner.py en creator.py geregeld, en AISorter in sorter.py.
# Dit is performanter omdat de __init__ van AI klassen zwaar kan zijn (model loading).


_cleaner = Cleaner() # Instantie van de basis Cleaner klasse

def clean_filename(filename):
    """
    Roept de clean_filename methode van de Cleaner klasse aan.
    De Cleaner klasse handelt nu zelf de AI-logica af.
    """
    return _cleaner.clean_filename(filename)

def format_folder_with_count(folder_path, file_count, total_count=None):
    """
    Formats the folder name with file count and optionally total count.
    Adds color tags based on settings.
    """
    folder_name = os.path.basename(folder_path)
    display_name = folder_name

    use_color_tags = get_bool_setting("use_color_tags")
    folder_name_color = get_setting("folder_name_color", "gold")
    folder_name_position = get_int_setting("folder_name_position") 

    count_str = f" ({file_count} items)"
    if total_count is not None:
        count_str = f" ({file_count}/{total_count} items)"

    if use_color_tags and folder_name_color:
        colored_folder_name = f"[COLOR {folder_name_color}]{folder_name}[/COLOR]"
        if folder_name_position == 0: # Before playlist items
            display_name = f"{colored_folder_name}{count_str}"
        else: # After playlist items
            display_name = f"{count_str} {colored_folder_name}"
    else:
        display_name = f"{folder_name}{count_str}"

    return display_name

def format_duration_seconds(seconds):
    """
    Formateert een duur in seconden naar een leesbaar HH:MM:SS formaat.
    """
    if seconds is None:
        return ""
    
    try:
        seconds = int(seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours:02}:{minutes:02}:{seconds:02}"
        else:
            return f"{minutes:02}:{seconds:02}"
    except (ValueError, TypeError):
        log(f"Fout bij formatteren van duur: '{seconds}' is geen valide getal.", xbmc.LOGWARNING)
        return ""

def format_date_timestamp(date_string_or_timestamp):
    """
    Formateert een datumstring (YYYY-MM-DD) of timestamp naar een leesbaarder formaat.
    """
    if not date_string_or_timestamp:
        return ""

    if isinstance(date_string_or_timestamp, (int, float)):
        # Het is een timestamp
        try:
            date_obj = datetime.datetime.fromtimestamp(date_string_or_timestamp)
            return date_obj.strftime("%d-%m-%Y") # Bijv. 01-01-2023
        except Exception as e:
            log(f"Fout bij formatteren van timestamp: {date_string_or_timestamp} - {e}", xbmc.LOGWARNING)
            return ""
    elif isinstance(date_string_or_timestamp, str):
        # Het is al een 'YYYY-MM-DD' string of vergelijkbaar
        try:
            # Probeer te parsen voor het geval het een ongebruikelijk formaat is,
            # maar de _get_file_info methode zou al `YYYY-MM-DD` moeten leveren.
            date_obj = datetime.datetime.strptime(date_string_or_timestamp, '%Y-%m-%d')
            return date_obj.strftime("%d-%m-%Y") # Bijv. 01-01-2023
        except ValueError:
            # Als het al een datum is die niet strikt `YYYY-MM-DD` is, retourneer deze dan maar.
            # Dit zou niet moeten gebeuren als _get_file_info correct werkt.
            log(f"Onverwacht datumformaat: {date_string_or_timestamp}. Retourneer origineel.", xbmc.LOGWARNING)
            return date_string_or_timestamp
    else:
        log(f"Onbekend type voor datum formatteren: {type(date_string_or_timestamp)}. Retourneer leeg.", xbmc.LOGWARNING)
        return ""