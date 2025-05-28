import os
import xbmc
from resources.lib.utils import (
    get_bool_setting,
    get_int_setting,
    get_setting,
    log
)

class Sorter:
    def sort(self, file_list):
        """
        Hoofdsorteerfunctie die alle instellingen verwerkt
        """
        try:
            # Stap 1: Sorteer alle bestanden (basis)
            sorted_files = self._basic_sort(file_list)
            
            # Stap 2: Pas folderlimits toe indien ingeschakeld
            if get_bool_setting("limit_files_per_folder"):
                max_files = get_int_setting("max_files_per_folder")
                prioritize_new = get_bool_setting("prioritize_new_files")
                sorted_files = self._apply_folder_limits(sorted_files, max_files, prioritize_new)
                
            return sorted_files
            
        except Exception as e:
            log(f"Sorting error: {str(e)}", xbmc.LOGERROR)
            return file_list  # Fallback naar originele lijst bij fouten

    def _basic_sort(self, files):
        """Basis sortering op bestandsnaam of datum"""
        sort_mode = get_setting("sort_mode", "name")  # 'name' of 'date'
        
        if sort_mode == "date":
            return sorted(files, key=lambda x: os.path.getmtime(x), reverse=True)
        else:  # Standaard op naam
            return sorted(files, key=lambda x: os.path.basename(x).lower())

    def _apply_folder_limits(self, files, max_files, prioritize_new):
        """
        Past folderlimits toe met optionele nieuwe-bestanden-eerst prioritering
        """
        folder_dict = {}
        
        # Groepeer per folder
        for filepath in files:
            folder = os.path.dirname(filepath)
            folder_dict.setdefault(folder, []).append(filepath)
        
        # Sorteer folders en pas limits toe
        result = []
        for folder, folder_files in folder_dict.items():
            # Sorteer bestanden binnen folder
            if prioritize_new:
                folder_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            else:
                folder_files.sort(key=lambda x: os.path.basename(x).lower())
                
            # Neem maximaal toegestane aantal
            result.extend(folder_files[:max_files])
            
        return result

    def format_display_name(self, filepath):
        """Voeg foldernaam toe met kleur indien ingeschakeld"""
        if not get_bool_setting("show_folder_names"):
            return os.path.basename(filepath)
            
        folder = os.path.basename(os.path.dirname(filepath))
        color = get_setting("folder_name_color", "blue")
        return f"[COLOR {color}]{folder}[/COLOR]/{os.path.basename(filepath)}"