# resources/lib/downloader.py

import os
import xbmcvfs
import xbmcgui
import xbmc
import re
from urllib.parse import urlparse
from resources.lib.utils import log, get_setting, translate_path, get_bool_setting # get_bool_setting toegevoegd

class Downloader:
    def download_file(self, url, is_adult_content_flag=False):
        log(f"Attempting to download: {url}, Adult: {is_adult_content_flag}")
        dialog = xbmcgui.Dialog()
        progress_dialog = xbmcgui.DialogProgress()

        try:
            filename = os.path.basename(urlparse(url).path)

            download_path_setting = ""
            # Bepaal het pad
            if is_adult_content_flag and get_setting('adult_download_path'):
                download_path_setting = get_setting('adult_download_path')
            else:
                download_path_setting = get_setting('download_path', translate_path('special://home/downloads/'))

            if not xbmcvfs.exists(download_path_setting):
                xbmcvfs.mkdirs(download_path_setting)

            # Bepaal of cleaning moet worden toegepast
            cleaning_scope_settings = get_setting('cleaning_scope', '0').split(',') # '0' is default voor Playlist Creation Process

            apply_general_cleaning = '1' in cleaning_scope_settings # Regular Download Proces
            apply_adult_cleaning = '2' in cleaning_scope_settings # Adult Download Proces

            cleaned_filename = filename
            if apply_general_cleaning:
                cleaned_filename = self._clean_filename_general(filename)

            if is_adult_content_flag and apply_adult_cleaning:
                cleaned_filename = self._clean_filename_adult(cleaned_filename)

            save_path = os.path.join(download_path_setting, cleaned_filename)

            log(f"Saving to: {save_path}")

            if xbmcvfs.exists(save_path):
                if not dialog.yesno("Download exists", f"File '{os.path.basename(save_path)}' already exists. Do you want to overwrite it?"):
                    log(f"Download cancelled by user: file already exists at {save_path}", xbmc.LOGINFO)
                    progress_dialog.close()
                    return False

            # ... (rest van de download_file functie blijft hetzelfde) ...

        except Exception as e:
            log(f"Error during download: {e}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification(get_setting('ADDON_NAME', 'Playlist Creator'), f"Download failed: {e}", xbmcgui.NOTIFICATION_ERROR, time=5000)
            progress_dialog.close()
            return False

        # ... (rest van de download_file functie blijft hetzelfde) ...

    # Nieuwe of aangepaste cleaning methodes
    def _clean_filename_general(self, filename):
        if get_bool_setting('download_cleanup_toggle', False): # Refer to the new general toggle
            cleaned_filename = filename
            remove_words = [w.strip() for w in get_setting('download_delete_words', '').split(',') if w.strip()]
            switch_words = [w.strip() for w in get_setting('download_switch_words', '').split(',') if w.strip()]
            regex_enable = get_bool_setting('download_regex_enable', False)
            regex_pattern = get_setting('download_regex_pattern', '')
            regex_replace = get_setting('download_regex_replace_with', '')

            return self._apply_cleaning_rules(
                cleaned_filename, 
                remove_words, 
                switch_words, 
                regex_enable, 
                regex_pattern, 
                regex_replace
            )
        return filename

    def _clean_filename_adult(self, filename):
        if get_bool_setting('download_cleanup_adult_toggle', False): # Refer to the new adult toggle
            cleaned_filename = filename
            adult_remove_words = [w.strip() for w in get_setting('download_delete_words_adult', '').split(',') if w.strip()]
            adult_switch_words = [w.strip() for w in get_setting('download_switch_words_adult', '').split(',') if w.strip()]
            adult_regex_enable = get_bool_setting('download_regex_enable_adult', False)
            adult_regex_pattern = get_setting('download_regex_pattern_adult', '')
            adult_regex_replace = get_setting('download_regex_replace_with_adult', '')

            return self._apply_cleaning_rules(
                cleaned_filename, 
                adult_remove_words, 
                adult_switch_words, 
                adult_regex_enable, 
                adult_regex_pattern, 
                adult_regex_replace
            )
        return filename

    def _apply_cleaning_rules(self, text, remove_words, switch_words, regex_enable, regex_pattern, regex_replace):
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
        return temp_text.strip() # Zorg ervoor dat lege spaties aan het begin/einde worden verwijderd