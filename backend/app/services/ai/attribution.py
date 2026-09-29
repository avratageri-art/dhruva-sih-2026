"""
attribution.py — Real AI-powered threat-actor attribution engine.

Pipeline:
  1. Semantic similarity   — sentence-transformers/all-MiniLM-L6-v2 embeddings
                             (cosine similarity on per-actor text corpora)
  2. Stylometric analysis  — classical NLP features (lexical richness, avg word
                             length, punctuation density, type-token ratio,
                             function-word usage)
  3. Behavioural analysis  — temporal patterns (active hours histogram, UTC
                             offset estimate, posting frequency)
  4. Handle/entity overlap — Jaro-Winkler similarity on handle sets
  5. Weighted fusion       — final score from all four subsystems

The model is loaded once (singleton) at module import time using lazy loading
so uvicorn startup remains fast if the package is not yet available.
"""

from __future__ import annotations

import logging
import math
import re
import statistics
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Model singleton — lazy load so the server can start even offline
# ─────────────────────────────────────────────────────────────────────────────

_MODEL = None
_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def _get_model():
    global _MODEL
    if _MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"[AttributionEngine] Loading {_MODEL_NAME} …")
            _MODEL = SentenceTransformer(_MODEL_NAME)
            logger.info("[AttributionEngine] Model ready ✓")
        except Exception as e:
            logger.error(f"[AttributionEngine] Could not load model: {e}")
            _MODEL = None
    return _MODEL


# ─────────────────────────────────────────────────────────────────────────────
# 1. SEMANTIC SIMILARITY via sentence-transformers
# ─────────────────────────────────────────────────────────────────────────────

