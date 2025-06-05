import os
import xbmc
import re # Nodig voor _preprocess_title
from resources.lib.core.base_utils import log, NLTK_DATA_PATH # Importeer NLTK_DATA_PATH voor nltk.data.path

# _nltk_available en _fuzzywuzzy_available vlaggen worden gezet in de try-except blokken hieronder.
# Deze hoeven niet standaard op False te staan.

try:
    import nltk
    # Voeg NLTK_DATA_PATH toe aan nltk.data.path als het er nog niet is
    # Dit is cruciaal voor het vinden van de gedownloade NLTK data.
    if NLTK_DATA_PATH not in nltk.data.path:
        nltk.data.path.append(NLTK_DATA_PATH)
        log(f"NLTK data path toegevoegd in AISorter: {NLTK_DATA_PATH}", xbmc.LOGDEBUG)

    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer
    from nltk.tokenize import word_tokenize
    _nltk_available = True
    log("NLTK succesvol geïmporteerd in AISorter.", xbmc.LOGDEBUG)
except ImportError as e:
    _nltk_available = False
    log(f"NLTK of een afhankelijkheid niet gevonden voor AISorter: {e}. AI sorteerfunctionaliteit zal beperkt zijn.", xbmc.LOGWARNING)
except Exception as e:
    _nltk_available = False
    log(f"Algemene fout tijdens NLTK import in AISorter: {str(e)}. AI sorteerfunctionaliteit zal beperkt zijn.", xbmc.LOGERROR)

try:
    from thefuzz import fuzz, process
    _fuzzywuzzy_available = True
    log("Fuzzywuzzy succesvol geïmporteerd in AISorter.", xbmc.LOGDEBUG)
except ImportError as e:
    _fuzzywuzzy_available = False
    log(f"Fuzzywuzzy module niet gevonden voor AISorter: {e}. Content-Based sorting zal geen fuzzy matching gebruiken.", xbmc.LOGWARNING)
except Exception as e:
    _fuzzywuzzy_available = False
    log(f"Algemene fout tijdens Fuzzywuzzy import in AISorter: {str(e)}. Content-Based sorting zal geen fuzzy matching gebruiken.", xbmc.LOGERROR)

