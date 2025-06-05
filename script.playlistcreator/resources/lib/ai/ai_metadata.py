import re
import os
import xbmc
from datetime import datetime # Added for datetime.fromtimestamp
from resources.lib.core.base_utils import log

# _dateutil_available vlag wordt gezet in de try-except blokken hieronder.
# Deze hoeft niet standaard op False te staan.

_dateutil_available = False
try:
    import dateutil.parser as parser
    _dateutil_available = True
    log("dateutil.parser succesvol geïmporteerd in AIMetadataEnhancer.", xbmc.LOGDEBUG)
except ImportError as e:
    _dateutil_available = False
    log(f"dateutil.parser module niet gevonden voor AIMetadataEnhancer: {e}. Datumparsen zal beperkt zijn.", xbmc.LOGWARNING)
except Exception as e:
    _dateutil_available = False
    log(f"Algemene fout tijdens dateutil import in AIMetadataEnhancer: {str(e)}. Datumparsen zal beperkt zijn.", xbmc.LOGERROR)

# Mutagen is declared as a module dependency in addon.xml, but keep the try-except for robustness
_mutagen_available = False
try:
    from mutagen import File as AudioFile
    _mutagen_available = True
    log("Mutagen succesvol geïmporteerd in AIMetadataEnhancer.", xbmc.LOGDEBUG)
except ImportError as e:
    _mutagen_available = False
    log(f"Mutagen module niet gevonden voor AIMetadataEnhancer: {e}. Audio metadata-extractie zal worden uitgeschakeld.", xbmc.LOGWARNING)
except Exception as e:
    _mutagen_available = False
    log(f"Algemene fout tijdens Mutagen import in AIMetadataEnhancer: {str(e)}. Audio metadata-extractie zal worden uitgeschakeld.", xbmc.LOGERROR)


class AIMetadataEnhancer:
    def __init__(self):
        log("AIMetadataEnhancer geïnitialiseerd.")
        self._initialized_with_dateutil = _dateutil_available # Gebruik de globale vlag
        self._initialized_with_mutagen = _mutagen_available # Gebruik de globale vlag

    def enhance_metadata(self, file_path, current_metadata):
        """
        Verrijkt metadata met AI-technieken, zoals datumextractie uit bestandsnamen.
        Args:
            file_path (str): Het volledige pad naar het bestand.
            current_metadata (dict): Bestaande metadata (bijv. van os.stat).
        Returns:
            dict: De verrijkte metadata.
        """
        log(f"AIMetadataEnhancer: Bezig met verrijken van metadata voor '{file_path}'", xbmc.LOGDEBUG)
        metadata = dict(current_metadata) # Maak een kopie om te bewerken

        filename = os.path.basename(file_path)
        name_without_ext = os.path.splitext(filename)[0]

        # Datumextractie met dateutil.parser
        if self._initialized_with_dateutil:
            # Probeer een datum te extraheren uit de bestandsnaam
            # Zoek naar veelvoorkomende datumformaten (YYYY-MM-DD, DD-MM-YYYY, YYYYMMDD, etc.)
            date_patterns = [
                r'\b(\d{4}[-/_]\d{2}[-/_]\d{2})\b',  # YYYY-MM-DD
                r'\b(\d{2}[-/_]\d{2}[-/_]\d{4})\b',  # DD-MM-YYYY
                r'\b(\d{4}\d{2}\d{2})\b',            # YYYYMMDD
                r'\b(\d{2}\d{2}\d{4})\b',            # DDMMYYYY
                r'\b(\d{4}[.]\d{2}[.]\d{2})\b',      # YYYY.MM.DD
                r'\b(\d{1,2}(?:st|nd|rd|th)?\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s\d{4})\b', # 1st Jan 2023
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s\d{1,2}(?:st|nd|rd|th)?(?:,)?\s\d{4}\b', # Jan 1, 2023
                r'\b(\d{4})\b',                      # Alleen jaar (als laatste redmiddel en contextueel, anders te breed)
            ]
            
            extracted_date_str = None
            for pattern in date_patterns:
                match = re.search(pattern, name_without_ext, re.IGNORECASE)
                if match:
                    extracted_date_str = match.group(1).replace('_', '-').replace('/', '-') # Normaliseer scheidingstekens
                    break

            if extracted_date_str:
                try:
                    # Gebruik dateutil.parser om de gedetecteerde datumstring te parsen
                    # fuzzy=True laat het parsen van onvolledige of "vieze" strings toe
                    # dayfirst=False (standaard) of True, afhankelijk van voorkeursformaat.
                    # Voor algemene parsing, laat dayfirst op default.
                    parsed_date = parser.parse(extracted_date_str, fuzzy=True) 
                    metadata['date'] = parsed_date.strftime('%Y-%m-%d')
                    log(f"AIMetadataEnhancer: Datum '{metadata['date']}' geëxtraheerd uit '{file_path}' via dateutil.", xbmc.LOGDEBUG)
                except Exception as e:
                    log(f"AIMetadataEnhancer: Fout bij parsen van gedetecteerde datum '{extracted_date_str}' uit '{file_path}': {str(e)}", xbmc.LOGWARNING)
            else:
                log(f"AIMetadataEnhancer: Geen duidelijk datumformaat gevonden in '{name_without_ext}'.", xbmc.LOGDEBUG)

        # Probeer audio metadata te extraheren met mutagen (als beschikbaar)
        if self._initialized_with_mutagen:
            try:
                # Mutagen werkt op lokale bestandspaden, dus we moeten xbmcvfs.translatePath gebruiken
                local_file_path = xbmc.translatePath(file_path)
                audio = AudioFile(local_file_path)
                if audio:
                    if 'title' in audio and audio['title']:
                        metadata['title'] = str(audio['title'])
                        log(f"AIMetadataEnhancer: Titel '{metadata['title']}' geëxtraheerd met Mutagen.", xbmc.LOGDEBUG)
                    if 'artist' in audio and audio['artist']:
                        metadata['artist'] = str(audio['artist'])
                        log(f"AIMetadataEnhancer: Artiest '{metadata['artist']}' geëxtraheerd met Mutagen.", xbmc.LOGDEBUG)
                    if 'length' in audio.info:
                        metadata['duration'] = int(audio.info.length) # Duur in seconden
                        log(f"AIMetadataEnhancer: Duur '{metadata['duration']}' geëxtraheerd met Mutagen.", xbmc.LOGDEBUG)
            except Exception as e:
                log(f"AIMetadataEnhancer: Fout bij extraheren van audio metadata uit '{file_path}' met Mutagen: {str(e)}", xbmc.LOGWARNING)
        else:
            log("AIMetadataEnhancer: Mutagen niet beschikbaar voor audio metadata extractie.", xbmc.LOGDEBUG)

        return metadata