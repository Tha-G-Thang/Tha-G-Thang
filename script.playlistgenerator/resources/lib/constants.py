import os

ADDON_ID = 'script.playlistgenerator'
ADDON_NAME = 'Playlist [COLOR gold]G[/COLOR]-enerator Plus'
CONFIG_FILE = 'config.json'

DEFAULT_CATEGORY_PATH = os.path.join('special://profile', 'addon_data', ADDON_ID, 'streams', 'categorien')

DEFAULT_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv']

CATEGORY_NAMES = [
    "Youtube Clips",
    "Trailers",
    "Compilations",
    "Music Videos",
    "Shorts",
    "[COLOR black]Adult[/COLOR]",
    "_",
    "Filename Only"
]