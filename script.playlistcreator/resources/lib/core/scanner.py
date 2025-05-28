import os
import xbmcvfs
from resources.lib.utils import log

class Scanner:
    def scan(self, folder_path):
        try:
            _, files = xbmcvfs.listdir(folder_path)
            return [
                f for f in files 
                if os.path.splitext(f)[1].lower() in ('.mp4','.mkv','.avi')
            ]
        except Exception as e:
            log(f"Scan failed: {str(e)}", xbmc.LOGERROR)
            return []