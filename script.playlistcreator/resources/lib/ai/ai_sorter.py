from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from resources.lib.utils import log

class AISorter:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def cluster_titles(self, titles, n_clusters=3):
        embeddings = self.model.encode(titles)
        labels = KMeans(n_clusters=n_clusters).fit_predict(embeddings)
        log(f"Clustered {len(titles)} titles into {n_clusters} groups.")
        return dict(zip(titles, labels))