import google.generativeai as genai
from app.core.config import settings

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
    Summarise research paper text into structured research notes with a fixed template.
    """

    # Build metadata section
    metadata = f"## Research Notes: {title or 'Unknown Title'}\n\n"
    if authors:
        metadata += f"*Authors:* {authors}\n"
    if institution:
        metadata += f"*Institution(s):* {institution}\n"
    if arxiv_id:
        metadata += f"*ArXiv ID:* {arxiv_id} (https://arxiv.org/abs/{arxiv_id})\n"
    if published_at:
        metadata += f"*Published:* {published_at}\n"
    if source:
        metadata += f"*Source/Dataset/Challenge:* {source}\n"
    metadata += "\n---\n\n"

    prompt = f"""
    You are an assistant for researchers. Summarise the following research paper
    into structured research notes using the exact template below.

    Requirements:
    - Always use Markdown formatting.
    - Always include every section in the template.
    - If a section has no information in the text, explicitly write: "No explicit information provided."
    - Keep technical details (datasets, baselines, metrics, equations, percentages).
    - Highlight key results (e.g., best scores) using **bold**.
    - Use bullet points where appropriate.

    --- TEMPLATE START ---
    {metadata}

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

    ---
    Text to summarise:
    {content}
    """

    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(prompt)
    return response.text
