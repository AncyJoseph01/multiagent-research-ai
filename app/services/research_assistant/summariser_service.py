import re
import time
import logging
import google.generativeai as genai
from app.core.config import settings
from google.api_core.exceptions import ResourceExhausted

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)

def summarise_text(
    content: str,
    title: str = None,
    authors: str = None,
    institution: str = None,
    arxiv_id: str = None,
    published_at: str = None,
    source: str = None,
) -> str:
    """
    Summarise research paper text into structured research notes using a fixed template.
    Ensures authors are included, key metrics are bolded, and the word 'structured' is removed.
    """

    # Build optional metadata string to inject into the main content
    meta_lines = []
    if authors:
        meta_lines.append(f"**Authors:** {authors}")
    if institution:
        meta_lines.append(f"**Institution(s):** {institution}")
    if arxiv_id:
        meta_lines.append(f"**ArXiv ID:** {arxiv_id} (https://arxiv.org/abs/{arxiv_id})")
    if published_at:
        meta_lines.append(f"**Published:** {published_at}")
    if source:
        meta_lines.append(f"**Source/Dataset/Challenge:** {source}")
    
    metadata = "\n".join(meta_lines)
    if metadata:
        metadata += "\n\n"  # spacing before main content

    prompt = f"""
You are an assistant for researchers. Summarise the following research paper
into structured research notes using the exact template below.

Requirements:
- Always use Markdown formatting.
- Include **authors** in the summary section.
- Include every section in the template.
- Keep technical details (datasets, baselines, metrics, equations, percentages).
- Highlight key results and metrics (e.g., BLEU, F1, silhouette scores) using **bold**.
- Use bullet points where appropriate.
- Do NOT include the word "structured" anywhere in the output.

--- TEMPLATE START ---
{metadata}
## Research Notes: {title or 'Unknown Title'}
**Authors:** {authors or "No explicit information provided."}

**Quick Takeaway and Key Insights:**  
[2–10 sentence simple explanation of the paper’s problem, method, and outcome]

**Abstract:**  
[Concise technical summary]

**Methods:**  
- **Preprocessing:** [...]
- **Model/Architecture:** [...]
- **Training Procedure:** [...]
- **Evaluation Setup:** [...]

**Findings / Results:**  
- **In-domain Results:**  
  - [...]
- **Cross-domain / Generalization Results:**  
  - [...]
- **Key Insights:**  
  - [...]

**Contributions:**  
- [...]

**Limitations / Challenges:**  
- [...]

**Future Directions:**  
- [...]
--- TEMPLATE END ---

Text to summarise:
{content}
"""

    model = genai.GenerativeModel("gemini-2.5-flash-lite")

    # Retry logic for API quota limits
    max_retries = 3
    retry_delay = 15  # Start with 15 seconds
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            break  # Success, exit retry loop
        except ResourceExhausted as e:
            if attempt < max_retries - 1:
                logger.warning(f"⚠️ Quota exceeded on attempt {attempt + 1}/{max_retries}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"❌ Failed after {max_retries} attempts due to quota limit")
                raise e
        except Exception as e:
            logger.error(f"Error generating summary: {e}", exc_info=True)
            raise e

    # Remove any leading "structured" or accidental whitespace/newlines
    final_text = response.text.strip()
    final_text = re.sub(r'^\s*structured\s*[:\-]?\s*', '', final_text, flags=re.IGNORECASE)
    
    # Remove template markers
    final_text = re.sub(r'---\s*TEMPLATE\s+START\s*---', '', final_text, flags=re.IGNORECASE)
    final_text = re.sub(r'---\s*TEMPLATE\s+END\s*---', '', final_text, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    final_text = final_text.strip()

    return final_text
