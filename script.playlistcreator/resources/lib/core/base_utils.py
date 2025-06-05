import xbmc
import xbmcaddon
import xbmcvfs
import os
import json
import xbmcgui
import urllib.request
import zipfile
import shutil # Nodig voor het verwijderen van mappen

# Importeer de nieuwe constanten
from resources.lib.constants import SETTING_TYPE_MAP, DEFAULT_SETTINGS # Importeer de nieuwe map en defaults

# Addon constanten en basis utilities die overal nodig zijn
ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ADDON_PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
PLAYLIST_DIR = os.path.join(ADDON_PROFILE, "playlists")
# Locatie voor NLTK data binnen de add-on profielmap
NLTK_DATA_PATH = os.path.join(ADDON_PROFILE, "nltk_data")
# NIEUW: URL voor NLTK data (gh-pages branch van nltk_data repository)
NLTK_DATA_URL = "https://github.com/nltk/nltk_data/archive/gh-pages.zip" # Aangepast naar direct downloaden van zip

# --- Logging Functies ---
def log(msg, level=xbmc.LOGINFO):
    """
    Logt berichten naar de Kodi logfile.
    Args:
        msg (str): Het bericht om te loggen.
        level (int): Het logniveau (standaard INFO).
    """
    try:
        if get_bool_setting('debug_logging') and level >= xbmc.LOGDEBUG:
            xbmc.log(f"[{ADDON_ID}] {msg}", level)
        elif not get_bool_setting('debug_logging') and level >= get_int_setting('log_level', xbmc.LOGINFO):
            xbmc.log(f"[{ADDON_ID}] {msg}", level)
    except Exception as e:
        # Dit is een fallback als logging zelf faalt
        print(f"ERROR: Could not log message: {msg} - {e}")
        xbmc.log(f"[{ADDON_ID}] ERROR: Could not log message: {msg} - {e}", xbmc.LOGERROR)

# --- Instellingen Functies ---
def get_setting(setting_id, default=None):
    """
    Haalt een instelling op.
    Args:
        setting_id (str): De ID van de instelling.
        default (any): De standaardwaarde als de instelling niet gevonden wordt.
                       Wordt automatisch ingesteld indien niet opgegeven, op basis van DEFAULT_SETTINGS of type.
    Returns:
        any: De waarde van de instelling.
    """
    try:
        value = ADDON.getSetting(setting_id)
        if value:
            setting_type = SETTING_TYPE_MAP.get(setting_id)
            if setting_type == "bool":
                return value == "true"
            elif setting_type == "int" or setting_type == "number":
                return int(value)
            # Voor 'select' en 'enum' retourneren we de string, omzetting naar int gebeurt bij gebruik.
            # Voor 'color' retourneren we de string.
            return value
        else:
            # Gebruik de default uit DEFAULT_SETTINGS of de doorgegeven default
            if setting_id in DEFAULT_SETTINGS:
                log(f"get_setting: Gebruikt DEFAULT_SETTINGS voor '{setting_id}'.", xbmc.LOGDEBUG)
                return DEFAULT_SETTINGS[setting_id]
            else:
                log(f"get_setting: Gebruikt opgegeven default voor '{setting_id}' of None.", xbmc.LOGDEBUG)
                return default
    except Exception as e:
        log(f"Fout bij ophalen setting '{setting_id}': {str(e)}. Retourneer default: {default}", xbmc.LOGERROR)
        return default

def set_setting(setting_id, value):
    """
    Stelt een instelling in.
    BELANGRIJK: Voorkomt het schrijven van default="true" attributen naar addon_data/settings.xml.
    Args:
        setting_id (str): De ID van de instelling.
        value (any): De waarde om in te stellen.
    """
    try:
        ADDON.setSetting(setting_id, str(value))
        log(f"Instelling '{setting_id}' gezet op '{value}'.", xbmc.LOGDEBUG)
    except Exception as e:
        log(f"Fout bij instellen setting '{setting_id}' op '{value}': {str(e)}", xbmc.LOGERROR)

def get_bool_setting(setting_id, default=False):
    """Haalt een boolean instelling op."""
    return get_setting(setting_id, default)

def get_int_setting(setting_id, default=0):
    """Haalt een integer instelling op."""
    try:
        return int(get_setting(setting_id, str(default)))
    except ValueError:
        log(f"Waarde voor int setting '{setting_id}' is geen geldig getal. Retourneer default: {default}", xbmc.LOGWARNING)
        return default

