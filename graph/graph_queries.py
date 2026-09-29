from .neo4j_client import neo4j_client
from typing import Dict, Any, List

def create_actor_node(actor_id: int, actor_name: str, category: str):
    query = """
    MERGE (a:Actor {id: $actor_id})
    SET a.name = $actor_name, a.category = $category
    RETURN a
    """
    return neo4j_client.execute_query(query, {"actor_id": actor_id, "actor_name": actor_name, "category": category})

def create_handle_node(handle_id: int, handle: str, platform: str):
    query = """
    MERGE (h:Handle {id: $handle_id})
    SET h.handle = $handle, h.platform = $platform
    RETURN h
    """
    return neo4j_client.execute_query(query, {"handle_id": handle_id, "handle": handle, "platform": platform})

def link_actor_to_handle(actor_id: int, handle_id: int, confidence: float, source: str, timestamp: str, evidence: str):
    query = """
    MATCH (a:Actor {id: $actor_id})
    MATCH (h:Handle {id: $handle_id})
    MERGE (a)-[r:USES_HANDLE]->(h)
    SET r.confidence = $confidence, r.source = $source, r.timestamp = $timestamp, r.evidence = $evidence
    RETURN r
    """
    params = {
        "actor_id": actor_id,
        "handle_id": handle_id,
        "confidence": confidence,
        "source": source,
        "timestamp": timestamp,
        "evidence": evidence
    }
    return neo4j_client.execute_query(query, params)

def get_actor_graph(actor_id: int):
    query = """
    MATCH (a:Actor {id: $actor_id})-[r]-(connected)
    RETURN a, r, connected
    """
    return neo4j_client.execute_query(query, {"actor_id": actor_id})
