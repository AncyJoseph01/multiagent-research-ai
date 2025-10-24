# 📚 Agentic Research Assistant

An **AI-powered academic research assistant** that helps users **curate their own paper library** and **chat with research context**.  
The system combines **document management**, **retrieval-augmented generation (RAG)**, **multi-stage chain-of-thought reasoning**, and **automatic arXiv integration** to deliver structured academic insights.  

This project is an **Agentic AI system**  not just a chatbot or a RAG pipeline.  
It goes beyond simple Q&A by **reasoning, acting, and adapting**:

- 🧠 **Reasoning**: Uses a multi-stage chain-of-thought process (*Exploration → Draft → Reflection → Synthesis*) before answering.  
- ⚡ **Acting**: Takes autonomous actions like fetching arXiv papers, downloading PDFs, chunking, embedding, and summarising them.  
- 🔄 **Adapting**: Expands and updates the user’s personal research library automatically, skipping duplicates and enriching future chats.  

Unlike a static RAG system, this assistant can **plan**, **take decisions**, and **improve its own knowledge base** over time the hallmarks of an **agentic AI** system.  


---

## 🚀 Features

### 📝 Paper Management
- Upload your own research **PDFs**.  
- Search and fetch papers directly from **arXiv by keyword**.  
- System automatically:
  - Extracts full text from PDFs  
  - Splits into chunks & creates embeddings (via pgvector)  
  - Generates structured **research-style summaries**  
- View all stored papers and their summaries in your personal library.  

### 🤖 Agentic Chat Assistant
- Ask research questions in natural language.  
- Assistant retrieves relevant papers from your library (RAG).  
- Runs **multi-stage chain-of-thought reasoning** (*Exploration → Draft → Reflection → Synthesis*).  
- If missing knowledge is detected, it can:
  - Extract arXiv IDs from reasoning  
  - Fetch & process new papers automatically  
- Produces structured, academic-style answers in Markdown.  
- Stores all queries, answers, and reasoning transcripts.  

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy  
- **Database:** PostgreSQL + [pgvector](https://github.com/pgvector/pgvector) (for embeddings)  
- **LLM:** Google Gemini (`gemini-2.5-pro`)  

- **Services:**
  - `embedding_service` → creates & saves embeddings  
  - `retrieval_service` → retrieves top-k relevant chunks  
  - `pdf_service` → extracts text & splits into chunks  
  - `arxiv_service` → fetches papers from arXiv API  
  - `summariser_service` → generates structured summaries  
  - `research_assistant` → orchestrates RAG + CoT + agentic paper fetching  

---

## ⚙️ How It Works

### 📥 Paper Management
1. User uploads a **PDF** or enters an **arXiv keyword**.  
2. System downloads/extracts text → chunks → embeddings.  
3. Generates a **structured summary** (research-style).  
4. Paper, summary, and embeddings are stored for future queries.  

### 💬 Chat with Research Assistant
1. User asks a research question.  
2. System embeds query → retrieves **top-k relevant papers**.  
3. Runs **multi-stage reasoning** with context:
   - *Exploration → Draft → Reflection → Synthesis*  
4. If reasoning suggests **new arXiv papers**, system:
   - Verifies ID, downloads PDF, extracts text, creates embeddings, and summarises.  
   - Skips duplicates already in database.  
5. Produces a **final structured answer** in Markdown.  
6. Saves query, answer, and full CoT transcript to DB.  

---
