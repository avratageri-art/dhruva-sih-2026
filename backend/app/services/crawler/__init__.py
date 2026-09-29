from app.services.crawler.dark_crawler import DarkCrawler
from app.services.crawler.adapter import OnionCrawlerAdapter, SyntheticSourceAdapter, SourceAdapter
from app.services.crawler.pipeline import CrawlerPipeline
from app.services.crawler.forum_parser import scan_forum_directory, normalize_forum_post
from app.services.crawler.breach_engine import BreachLookupEngine, enrich_entities_with_breaches
from app.services.crawler.ingestion_worker import run_ingestion_cycle, start_background_worker, stop_background_worker

__all__ = [
    "DarkCrawler", "OnionCrawlerAdapter", "SyntheticSourceAdapter", "SourceAdapter", "CrawlerPipeline",
    "scan_forum_directory", "normalize_forum_post",
    "BreachLookupEngine", "enrich_entities_with_breaches",
    "run_ingestion_cycle", "start_background_worker", "stop_background_worker",
]
