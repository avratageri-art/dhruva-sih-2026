from typing import List, Dict
from datetime import datetime
import numpy as np

class BehaviourPipeline:
    def __init__(self):
        pass

    def extract_time_features(self, timestamps: List[datetime]) -> Dict[str, any]:
        if not timestamps:
            return {}
            
        hours = [t.hour for t in timestamps]
        days = [t.weekday() for t in timestamps]
        
        # Estimate timezone based on peak activity (assuming 18:00-02:00 local time is peak for malicious activity generally)
        # This is a very rough heuristic for demo
        peak_utc_hour = max(set(hours), key=hours.count)
        
        return {
            "active_hours": list(set(hours)),
            "peak_utc_hour": peak_utc_hour,
            "active_days": list(set(days)),
            "weekend_ratio": sum(1 for d in days if d >= 5) / len(days)
        }
        
    def calculate_behaviour_similarity(self, features1: Dict[str, any], features2: Dict[str, any]) -> float:
        if not features1 or not features2:
            return 0.0
            
        # Hour overlap
        hours1 = set(features1.get("active_hours", []))
        hours2 = set(features2.get("active_hours", []))
        
        if not hours1 and not hours2:
            hour_sim = 1.0
        else:
            intersection = len(hours1.intersection(hours2))
            union = len(hours1.union(hours2))
            hour_sim = intersection / union if union > 0 else 0.0
            
        # Day overlap
        days1 = set(features1.get("active_days", []))
        days2 = set(features2.get("active_days", []))
        
        if not days1 and not days2:
            day_sim = 1.0
        else:
            intersection = len(days1.intersection(days2))
            union = len(days1.union(days2))
            day_sim = intersection / union if union > 0 else 0.0
            
        # Weekend Ratio diff
        wr1 = features1.get("weekend_ratio", 0.0)
        wr2 = features2.get("weekend_ratio", 0.0)
        wr_sim = 1.0 - abs(wr1 - wr2)
        
        return round((hour_sim * 0.4) + (day_sim * 0.4) + (wr_sim * 0.2), 4)

behaviour_pipeline = BehaviourPipeline()
