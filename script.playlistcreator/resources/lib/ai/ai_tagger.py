import re
import xbmc
from resources.lib.core.base_utils import log, NLTK_DATA_PATH # Importeer NLTK_DATA_PATH

# _nltk_available vlag wordt gezet in de try-except blokken hieronder.
# Deze hoeft niet standaard op False te staan.

try:
    import nltk
    # Voeg NLTK_DATA_PATH toe aan nltk.data.path als het er nog niet is
    if NLTK_DATA_PATH not in nltk.data.path:
        nltk.data.path.append(NLTK_DATA_PATH)
        log(f"NLTK data path toegevoegd in AITagger: {NLTK_DATA_PATH}", xbmc.LOGDEBUG)

    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.probability import FreqDist
    # Optioneel: POS-tagging (voor geavanceerdere tagging)
    # from nltk.tag import pos_tag
    # from nltk.chunk import ne_chunk # Voor Named Entity Recognition
    
    _nltk_available = True
    log("NLTK succesvol geïmporteerd in AITagger.", xbmc.LOGDEBUG)
except ImportError as e:
    _nltk_available = False
    log(f"NLTK of een afhankelijkheid niet gevonden voor AITagger: {e}. Automatische tagging zal worden uitgeschakeld.", xbmc.LOGWARNING)
except Exception as e:
    _nltk_available = False
    log(f"Algemene fout tijdens NLTK import in AITagger: {str(e)}. Automatische tagging zal worden uitgeschakeld.", xbmc.LOGERROR)

class AITagger:
    def __init__(self):
        self.stop_words = set()
        self._initialized_with_nlp = False

        if _nltk_available:
            try:
                # Probeer NLTK data te laden
                nltk.data.find('corpora/stopwords')
                nltk.data.find('tokenizers/punkt')
                # nltk.data.find('taggers/averaged_perceptron_tagger') # Voor pos_tag als gebruikt
                # nltk.data.find('chunkers/maxent_ne_chunker') # Voor ne_chunk als gebruikt
                # nltk.data.find('corpora/words') # Ook vaak nuttig

                self.stop_words = set(stopwords.words('english'))
                self._initialized_with_nlp = True
                log("AITagger: NLTK componenten (stopwords, punkt) succesvol geladen.", xbmc.LOGDEBUG)
            except LookupError as e:
                log(f"AITagger: NLTK data niet gevonden: {str(e)}. Zorg ervoor dat de data is gedownload via add-on instellingen. NLP functionaliteit zal beperkt zijn.", xbmc.LOGWARNING)
                self._initialized_with_nlp = False
            except Exception as e:
                log(f"AITagger: Fout bij initialiseren van NLTK componenten: {str(e)}. NLP functionaliteit zal beperkt zijn.", xbmc.LOGERROR)
                self._initialized_with_nlp = False
        else:
            log("AITagger geïnitialiseerd zonder NLTK wegens importfout. NLP functionaliteit zal beperkt zijn.", xbmc.LOGWARNING)

    def generate_tags(self, text, num_tags=5):
        """
        Genereert relevante tags uit een tekststring.
        Gebruikt NLP-technieken (tokenisatie, stopwoordverwijdering, frequentieanalyse) indien NLTK beschikbaar is.
        """
        log(f"AITagger: Bezig met genereren van tags voor '{text}'", xbmc.LOGDEBUG)

        if not _nltk_available or not self._initialized_with_nlp:
            log("AITagger: NLTK niet beschikbaar, AI tagging onmogelijk. Retourneer lege tags.", xbmc.LOGWARNING)
            return []

        # Basis opschoning van de tekst
        cleaned_text = re.sub(r'[^a-zA-Z0-9\s]', '', text).lower()
        
        try:
            tokens = word_tokenize(cleaned_text)
        except LookupError:
            log("AITagger: 'punkt' tokenizer data niet gevonden. Kan niet tokenizen. Retourneer lege tags.", xbmc.LOGWARNING)
            self._initialized_with_nlp = False # Schakel NLP uit voor verdere calls
            return []
        
        # Filter stopwoorden en korte/niet-alfabetische tokens
        filtered_tokens = [
            word for word in tokens 
            if word not in self.stop_words and len(word) > 2 and word.isalpha()
        ]
        
        if not filtered_tokens:
            log("AITagger: Geen relevante woorden gevonden voor tagging.", xbmc.LOGDEBUG)
            return []

        # Frequentieanalyse
        fdist = FreqDist(filtered_tokens)
        
        # Haal de meest voorkomende woorden op als tags
        tags = [word for word, _ in fdist.most_common(num_tags)]
        
        log(f"AITagger: Tags gegenereerd voor '{text}': {tags}", xbmc.LOGDEBUG)
        return tags