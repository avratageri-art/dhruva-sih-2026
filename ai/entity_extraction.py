import re
import datetime
from typing import List, Dict, Any

# Pre-compile regular expressions for performance
REGEX_PATTERNS = {
    "pgp_fingerprint": re.compile(r"\b[0-9A-Fa-f]{40}\b"),
    "btc_wallet": re.compile(r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b"),
    "eth_wallet": re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
    "onion_address": re.compile(r"\b[a-z2-7]{16,56}\.onion\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "url": re.compile(r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+")
}

try:
    import spacy
    # Load small english model if available
    nlp = spacy.load("en_core_web_sm")
except (ImportError, OSError):
    nlp = None

class EntityExtractor:
    def __init__(self, source_name: str = "Unknown"):
        self.source_name = source_name

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        entities = []
        now = datetime.datetime.utcnow().isoformat()

        # 1. Regex-based deterministic extraction
        for entity_type, pattern in REGEX_PATTERNS.items():
            matches = pattern.findall(text)
            for match in matches:
                entities.append({
                    "value": match,
                    "entity_type": entity_type,
                    "source": self.source_name,
                    "timestamp": now,
                    "confidence": 0.95,
                    "extraction_method": "regex"
                })

        # 2. NLP-based extraction (if spaCy is available)
        if nlp:
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ in ["ORG", "DATE", "PERSON", "GPE"]:
                    entities.append({
                        "value": ent.text,
                        "entity_type": ent.label_,
                        "source": self.source_name,
                        "timestamp": now,
                        "confidence": 0.70,
                        "extraction_method": "spacy_ner"
                    })
                    
        return entities

    def extract_all(self, text: str) -> List[Dict[str, Any]]:
        return self.extract_entities(text)

extraction_pipeline = EntityExtractor("Global Pipeline")

if __name__ == "__main__":
    extractor = EntityExtractor("Test Source")
    sample_text = "Synthetic demo: @demo_shadowfox, DEMO_BTC_WALLET_NOT_VALID, and demo-hidden-service.invalid"
    results = extractor.extract_entities(sample_text)
    import json
    print(json.dumps(results, indent=2))