# --- JSON Bestandsbeheer ---
def load_json(filename):
    """Laadt data uit een JSON bestand."""
    filepath = os.path.join(ADDON_PROFILE, filename)
    if xbmcvfs.exists(filepath):
        try:
            with xbmcvfs.File(filepath, 'r') as f:
                content = f.read()
                if content:
                    return json.loads(content)
                else:
                    log(f"Bestand '{filepath}' is leeg.", xbmc.LOGWARNING)
                    return None
        except Exception as e:
            log(f"Fout bij laden van JSON bestand '{filepath}': {str(e)}", xbmc.LOGERROR)
            return None
    log(f"JSON bestand niet gevonden: '{filepath}'", xbmc.LOGDEBUG)
    return None

def save_json(filename, data):
    """Slaat data op naar een JSON bestand."""
    filepath = os.path.join(ADDON_PROFILE, filename)
    try:
        if not xbmcvfs.exists(ADDON_PROFILE):
            xbmcvfs.mkdirs(ADDON_PROFILE)
        with xbmcvfs.File(filepath, 'w') as f:
            f.write(json.dumps(data, indent=2))
        log(f"JSON data succesvol opgeslagen naar '{filepath}'.", xbmc.LOGDEBUG)
        return True
    except Exception as e:
        log(f"Fout bij opslaan van JSON bestand '{filepath}': {str(e)}", xbmc.LOGERROR)
        return False

# --- NLTK Functies ---
def check_nltk_data_status():
    """
    Controleert of NLTK data aanwezig is en update de status instelling.
    Deze functie controleert specifiek op 'punkt' en 'stopwords'.
    """
    status_label = "Niet geïnstalleerd"
    download_location_label = "Niet van toepassing"
    nltk_data_downloaded_status = False

    try:
        import nltk
        if NLTK_DATA_PATH not in nltk.data.path:
            nltk.data.path.append(NLTK_DATA_PATH)
        
        # Controleer specifieke corpora die nodig zijn
        punkt_downloaded = False
        stopwords_downloaded = False

        try:
            nltk.data.find('tokenizers/punkt')
            punkt_downloaded = True
        except LookupError:
            pass

        try:
            nltk.data.find('corpora/stopwords')
            stopwords_downloaded = True
        except LookupError:
            pass

        if punkt_downloaded and stopwords_downloaded:
            status_label = "Geïnstalleerd (Punkt & Stopwords)"
            nltk_data_downloaded_status = True
            download_location_label = NLTK_DATA_PATH
            log("NLTK data (punkt, stopwords) gevonden en geïnstalleerd.", xbmc.LOGINFO)
        else:
            status_label = "Gedeeltelijk geïnstalleerd (Missing: " + \
                           (", Punkt" if not punkt_downloaded else "") + \
                           (", Stopwords" if not stopwords_downloaded else "") + ")"
            log(f"NLTK data is gedeeltelijk geïnstalleerd: {status_label}", xbmc.LOGWARNING)

    except ImportError:
        status_label = "NLTK module niet gevonden"
        log("NLTK module niet gevonden. AI functionaliteit uitgeschakeld.", xbmc.LOGERROR)
    except Exception as e:
        status_label = f"Fout bij controleren NLTK: {str(e)}"
        log(f"Onverwachte fout bij controleren NLTK data: {str(e)}", xbmc.LOGERROR)

    set_setting("nltk_data_status_display", status_label)
    set_setting("nltk_download_location_display", download_location_label)
    set_setting("nltk_data_downloaded", nltk_data_downloaded_status)
    log(f"NLTK status geüpdatet: {status_label}", xbmc.LOGDEBUG)

