import feedparser
from typing import List, Dict
from urllib.parse import quote_plus
from datetime import datetime, date
import logging 

# List of known date formats from the Arxiv API
ARXIV_DATE_FORMATS = [
    '%Y-%m-%dT%H:%M:%SZ',  
    '%a, %d %b %Y %H:%M:%S %Z',  
    '%Y-%m-%dT%H:%M:%S',  
    '%Y-%m-%d %H:%M:%S %Z',
    '%Y-%m-%dT%H:%M:%S.%f%Z', 
]

logger = logging.getLogger(__name__)

def fetch_arxiv_papers(keyword: str, max_results: int = 5) -> List[Dict]:
    """
    Fetch papers from arXiv API by keyword.
    Returns list of dicts with paper metadata.
    """
    encoded_keyword = quote_plus(keyword)
    url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_keyword}&start=0&max_results={max_results}"
    
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

        papers.append({
            "title": entry.title,
            "abstract": entry.summary,
            "authors": ", ".join([author.name for author in entry.authors]),
            "arxiv_id": entry.id.split("/")[-1],
            "url": entry.link,
            "published_at": published_date
        })
    return papers