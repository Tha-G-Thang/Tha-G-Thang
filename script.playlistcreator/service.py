import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import time
import re
from datetime import datetime, timedelta

from resources.lib.constants import ADDON_ID, ADDON_PROFILE, PLAYLIST_DIR, ADDON_NAME
from resources.lib.core.base_utils import log, get_setting, set_setting
from resources.lib.core.set_manager import update_all_sets

def validate_settings_service():
    """Ensure essential directories exist and settings are valid for the service."""
    if not xbmcvfs.exists(ADDON_PROFILE):
        xbmcvfs.mkdirs(ADDON_PROFILE)
        log(f"Service: Created addon profile directory: {ADDON_PROFILE}", xbmc.LOGINFO)
    if not xbmcvfs.exists(PLAYLIST_DIR):
        xbmcvfs.mkdirs(PLAYLIST_DIR)
        log(f"Service: Created playlist directory: {PLAYLIST_DIR}", xbmc.LOGINFO)

    update_time_str = get_setting('update_time', '03:00')
    if not re.match(r'^\d{2}:\d{2}$', update_time_str):
        set_setting('update_time', '03:00')
        log("Service: Invalid update_time format corrected to 03:00.", xbmc.LOGWARNING)

def check_scheduled_updates_service():
    """Check if scheduled updates need to be run."""
    auto_update_enabled = get_setting('auto_update', 'false') == 'true'
    update_interval_type = int(get_setting('update_interval', '0'))
    update_time_str = get_setting('update_time', '03:00')
    last_update_str = get_setting('last_update', 'Never')

    if not auto_update_enabled:
        return

    now = datetime.now()
    last_update_time = None
    if last_update_str != 'Never':
        try:
            last_update_time = datetime.fromisoformat(last_update_str)
        except ValueError:
            log(f"Service: Invalid last_update format: {last_update_str}. Resetting.", xbmc.LOGWARNING)
            set_setting('last_update', 'Never')
            last_update_time = None

    needs_update = False

    if update_interval_type == 0:
        if last_update_time is None or (now - last_update_time).total_seconds() >= 3600:
            needs_update = True
    else:
        try:
            update_hour, update_minute = map(int, update_time_str.split(':'))
            scheduled_today = now.replace(hour=update_hour, minute=update_minute, second=0, microsecond=0)

            if update_interval_type == 1:
                if last_update_time is None:
                    if now >= scheduled_today:
                        needs_update = True
                elif now >= scheduled_today and last_update_time < scheduled_today:
                    needs_update = True
                elif now < scheduled_today and last_update_time.date() < (now - timedelta(days=1)).date():
                     needs_update = True
                
            elif update_interval_type == 2:
                if now.weekday() == 0:
                    if last_update_time is None:
                        if now >= scheduled_today:
                            needs_update = True
                    elif now >= scheduled_today and last_update_time < scheduled_today:
                        needs_update = True
                    elif now < scheduled_today and last_update_time.date() < (now - timedelta(days=7)).date():
                        needs_update = True

        except Exception as e:
            log(f"Service: Error parsing update time or checking schedule: {e}", xbmc.LOGERROR)
            needs_update = False

    if needs_update:
        log("Service: Running scheduled playlist updates.", xbmc.LOGINFO)
        update_all_sets()
        set_setting('last_update', now.isoformat())
        xbmcgui.Dialog().notification(ADDON_NAME, "Geplande update van afspeellijsten voltooid!", xbmcgui.NOTIFICATION_INFO, 3000)
    else:
        log("Service: No scheduled update needed at this time.", xbmc.LOGDEBUG)

class PlaylistService(xbmc.Monitor):
    """Kodi service for background tasks like scheduled updates."""
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.last_check = time.time()
        log("PlaylistService initialized.", xbmc.LOGINFO)
        validate_settings_service()
        check_scheduled_updates_service()

    def onTimer(self):
        """Called every second by Kodi's Monitor."""
        if get_setting('auto_update', 'false') == 'true':
            if get_setting('pause_during_playback', 'true') == 'true' and xbmc.Player().isPlaying():
                log("Service: Pausing scheduled updates during playback.", xbmc.LOGDEBUG)
                return
            
            if time.time() - self.last_check > 60:
                log("Service: Checking for scheduled updates...", xbmc.LOGDEBUG)
                check_scheduled_updates_service()
                self.last_check = time.time()

if __name__ == '__main__':
    log("Service: Addon gestart als service.", xbmc.LOGINFO)
    service = PlaylistService()
    while not xbmc.Monitor().abortRequested():
        xbmc.sleep(1000)
    log("Service: Addon service terminated.", xbmc.LOGINFO)