import os
import xbmc
import stat # Nodig voor os.stat om m_time te krijgen

from resources.lib.core.base_utils import get_setting, get_bool_setting, get_int_setting, log

# Probeer de AISorter te importeren, vang de ImportError op als de module niet beschikbaar is.
# Dit zorgt ervoor dat de add-on niet crasht als AI niet is geconfigureerd of geïnstalleerd.
_ai_sorter_instance = None
if get_bool_setting("enable_ai") and get_bool_setting("ai_content_grouping"):
    try:
        from resources.lib.core.ai.ai_sorter import AISorter
        _ai_sorter_instance = AISorter()
        log("AISorter instance succesvol geladen in sorter.py.", xbmc.LOGDEBUG)
    except ImportError as e:
        log(f"AISorter module niet gevonden: {e}. Content-Based sorting zal niet beschikbaar zijn.", xbmc.LOGWARNING)
        _ai_sorter_instance = None
    except Exception as e:
        log(f"Fout bij laden/initialiseren van AISorter: {str(e)}. Content-Based sorting zal niet beschikbaar zijn.", xbmc.LOGERROR)
else:
    log("AI Content Grouping of algemene AI is uitgeschakeld. AISorter zal niet worden gebruikt.", xbmc.LOGINFO)

class Sorter:
    def __init__(self):
        pass

    def sort(self, file_list):
        """
        Sorteert een lijst van bestanden op basis van de gebruiker-gedefinieerde instellingen.
        """
        log(f"Sorter: Starten met sorteren van {len(file_list)} bestanden.", xbmc.LOGDEBUG)

        file_sort_mode = get_setting("file_sort_order", "0")
        
        # AI-gebaseerde sortering
        if file_sort_mode == "3" and _ai_sorter_instance: # "Content-Based"
            log("Sorter: Bestanden sorteren op inhoud (AI-gebaseerd).", xbmc.LOGDEBUG)
            try:
                # AISorter verwacht een lijst van file_paths
                sorted_files = _ai_sorter_instance.sort_by_content(file_list)
                return sorted_files
            except Exception as e:
                log(f"Fout bij AI-gebaseerde sortering: {str(e)}. Terugval op 'Meest recent eerst'.", xbmc.LOGERROR)
                file_sort_mode = "0" # Terugval naar standaard sortering
                
        # Standaard sortering
        if file_sort_mode == "0": # Meest recent eerst (Newest first)
            log("Sorter: Bestanden sorteren op meest recent eerst.", xbmc.LOGDEBUG)
            # Sorteren op aanpassingsdatum (m_time) in aflopende volgorde
            return sorted(file_list, key=lambda f: os.stat(f).st_mtime, reverse=True)
        elif file_sort_mode == "1": # Oudste eerst (Oldest first)
            log("Sorter: Bestanden sorteren op oudste eerst.", xbmc.LOGDEBUG)
            # Sorteren op aanpassingsdatum (m_time) in oplopende volgorde
            return sorted(file_list, key=lambda f: os.stat(f).st_mtime)
        elif file_sort_mode == "2": # Alfabetisch (A-Z)
            log("Sorter: Bestanden alfabetisch (A-Z) sorteren.", xbmc.LOGDEBUG)
            # Sorteren op bestandsnaam (lowercase voor case-insensitieve sortering)
            return sorted(file_list, key=lambda f: os.path.basename(f).lower())
        else: # Fallback: Meest recent eerst
            log(f"Sorter: Onbekende bestands-sorteermodus '{file_sort_mode}'. Terugval op 'Meest recent eerst'.", xbmc.LOGWARNING)
            return sorted(file_list, key=lambda f: os.stat(f).st_mtime, reverse=True)

    def sort_folders(self, folders):
        """
        Sorteert een lijst van mappen op basis van de gebruiker-gedefinieerde instellingen.
        """
        log(f"Sorter: Starten met sorteren van {len(folders)} mappen.", xbmc.LOGDEBUG)

        folder_sort_mode = get_setting("folder_sort_order", "0") # Default A-Z

        if folder_sort_mode == "0": # A-Z
            log("Sorter: Mappen alfabetisch (A-Z) sorteren.", xbmc.LOGDEBUG)
            return sorted(folders, key=lambda x: os.path.basename(x).lower())
        elif folder_sort_mode == "1": # Z-A
            log("Sorter: Mappen alfabetisch (Z-A) sorteren.", xbmc.LOGDEBUG)
            return sorted(folders, key=lambda x: os.path.basename(x).lower(), reverse=True)
        elif folder_sort_mode == "2": # Custom Order
            log("Sorter: Mappen sorteren op aangepaste volgorde.", xbmc.LOGDEBUG)
            custom_order_str = get_setting("custom_folder_order", "")
            if custom_order_str:
                custom_order_list = [f.strip().lower() for f in custom_order_str.split(',') if f.strip()]
                # Sorteer eerst op aanwezigheid in de custom order, dan op de index, dan alfabetisch voor de rest
                return sorted(folders, key=lambda x: (
                    custom_order_list.index(os.path.basename(x).lower()) if os.path.basename(x).lower() in custom_order_list else len(custom_order_list),
                    os.path.basename(x).lower()
                ))
            else:
                log("Custom folder order requested but setting 'custom_folder_order' is empty. Falling back to A-Z.", xbmc.LOGWARNING)
                return sorted(folders, key=lambda x: os.path.basename(x).lower())
        else: # Fallback naar A-Z
            log(f"Sorter: Onbekende mappen-sorteermodus '{folder_sort_mode}'. Terugval op A-Z.", xbmc.LOGWARNING)
            return sorted(folders, key=lambda x: os.path.basename(x).lower())