from typing import Dict, Any, Tuple
from .stylometry import stylometry_pipeline
from .behaviour import behaviour_pipeline
from .entity_resolution import entity_resolution_pipeline

class AttributionEngine:
    def __init__(self):
        # Weights for different intelligence vectors
        self.weights = {
            "stylometry": 0.35,
            "behaviour": 0.25,
            "entity_resolution": 0.20,
            "graph_correlation": 0.20
        }

    def assess_attribution(self, actor1_data: Dict[str, Any], actor2_data: Dict[str, Any]) -> Tuple[float, str, str]:
        """
        Calculates attribution score between two actor profiles.
        Expects dicts with 'texts', 'timestamps', 'handles', 'graph_score'
        """
        score = 0.0
        explanations = []
        
        # 1. Stylometry
        texts1 = actor1_data.get("texts", [])
        texts2 = actor2_data.get("texts", [])
        if texts1 and texts2:
            # Combine all texts for a macro analysis
            t1 = " ".join(texts1)
            t2 = " ".join(texts2)
            stylo_results = stylometry_pipeline.analyze(t1, t2)
            stylo_sim = stylo_results["overall_stylometric_similarity"]
            score += stylo_sim * self.weights["stylometry"]
            explanations.append(f"Stylometric similarity: {stylo_sim:.2f}")
        else:
            # Distribute weight if missing
            explanations.append("Stylometric data missing.")
            
        # 2. Behaviour
        times1 = actor1_data.get("timestamps", [])
        times2 = actor2_data.get("timestamps", [])
        if times1 and times2:
            f1 = behaviour_pipeline.extract_time_features(times1)
            f2 = behaviour_pipeline.extract_time_features(times2)
            behav_sim = behaviour_pipeline.calculate_behaviour_similarity(f1, f2)
            score += behav_sim * self.weights["behaviour"]
            explanations.append(f"Behavioural similarity: {behav_sim:.2f}")
        else:
            explanations.append("Behavioural data missing.")
            
        # 3. Entity Resolution
        handles1 = actor1_data.get("handles", [])
        handles2 = actor2_data.get("handles", [])
        if handles1 and handles2:
            max_sim = 0.0
            for h1 in handles1:
                for h2 in handles2:
                    sim = entity_resolution_pipeline.calculate_handle_similarity(h1, h2)
                    max_sim = max(max_sim, sim)
            score += max_sim * self.weights["entity_resolution"]
            explanations.append(f"Handle similarity max: {max_sim:.2f}")
        else:
            explanations.append("Handle data missing.")
            
        # 4. Graph Correlation (mocked input)
        graph_score = actor1_data.get("graph_score", 0.0) # Assumes graph pre-computed this
        score += graph_score * self.weights["graph_correlation"]
        explanations.append(f"Graph correlation score: {graph_score:.2f}")
        
        # Determine confidence label
        if score >= 0.85:
            label = "HIGH"
        elif score >= 0.65:
            label = "MEDIUM"
        else:
            label = "LOW"
            
        explanation_str = " | ".join(explanations)
        return round(score * 100, 2), label, explanation_str

attribution_engine = AttributionEngine()
