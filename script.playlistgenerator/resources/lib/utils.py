import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import json
import urllib.parse
import sys
import os
import re
from datetime import datetime

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))

# Ensure profile directory exists
if not xbmcvfs.exists(ADDON_PROFILE):
    xbmcvfs.mkdirs(ADDON_PROFILE)

CONFIG_FILE = os.path.join(ADDON_PROFILE, 'settings.json')
PLAYLIST_DIR = os.path.join(ADDON_PROFILE, 'playlists')

DIALOG = xbmcgui.Dialog()

def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_NAME}] {msg}", level)

def show_notification(heading, message, time=3000, icon=xbmcgui.NOTIFICATION_INFO):
    DIALOG.notification(heading, message, time, icon)

def show_ok_dialog(heading, message):
    DIALOG.ok(heading, message)

def show_yesno_dialog(heading, message):
    return DIALOG.yesno(heading, message)

def load_json(filepath):
    if xbmcvfs.exists(filepath):
        try:
            with xbmcvfs.File(filepath, 'r') as f:
                content = f.read()
            return json.loads(content)
        except Exception as e:
            log(f"Error loading JSON from {filepath}: {e}", xbmc.LOGERROR)
            return {}
    return {}

def save_json(filepath, data):
    try:
        dirname = os.path.dirname(filepath)
        if not xbmcvfs.exists(dirname):
            xbmcvfs.mkdirs(dirname)

        with xbmcvfs.File(filepath, 'w') as f:
            f.write(json.dumps(data, indent=4))
        return True
    except Exception as e:
        log(f"Error saving JSON to {filepath}: {e}", xbmc.LOGERROR)
        return False

def get_setting(setting_id, default=''):
    return ADDON.getSetting(setting_id) or default

def get_all_addon_settings():
    settings = {}
    setting_ids = [
        "file_extensions", "exclude_pattern", "min_file_size", "enable_max_size", "max_file_size",
        "enable_date_filter", "min_file_date", "sort_mode", "enable_playlist_limit", "limit_mode",
        "file_count", "total_file_count", "enable_rotation", "rotation_offset",
        "enable_display_name_color", "folder_name_color", "scan_depth", "exclude_folders",
        "default_download_folder", "clips_download_folder", "adult_download_folder"
    ]
    for setting_id in setting_ids:
        settings[setting_id] = get_setting(setting_id)

    settings["min_file_size"] = float(settings["min_file_size"]) if settings["min_file_size"] else 0.0
    settings["max_file_size"] = float(settings["max_file_size"]) if settings["max_file_size"] else 0.0
    settings["scan_depth"] = int(settings["scan_depth"]) if settings["scan_depth"] else 1
    settings["file_count"] = int(settings["file_count"]) if settings["file_count"] else 100
    settings["total_file_count"] = int(settings["total_file_count"]) if settings["total_file_count"] else 1000
    settings["rotation_offset"] = int(settings["rotation_offset"]) if settings["rotation_offset"] else 0

    settings["enable_max_size"] = settings["enable_max_size"] == 'true'
    settings["enable_date_filter"] = settings["enable_date_filter"] == 'true'
    settings["enable_playlist_limit"] = settings["enable_playlist_limit"] == 'true'
    settings["enable_rotation"] = settings["enable_rotation"] == 'true'
    settings["enable_display_name_color"] = settings["enable_display_name_color"] == 'true'

    return settings

def generate_playlist_filename(set_name):
    safe_name = re.sub(r'[^\w\s-]', '', set_name).strip().replace(' ', '_')
    return f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.m3u"

def get_file_details(path):
    details = {
        'size': None,
        'creation_time': None,
        'duration': None
    }

    stat = xbmcvfs.Stat(path)
    if stat.st_size() > -1:
        details['size'] = stat.st_size()
    if stat.st_ctime() > -1:
        details['creation_time'] = stat.st_ctime()

    try:
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.mpeg', '.mpg', '.flv', '.webm', '.ts', '.m2ts', '.mts', '.ogm', '.vob', '.ps', '.f4v', '.3gp', '.divx', '.xvid']
        if os.path.splitext(path)[1].lower() in video_extensions:
            json_query = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Files.GetFileDetails", "params": {"file": "%s", "properties": ["streamdetails"]}, "id": 1}' % json.dumps(path)
            )
            response = json.loads(json_query)
            if 'result' in response and 'filedetails' in response['result'] and 'streamdetails' in response['result']['filedetails']:
                video_streams = response['result']['filedetails'].get('video', [])
                if video_streams:
                    duration = video_streams[0].get('durationinseconds')
                    if duration is not None:
                        details['duration'] = duration
    except Exception as e:
        log(f"Error getting duration for {path} via JSON-RPC: {e}", xbmc.LOGWARNING)

    return details

def parse_argv(argv):
    args = {}
    if argv and len(argv) > 1:
        query_string = argv[1]

        match = re.match(r'\?\d+\?(.*)', query_string)
        if match:
            query_string = match.group(1)
        elif query_string.startswith('?'):
            query_string = query_string[1:]

        parsed_q = urllib.parse.parse_qs(query_string)
        for key, value_list in parsed_q.items():
            if value_list:
                args[key] = value_list[0]
    return args

def build_url(query, handle=None):
    base_url = sys.argv[0]

    if handle is None:
        try:
            handle = int(sys.argv[1])
        except (IndexError, ValueError):
            handle = 0
            log(f"Warning: build_url called without explicit handle and sys.argv[1] is missing/invalid. Using 0. sys.argv: {sys.argv}", xbmc.LOGWARNING)

    encoded_query = urllib.parse.urlencode(query)

    full_url = f"{base_url}?{handle}&{encoded_query}"
    log(f"Building URL: {full_url}", xbmc.LOGDEBUG)
    return full_url
