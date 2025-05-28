import xbmcvfs
from resources.lib.core.scanner import Scanner
from resources.lib.core.sorter import Sorter
from resources.lib.utils import log, clean_filename, ADDON_PROFILE
from resources.lib.core.sorter import Sorter

class PlaylistCreator:
    def generate(self):
        sorter = Sorter()
        sorted_files = sorter.sort(found_files)
        display_names = [sorter.format_display_name(f) for f in sorted_files]

    def __init__(self, scanner=None, sorter=None):
    """
    :param scanner: Optioneel scanner-object (voor testing)
    :param sorter: Optioneel sorter-object
    """
    self.scanner = scanner if scanner else Scanner()
    self.sorter = sorter if sorter else Sorter()
    self._playlist_cache = []  # Cache voor performance

    def _format_entry(self, file_path):
    if get_bool_setting("show_folder_names"):
        folder = os.path.basename(os.path.dirname(file_path))
        color = get_setting("folder_name_color")
        return f"[COLOR {color}]{folder}[/COLOR]/{os.path.basename(file_path)}"
    return os.path.basename(file_path)
    def generate(self, folder_path):
        try:
            files = self.scanner.scan(folder_path)
            if not files:
                raise ValueError("No supported files found")
                
            sorted_files = self.sorter.sort(files)
            playlist_path = f"{ADDON_PROFILE}/playlist.m3u"
            
            with xbmcvfs.File(playlist_path, 'w') as f:
                f.write("#EXTM3U\n")
                for file in sorted_files:
                    f.write(f"{clean_filename(file)}\n")
            
            return True
        except Exception as e:
            log(f"Generation failed: {str(e)}", xbmc.LOGERROR)
            return False