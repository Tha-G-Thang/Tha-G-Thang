from sentence_transformers import SentenceTransformer
import numpy as np
from resources.lib.utils import log

class AIQuery:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def search(self, query, corpus):
        query_vec = self.model.encode([query])[0]
        corpus_vecs = self.model.encode(corpus)
        scores = np.dot(corpus_vecs, query_vec)
        best = corpus[np.argmax(scores)]
        log(f"Query '{query}' best match: {best}")
        return best