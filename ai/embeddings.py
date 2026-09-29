import os
import sys
from typing import List, Dict, Union
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

# Append parent dir for config
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.app.config import settings

class EmbeddingPipeline:
    def __init__(self):
        self.model_name = settings.MODEL_NAME
        self.model = None
        # Simple in-memory cache for demo purposes
        self._cache: Dict[str, np.ndarray] = {}

    def _load_model(self):
        if self.model is None and SentenceTransformer is not None:
            # Can be configured to load from MODEL_PATH if offline
            self.model = SentenceTransformer(self.model_name)

    def preprocess(self, text: str) -> str:
        # Basic preprocessing: lowercasing, stripping extra whitespace
        return " ".join(text.lower().split())

    def get_embedding(self, text: str) -> np.ndarray:
        clean_text = self.preprocess(text)
        
        if clean_text in self._cache:
            return self._cache[clean_text]
            
        self._load_model()
        if self.model is None:
            # Fallback if sentence-transformers isn't installed
            emb = np.random.rand(384)
            self._cache[clean_text] = emb
            return emb
            
        emb = self.model.encode(clean_text)
        self._cache[clean_text] = emb
        return emb

    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        return np.array([self.get_embedding(t) for t in texts])

    def calculate_similarity(self, text1: str, text2: str) -> float:
        emb1 = self.get_embedding(text1).reshape(1, -1)
        emb2 = self.get_embedding(text2).reshape(1, -1)
        return float(cosine_similarity(emb1, emb2)[0][0])

    def nearest_neighbors(self, query: str, corpus: List[str], top_k: int = 5) -> List[Dict[str, Union[str, float]]]:
        if not corpus:
            return []
            
        query_emb = self.get_embedding(query).reshape(1, -1)
        corpus_embs = self.get_embeddings(corpus)
        
        similarities = cosine_similarity(query_emb, corpus_embs)[0]
        
        # Sort by similarity descending
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append({
                "text": corpus[idx],
                "similarity": float(similarities[idx])
            })
            
        return results

    def cluster_texts(self, texts: List[str], eps: float = 0.3, min_samples: int = 2) -> Dict[int, List[str]]:
        if len(texts) < min_samples:
            return {-1: texts}
            
        embs = self.get_embeddings(texts)
        
        # Using 1 - cosine_similarity as distance metric
        distance_matrix = 1 - cosine_similarity(embs)
        
        clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="precomputed")
        labels = clustering.fit_predict(distance_matrix)
        
        clusters = {}
        for i, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(texts[i])
            
        return clusters

embedding_pipeline = EmbeddingPipeline()