def _embed_texts(texts: List[str]) -> Optional[np.ndarray]:
    """Return mean embedding for a list of texts, or None if model unavailable."""
    model = _get_model()
    if model is None or not texts:
        return None
    clean = [t for t in texts if isinstance(t, str) and t.strip()]
    if not clean:
        return None
    try:
        embeddings = model.encode(clean, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.mean(axis=0)  # shape (384,)
    except Exception as e:
        logger.error(f"[Semantic] Encoding failed: {e}")
        return None


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity, normalised to [0, 1]."""
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    raw = float(np.dot(a, b) / denom)   # −1 … 1
    return (raw + 1) / 2                 # 0 … 1


def semantic_similarity(texts_a: List[str], texts_b: List[str]) -> Tuple[float, str]:
    """
    Returns (score 0-1, status_message).
    Falls back to 0 if model is unavailable.
    """
    emb_a = _embed_texts(texts_a)
    emb_b = _embed_texts(texts_b)
    if emb_a is None or emb_b is None:
        return 0.0, "model_unavailable"
    score = _cosine(emb_a, emb_b)
    return round(score, 4), "ok"


# ─────────────────────────────────────────────────────────────────────────────
# 2. STYLOMETRIC ANALYSIS — classical NLP features
# ─────────────────────────────────────────────────────────────────────────────

_FUNCTION_WORDS = {
    "the", "a", "an", "is", "it", "in", "on", "at", "to", "and",
    "or", "but", "of", "for", "with", "you", "i", "we", "they",
    "he", "she", "this", "that", "are", "was", "be", "has", "have",
    "do", "did", "not", "no", "if", "so", "as", "by", "from",
}


def _extract_stylometric_features(texts: List[str]) -> Dict[str, float]:
    """
    Extract classic stylometric features from a corpus.

    Features:
      - avg_word_len        : mean word character length
      - type_token_ratio    : vocab diversity (unique / total tokens)
      - punct_density       : punctuation chars / total chars
      - uppercase_ratio     : UPPERCASE words / total words
      - avg_sentence_len    : mean tokens per sentence
      - function_word_ratio : function words / total words
      - exclamation_rate    : '!' per sentence
      - question_rate       : '?' per sentence
      - digit_ratio         : digit chars / total chars
    """
    combined = " ".join(t for t in texts if isinstance(t, str))
    if not combined.strip():
        return {k: 0.0 for k in [
            "avg_word_len", "type_token_ratio", "punct_density",
            "uppercase_ratio", "avg_sentence_len", "function_word_ratio",
            "exclamation_rate", "question_rate", "digit_ratio",
        ]}

    words = re.findall(r"\b\w+\b", combined)
    sentences = re.split(r"[.!?]+", combined)
    sentences = [s for s in sentences if s.strip()]

    total_chars = max(len(combined), 1)
    total_words = max(len(words), 1)
    total_sents = max(len(sentences), 1)

    word_lower = [w.lower() for w in words]
    punct_chars = sum(1 for c in combined if c in '.,;:!?()[]{}"\'-/')
    digit_chars = sum(1 for c in combined if c.isdigit())
    uppercase_words = sum(1 for w in words if w.isupper() and len(w) > 1)
    func_words = sum(1 for w in word_lower if w in _FUNCTION_WORDS)
    unique_tokens = len(set(word_lower))
    avg_word_len = sum(len(w) for w in words) / total_words
    avg_sent_len = total_words / total_sents

    return {
        "avg_word_len":        round(avg_word_len, 3),
        "type_token_ratio":    round(unique_tokens / total_words, 3),
        "punct_density":       round(punct_chars / total_chars, 4),
        "uppercase_ratio":     round(uppercase_words / total_words, 4),
        "avg_sentence_len":    round(avg_sent_len, 3),
        "function_word_ratio": round(func_words / total_words, 4),
        "exclamation_rate":    round(combined.count("!") / total_sents, 4),
        "question_rate":       round(combined.count("?") / total_sents, 4),
        "digit_ratio":         round(digit_chars / total_chars, 4),
    }


def stylometric_similarity(feats_a: Dict[str, float], feats_b: Dict[str, float]) -> float:
    """
    Compute similarity between two stylometric feature vectors.
    Uses normalised Euclidean distance converted to a similarity score in [0, 1].
    """
    keys = sorted(feats_a.keys())
    if not keys:
        return 0.0

    vec_a = np.array([feats_a.get(k, 0.0) for k in keys], dtype=float)
    vec_b = np.array([feats_b.get(k, 0.0) for k in keys], dtype=float)

    # Normalise each dimension to [0,1] using typical max values
    norms = np.array([10, 1, 0.2, 0.5, 50, 1, 5, 5, 0.5], dtype=float)
    norms = np.maximum(norms, 1e-9)
    vec_a = np.clip(vec_a / norms, 0, 1)
    vec_b = np.clip(vec_b / norms, 0, 1)

    dist = np.linalg.norm(vec_a - vec_b) / math.sqrt(len(keys))  # 0 … 1
    similarity = 1.0 - dist
    return round(float(np.clip(similarity, 0, 1)), 4)


# ─────────────────────────────────────────────────────────────────────────────
# 3. BEHAVIOURAL ANALYSIS — temporal patterns
# ─────────────────────────────────────────────────────────────────────────────

def _parse_timestamps(timestamps: List[str]) -> List[datetime]:
    parsed = []
    for ts in timestamps:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed.append(datetime.strptime(ts[:19], fmt))
                break
            except Exception:
                continue
    return parsed


def _extract_behavioural_features(timestamps: List[str]) -> Dict[str, Any]:
    """
    Extract temporal behavioural signals.

    Features:
      - active_hour_histogram : 24-bin normalised activity histogram
      - peak_hour             : most active hour of day
      - posting_frequency     : posts per day (over observed span)
      - night_activity_ratio  : fraction of posts 22:00–06:00
      - weekend_ratio         : fraction on weekends
    """
    dts = _parse_timestamps(timestamps)
    if not dts:
        return {
            "active_hour_histogram": [0.0] * 24,
            "peak_hour": -1,
            "posting_frequency": 0.0,
            "night_activity_ratio": 0.0,
            "weekend_ratio": 0.0,
        }

    hour_counts = Counter(dt.hour for dt in dts)
    histogram = [hour_counts.get(h, 0) for h in range(24)]
    total = sum(histogram) or 1
    norm_hist = [c / total for c in histogram]

    peak_hour = histogram.index(max(histogram))
    night = sum(histogram[h] for h in list(range(22, 24)) + list(range(0, 7)))
    night_ratio = night / total

    weekend = sum(1 for dt in dts if dt.weekday() >= 5)
    weekend_ratio = weekend / total

    if len(dts) > 1:
        span_days = max((max(dts) - min(dts)).days, 1)
        posting_freq = len(dts) / span_days
    else:
        posting_freq = 0.0

    return {
        "active_hour_histogram": norm_hist,
        "peak_hour": peak_hour,
        "posting_frequency": round(posting_freq, 4),
        "night_activity_ratio": round(night_ratio, 4),
        "weekend_ratio": round(weekend_ratio, 4),
    }


def behavioural_similarity(feats_a: Dict[str, Any], feats_b: Dict[str, Any]) -> float:
    """
    Compare two behavioural profiles.
    Histogram overlap + scalar feature similarity combined.
    """
    # Histogram overlap (Bhattacharyya coefficient)
    hist_a = np.array(feats_a.get("active_hour_histogram", [0.0] * 24))
    hist_b = np.array(feats_b.get("active_hour_histogram", [0.0] * 24))
    bhatt = float(np.sum(np.sqrt(hist_a * hist_b + 1e-12)))  # 0 … 1

    # Scalar features
    scalar_keys = ["night_activity_ratio", "weekend_ratio", "posting_frequency"]
    scalar_diffs = []
    for k in scalar_keys:
        va = feats_a.get(k, 0.0)
        vb = feats_b.get(k, 0.0)
        maxv = max(abs(va), abs(vb), 1e-9)
        scalar_diffs.append(1.0 - abs(va - vb) / maxv)

    scalar_sim = float(np.mean(scalar_diffs)) if scalar_diffs else 0.5

    combined = 0.6 * bhatt + 0.4 * scalar_sim
    return round(float(np.clip(combined, 0, 1)), 4)


# ─────────────────────────────────────────────────────────────────────────────
# 4. HANDLE / ENTITY OVERLAP — Jaro-Winkler
# ─────────────────────────────────────────────────────────────────────────────

def _jaro_winkler(s1: str, s2: str) -> float:
    """Jaro-Winkler string similarity (0–1)."""
    s1, s2 = s1.lower(), s2.lower()
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0
    match_dist = max(len1, len2) // 2 - 1
    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0
    transpositions = 0
    for i in range(len1):
        start = max(0, i - match_dist)
        end = min(i + match_dist + 1, len2)
        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = s2_matches[j] = True
            matches += 1
            break
    if matches == 0:
        return 0.0
    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1
    jaro = (matches / len1 + matches / len2 +
            (matches - transpositions / 2) / matches) / 3
    prefix = 0
    for i in range(min(4, len1, len2)):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break
    return round(jaro + prefix * 0.1 * (1 - jaro), 4)


def handle_similarity(handles_a: List[str], handles_b: List[str]) -> float:
    """
    Entity resolution pipeline:
    Combines:
      1. Orthographic handle similarity (Jaro-Winkler)
      2. Semantic embedding similarity from sentence-transformers/all-MiniLM-L6-v2
    """
    if not handles_a or not handles_b:
        return 0.0
    # Check exact overlap first
    set_a = {h.lower().lstrip("@") for h in handles_a}
    set_b = {h.lower().lstrip("@") for h in handles_b}
    if set_a & set_b:
        return 1.0
    # Pairwise JW orthographic similarity
    scores = [
        _jaro_winkler(a, b)
        for a in set_a
        for b in set_b
    ]
    ortho_score = max(scores) if scores else 0.0

    # Model-based semantic embedding similarity for entity resolution
    sem_score, _ = semantic_similarity(list(set_a), list(set_b))

    fused = 0.60 * ortho_score + 0.40 * sem_score
    return round(float(np.clip(fused, 0.0, 1.0)), 4)


# ─────────────────────────────────────────────────────────────────────────────
# 5. GRAPH / ENTITY RELATIONSHIP SCORE
# ─────────────────────────────────────────────────────────────────────────────

def graph_correlation_score(actor_a_data: Dict, actor_b_data: Dict) -> float:
    """
    Simple Jaccard similarity on shared infrastructure indicators / wallets / PGPs.
    Actors pass optional 'wallets', 'pgps', 'onion_services' lists.
    """
    score = 0.0
    fields = ["wallets", "pgps", "onion_services"]
    for f in fields:
        set_a = set(actor_a_data.get(f, []))
        set_b = set(actor_b_data.get(f, []))
        if set_a or set_b:
            intersection = len(set_a & set_b)
            union = len(set_a | set_b)
            score = max(score, intersection / union if union > 0 else 0.0)
    # Also factor in any pre-computed graph_score
    ext_score_a = actor_a_data.get("graph_score", 0.0)
    ext_score_b = actor_b_data.get("graph_score", 0.0)
    combined = max(score, (ext_score_a + ext_score_b) / 2)
    return round(float(np.clip(combined, 0, 1)), 4)


# ─────────────────────────────────────────────────────────────────────────────
# 6. FUSION — weighted attribution score
# ─────────────────────────────────────────────────────────────────────────────

# Weights must sum to 1.0
WEIGHTS = {
    "semantic":    0.35,
    "stylometric": 0.25,
    "behavioural": 0.20,
    "handle":      0.15,
    "graph":       0.05,
}


def _confidence_label(score: float) -> str:
    if score >= 0.80:
        return "VERY HIGH"
    if score >= 0.65:
        return "HIGH"
    if score >= 0.50:
        return "MEDIUM"
    if score >= 0.35:
        return "LOW"
    return "VERY LOW"


class AttributionEngine:
    """
    Singleton attribution engine.  Call `assess_attribution(actor_a, actor_b)`.

    actor_data dict schema:
        texts:          List[str]   — post content for that actor
        timestamps:     List[str]   — ISO-8601 timestamps matching texts
        handles:        List[str]
        wallets:        List[str]   (optional)
        pgps:           List[str]   (optional)
        onion_services: List[str]   (optional)
        graph_score:    float       (optional, 0-1)
    """

    def assess_attribution(
        self,
        actor_a_data: Dict,
        actor_b_data: Dict,
    ) -> Tuple[float, str, str]:
        """
        Returns:
            score_pct   : float  0–100
            label       : str    confidence label
            explanation : str    human-readable breakdown
        """
        texts_a = actor_a_data.get("texts", [])
        texts_b = actor_b_data.get("texts", [])
        ts_a    = actor_a_data.get("timestamps", [])
        ts_b    = actor_b_data.get("timestamps", [])
        h_a     = actor_a_data.get("handles", [])
        h_b     = actor_b_data.get("handles", [])

        # 1. Semantic
        sem_score, sem_status = semantic_similarity(texts_a, texts_b)

        # 2. Stylometric
        feats_a = _extract_stylometric_features(texts_a)
        feats_b = _extract_stylometric_features(texts_b)
        stylo_score = stylometric_similarity(feats_a, feats_b)

        # 3. Behavioural
        behav_a = _extract_behavioural_features(ts_a)
        behav_b = _extract_behavioural_features(ts_b)
        behav_score = behavioural_similarity(behav_a, behav_b)

        # 4. Handle overlap
        handle_score = handle_similarity(h_a, h_b)

        # 5. Graph
        graph_score = graph_correlation_score(actor_a_data, actor_b_data)

        # Weighted fusion
        raw = (
            WEIGHTS["semantic"]    * sem_score +
            WEIGHTS["stylometric"] * stylo_score +
            WEIGHTS["behavioural"] * behav_score +
            WEIGHTS["handle"]      * handle_score +
            WEIGHTS["graph"]       * graph_score
        )
        score = float(np.clip(raw, 0.0, 1.0))
        score_pct = round(score * 100, 2)
        label = _confidence_label(score)

        explanation = (
            f"[sentence-transformers/{_MODEL_NAME.split('/')[-1]}] "
            f"Semantic similarity: {sem_score:.3f} ({sem_status}) | "
            f"Stylometric similarity: {stylo_score:.3f} | "
            f"Behavioural similarity: {behav_score:.3f} | "
            f"Handle overlap (Jaro-Winkler): {handle_score:.3f} | "
            f"Graph correlation: {graph_score:.3f} | "
            f"Weighted attribution score: {score_pct:.1f}%"
        )

        # Negative signals
        tz_mismatch = abs(
            behav_a.get("peak_hour", 12) - behav_b.get("peak_hour", 12)
        ) > 8
        platform_mismatch = handle_score < 0.15

        if tz_mismatch:
            explanation += " | WARNING: significant timezone offset detected"
        if platform_mismatch:
            explanation += " | NOTE: low handle similarity (different platforms likely)"

        logger.info(
            f"[AttributionEngine] assess: sem={sem_score:.3f} "
            f"stylo={stylo_score:.3f} behav={behav_score:.3f} "
            f"handle={handle_score:.3f} graph={graph_score:.3f} "
            f"→ {score_pct:.1f}% [{label}]"
        )
        return score_pct, label, explanation

    def get_subsystem_scores(
        self,
        actor_a_data: Dict,
        actor_b_data: Dict,
    ) -> Dict[str, float]:
        """Return individual subsystem scores (for UI display)."""
        texts_a = actor_a_data.get("texts", [])
        texts_b = actor_b_data.get("texts", [])
        ts_a    = actor_a_data.get("timestamps", [])
        ts_b    = actor_b_data.get("timestamps", [])
        h_a     = actor_a_data.get("handles", [])
        h_b     = actor_b_data.get("handles", [])

        sem_score, _ = semantic_similarity(texts_a, texts_b)
        feats_a = _extract_stylometric_features(texts_a)
        feats_b = _extract_stylometric_features(texts_b)
        stylo_score = stylometric_similarity(feats_a, feats_b)
        behav_a = _extract_behavioural_features(ts_a)
        behav_b = _extract_behavioural_features(ts_b)
        behav_score = behavioural_similarity(behav_a, behav_b)
        handle_score = handle_similarity(h_a, h_b)
        graph_score = graph_correlation_score(actor_a_data, actor_b_data)

        return {
            "semantic":    round(sem_score, 4),
            "stylometric": round(stylo_score, 4),
            "behavioural": round(behav_score, 4),
            "handle":      round(handle_score, 4),
            "graph":       round(graph_score, 4),
            "model":       _MODEL_NAME,
            "model_loaded": _get_model() is not None,
        }


# Module-level singleton
attribution_engine = AttributionEngine()
