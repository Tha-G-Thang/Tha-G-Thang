import os
import xbmcvfs
import xbmcgui
import xbmc
import re
from urllib.parse import urlparse
from resources.lib.utils import log, get_setting, translate_path, get_bool_setting, get_string # get_bool_setting en get_string toegevoegd

class Downloader:
    def download_file(self, url, is_adult_content_flag=False):
        log(f"Attempting to download: {url}, Adult: {is_adult_content_flag}")
        dialog = xbmcgui.Dialog()
        progress_dialog = xbmcgui.DialogProgress()

        try:
            filename = os.path.basename(urlparse(url).path)
            
            download_path_setting = ""
            # Bepaal het pad
            if is_adult_content_flag and get_setting('30704'): # Adult Download Path
                download_path_setting = get_setting('30704')
            else:
                download_path_setting = get_setting('30701', translate_path('special://home/downloads/')) # Default Download Path

            if not xbmcvfs.exists(download_path_setting):
                xbmcvfs.mkdirs(download_path_setting)
            
            # Bepaal of cleaning moet worden toegepast
            cleaning_scope_settings = get_setting('30801', '0').split(',') # '0' is default voor Playlist Creation Process

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
                if not dialog.yesno(get_string(3023), get_string(3024).format(os.path.basename(save_path))): # "Download exists", "File '{}' already exists. Do you want to overwrite it?"
                    log(f"Download cancelled by user: file already exists at {save_path}", xbmc.LOGINFO)
                    progress_dialog.close()
                    return False
            
            # ... (rest van de download_file functie blijft hetzelfde) ...
            
            # Start de download (voorbeeld van Kodi's io-functies)
            progress_dialog.create(get_string(3025), get_string(3026).format(cleaned_filename)) # "Downloading", "Downloading: {}"
            
            # Kodi file IO kan direct URL's aan.
            # Echter, voor echte HTTP/S downloads met voortgang is een externe library zoals requests of urllib.request beter,
            # of handmatige chunking met xbmcvfs.File.open().
            # Voorbeeld met xbmcvfs.File, dit is een simplistische benadering en kan blokkeren voor grote bestanden.
            # Een robuuste implementatie zou threading of een Kodi-specifieke downloadfunctie vereisen.
            
            # Dit is een placeholder voor de werkelijke downloadlogica
            # xbmcvfs.copy(url, save_path) # Dit werkt alleen voor lokale/SMB/NFS paden, niet voor HTTP/S

            # Voor HTTP/S downloads zou je urllib.request (Python standaard) of requests (als je het installeert in addon) gebruiken.
            # Hieronder een rudimentair voorbeeld met urllib.request (blokkerend, zonder echte voortgang updates direct van de download)
            # Voor echte voortgang via progress_dialog zou je de file in chunks moeten downloaden.
            
            import urllib.request
            response = urllib.request.urlopen(url)
            file_size = int(response.info().get('Content-Length', -1))
            chunk_size = 8192 # bytes

            bytes_read = 0
            with xbmcvfs.File(save_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_read += len(chunk)
                    if file_size > 0:
                        percent = int(bytes_read * 100 / file_size)
                        progress_dialog.update(percent, get_string(3026).format(cleaned_filename), get_string(3027).format(percent)) # "Downloading: {}", "{}% Complete"
                    if progress_dialog.iscanceled():
                        log(f"Download of {cleaned_filename} cancelled by user.", xbmc.LOGINFO)
                        xbmcvfs.delete(save_path) # Verwijder onvolledig bestand
                        dialog.notification(get_string(3025), get_string(3028), time=3000) # "Downloading", "Download cancelled."
                        progress_dialog.close()
                        return False

            progress_dialog.close()
            dialog.notification(get_string(3025), get_string(3029).format(cleaned_filename), time=5000) # "Downloading", "Download complete: {}"
            return True


        except Exception as e:
            log(f"Error during download: {e}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification(get_string(3025), get_string(3030).format(e), xbmcgui.NOTIFICATION_ERROR, time=5000) # "Downloading", "Download failed: {}"
            progress_dialog.close()
            return False
        
    def _clean_filename_general(self, filename):
        if get_bool_setting('30807', False): # Enable General Filename Cleanup
            cleaned_filename = filename
            remove_words = [w.strip() for w in get_setting('30810', '').split(',') if w.strip()] # Remove Words
            switch_words = [w.strip() for w in get_setting('30813', '').split(',') if w.strip()] # Switch Words
            regex_enable = get_bool_setting('30816', False) # Use Regex Replace
            regex_pattern = get_setting('30819', '') # Regex Pattern
            regex_replace = get_setting('30822', '') # Regex Replace With
            
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
        if get_bool_setting('30825', False): # Enable Adult Specific Filename Cleanup
            cleaned_filename = filename
            adult_remove_words = [w.strip() for w in get_setting('30828', '').split(',') if w.strip()] # Adult Content Remove Words
            adult_switch_words = [w.strip() for w in get_setting('30831', '').split(',') if w.strip()] # Adult Content Switch Words
            adult_regex_enable = get_bool_setting('30834', False) # Use Adult Regex Replace
            adult_regex_pattern = get_setting('30837', '') # Adult Regex Pattern
            adult_regex_replace = get_setting('30840', '') # Adult Regex Replace With
            
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
                # Use word boundaries \b for whole word matching
                temp_text = re.sub(r'\b' + re.escape(word) + r'\b', '', temp_text, flags=re.IGNORECASE).strip()
        
        for switch_pair in switch_words:
            if '=' in switch_pair:
                old, new = switch_pair.split('=', 1)
                temp_text = re.sub(re.escape(old), new, temp_text, flags=re.IGNORECASE) # 'new' should not be escaped
        
        if regex_enable and regex_pattern:
            try:
                temp_text = re.sub(regex_pattern, regex_replace, temp_text, flags=re.IGNORECASE)
            except re.error as regex_e:
                log(f"Regex error during cleaning: {regex_e}", xbmc.LOGERROR)
        return temp_text.strip() # Zorg ervoor dat lege spaties aan het begin/einde worden verwijderd