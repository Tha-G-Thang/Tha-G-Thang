import xbmcvfs
import xbmcgui
import xbmc
import os 
# Importeer van base_utils en utils
from resources.lib.core.base_utils import log, get_setting, get_bool_setting, ADDON
from resources.lib.utils import clean_filename # clean_filename is nu in utils.py

class Downloader:
    def __init__(self):
        pass

    def download_file(self, url, is_adult_content=False):
        """
        Generieke downloadmethode voor alle use-cases.
        Args:
            url (str): Bron-URL.
            is_adult_content (bool): Gebruik adult-downloadmap indien True.
        Returns:
            bool: True bij succes, False bij falen.
        """
        try:
            filename = self._extract_filename(url)
            cleaned_name = clean_filename(filename) # Gebruikt de clean_filename uit utils
            target_path = self._get_target_path(cleaned_name, is_adult_content)
            
            log(f"Download gestart: {url} -> {target_path}")

            if url.startswith("plugin://"):
                xbmcgui.Dialog().notification(
                    ADDON.getAddonInfo('name'), 
                    "Plugin URLs kunnen niet direct gedownload worden.", 
                    xbmcgui.NOTIFICATION_INFO, 5000
                )
                log(f"Poging tot downloaden van plugin URL: {url} (niet ondersteund)", xbmc.LOGWARNING)
                return False
            
            if xbmcvfs.copy(url, target_path):
                xbmcgui.Dialog().notification(
                    ADDON.getAddonInfo('name'), 
                    f"'{os.path.basename(target_path)}' gedownload!", 
                    xbmcgui.NOTIFICATION_INFO, 5000
                )
                log(f"Bestand succesvol gedownload naar: {target_path}", xbmc.LOGINFO)
                return True
            else:
                xbmcgui.Dialog().notification(
                    ADDON.getAddonInfo('name'), 
                    f"Download mislukt: '{os.path.basename(target_path)}'", 
                    xbmcgui.NOTIFICATION_ERROR, 5000
                )
                log(f"Mislukt om '{url}' te downloaden naar '{target_path}'", xbmc.LOGERROR)
                return False
        except Exception as e:
            xbmcgui.Dialog().notification(
                ADDON.getAddonInfo('name'), 
                f"Onverwachte downloadfout: {str(e)}", 
                xbmcgui.NOTIFICATION_ERROR, 5000
            )
            log(f"Onverwachte fout in Downloader.download_file: {str(e)}", xbmc.LOGERROR)
            return False

    def _extract_filename(self, url):
        """
        Extraheert een bestandsnaam uit een URL of genereert anders een generieke naam
        """
        filename = url.split('/')[-1].split('?')[0]
        if not filename:
            filename = "downloaded_file.mp4" # Fallback naam
        return filename

    def _get_target_path(self, filename, is_adult_content):
        """
        Bepaalt het volledige doelpad op basis van de instellingen.
        """
        if is_adult_content:
            base_path_setting_id = "download_path_adult"
            default_path = "special://downloads/Adult/"
        else:
            base_path_setting_id = "download_path"
            default_path = "special://downloads/"
        
        base_path = get_setting(base_path_setting_id, default_path)
        
        base_path = xbmcvfs.translatePath(base_path)
        if not base_path.endswith(os.sep):
            base_path += os.sep
            
        if not xbmcvfs.exists(base_path):
            xbmcvfs.mkdirs(base_path)
            log(f"Download directory '{base_path}' aangemaakt.", xbmc.LOGINFO)
            
        return os.path.join(base_path, filename)