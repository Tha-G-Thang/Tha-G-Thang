import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import json
import random
import urllib.parse
from datetime import datetime, timedelta
import re
import time
import sys
from functools import cmp_to_key

# Addon Setup
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')

# Importeer basis utility functies en managers
from resources.lib.core.creator import PlaylistCreator
from resources.lib.core.manager import SetManager
from resources.lib.core.stream_set_manager import StreamSetManager
from resources.lib.core.base_utils import log, get_setting, set_setting, perform_migration, ADDON_PROFILE, PLAYLIST_DIR, load_json, save_json, get_bool_setting, check_nltk_data_status, download_and_extract_nltk_data
from resources.lib.core.menu_handler import handle_context_action # Voor contextmenu acties

# Initialiseer managers (deze worden nu geïnstantieerd)
set_manager = SetManager()
stream_set_manager = StreamSetManager()
playlist_creator = PlaylistCreator()

# Zorg ervoor dat de addon mappen bestaan bij opstarten
def initialize_addon_dirs():
    if not xbmcvfs.exists(ADDON_PROFILE):
        log(f"Creating add-on profile directory: {ADDON_PROFILE}", xbmc.LOGINFO)
        xbmcvfs.mkdirs(ADDON_PROFILE)
    if not xbmcvfs.exists(PLAYLIST_DIR):
        log(f"Creating playlists directory: {PLAYLIST_DIR}", xbmc.LOGINFO)
        xbmcvfs.mkdirs(PLAYLIST_DIR)

def show_main_menu():
    log("Entering show_main_menu()", xbmc.LOGDEBUG)
    options = []
    
    # Haal sets op. Zorg voor een fallback als de JSON leeg/corrupt is
    sets = set_manager.get_sets()
    
    # Voeg basisopties toe, ongeacht de aanwezigheid van sets
    options.append("Create New Playlist Set")
    options.append("Run Quick Scan & Create Playlist")
    
    if sets: # Alleen tonen als er sets zijn
        options.append("Manage Playlist Sets")
        options.append("Update All Playlists")
    
    # Algemene opties
    options.append("Schedule Updates") # Deze optie kan nu alleen de settings openen voor 'enable_timer'
    options.append("Add-on Settings")
    options.append("Show Add-on Info")
    options.append("Exit")

    dialog = xbmcgui.Dialog()
    
    while True:
        log(f"Displaying main menu with {len(options)} options.", xbmc.LOGDEBUG)
        choice = dialog.select(f"[B]{ADDON_NAME}[/B] - Main Menu", options)

        if choice == 0:  # Create New Playlist Set
            set_manager.create_new_set_flow()
        elif choice == 1: # Run Quick Scan & Create Playlist
            playlist_creator.run_quick_scan()
        elif choice == 2: # Manage Playlist Sets (index verschuift als sets leeg is)
            if sets:
                set_manager.manage_sets()
            else: # Dit is dan de Schedule Updates optie
                show_timer_settings()
        elif choice == 3: # Update All Playlists (index verschuift als sets leeg is)
            if sets:
                set_manager.update_all_sets()
            else: # Dit is dan de Add-on Settings optie
                ADDON.openSettings()
        elif choice == 4: # Schedule Updates (index verschuift als sets leeg is)
            if sets:
                show_timer_settings()
            else: # Dit is dan de Show Add-on Info optie
                show_info_dialog()
        elif choice == 5: # Add-on Settings (index verschuift als sets leeg is)
            if sets:
                ADDON.openSettings()
            else: # Dit is dan de Exit optie
                break
        elif choice == 6: # Show Add-on Info (index verschuift als sets leeg is)
            if sets:
                show_info_dialog()
            else:
                break # Exit
        elif choice == 7 or choice == -1: # Exit (index verschuift als sets leeg is)
            break
        
        # Na een actie, refresh de sets om de menu-opties te updaten indien nodig
        sets = set_manager.get_sets()
        log("Menu action completed, refreshing sets for next loop iteration.", xbmc.LOGDEBUG)

def show_timer_settings():
    """Toon de timerinstellingen voor de add-on."""
    log("Entering show_timer_settings(). Opening add-on settings for timer.", xbmc.LOGDEBUG)
    ADDON.openSettings()
    # Hier kun je eventueel direct naar een specifieke categorie navigeren als de Kodi API dit toestaat.
    # Voor nu opent het de algemene instellingen.

def show_info_dialog():
    """Toont een informatie dialoog met add-on details."""
    log("Entering show_info_dialog().", xbmc.LOGDEBUG)
    info_text = f"""
[B]{ADDON_NAME} v{ADDON.getAddonInfo('version')}[/B]

This add-on generates playlists from your local video files,
with a focus on non-standard media and customizable sorting options.

[B]Features:[/B]
- Automatic folder scanning and playlist creation.
- Management of \"Sets\" (predefined settings and folders).
- Management of \"Stream Sets\" (saved and playable streams).
- Integration with NLTK for advanced AI features (optional).
- Customizable sorting and filtering options.

[B]Help:[/B]
For detailed instructions and troubleshooting,
visit the GitHub repository or the Kodi forum (if available).
Currently, no external link is available via this add-on.

[B]Add-on Profile Location:[/B]
{ADDON_PROFILE}

[B]Playlists Location:[/B]
{PLAYLIST_DIR}
"""
    xbmcgui.Dialog().ok(ADDON_NAME, info_text)
    log("Info dialog shown.", xbmc.LOGDEBUG)


if __name__ == '__main__':
    log(f"{ADDON_NAME} starting. sys.argv: {sys.argv}", xbmc.LOGINFO)

    initialize_addon_dirs() # Zorg dat mappen bestaan

    # Voer migratielogica uit bij elke opstart
    log("Performing migration check...", xbmc.LOGDEBUG)
    perform_migration()
    log("Migration check complete.", xbmc.LOGDEBUG)
    
    # Dit blok is nu alleen voor contextmenu's of andere parameters
    if len(sys.argv) > 1:
        log(f"Handling action with arguments: {sys.argv}", xbmc.LOGINFO)
        handle_context_action(sys.argv) 
        log("Action with arguments handled. Exiting.", xbmc.LOGDEBUG)
        sys.exit() 
    else:
        # Run as script (show main menu)
        log("Running as script (showing main menu).", xbmc.LOGINFO)
        show_main_menu()
        log("Main menu closed. Exiting.", xbmc.LOGDEBUG)
        sys.exit()