"""
Mocked ChromaDB client file.
This remains here to satisfy any legacy imports but does not load the real chromadb library,
preventing Windows build failures.
"""

import logging

logger = logging.getLogger(__name__)


def get_chroma_client():
    """Returns a mock Chroma client."""
    logger.info("ChromaDB client mocked out.")
    return None


def get_chroma_collection():
    """Returns a mock Chroma collection."""
    logger.info("ChromaDB collection mocked out.")
    return None
