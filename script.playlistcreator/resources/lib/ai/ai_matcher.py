from thefuzz import fuzz # Ensure fuzzywuzzy is installed and thefuzz is accessible
from resources.lib.core.base_utils import log # Use base_utils log for consistency
import xbmc # Added for logging levels

class AIMatcher:
    def match(self, input_str, candidates):
        """
        Vindt de beste fuzzy match voor een invoerstring uit een lijst van kandidaten.
        Args:
            input_str (str): De string die gematcht moet worden.
            candidates (list): Een lijst van mogelijke match-strings.
        Returns:
            tuple: Een tuple (beste_match_string, score) of (None, 0) als geen kandidaten.
        """
        if not candidates:
            log("AIMatcher: Geen kandidaten om mee te matchen.", xbmc.LOGDEBUG)
            return None, 0

        # Gebruik fuzz.ratio voor een eenvoudige vergelijking, of een andere scorer zoals fuzz.token_set_ratio
        scores = {candidate: fuzz.ratio(input_str, candidate) for candidate in candidates}
        
        best_match = None
        highest_score = 0
        
        if scores:
            best_match, highest_score = max(scores.items(), key=lambda x: x[1])
            log(f"AIMatcher: Beste fuzzy match voor '{input_str}': '{best_match}' met score {highest_score}", xbmc.LOGDEBUG)
        else:
            log(f"AIMatcher: Geen matches gevonden voor '{input_str}'", xbmc.LOGDEBUG)
            
        return best_match, highest_score