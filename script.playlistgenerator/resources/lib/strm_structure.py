import os
import xbmcvfs
from .constants import CATEGORY_NAMES
from .strm_utils import log, translate_path, get_setting

def ensure_category_structure():
    base_path = translate_path(get_setting('streams_target_root'))
    if not base_path.endswith('/'):
        base_path += '/'
    created = []

    for category in CATEGORY_NAMES:
        dir_path = os.path.join(base_path, category)
        if not xbmcvfs.exists(dir_path):
            try:
                xbmcvfs.mkdirs(dir_path)
                created.append(category)
            except Exception as e:
                log(f"Failed to create category folder {category}: {e}", xbmc.LOGERROR)

    if created:
        log(f"Created category folders: {', '.join(created)}")
    else:
        log("Category folders already exist or nothing created.")