class AISorter:
    def __init__(self):
        self.stop_words = set()
        self.stemmer = None
        self._initialized_with_nlp = False
        self._initialized_with_fuzzy = _fuzzywuzzy_available # Check fuzzywuzzy beschikbaarheid hier

        if _nltk_available:
            try:
                # Probeer NLTK data te laden
                nltk.data.find('corpora/stopwords')
                nltk.data.find('tokenizers/punkt')

                self.stop_words = set(stopwords.words('english'))
                self.stemmer = PorterStemmer()
                self._initialized_with_nlp = True
                log("AISorter: NLTK componenten (stopwords, stemmer) succesvol geladen.", xbmc.LOGDEBUG)
            except LookupError as e:
                log(f"AISorter: NLTK data niet gevonden: {str(e)}. Zorg ervoor dat de data is gedownload via add-on instellingen. NLP functionaliteit zal beperkt zijn.", xbmc.LOGWARNING)
                self._initialized_with_nlp = False
            except Exception as e:
                log(f"AISorter: Fout bij initialiseren van NLTK componenten: {str(e)}. NLP functionaliteit zal beperkt zijn.", xbmc.LOGERROR)
                self._initialized_with_nlp = False
        else:
            log("AISorter geïnitialiseerd zonder NLTK wegens importfout. NLP functionaliteit zal beperkt zijn.", xbmc.LOGWARNING)

    def sort_by_content(self, files):
        """
        Sorteert bestanden op basis van hun inhoud (titel/bestandsnaam) door clustering.
        Valt terug op alfabetische sortering als NLTK niet beschikbaar is.
        """
        if not _nltk_available or not self._initialized_with_nlp:
            log("AISorter: NLTK niet beschikbaar of geïnitialiseerd. Terugval op alfabetische sortering.", xbmc.LOGWARNING)
            # Fallback naar alfabetische sortering indien AI niet werkt
            return sorted(files, key=lambda x: os.path.basename(x).lower())
        
        log(f"AISorter: Starten met inhoud-gebaseerd sorteren van {len(files)} bestanden.", xbmc.LOGDEBUG)

        # Map om titels te groeperen per voorverwerkte titel
        preprocessed_title_map = {}
        title_to_filepaths = {} # Om originele paden te behouden

        for f in files:
            title = os.path.basename(f)
            preprocessed_title = self._preprocess_title(title)
            
            if preprocessed_title not in preprocessed_title_map:
                preprocessed_title_map[preprocessed_title] = []
            preprocessed_title_map[preprocessed_title].append(title)
            
            # Voeg het originele bestandspad toe aan de lijst voor die titel
            if title not in title_to_filepaths:
                title_to_filepaths[title] = []
            title_to_filepaths[title].append(f)

        # Cluster titels
        clusters = self._cluster_titles(list(preprocessed_title_map.keys()))

        sorted_files = []
        for cluster_titles in clusters:
            # Sorteer binnen elk cluster alfabetisch op originele titel
            sorted_cluster_titles = sorted(cluster_titles, key=lambda x: self._preprocess_title(x).lower())
            for title in sorted_cluster_titles:
                if title in title_to_filepaths:
                    sorted_files.extend(title_to_filepaths[title])
                    del title_to_filepaths[title] # Verwijder verwerkte titels

        # Voeg eventuele overgebleven bestanden toe die niet geclusterd zijn (bijv. singletons)
        remaining_files = []
        for f in files:
            # Als het bestandspad nog steeds in title_to_filepaths zou zitten (wat niet zou moeten na del),
            # of als het nooit in een titelmapping terechtkwam, voeg het dan toe.
            # Eenvoudiger is om te controleren of het al is toegevoegd aan sorted_files.
            if f not in sorted_files:
                remaining_files.append(f)
        
        # Sorteer de overgebleven bestanden alfabetisch
        remaining_files_sorted = sorted(remaining_files, key=lambda x: os.path.basename(x).lower())

        log(f"AISorter: Inhoud-gebaseerd sorteren voltooid. {len(sorted_files)} geclusterd, {len(remaining_files_sorted)} overig.", xbmc.LOGDEBUG)
        return sorted_files + remaining_files_sorted

    def _preprocess_title(self, title):
        """
        Voorbewerkt een titel door tokenisatie, stopwoordverwijdering en stemming.
        """
        if not _nltk_available or not self._initialized_with_nlp:
            return title.lower() # Terugval op eenvoudige lowercase als NLTK niet beschikbaar is

        name_without_ext = os.path.splitext(title)[0]
        try:
            tokens = word_tokenize(name_without_ext.lower())
        except LookupError:
            log("AISorter: 'punkt' tokenizer data niet gevonden. Kan niet tokenizen. Terugval op eenvoudige preprocessie.", xbmc.LOGWARNING)
            self._initialized_with_nlp = False # Schakel NLP uit voor verdere calls
            return name_without_ext.lower()
        
        processed_tokens = []
        for word in tokens:
            word = re.sub(r'[^a-z0-9]', '', word) # Verwijder niet-alfanumerieke tekens
            if word and word not in self.stop_words and len(word) > 2: # Filter korte woorden en stopwoorden
                if self.stemmer:
                    processed_tokens.append(self.stemmer.stem(word))
                else:
                    processed_tokens.append(word)
        return " ".join(processed_tokens)

    def _cluster_titles(self, preprocessed_titles, threshold=75):
        """
        Clustert titels op basis van fuzzy matching.
        """
        if not self._initialized_with_fuzzy:
            log("AISorter: Fuzzywuzzy niet beschikbaar. Kan titels niet clusteren. Elk item krijgt een eigen cluster.", xbmc.LOGWARNING)
            return [[title] for title in preprocessed_titles] # Elk item is zijn eigen cluster

        log(f"AISorter: Starten met clusteren van {len(preprocessed_titles)} titels.", xbmc.LOGDEBUG)
        clusters = []
        
        # Houd bij welke titels al geclusterd zijn
        processed_indices = set()

        for i, title1 in enumerate(preprocessed_titles):
            if i in processed_indices:
                continue

            current_cluster = [title1]
            processed_indices.add(i)

            for j, title2 in enumerate(preprocessed_titles):
                if j in processed_indices:
                    continue

                # Gebruik token_set_ratio voor betere vergelijking van strings met verschillende volgorde/lengte
                score = fuzz.token_set_ratio(title1, title2)
                
                if score >= threshold:
                    current_cluster.append(title2)
                    processed_indices.add(j)
            
            clusters.append(current_cluster)
        
        log(f"AISorter: Clusteren voltooid. Aantal clusters: {len(clusters)}", xbmc.LOGDEBUG)
        return clusters