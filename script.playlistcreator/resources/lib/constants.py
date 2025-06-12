import xbmcaddon
import xbmcvfs
import os

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PROFILE = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')
CONFIG_FILE = os.path.join(ADDON_PROFILE, 'playlist_sets.json')
PLAYLIST_DIR = xbmcvfs.translatePath('special://profile/playlists/video/')
FAVORITES_FILE = os.path.join(ADDON_PROFILE, 'favorites.json')
SMART_FOLDERS_FILE = os.path.join(ADDON_PROFILE, 'smart_folders.json')
STREAM_SETS_FILE = 'stream_sets.json' # AANGEPAST: Dit is nu alleen de bestandsnaam