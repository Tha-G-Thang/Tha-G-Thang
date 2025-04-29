import xbmc
import xbmcgui
import xbmcaddon
from datetime import datetime
from default import UpdateManager, Logger, NotificationHandler, SettingsManager

class MemoryWatchdog:
    """Tracks memory usage and prevents overload"""
    def __init__(self, threshold=85):
        self.threshold = threshold
        
    def is_safe(self):
        try:
            free_mem = float(xbmc.getInfoLabel('System.Memory(free.percent)'))
            return (100 - free_mem) < self.threshold  # Convert free% to used%
        except:
            return True  # Fail-safe

class PlaylistService:
    def __init__(self):
        self.monitor = xbmc.Monitor()
        self.watchdog = MemoryWatchdog(threshold=85)
        self.update_interval = 300  # 5 minutes
        
    def run(self):
        """Main service loop"""
        Logger.log("Service started (Optimized Mode)")
        while not self.monitor.abortRequested():
            if self.watchdog.is_safe():
                if self._should_run_update():
                    self._safe_update()
            else:
                Logger.warning("Memory threshold exceeded - skipping scan")
                
            if self.monitor.waitForAbort(self.update_interval):
                break
    
    def _should_run_update(self):
        """Check if scheduled update should run"""
        if not SettingsManager.get_bool('enable_timer'):
            return False
            
        now = datetime.now()
        interval = SettingsManager.get_int('update_interval', 1)
        update_time = SettingsManager.get('update_time', '03:00')
        
        try:
            hour, minute = map(int, update_time.split(':'))
            last_update_str = SettingsManager.get('last_update')
            last_update = (datetime.strptime(last_update_str, "%Y-%m-%d %H:%M:%S") 
                         if last_update_str and last_update_str != 'Never' else None)
            
            time_matches = now.hour == hour and now.minute == minute
            
            if interval == 0:  # Hourly
                return time_matches and (not last_update or (now - last_update).total_seconds() >= 3600)
            elif interval == 1:  # Daily
                return time_matches and (not last_update or (now - last_update).total_seconds() >= 86400)
            elif interval == 2:  # Weekly
                return time_matches and now.weekday() == 0 and (not last_update or (now - last_update).total_seconds() >= 604800)
        except Exception as e:
            Logger.error(f"Schedule check error: {str(e)}")
            return False
    
    def _safe_update(self):
        """Run update with error handling"""
        try:
            UpdateManager.update_playlists_with_mode()
        except MemoryError:
            Logger.error("MemoryError - skipping update")
            xbmc.executebuiltin("Dialog.Close(all,true)")  # Clean up any open dialogs
        except Exception as e:
            Logger.error(f"Update error: {str(e)}")
            if SettingsManager.get('operation_mode') == '0':
                NotificationHandler.show(f"Update failed: {str(e)}", error=True)

if __name__ == '__main__':
    service = PlaylistService()
    service.run()