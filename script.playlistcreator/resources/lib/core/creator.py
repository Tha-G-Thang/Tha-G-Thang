import xbmc
import xbmcgui
import xbmcvfs
import time
import os
from datetime import datetime

from resources.lib.core.base_utils import log, get_setting, get_bool_setting, ADDON
from resources.lib.core.cleaner import Cleaner
from resources.lib.core.scanner import Scanner
from resources.lib.core.sorter import Sorter
from resources.lib.constants import PLAYLIST_DIR, VIDEO_EXTS # Importeer PLAYLIST_DIR en VIDEO_EXTS
from resources.lib.utils import format_duration_seconds # Nieuwe import voor duurformattering

# Import AITagger conditionally
_ai_tagger_instance = None
if get_bool_setting("enable_ai") and get_bool_setting("ai_auto_tagging"):
    try:
        from resources.lib.core.ai.ai_tagger import AITagger
        _ai_tagger_instance = AITagger()
        log("AITagger instance succesvol geladen in creator.py.", xbmc.LOGDEBUG)
    except ImportError as e:
        log(f"AITagger module niet gevonden: {e}. Automatische tagging zal niet beschikbaar zijn.", xbmc.LOGWARNING)
        _ai_tagger_instance = None
    except Exception as e:
        log(f"Fout bij laden van AITagger in creator.py: {str(e)}. AI tagging uitgeschakeld.", xbmc.LOGERROR)
        _ai_tagger_instance = None
else:
    log("AI Auto Tagging of algemene AI is uitgeschakeld. AITagger zal niet worden gebruikt.", xbmc.LOGINFO)

# Import AIMetadataEnhancer conditionally
_ai_metadata_enhancer_instance = None
if get_bool_setting("enable_ai") and get_bool_setting("ai_metadata_enhance"):
    try:
        from resources.lib.core.ai.ai_metadata import AIMetadataEnhancer
        _ai_metadata_enhancer_instance = AIMetadataEnhancer()
        log("AIMetadataEnhancer instance succesvol geladen in creator.py.", xbmc.LOGDEBUG)
    except ImportError as e:
        log(f"AIMetadataEnhancer module niet gevonden: {e}. AI metadata-verbetering zal niet beschikbaar zijn.", xbmc.LOGWARNING)
        _ai_metadata_enhancer_instance = None
    except Exception as e:
        log(f"Fout bij laden van AIMetadataEnhancer in creator.py: {str(e)}. AI metadata-verbetering uitgeschakeld.", xbmc.LOGERROR)
else:
    log("AI Metadata Enhancement of algemene AI is uitgeschakeld. AIMetadataEnhancer zal niet worden gebruikt.", xbmc.LOGINFO)

