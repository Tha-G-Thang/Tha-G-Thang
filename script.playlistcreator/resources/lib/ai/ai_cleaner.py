import re
import os
import xbmc
from resources.lib.core.base_utils import log, NLTK_DATA_PATH # Importeer NLTK_DATA_PATH

# _nltk_available vlag wordt gezet in de try-except blokken hieronder.
# Deze hoeft niet standaard op False te staan.

try:
    import nltk
    # Voeg NLTK_DATA_PATH toe aan nltk.data.path als het er nog niet is
    # Dit is cruciaal voor het vinden van de gedownloade NLTK data.
    if NLTK_DATA_PATH not in nltk.data.path:
        nltk.data.path.append(NLTK_DATA_PATH)
        log(f"NLTK data path toegevoegd in AICleaner: {NLTK_DATA_PATH}", xbmc.LOGDEBUG)

    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer
    from nltk.tokenize import word_tokenize # expliciet importeren
    
    _nltk_available = True
    log("NLTK succesvol geïmporteerd in AICleaner.", xbmc.LOGDEBUG)
except ImportError as e:
    # Zorg ervoor dat _nltk_available False is bij ImportError
    _nltk_available = False
    log(f"NLTK of een afhankelijkheid (bijv. 'regex') niet gevonden voor AICleaner: {e}. AI opschoning zal beperkt zijn.", xbmc.LOGWARNING)
except Exception as e:
    # Zorg ervoor dat _nltk_available False is bij andere fouten
    _nltk_available = False
    log(f"Algemene fout tijdens NLTK import in AICleaner: {str(e)}. AI opschoning zal beperkt zijn.", xbmc.LOGERROR)

class AICleaner:
    def __init__(self):
        self.stop_words = set()
        self.stemmer = None
        self._initialized_with_nlp = False

        if _nltk_available:
            try:
                # Probeer NLTK data te laden
                nltk.data.find('corpora/stopwords')
                nltk.data.find('tokenizers/punkt') # Vaak nodig voor word_tokenize

                self.stop_words = set(stopwords.words('english'))
                self.stemmer = PorterStemmer()
                self._initialized_with_nlp = True
                log("AICleaner: NLTK componenten (stopwords, stemmer) succesvol geladen.", xbmc.LOGDEBUG)
            except LookupError as e:
                log(f"AICleaner: NLTK data niet gevonden: {str(e)}. Zorg ervoor dat de data is gedownload via add-on instellingen. NLP functionaliteit zal beperkt zijn.", xbmc.LOGWARNING)
                self._initialized_with_nlp = False
            except Exception as e:
                log(f"AICleaner: Fout bij initialiseren van NLTK componenten: {str(e)}. NLP functionaliteit zal beperkt zijn.", xbmc.LOGERROR)
                self._initialized_with_nlp = False
        else:
            log("AICleaner geïnitialiseerd zonder NLTK wegens importfout. NLP functionaliteit zal beperkt zijn.", xbmc.LOGWARNING)

    def clean(self, filename):
        """
        Voert AI-verbeterde opschoning van bestandsnamen uit.
        Gebruikt NLP-technieken (tokenisatie, stopwoordverwijdering, stemming) indien NLTK beschikbaar is.
        Valt terug op basis-opschoning als NLTK niet beschikbaar of geïnitialiseerd is.
        """
        if not _nltk_available or not self._initialized_with_nlp:
            log(f"AICleaner: NLTK niet beschikbaar of geïnitialiseerd. Terugval op basisopschoning voor '{filename}'.", xbmc.LOGDEBUG)
            return self._basic_clean(filename)

        log(f"AICleaner: Start AI-opschoning voor '{filename}'", xbmc.LOGDEBUG)

        # Verwijder bestandsextensie
        name_without_ext = os.path.splitext(filename)[0]
        
        # Tokenize en verwerk woorden
        # Gebruik de 'punkt' tokenizer voor word_tokenize, die moet zijn gedownload
        try:
            tokens = word_tokenize(name_without_ext.lower())
        except LookupError:
            log("AICleaner: 'punkt' tokenizer data niet gevonden. Kan niet tokenizen. Terugval op basisopschoning.", xbmc.LOGWARNING)
            self._initialized_with_nlp = False # Schakel NLP uit voor verdere calls
            return self._basic_clean(filename)
        
        processed_tokens = []
        for word in tokens:
            # Verwijder niet-alfanumerieke tekens en stem
            word = re.sub(r'[^a-z0-9]', '', word)
            if word and word not in self.stop_words and len(word) > 2: # Filter korte woorden en stopwoorden
                if self.stemmer: # Controleer of stemmer geïnitialiseerd is
                    processed_tokens.append(self.stemmer.stem(word))
                else:
                    processed_tokens.append(word) # Gebruik het woord zonder stemming als stemmer ontbreekt
        
        # Reconstructeer betekenisvolle titel
        cleaned_filename = " ".join(processed_tokens).title()
        
        log(f"AICleaner: AI-opschoning toegepast op '{filename}' -> '{cleaned_filename}'", xbmc.LOGDEBUG)
        return cleaned_filename

    def _basic_clean(self, filename):
        """
        Basis bestandsnaamopschoning (bijv. vervangt veelvoorkomende scheidingstekens door spaties).
        Deze methode is nu geïntegreerd voor fallback.
        """
        cleaned_filename = re.sub(r"[._-]", " ", filename).strip()
        cleaned_filename = re.sub(r'\s+', ' ', cleaned_filename).strip()
        log(f"AICleaner: Basis opschoning toegepast op '{filename}' -> '{cleaned_filename}'", xbmc.LOGDEBUG)
        return cleaned_filename