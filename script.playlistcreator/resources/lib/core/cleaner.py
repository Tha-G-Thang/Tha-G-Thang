import re
import xbmc
import urllib.parse
from resources.lib.core.base_utils import log, get_bool_setting, get_setting

_ai_cleaner_instance = None
# Conditioneel importeren van AICleaner
# De AICleaner wordt alleen geïmporteerd en geïnitialiseerd als zowel enable_ai als ai_title_cleaning True zijn.
# Dit voorkomt onnodige importfouten en resourceverbruik.
if get_bool_setting("enable_ai") and get_bool_setting("ai_title_cleaning"):
    try:
        from resources.lib.core.ai.ai_cleaner import AICleaner
        _ai_cleaner_instance = AICleaner()
        log("AICleaner instance succesvol geladen in cleaner.py.", xbmc.LOGDEBUG)
    except ImportError as e:
        log(f"AICleaner module niet gevonden: {e}. AI bestandsnaam opschoning zal niet beschikbaar zijn.", xbmc.LOGWARNING)
        _ai_cleaner_instance = None
    except Exception as e:
        log(f"Fout bij initialiseren van AICleaner in cleaner.py: {str(e)}. AI cleaning uitgeschakeld.", xbmc.LOGERROR)
        _ai_cleaner_instance = None
else:
    log("AI Title Cleaning of algemene AI is uitgeschakeld. AICleaner zal niet worden gebruikt.", xbmc.LOGINFO)

class Cleaner:
    def __init__(self):
        pass

    def clean_filename(self, filename):
        """
        Reinigt een bestandsnaam, optioneel met AI-verbeterde methoden.
        Args:
            filename (str): De te reinigen bestandsnaam.
        Returns:
            str: De gereinigde bestandsnaam.
        """
        # Bestandsnaam decoderen voor Kodi compatibiliteit
        decoded_filename = urllib.parse.unquote(filename)

        # Gebruik AI opschoning als de instellingen dit toelaten en de AI-module is geladen
        if get_bool_setting("enable_ai") and get_bool_setting("ai_title_cleaning") and _ai_cleaner_instance:
            log(f"cleaner.py: Gebruik van AI-verbeterde opschoning voor '{decoded_filename}'", xbmc.LOGDEBUG)
            return self._ai_enhanced_clean(decoded_filename)
        else:
            log(f"cleaner.py: Gebruik van basis-opschoning voor '{decoded_filename}'", xbmc.LOGDEBUG)
            return self._basic_clean(decoded_filename)

    def _basic_clean(self, filename):
        """
        Voert een basisopschoning uit op de bestandsnaam (vervangt scheidingstekens, verwijdert extra spaties).
        """
        cleaned_filename = re.sub(r"[._-]", " ", filename).strip()
        cleaned_filename = re.sub(r'\s+', ' ', cleaned_filename).strip()
        log(f"Cleaner: Basis opschoning toegepast op '{filename}' -> '{cleaned_filename}'", xbmc.LOGDEBUG)
        return cleaned_filename

    def _ai_enhanced_clean(self, filename):
        """
        Roept de AI-schoonmaker aan als deze beschikbaar is, anders valt het terug op de basisopschoning.
        """
        if _ai_cleaner_instance:
            try:
                cleaned_name = _ai_cleaner_instance.clean(filename)
                log(f"Cleaner: AI-verbeterde opschoning toegepast op '{filename}' -> '{cleaned_name}' (via AICleaner)", xbmc.LOGDEBUG)
                return cleaned_name
            except Exception as e:
                log(f"Fout bij AI-verbeterde opschoning van '{filename}': {str(e)}. Terugval naar basisopschoning.", xbmc.LOGERROR)
                return self._basic_clean(filename)
        else:
            # Dit pad zou niet bereikt moeten worden als de initiële check correct is,
            # maar dient als extra veiligheid.
            log(f"Cleaner: AICleaner instance niet beschikbaar voor '{filename}'. Terugval naar basisopschoning.", xbmc.LOGWARNING)
            return self._basic_clean(filename)