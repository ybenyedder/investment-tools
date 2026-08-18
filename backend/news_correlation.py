import os
import httpx
import logging
import chromadb
from chromadb.config import Settings
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)

# Environment variables
CHROMA_URL = os.environ.get("CHROMA_URL", "http://localhost:8001")
EMBEDDING_URL = os.environ.get("EMBEDDING_URL", "http://localhost:8003/embed")

def get_chroma_client():
    host = CHROMA_URL.replace("http://", "").split(":")[0]
    port = CHROMA_URL.split(":")[-1]
    return chromadb.HttpClient(host=host, port=port, settings=Settings(allow_reset=True))

def get_query_embedding(query: str):
    """Get embedding from the external embedding service (all-MiniLM-L6-v2)."""
    try:
        response = httpx.post(EMBEDDING_URL, json={"input": [query]}, timeout=10)
        response.raise_for_status()
        return response.json().get("embeddings", [])[0]
    except Exception as e:
        logging.error(f"Failed to get embedding for query '{query}': {e}")
        return None

def fetch_recent_news(ticker: str, name: str, limit: int = 5):
    """Fetch semantically related news from ChromaDB for a given ticker/company name."""
    client = get_chroma_client()
    try:
        collection = client.get_collection(name="messages")
    except Exception as e:
        logging.warning("ChromaDB collection 'messages' not found. Ensure WhatsApp bot has ingested data.")
        return []

    # Try searching using both the ticker and company name
    query_text = f"{name} {ticker} stock market news"
    query_embedding = get_query_embedding(query_text)

    if not query_embedding:
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=limit
    )
    
    news_items = []
    if results and 'documents' in results and len(results['documents']) > 0:
        docs = results['documents'][0]
        ids = results['ids'][0]
        distances = results['distances'][0]
        
        for idx in range(len(docs)):
            # Distances in Chroma using cosine/L2 are smaller for better matches. 
            # Filter out very bad matches if needed.
            news_items.append({
                "id": ids[idx],
                "text": docs[idx],
                "distance": distances[idx],
                "timestamp": datetime.utcnow() - timedelta(hours=idx*12) # Mock timestamp if not in metadata, ideally we get this from Mongo or Chroma metadata
            })
    
    return news_items

def calculate_news_impact(ticker: str, name: str):
    """
    Returns a score indicating the anticipated stock impact (-1.0 to 1.0) 
    based on real-time news in the WhatsApp DB.
    """
    news_items = fetch_recent_news(ticker, name)
    if not news_items:
        return {"impact_score": 0.0, "news_count": 0, "latest_news": "No recent WhatsApp news"}

    # Dummy/heuristic sentiment scoring for proof-of-concept
    # A real system would use a LLM or FinBERT here to score the text.
    bullish_keywords = ['surge', 'beat', 'up', 'buy', 'growth', 'profit', 'dividend', 'announce', 'partner']
    bearish_keywords = ['drop', 'fall', 'sell', 'loss', 'miss', 'down', 'lawsuit', 'resign', 'crash']
    
    total_score = 0
    for item in news_items:
        text = item['text'].lower()
        score = 0
        for b in bullish_keywords:
            if b in text: score += 1
        for b in bearish_keywords:
            if b in text: score -= 1
        
        # Weight by how semantically close it was (lower distance is better)
        weight = max(0.1, 2.0 - item['distance'])
        total_score += score * weight

    # Normalize score between -1 and 1
    normalized_score = max(-1.0, min(1.0, total_score / max(1, len(news_items))))
    
    return {
        "impact_score": normalized_score,
        "news_count": len(news_items),
        "latest_news": news_items[0]['text'][:100] + "..." if news_items else "N/A"
    }

