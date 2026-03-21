import feedparser
from typing import List, Dict
from urllib.parse import quote_plus
from datetime import datetime, date
import logging 
import requests
from difflib import SequenceMatcher
# List of known date formats from the Arxiv API
ARXIV_DATE_FORMATS = [
    '%Y-%m-%dT%H:%M:%SZ',   
    '%a, %d %b %Y %H:%M:%S %Z',   
    '%Y-%m-%dT%H:%M:%S',   
    '%Y-%m-%d %H:%M:%S %Z',
    '%Y-%m-%dT%H:%M:%S.%f%Z', 
]

logger = logging.getLogger(__name__)

def calculate_keyword_match(keyword: str, title: str, abstract: str) -> float:
    """
    Calculate keyword match percentage (0-100) based on title and abstract similarity.
    Strictly prioritizes exact and high-relevance matches.
    """
    keyword_lower = keyword.lower()
    title_lower = title.lower()
    abstract_lower = abstract.lower()
    
    # Exact title match = 100%
    if keyword_lower == title_lower:
        return 100.0
    
    # Title contains keyword exactly = 95%+
    if keyword_lower in title_lower:
        # Score based on how much of the title is the keyword
        ratio = len(keyword_lower) / len(title_lower)
        return 85.0 + (ratio * 15.0)  # Range: 85-100%
    
    # Use SequenceMatcher for similarity scoring
    title_ratio = SequenceMatcher(None, keyword_lower, title_lower).ratio() * 100
    abstract_ratio = SequenceMatcher(None, keyword_lower, abstract_lower).ratio() * 100
    
    # Weight title match 80%, abstract match 20%
    match_score = (title_ratio * 0.8) + (abstract_ratio * 0.2)
    
    return match_score

def fetch_arxiv_papers(keyword: str, max_results: int = 3) -> List[Dict]:
    """
    Fetch papers from arXiv API by keyword.
    Fetches more results, ranks them by relevance, and returns with match scores.
    Returns list of dicts with paper metadata sorted by keyword match score.
    """
    encoded_keyword = quote_plus(keyword)
    # Fetch more results internally to rank properly
    internal_max = max(15, max_results * 3)
    url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_keyword}&start=0&max_results={internal_max}"
    
    entries = feedparser.parse(url).entries

    papers = []
    for entry in entries:
        published_date = None
        for fmt in ARXIV_DATE_FORMATS:
            try:
                published_date = datetime.strptime(entry.published, fmt).date()
                break   
            except (ValueError, TypeError):
                continue 

        if published_date is None:
            logger.warning(f"Could not parse date for entry: {entry.title}. Original string: '{entry.published}'")

        # --- FIX: Construct the PDF URL directly from the arxiv_id ---
        arxiv_id = entry.id.split("/")[-1]
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        
        # Calculate keyword match score
        match_score = calculate_keyword_match(keyword, entry.title, entry.summary)
        
        papers.append({
            "title": entry.title,
            "abstract": entry.summary,
            "authors": ", ".join([author.name for author in entry.authors]),
            "arxiv_id": arxiv_id,
            "url": entry.link,
            "pdf_url": pdf_url,
            "published_at": published_date,
            "match_score": round(match_score, 2)
        })
    
    # Sort by match score descending (highest relevance first)
    papers.sort(key=lambda x: x["match_score"], reverse=True)
    
    return papers[:max_results]

async def download_pdf_content(pdf_url: str) -> bytes:
    """
    Downloads the PDF content from a given URL.
    """
    try:
        response = requests.get(pdf_url, stream=True)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download PDF from {pdf_url}: {e}")
        return None