def download_and_extract_nltk_data():
    """
    Downloadt en extraheert de NLTK data.
    """
    log("Starten met downloaden van NLTK data...", xbmc.LOGINFO)
    dialog = xbmcgui.DialogProgress()
    dialog.create(ADDON_NAME, "NLTK data downloaden...")
    
    try:
        # Maak de NLTK_DATA_PATH map als deze niet bestaat
        if not xbmcvfs.exists(NLTK_DATA_PATH):
            xbmcvfs.mkdirs(NLTK_DATA_PATH)
            log(f"NLTK data directory aangemaakt: {NLTK_DATA_PATH}", xbmc.LOGDEBUG)
        else:
            # Optioneel: leeg de map als deze al bestaat om corrupte downloads te voorkomen
            # Let op: dit verwijdert alle bestaande data!
            log(f"Bestaande NLTK data directory '{NLTK_DATA_PATH}' legen...", xbmc.LOGINFO)
            shutil.rmtree(xbmcvfs.translatePath(NLTK_DATA_PATH)) # Gebruik shutil.rmtree voor mappen
            xbmcvfs.mkdirs(NLTK_DATA_PATH)
            log("NLTK data directory succesvol geleegd.", xbmc.LOGINFO)

        zip_path = os.path.join(ADDON_PROFILE, "nltk_data.zip")
        local_nltk_data_path = xbmcvfs.translatePath(NLTK_DATA_PATH)

        # Download de zipfile
        log(f"Downloaden van '{NLTK_DATA_URL}' naar '{zip_path}'...", xbmc.LOGINFO)
        urllib.request.urlretrieve(NLTK_DATA_URL, zip_path, lambda blocks, block_size, total_size: dialog.update(int(blocks * block_size * 100 / total_size)))
        
        dialog.update(100, "NLTK data gedownload. Start extractie...")
        log(f"NLTK data gedownload naar '{zip_path}'. Start extractie naar '{local_nltk_data_path}'.", xbmc.LOGINFO)

        # Extract de zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # De gh-pages zip heeft een root map zoals 'nltk_data-gh-pages'.
            # We moeten de inhoud van die map extraheren.
            root_dirs = [m.split('/')[0] for m in zip_ref.namelist() if '/' in m]
            common_root_dir = None
            if root_dirs:
                # Vind de meest voorkomende root map (meestal de enige)
                from collections import Counter
                common_root_dir = Counter(root_dirs).most_common(1)[0][0]

            if common_root_dir:
                log(f"Gedetecteerde root directory in zip: '{common_root_dir}'. Extraheer inhoud.", xbmc.LOGDEBUG)
                for member in zip_ref.namelist():
                    if member.startswith(common_root_dir + '/'):
                        # Nieuw pad is zonder de root directory
                        target_path = os.path.join(local_nltk_data_path, os.path.relpath(member, common_root_dir))
                        if os.path.isdir(target_path): # Dir aanmaken
                            if not os.path.exists(target_path):
                                os.makedirs(target_path)
                            continue

                        # Zorg ervoor dat de directory voor het bestand bestaat
                        target_dir = os.path.dirname(target_path)
                        if not os.path.exists(target_dir):
                            os.makedirs(target_dir)

                        # Extract bestand
                        with open(target_path, 'wb') as outfile:
                            outfile.write(zip_ref.read(member))
            else:
                log("Geen gemeenschappelijke root directory gedetecteerd in zip. Extraheer alles direct.", xbmc.LOGWARNING)
                zip_ref.extractall(local_nltk_data_path)


        # Verwijder de gedownloade zip
        xbmcvfs.delete(zip_path)

        dialog.close()
        xbmcgui.Dialog().notification(ADDON_NAME, "NLTK data succesvol gedownload en geïnstalleerd!", xbmcgui.NOTIFICATION_INFO, 5000)
        log("NLTK data succesvol gedownload en geïnstalleerd.", xbmc.LOGINFO)
        # Na succesvolle download, update de status in de settings (voor de volgende keer openen)
        check_nltk_data_status()
        return True
    except Exception as e:
        dialog.close()
        xbmcgui.Dialog().notification(ADDON_NAME, f"Fout bij downloaden/installeren NLTK data: {str(e)}", xbmcgui.NOTIFICATION_ERROR, 7000)
        log(f"Fout bij downloaden/installeren NLTK data: {str(e)}", xbmc.LOGERROR)
        return False
    
# --- Migratielogica (NIEUW) ---
def perform_migration():
    """
    Voert migratie van oude instellingen naar nieuwe types/namen uit.
    Deze functie wordt eenmalig uitgevoerd na een update.
    """
    log("Starten van migratielogica...", xbmc.LOGINFO)
    
    # Gebruik een setting om te controleren of de migratie al is uitgevoerd
    # Bijvoorbeeld, sla de versie van de laatste migratie op.
    current_migration_version = get_setting('last_migration_version', '0.0.0')
    addon_version = ADDON.getAddonInfo('version')

    # Voor nu voeren we de migratie uit als de add-on versie hoger is dan de laatst gemigreerde versie
    # of als 'last_migration_version' nog niet bestaat (eerste run).
    # Dit is een simpele vergelijking, voor complexere versies is een parseerfunctie nodig.
    # Echter, Python's string vergelijking werkt prima voor '3.0.0' > '2.0.0'.
    if addon_version <= current_migration_version:
        log(f"Add-on versie ({addon_version}) is niet nieuwer dan laatst gemigreerde versie ({current_migration_version}). Migratie overgeslagen.", xbmc.LOGINFO)
        return

    log(f"Add-on versie ({addon_version}) is nieuwer dan laatst gemigreerde versie ({current_migration_version}). Migratie wordt uitgevoerd.", xbmc.LOGINFO)

    migrated_settings_count = 0

    # Mapping van oude setting ID's naar nieuwe ID's en hun conversielogica
    # Dit moet alle instellingen bevatten die van type zijn veranderd of hernoemd zijn.
    # WAARSCHUWING: De waarden van