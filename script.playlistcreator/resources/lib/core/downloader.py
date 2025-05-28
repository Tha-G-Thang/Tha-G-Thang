import xbmcvfs
from resources.lib.utils import log, clean_filename

class Downloader:
    def __init__(self):
        self.download_path = xbmcvfs.translatePath("special://downloads/")

    def download(self, url, is_adult_content=False):
        """
        Generieke downloadmethode voor alle use-cases
        Args:
            url: Bron-URL
            is_adult_content: Gebruik adult-downloadmap indien True
        """
        try:
            filename = self._extract_filename(url)
            cleaned_name = clean_filename(filename)
            full_path = self._get_target_path(cleaned_name, is_adult_content)
            
            # Kern-downloadlogica hier
            log(f"Download gestart: {url} -> {full_path}")
            return True
            
        except Exception as e:
            log(f"Downloadfout: {str(e)}", xbmc.LOGERROR)
            return False

    def download_file(self, url, is_adult_content=False):
        """
        Gespecialiseerde versie voor contextmenu
        - Extra validatie
        - Gedetailleerde logging
        """
        log(f"Contextmenu-actie: {'adult' if is_adult_content else 'normal'} download")
        if not url.startswith(('http://', 'https://', 'plugin://')):
            raise ValueError("Ongeldig URL-formaat")
        return self.download(url, is_adult_content)

    def _extract_filename(self, url):
        return url.split('/')[-1].split('?')[0]

    def _get_target_path(self, filename, is_adult_content):
        subdir = "adult/" if is_adult_content else ""
        return f"{self.download_path}{subdir}{filename}"