import xbmcgui
import xbmcvfs
from resources.lib.utils import log, load_json, save_json

class SetManager:
    def select_folder(self):
        dialog = xbmcgui.Dialog()
        folder = dialog.browse(0, "Select folder", 'files')
        return folder if folder else None

    def manage_sets(self):
        sets = load_json("sets.json") or {}
        # ... volledige management logica