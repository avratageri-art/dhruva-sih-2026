import re
import string
from collections import Counter
from typing import Dict
from .embeddings import embedding_pipeline

def calculate_jaccard(set1: set, set2: set) -> float:
    if not set1 and not set2:
        return 1.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0.0

def get_ngrams(text: str, n: int) -> set:
    words = text.lower().split()
    return set(zip(*[words[i:] for i in range(n)]))

def get_char_ngrams(text: str, n: int) -> set:
    text = text.lower()
    return set([text[i:i+n] for i in range(len(text)-n+1)])

def calculate_sentence_length_similarity(text1: str, text2: str) -> float:
    sentences1 = [s for s in re.split(r'[.!?]+', text1) if s.strip()]
    sentences2 = [s for s in re.split(r'[.!?]+', text2) if s.strip()]
    
    avg_len1 = sum(len(s.split()) for s in sentences1) / len(sentences1) if sentences1 else 0
    avg_len2 = sum(len(s.split()) for s in sentences2) / len(sentences2) if sentences2 else 0
    
    max_len = max(avg_len1, avg_len2)
    if max_len == 0:
        return 1.0
        
    diff = abs(avg_len1 - avg_len2)
    return max(0.0, 1.0 - (diff / max_len))

def calculate_punctuation_similarity(text1: str, text2: str) -> float:
    punct1 = Counter([c for c in text1 if c in string.punctuation])
    punct2 = Counter([c for c in text2 if c in string.punctuation])
    
    all_punct = set(punct1.keys()).union(set(punct2.keys()))
    if not all_punct:
        return 1.0
        
    total_diff = sum(abs(punct1.get(p, 0) - punct2.get(p, 0)) for p in all_punct)
    max_possible_diff = sum(punct1.get(p, 0) + punct2.get(p, 0) for p in all_punct)
    
    return max(0.0, 1.0 - (total_diff / max_possible_diff)) if max_possible_diff > 0 else 1.0

def calculate_lexical_diversity(text: str) -> float:
    words = text.lower().split()
    if not words:
        return 0.0
    return len(set(words)) / len(words)

class StylometryPipeline:
    def __init__(self):
        self.weights = {
            "semantic": 0.40,
            "word_ngram": 0.20,
            "char_ngram": 0.15,
            "sentence_length": 0.10,
            "punctuation": 0.05,
            "lexical_diversity": 0.10
        }

    def analyze(self, text1: str, text2: str) -> Dict[str, float]:
        # Semantic
        semantic_sim = embedding_pipeline.calculate_similarity(text1, text2)
        
        # Word N-grams (Bigrams)
        bg1 = get_ngrams(text1, 2)
        bg2 = get_ngrams(text2, 2)
        word_sim = calculate_jaccard(bg1, bg2)
        
        # Char N-grams (Trigrams)
        cg1 = get_char_ngrams(text1, 3)
        cg2 = get_char_ngrams(text2, 3)
        char_sim = calculate_jaccard(cg1, cg2)
        
        # Sentence length
        len_sim = calculate_sentence_length_similarity(text1, text2)
        
        # Punctuation
        punct_sim = calculate_punctuation_similarity(text1, text2)
        
        # Lexical Diversity
        ld1 = calculate_lexical_diversity(text1)
        ld2 = calculate_lexical_diversity(text2)
        ld_max = max(ld1, ld2)
        ld_sim = 1.0 - (abs(ld1 - ld2) / ld_max) if ld_max > 0 else 1.0
        
        overall = (
            semantic_sim * self.weights["semantic"] +
            word_sim * self.weights["word_ngram"] +
            char_sim * self.weights["char_ngram"] +
            len_sim * self.weights["sentence_length"] +
            punct_sim * self.weights["punctuation"] +
            ld_sim * self.weights["lexical_diversity"]
        )
        
        return {
            "semantic_similarity": round(semantic_sim, 4),
            "character_similarity": round(char_sim, 4),
            "lexical_similarity": round(word_sim, 4),
            "punctuation_similarity": round(punct_sim, 4),
            "sentence_structure_similarity": round(len_sim, 4),
            "diversity_similarity": round(ld_sim, 4),
            "overall_stylometric_similarity": round(overall, 4)
        }

stylometry_pipeline = StylometryPipeline()
