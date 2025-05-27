import os
import xbmc
import xbmcaddon
import xbmcvfs
import json
import re
import datetime
import xbmcgui
import time

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
    if get_bool_setting('show_metadata', False): # default is nu false
        year = file_info.get('year', 0)
        resolution = file_info.get('resolution', '')
        if year > 0:
            metadata_string += f" ({year})"
        if resolution:
            metadata_string += f" [{resolution}]"
    
    if get_bool_setting('show_duration', False):
        duration_seconds = file_info.get('duration', 0)
        if duration_seconds > 0:
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            metadata_string += f" [{minutes:02d}:{seconds:02d}]"

    if get_bool_setting('show_file_size', False):
        size_bytes = file_info.get('size', 0)
        if size_bytes > 0:
            size_mb = size_bytes / (1024 * 1024)
            metadata_string += f" [{size_mb:.1f}MB]"

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
            temp_text = re.sub(r'\\b' + re.escape(word) + r'\\b', '', temp_text, flags=re.IGNORECASE).strip()
    
    for switch_pair in switch_words:
        if '=' in switch_pair:
            old, new = switch_pair.split('=', 1)
            temp_text = re.sub(re.escape(old), re.escape(new), temp_text, flags=re.IGNORECASE)
    
    if regex_enable and regex_pattern:
        try:
            temp_text = re.sub(regex_pattern, regex_replace, temp_text, flags=re.IGNORECASE)
        except re.error as regex_e:
            log(f"Regex error during cleaning: {regex_e}", xbmc.LOGERROR)
    return temp_text.strip()