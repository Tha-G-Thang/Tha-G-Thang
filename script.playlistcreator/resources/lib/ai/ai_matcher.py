from thefuzz import fuzz
from resources.lib.utils import log

class AIMatcher:
    def match(self, input_str, candidates):
        scores = {candidate: fuzz.ratio(input_str, candidate) for candidate in candidates}
        best = max(scores.items(), key=lambda x: x[1])
        log(f"Best fuzzy match for '{input_str}': {best}")
        return best