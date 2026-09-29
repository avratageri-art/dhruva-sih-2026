import numpy as np
from typing import List, Dict, Any, Optional

def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
        
    if len(s2) == 0:
        return len(s1)
        
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
        
    return previous_row[-1]

def normalize_leetspeak(text: str) -> str:
    leet_map = {
        '0': 'o', '1': 'i', '3': 'e', '4': 'a',
        '5': 's', '7': 't', '@': 'a', '$': 's'
    }
    result = text.lower()
    for k, v in leet_map.items():
        result = result.replace(k, v)
    return result

def strip_affixes(text: str) -> str:
    text = text.lower()
    prefixes = ['the', 'real', 'official', 'mr', 'x']
    suffixes = ['official', 'bot', 'real', '123']
    
    for p in prefixes:
        if text.startswith(p) and len(text) > len(p):
            text = text[len(p):]
            
    for s in suffixes:
        if text.endswith(s) and len(text) > len(s):
            text = text[:-len(s)]
            
    return text.strip('_-. ')

class EntityResolutionPipeline:
    """
    Entity Resolution Pipeline combining:
      1. Orthographic matching (leetspeak normalization, affix stripping, Levenshtein edit distance)
      2. Semantic embedding similarity using pretrained sentence-transformers/all-MiniLM-L6-v2
    """
    def __init__(self):
        self._embedding_pipeline = None

    @property
    def embedding_pipeline(self):
        if self._embedding_pipeline is None:
            try:
                from .embeddings import embedding_pipeline
                self._embedding_pipeline = embedding_pipeline
            except Exception:
                self._embedding_pipeline = None
        return self._embedding_pipeline

    def calculate_orthographic_similarity(self, h1: str, h2: str) -> float:
        h1_norm = normalize_leetspeak(h1)
        h2_norm = normalize_leetspeak(h2)
        
        # Exact match after norm
        if h1_norm == h2_norm:
            return 1.0
            
        h1_stripped = strip_affixes(h1_norm)
        h2_stripped = strip_affixes(h2_norm)
        
        # Match after stripping
        if h1_stripped == h2_stripped:
            return 0.95
            
        # Levenshtein distance on stripped
        max_len = max(len(h1_stripped), len(h2_stripped))
        if max_len == 0:
            return 0.0
            
        dist = levenshtein_distance(h1_stripped, h2_stripped)
        sim = 1.0 - (dist / max_len)
        
        return round(max(0.0, sim), 4)

    def calculate_handle_similarity(self, h1: str, h2: str, context1: str = "", context2: str = "") -> float:
        """
        Calculate combined handle & entity similarity using both orthographic
        heuristics and real SentenceTransformer embeddings.
        """
        ortho_sim = self.calculate_orthographic_similarity(h1, h2)
        if ortho_sim == 1.0:
            return 1.0

        # Semantic similarity via sentence-transformers/all-MiniLM-L6-v2
        semantic_sim = 0.0
        if self.embedding_pipeline:
            text1 = f"{h1} {context1}".strip()
            text2 = f"{h2} {context2}".strip()
            try:
                semantic_sim = self.embedding_pipeline.calculate_similarity(text1, text2)
                semantic_sim = max(0.0, float(semantic_sim))
            except Exception:
                semantic_sim = 0.0

        combined = 0.60 * ortho_sim + 0.40 * semantic_sim
        return round(float(np.clip(combined, 0.0, 1.0)), 4)

    def resolve_entities(
        self,
        entity_a: Dict[str, Any],
        entity_b: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Full entity resolution comparing two entity profiles:
        - Handles (orthographic + semantic embeddings)
        - Shared indicators (wallets, PGP keys)
        """
        handles_a = entity_a.get("handles", [])
        handles_b = entity_b.get("handles", [])
        
        max_handle_sim = 0.0
        max_ortho_sim = 0.0
        max_sem_sim = 0.0
        
        for h1 in handles_a:
            for h2 in handles_b:
                ortho = self.calculate_orthographic_similarity(h1, h2)
                sem = 0.0
                if self.embedding_pipeline:
                    try:
                        sem = float(self.embedding_pipeline.calculate_similarity(h1, h2))
                    except Exception:
                        sem = 0.0
                combined = 0.60 * ortho + 0.40 * sem
                if combined > max_handle_sim:
                    max_handle_sim = combined
                    max_ortho_sim = ortho
                    max_sem_sim = sem

        # Shared wallets / PGP
        wallets_a = set(entity_a.get("wallets", []))
        wallets_b = set(entity_b.get("wallets", []))
        shared_wallets = list(wallets_a & wallets_b)

        pgp_a = set(entity_a.get("pgps", []))
        pgp_b = set(entity_b.get("pgps", []))
        shared_pgp = list(pgp_a & pgp_b)

        indicator_score = 1.0 if (shared_wallets or shared_pgp) else 0.0
        final_resolution_score = max(max_handle_sim, indicator_score)

        return {
            "entity_resolution_score": round(final_resolution_score, 4),
            "handle_similarity": round(max_handle_sim, 4),
            "orthographic_similarity": round(max_ortho_sim, 4),
            "semantic_similarity": round(max_sem_sim, 4),
            "shared_wallets": shared_wallets,
            "shared_pgp": shared_pgp,
            "model_used": "sentence-transformers/all-MiniLM-L6-v2",
        }

entity_resolution_pipeline = EntityResolutionPipeline()

