from keybert import KeyBERT
from resources.lib.utils import log

class AITagger:
    def __init__(self):
        self.model = KeyBERT()

    def generate_tags(self, text):
        tags = self.model.extract_keywords(text, keyphrase_ngram_range=(1, 2))
        log(f"Generated tags for '{text}': {tags}")
        return tags