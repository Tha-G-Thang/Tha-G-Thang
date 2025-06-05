import os
import xbmcvfs
import time
import xbmc
import re
from resources.lib.core.base_utils import get_setting, get_bool_setting, log

class Scanner:
    def scan(self, folder_path):
        min_size_mb = int(get_setting('min_file_size_mb', '0'))
        min_size_bytes = min_size_mb * 1024 * 1024
        timeout = int(get_setting('scan_timeout_seconds', '30'))
        recursive_scan = get_bool_setting('recursive_scan') # Lees de instelling
        folder_depth_limit = int(get_setting('folder_depth_limit', '5')) # Lees de dieptelimiet

        content_filter_mode = get_setting('content_filter_mode', 'all')
        adult_keywords_str = get_setting('adult_content_keywords', 'adult,xxx,18plus')
        adult_keywords = [k.strip().lower() for k in adult_keywords_str.split(',') if k.strip()]

        start_time = time.time()
        files = []

        log(f"SCANNER: Starten van scan voor map: '{folder_path}' (Recursief: {recursive_scan}, Diepte: {folder_depth_limit})", xbmc.LOGINFO)
        
        # ACTIVEER de _scan_recursive functie en verwijder de tijdelijke debug-regel
        all_files = self._scan_recursive(folder_path, 0, recursive_scan, folder_depth_limit)

        for f in all_files:
            if time.time() - start_time > timeout:
                log(f"Scan van '{folder_path}' getimed out na {timeout} seconden.", xbmc.LOGWARNING)
                xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Scan getimed out, mogelijk niet alle bestanden gevonden.", xbmcgui.NOTIFICATION_WARNING, 5000)
                break # Stop met verwerken als timeout is bereikt

            file_size = 0
            try:
                if xbmcvfs.exists(f):
                    file_size = xbmcvfs.Stat(f).st_size()
            except Exception as e:
                log(f"Fout bij ophalen bestandsgrootte voor '{f}': {str(e)}", xbmc.LOGWARNING)
                continue # Sla dit bestand over

            if file_size < min_size_bytes:
                log(f"SCANNER_DEBUG: '{f}' overgeslagen (te klein: {file_size} bytes)", xbmc.LOGDEBUG)
                continue

            if content_filter_mode == 'adult' and not self._is_adult_content(f, adult_keywords):
                log(f"SCANNER_DEBUG: '{f}' overgeslagen (geen volwassen inhoud, filter actief)", xbmc.LOGDEBUG)
                continue
            elif content_filter_mode == 'non_adult' and self._is_adult_content(f, adult_keywords):
                log(f"SCANNER_DEBUG: '{f}' overgeslagen (volwassen inhoud, filter actief)", xbmc.LOGDEBUG)
                continue
            
            files.append(f)
            log(f"SCANNER_DEBUG: Bestand gevonden en toegevoegd: '{f}'", xbmc.LOGDEBUG)

        log(f"Scan van '{folder_path}' voltooid. Totaal {len(files)} bestanden gevonden die aan criteria voldoen.", xbmc.LOGINFO)
        return files

    def _scan_recursive(self, folder, current_depth, recursive_scan_enabled, depth_limit):
        """
        Recursief scan van mappen voor ondersteunde mediabestanden.
        """
        all_found_files = []
        supported_extensions = [ext.strip().lower() for ext in get_setting('file_extensions', '').split(',') if ext.strip()]
        
        log(f"SCANNER_DEBUG: Start recursieve scan in '{folder}' (diepte: {current_depth}, limiet: {depth_limit})", xbmc.LOGDEBUG)

        try:
            # Lijst van bestanden en mappen in de huidige directory
            contents = xbmcvfs.listdir(folder)
            files = contents[0] # Bestanden
            dirs = contents[1]  # Mappen

            for f in files:
                full_path = os.path.join(folder, f)
                # Controleer extensie
                if os.path.splitext(f)[1].lower() in supported_extensions:
                    all_found_files.append(full_path)
                    log(f"SCANNER_DEBUG: Bestand '{full_path}' toegevoegd.", xbmc.LOGDEBUG)

            # Recursief scannen van submappen
            if recursive_scan_enabled and current_depth < depth_limit:
                for d in dirs:
                    full_subdir_path = os.path.join(folder, d)
                    if xbmcvfs.isdir(full_subdir_path): # Controleer expliciet of het een map is
                        all_found_files.extend(self._scan_recursive(full_subdir_path, current_depth + 1, recursive_scan_enabled, depth_limit))
                    else:
                        log(f"SCANNER_DEBUG: '{full_subdir_path}' is geen map, overslaan voor recursieve scan.", xbmc.LOGDEBUG)
            elif recursive_scan_enabled and current_depth >= depth_limit:
                 log(f"SCANNER_DEBUG: Maximale diepte bereikt voor '{folder}' (diepte {current_depth}).", xbmc.LOGDEBUG)
            elif not recursive_scan_enabled:
                 log(f"SCANNER_DEBUG: Recursieve scan uitgeschakeld voor '{folder}'.", xbmc.LOGDEBUG)
                 
        except Exception as e:
            log(f"SCANNER_DEBUG: Fout in recursieve scan in map '{folder}': {str(e)}", xbmc.LOGERROR)
            
        return all_found_files

    # --- OUDE LOGICA VERWIJDERD ---
    # De _scan_old_logic methode en de commentaarblokken hieromtrent zijn verwijderd.

    def _is_adult_content(self, file_path, adult_keywords):
        full_path_lower = file_path.lower()
        for keyword in adult_keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', full_path_lower):
                log(f"SCANNER_DEBUG: Gedetecteerde volwassen inhoud: '{file_path}' (via keyword '{keyword}')", xbmc.LOGDEBUG)
                return True
        
        folder_name = os.path.basename(os.path.dirname(file_path)).lower()
        for keyword in adult_keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', folder_name):
                log(f"SCANNER_DEBUG: Gedetecteerde volwassen inhoud in mapnaam: '{folder_name}' (via keyword '{keyword}')", xbmc.LOGDEBUG)
                return True
        return False