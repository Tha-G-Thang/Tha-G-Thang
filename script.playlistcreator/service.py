import xbmc
import xbmcaddon
import xbmcvfs
import os
import time
import re
from datetime import datetime, timedelta

from resources.lib.constants import ADDON_ID, ADDON_PROFILE, PLAYLIST_DIR, ADDON, ADDON_NAME # Importeer ADDON, ADDON_NAME
from resources.lib.core.base_utils import log, get_setting, set_setting # Correct: .core.base_utils
from resources.lib.core.set_manager import update_all_sets # Correct: .core.set_manager

def validate_settings_service():
   """Ensure essential directories exist and settings are valid for the service."""
   if not xbmcvfs.exists(ADDON_PROFILE):
       xbmcvfs.mkdirs(ADDON_PROFILE)
       log(f"Service: Created addon profile directory: {ADDON_PROFILE}", xbmc.LOGINFO)
   if not xbmcvfs.exists(PLAYLIST_DIR):
       xbmcvfs.mkdirs(PLAYLIST_DIR)
       log(f"Service: Created playlist directory: {PLAYLIST_DIR}", xbmc.LOGINFO)

   # Validate update time format
   update_time_str = get_setting('update_time', '03:00')
   if not re.match(r'^\d{2}:\d{2}$', update_time_str):
       set_setting('update_time', '03:00')
       log("Service: Invalid update_time format corrected to 03:00.", xbmc.LOGWARNING)

def check_scheduled_updates_service():
   """Check if scheduled updates need to be run."""
   auto_update_enabled = get_setting('auto_update', 'false') == 'true'
   update_interval = int(get_setting('update_interval', '0')) # 0: Hourly, 1: Daily, 2: Weekly
   update_time_str = get_setting('update_time', '03:00') # HH:MM
   last_update_str = get_setting('last_update', '')

   if not auto_update_enabled:
       log("Service: Automatic updates disabled.", xbmc.LOGDEBUG)
       return

   now = datetime.now()
   last_update_dt = None

   if last_update_str:
       try:
           last_update_dt = datetime.strptime(last_update_str, '%Y-%m-%d %H:%M:%S')
       except ValueError:
           log(f"Service: Invalid last_update format: {last_update_str}. Resetting.", xbmc.LOGWARNING)
           set_setting('last_update', '') # Reset if invalid
           last_update_dt = None

   perform_update = False

   if update_interval == 0: # Hourly
       if last_update_dt is None or now - last_update_dt >= timedelta(hours=1):
           perform_update = True
   elif update_interval == 1: # Daily
       try:
           update_hour, update_minute = map(int, update_time_str.split(':'))
           scheduled_update_time = now.replace(hour=update_hour, minute=update_minute, second=0, microsecond=0)

           if last_update_dt is None: # No last update, perform if scheduled time has passed today
               if now >= scheduled_update_time:
                   perform_update = True
           elif now >= scheduled_update_time and last_update_dt < scheduled_update_time:
               # If scheduled time has passed today AND last update was before today's scheduled time
               perform_update = True
           elif now < scheduled_update_time and last_update_dt and last_update_dt.date() < (now - timedelta(days=1)).date():
               # If scheduled time is in the future today, but last update was more than a day ago
               perform_update = True

       except ValueError as e:
           log(f"Service: Error parsing daily update time: {e}", xbmc.LOGERROR)
           return

   elif update_interval == 2: # Weekly
       try:
           update_hour, update_minute = map(int, update_time_str.split(':'))
           scheduled_update_time = now.replace(hour=update_hour, minute=update_minute, second=0, microsecond=0)
           
           # For simplicity, assume weekly update is on Monday (weekday 0)
           # This logic needs to be more robust for specific day of week if needed.
           # Here: if last_update_dt is more than a week ago, or it's a new week and time has passed.
           if last_update_dt is None:
               if now >= scheduled_update_time:
                   perform_update = True # Perform if no last update and current time is past scheduled time today
           elif now >= scheduled_update_time and (now - last_update_dt) >= timedelta(weeks=1):
               perform_update = True
           elif now < scheduled_update_time and last_update_dt and (now - last_update_dt) >= timedelta(days=7):
               perform_update = True # If it's a new week and time hasn't passed today, but last update was over a week ago
       except ValueError as e:
           log(f"Service: Error parsing weekly update time: {e}", xbmc.LOGERROR)
           return

   if perform_update:
       log("Service: Performing scheduled update for all sets.", xbmc.LOGINFO)
       update_all_sets()
       set_setting('last_update', now.strftime('%Y-%m-%d %H:%M:%S'))
       xbmcgui.Dialog().notification(ADDON_NAME, "Geplande update van afspeellijsten voltooid!", xbmcgui.NOTIFICATION_INFO, 3000)

class PlaylistService(xbmc.Monitor):
   """Kodi service for background tasks like scheduled updates."""
   def __init__(self, *args, **kwargs):
       xbmc.Monitor.__init__(self)
       self.last_check = time.time()
       log("PlaylistService initialized.", xbmc.LOGINFO)
       validate_settings_service() # Validate settings when service starts
       check_scheduled_updates_service() # Initial check on startup

   def onTimer(self):
       """Called every second by Kodi's Monitor."""
       # Only perform checks if the addon is enabled, and not during playback if setting is off
       if get_setting('auto_update', 'false') == 'true':
           if get_setting('pause_during_playback', 'true') == 'true' and xbmc.Player().isPlaying():
               log("Service: Pausing scheduled updates during playback.", xbmc.LOGDEBUG)
               return
           
           # Check every minute (60 seconds)
           if time.time() - self.last_check > 60:
               log("Service: Checking for scheduled updates...", xbmc.LOGDEBUG)
               check_scheduled_updates_service()
               self.last_check = time.time()

if __name__ == '__main__':
   log("Service: Addon gestart als service.", xbmc.LOGINFO)
   service = PlaylistService()
   # Keep the service alive until Kodi requests termination
   while not xbmc.Monitor().abortRequested():
       xbmc.sleep(1000) # Sleep and allow Kodi to process events
   log("Service: Addon service terminated.", xbmc.LOGINFO)