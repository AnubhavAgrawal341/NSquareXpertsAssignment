# PDF Q&A Web Application

This is a Django-based web app that allows users to upload PDF documents (handling 500+ pages), process them using RAG (Retrieval-Augmented Generation) with OpenAI, and engage in conversational Q&A about the content. It features a chat-like interface for queries tied to each PDF, with history, auto-summarization, and entity extraction as bonuses.

## Features
- **Upload PDF**: Simple form to upload PDFs; auto-processes into chunks, embeddings, and FAISS vector store.
- **Chat Interface**: Ask questions about a specific PDF; responses use RAG for accuracy, with conversational history.
- **Multi-PDF Support**: List and select from uploaded PDFs to start/resume chats.
- **Bonus/Creative**:
  - Auto-summarization on upload (using LLM on sampled chunks).
  - Entity extraction (persons, dates, etc., via LLM NER on sampled content).
  - Persistent chat history per PDF.
  - Handles large files (tested with 500+ page PDFs like public domain books).
- **Tech Stack**: Django backend, LangChain for RAG, OpenAI LLM/embeddings, FAISS for vector search, SQLite DB.

## Setup
1. Clone the repo: `git clone <github-link>`
2. Create virtual env: `python -m venv env` then `source env/bin/activate` (or `env\Scripts\activate` on Windows).
3. Install dependencies: `pip install -r requirements.txt`
4. Create `.env` in root: Add `OPENAI_API_KEY=your_openai_key_here`
5. Make migrations: `python manage.py makemigrations` then `python manage.py migrate`
6. Run server: `python manage.py runserver`
7. Access at `http://127.0.0.1:8000/upload/` (or root routes to core).

## Usage
- Upload a PDF via the form; redirects to chat for that PDF.
- In chat: Type questions, submit; see history, summary, entities.
- List PDFs to switch chats.
- For API-like queries: POST to `/query/<pdf_id>/` with JSON {"query": "question"}.

## Testing with 500+ Page PDF
- Download a large PDF (e.g., "War and Peace" PDF ~1000 pages from Project Gutenberg).
- Upload via the interface; processing handles large files chunk-by-chunk.
- Query examples: "What is the main plot?" or follow-ups using history.

## Bonus Implementation
- Summary & entities generated during processing (limited to initial chunks to avoid token limits; can expand).
- Creative: Conversational context via last 3 messages in prompt for better follow-ups.

## Deployment Notes
- For production: Use PostgreSQL, secure CSRF, add auth, switch to remote vector DB like Pinecone.
- GitHub: <link>
- Demo Video: <google-drive-link>
- Implementation Video: <google-drive-link>

## Assignment Responses
| No | Instruction | Status/Links |
|----|-------------|--------------|
|1| Provide GitHub link for your assignment | <GitHub Link> |
|2| Record the end-to-end demo. | <Google Drive Link> |
|3| Record the “How you have implemented the assignment” | <Google Drive Link> |
|4| Did you implement Chat like interface? | Yes |
|5| Did you follow RAG approach? To process the file, chunk it, store embeddings, and retrieve relevant context for each query | Yes |
|6| Did you test your assignment with minimum 500 pages file? You should upload, any book in PDF format with more than 500 pages. | Yes |
|7| In this assignment, what creative functionality you have added? | Added auto-summarization on upload, entity extraction (NER), conversational history with context in prompts, multi-PDF listing/support for multiple chats. |