class PlaylistCreator:
    def __init__(self):
        self.scanner = Scanner()
        self.cleaner = Cleaner()
        self.sorter = Sorter()
        # Zorg ervoor dat de PLAYLIST_DIR bestaat
        if not xbmcvfs.exists(PLAYLIST_DIR):
            xbmcvfs.mkdirs(PLAYLIST_DIR)
            log(f"Playlist map '{PLAYLIST_DIR}' aangemaakt.", xbmc.LOGINFO)

    def select_folder_source(self):
        """
        Opent een dialoogvenster voor de gebruiker om een videobron of map te selecteren,
        specifiek gericht op videobronnen.
        """
        dialog = xbmcgui.Dialog()
        chosen_folder = dialog.browse(
            type=3,  # xbmcgui.FileBrowser.DIRS_SHOW_AND_SELECT_DIRECTORY | xbmcgui.FileBrowser.FILTER_VIDEO
            heading="Selecteer een videobron of map",
            mask="", # Geen specifiek bestandstype filter nodig voor mappen
            option="ShowAndSelectDirectory",
            shareddir="videofiles" # Dit zorgt ervoor dat het begint bij uw geconfigureerde videobronnen
        )
        log(f"Gebruiker heeft gekozen: {chosen_folder}", xbmc.LOGDEBUG)
        return chosen_folder

    def _get_file_info(self, file_path):
        """
        Haalt gedetailleerde informatie op over een bestand, inclusief duur, en schone namen.
        """
        file_info = {}
        try:
            # Decodeer de URL om lokale paden correct te hanteren
            decoded_path = xbmcvfs.translatePath(file_path)
            
            stat_info = xbmcvfs.Stat(decoded_path)
            
            file_info['path'] = file_path
            file_info['filename'] = os.path.basename(decoded_path)
            file_info['size'] = stat_info.st_size()
            file_info['last_modified_date'] = datetime.fromtimestamp(stat_info.st_mtime()).strftime('%Y-%m-%d')
            
            # Duur standaard op 0, AI kan dit eventueel bijwerken
            file_info['duration'] = 0 

            # Opschonen van de bestandsnaam
            file_info['cleaned_filename'] = self.cleaner.clean_filename(file_info['filename'])

            # Opschonen van de mapnaam
            folder_path_only = os.path.dirname(decoded_path)
            folder_name = os.path.basename(folder_path_only)
            file_info['cleaned_folder_name'] = self.cleaner.clean_filename(folder_name)

            # AI Metadata Enhancement (indien ingeschakeld)
            if get_bool_setting("enable_ai") and get_bool_setting("ai_metadata_enhance") and _ai_metadata_enhancer_instance:
                # AIMetadataEnhancer kan de duur vinden
                enhanced_metadata = _ai_metadata_enhancer_instance.enhance_metadata(file_path, file_info['cleaned_filename'])
                file_info.update(enhanced_metadata) # Overwrite of voeg toe
                if 'duration' in enhanced_metadata and enhanced_metadata['duration'] > 0:
                    file_info['duration'] = enhanced_metadata['duration']
                    log(f"Duur bijgewerkt via AI: {file_info['duration']} voor {file_info['filename']}", xbmc.LOGDEBUG)

            # AI Auto Tagging (indien ingeschakeld)
            if get_bool_setting("enable_ai") and get_bool_setting("ai_auto_tagging") and _ai_tagger_instance:
                tags = _ai_tagger_instance.generate_tags(file_info['cleaned_filename'])
                file_info['tags'] = tags
            else:
                file_info['tags'] = []

            log(f"Bestandsinfo voor '{file_info['filename']}': {file_info}", xbmc.LOGDEBUG)
            return file_info

        except Exception as e:
            log(f"Fout bij ophalen bestandsinfo voor '{file_path}': {str(e)}", xbmc.LOGWARNING)
            return None

    def generate_playlist_file(self, folders, playlist_name="Generated_Playlist"):
        """
        Genereert een M3U afspeellijstbestand op basis van de gescande mappen en instellingen,
        inclusief EXTINF tags met geschoonde map- en bestandsnamen en Kodi-kleurtags.
        """
        log(f"Start genereren van afspeellijst '{playlist_name}' voor mappen: {folders}", xbmc.LOGINFO)
        all_files = []
        dialog = xbmcgui.DialogProgressBG() # Gebruik Background Progress Dialog

        try:
            total_folders = len(folders)
            for i, folder in enumerate(folders):
                if dialog.isCancelled():
                    log("Afspeellijst generatie geannuleerd door gebruiker.", xbmc.LOGINFO)
                    break
                dialog.update(int((i / total_folders) * 100), f"Scannen map {i+1}/{total_folders}:", os.path.basename(folder))
                
                scanned_files = self.scanner.scan(folder)
                all_files.extend(scanned_files)
                log(f"Gescande bestanden in '{folder}': {len(scanned_files)}", xbmc.LOGDEBUG)

            if dialog.isCancelled():
                dialog.close()
                xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Afspeellijst generatie geannuleerd.", xbmcgui.NOTIFICATION_WARNING, 3000)
                return

            log(f"Totaal {len(all_files)} bestanden gevonden na scan.", xbmc.LOGINFO)

            # Sorteer de bestanden
            if all_files:
                show_busy_dialog("Bestanden sorteren...")
                sorted_files_paths = self.sorter.sort(all_files)
                hide_busy_dialog()
                log(f"Totaal {len(sorted_files_paths)} bestanden na sorteren.", xbmc.LOGINFO)
            else:
                xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Geen bestanden gevonden om afspeellijst te maken.", xbmcgui.NOTIFICATION_WARNING, 4000)
                log("Geen bestanden gevonden, afspeellijst niet gegenereerd.", xbmc.LOGWARNING)
                dialog.close()
                return

            # Bepaal het pad van de afspeellijst
            playlist_filename = f"{playlist_name}.m3u"
            playlist_path = xbmcvfs.translatePath(os.path.join(PLAYLIST_DIR, playlist_filename))
            
            # --- Backup bestaande afspeellijst ---
            backup_dir = xbmcvfs.translatePath(os.path.join(PLAYLIST_DIR, "backups"))
            if not xbmcvfs.exists(backup_dir):
                xbmcvfs.mkdirs(backup_dir)
                log(f"Backup map '{backup_dir}' aangemaakt.", xbmc.LOGINFO)

            if xbmcvfs.exists(playlist_path):
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                backup_filename = f"{playlist_name}_{timestamp}.m3u"
                backup_path = os.path.join(backup_dir, backup_filename)
                
                # Probeer te hernoemen, anders kopiëren en dan origineel verwijderen
                if xbmcvfs.rename(playlist_path, backup_path):
                    log(f"Bestaande afspeellijst '{playlist_filename}' verplaatst naar '{backup_filename}'.", xbmc.LOGINFO)
                else:
                    log(f"Kon afspeellijst '{playlist_filename}' niet hernoemen. Probeer te kopiëren.", xbmc.LOGWARNING)
                    if xbmcvfs.copy(playlist_path, backup_path):
                        xbmcvfs.delete(playlist_path)
                        log(f"Bestaande afspeellijst '{playlist_filename}' gekopieerd naar '{backup_filename}' en origineel verwijderd.", xbmc.LOGINFO)
                    else:
                        log(f"Kon afspeellijst '{playlist_filename}' niet kopiëren of verwijderen. Kan de nieuwe playlist niet aanmaken zonder overschrijven.", xbmc.LOGERROR)
                        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Kon bestaande afspeellijst niet veilig opslaan. Annuleer.", xbmcgui.NOTIFICATION_ERROR, 5000)
                        dialog.close()
                        return
            # --- Einde Backup logica ---

            # Schrijf de afspeellijst
            playlist_content = ["#EXTM3U"] # Start met de M3U header
            
            # Haal instellingen voor de display op
            show_folder_names_in_playlist = get_bool_setting("show_folder_names_in_playlist")
            playlist_folder_name_color_str = get_setting("playlist_folder_name_color", "green") # Standaard groen
            playlist_folder_name_position_idx = int(get_setting("playlist_folder_name_position", "0")) # 0 = Voor, 1 = Achter

            show_busy_dialog("Afspeellijst schrijven...")
            for file_path in sorted_files_paths:
                file_info = self._get_file_info(file_path)
                if file_info:
                    # Construct de titel voor de EXTINF tag
                    title_parts = []
                    
                    # Voeg de mapnaam toe met kleurtags indien ingesteld
                    if show_folder_names_in_playlist and file_info['cleaned_folder_name']:
                        colored_folder_name = f"[COLOR {playlist_folder_name_color_str.upper()}]{file_info['cleaned_folder_name']}[/COLOR]"
                        
                        if playlist_folder_name_position_idx == 0: # Voor
                            title_parts.append(colored_folder_name)
                        else: # Achter
                            # We voegen het later toe aan de titel
                            pass

                    # Voeg de schone bestandsnaam toe
                    title_parts.append(file_info['cleaned_filename'])

                    # Als de mapnaam 'achter' moest, voeg deze nu toe
                    if show_folder_names_in_playlist and file_info['cleaned_folder_name'] and playlist_folder_name_position_idx == 1: # Achter
                        title_parts.append(colored_folder_name)

                    # Voeg een spatie tussen de delen
                    display_title = " ".join(title_parts)

                    # Formatteer de duur voor de EXTINF tag (duur in seconden, als string)
                    # We gebruiken hier een ruwe duur of 0, zoals afgesproken
                    duration_str = str(int(file_info.get('duration', 0)))

                    # Voeg de EXTINF tag en het bestandspad toe
                    playlist_content.append(f"#EXTINF:{duration_str},{display_title}")
                    playlist_content.append(file_info['path'])
                else:
                    log(f"Bestand '{file_path}' overgeslagen door ontbrekende info.", xbmc.LOGWARNING)

            # Schrijf naar bestand
            if xbmcvfs.File(playlist_path, 'w').write("\n".join(playlist_content)):
                log(f"Afspeellijst succesvol geschreven naar: {playlist_path}", xbmc.LOGINFO)
                xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Afspeellijst '{playlist_name}' gegenereerd!", xbmcgui.NOTIFICATION_INFO, 5000)
            else:
                log(f"Fout bij schrijven van afspeellijst naar: {playlist_path}", xbmc.LOGERROR)
                xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Fout bij genereren afspeellijst.", xbmcgui.NOTIFICATION_ERROR, 5000)

        except Exception as e:
            log(f"Fout bij genereren van afspeellijst: {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Algemene fout: {str(e)}", xbmcgui.NOTIFICATION_ERROR, 7000)
        finally:
            dialog.close() # Sluit de achtergronddialoog altijd
            hide_busy_dialog() # Verberg de 'Busy' dialoog