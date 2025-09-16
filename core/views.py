from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from .models import UploadedPDF, ChatMessage, ExtractedEntity
import json
import os
import shutil
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from django.views.decorators.csrf import csrf_exempt  # For simplicity in dev; remove in prod or handle CSRF properly

def is_valid_openai_key(key):
    if not key or key.startswith('sk-your-key') or key == 'placeholder':
        return False
    # Optional: More checks, e.g., len(key) == 51 and key.startswith('sk-')
    return True

# Helper function to process PDF: Load, chunk, embed, store FAISS
def process_pdf(uploaded_pdf):
    key = os.getenv('OPENAI_API_KEY')
    if not is_valid_openai_key(key):
        # Dummy mode
        uploaded_pdf.summary = "This is a dummy summary because no valid OpenAI API key is provided."
        store_path = os.path.join('vector_stores', str(uploaded_pdf.id))
        os.makedirs(store_path, exist_ok=True)  # Create empty store dir
        ExtractedEntity.objects.create(
            pdf=uploaded_pdf,
            entity_type='Dummy Type',
            entity_text='Placeholder Entity',
            count=1
        )
        return
    
    # Load PDF
    loader = PyPDFLoader(uploaded_pdf.file.path)
    documents = loader.load()
    
    # Chunk the text
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    chunks = text_splitter.split_documents(documents)
    
    # Generate embeddings
    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv('OPENAI_API_KEY'))
    
    # Create and save vector store
    vector_store = FAISS.from_documents(chunks, embeddings)
    store_path = os.path.join('vector_stores', str(uploaded_pdf.id))
    if os.path.exists(store_path):
        shutil.rmtree(store_path)
    os.makedirs(store_path)
    vector_store.save_local(store_path)
    
    # Bonus: Generate summary
    llm = ChatOpenAI(
        model_name="gpt-3.5-turbo",
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        temperature=0.2
    )
    summary_prompt = ChatPromptTemplate.from_template(
        "Summarize the following document in 200-300 words: {context}"
    )
    chain = summary_prompt | llm | StrOutputParser()
    # For large docs, summarize first few chunks or sample; here, concatenate limited text
    context = " ".join([chunk.page_content for chunk in chunks[:10]])  # Limit to avoid token limits
    summary = chain.invoke({"context": context})
    uploaded_pdf.summary = summary
    uploaded_pdf.save()
    
    # Bonus: Extract entities (simple NER using LLM)
    entity_prompt = ChatPromptTemplate.from_template(
        "Extract key entities (persons, organizations, dates, locations) from this text: {context}\n"
        "Format as JSON list: [{{\"type\": \"person\", \"text\": \"Name\", \"count\": 1}}, ...]"
    )
    entity_chain = entity_prompt | llm | StrOutputParser()
    entities_str = entity_chain.invoke({"context": context})  # Again, limited context
    try:
        entities = json.loads(entities_str)
        for ent in entities:
            ExtractedEntity.objects.create(
                pdf=uploaded_pdf,
                entity_type=ent.get('type', 'unknown'),
                entity_text=ent.get('text', ''),
                count=ent.get('count', 1)
            )
    except json.JSONDecodeError:
        pass  # Skip if parsing fails

# View for uploading PDF
@csrf_exempt  # Temp for POST from JS; secure later
def upload_pdf(request):
    if request.method == 'POST':
        if 'pdf_file' in request.FILES:
            pdf_file = request.FILES['pdf_file']
            uploaded_pdf = UploadedPDF.objects.create(file=pdf_file)
            
            try:
                process_pdf(uploaded_pdf)
                uploaded_pdf.processed = True
                uploaded_pdf.save()
                # Redirect to query page for this PDF to start "chat"
                return redirect('query_pdf', pdf_id=uploaded_pdf.id)
            except Exception as e:
                return HttpResponse(f"Error processing PDF: {str(e)}", status=500)
    
    # GET: Render upload form
    return render(request, 'upload.html')

# View for querying PDF (chat-like: post query, get answer, store history)
@csrf_exempt
def query_pdf(request, pdf_id):
    try:
        uploaded_pdf = UploadedPDF.objects.get(id=pdf_id)
        if not uploaded_pdf.processed:
            return HttpResponse("PDF not processed yet.", status=400)
    except UploadedPDF.DoesNotExist:
        return HttpResponse("PDF not found.", status=404)
    
    key = os.getenv('OPENAI_API_KEY')
    
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            query = body.get('query')
            if not query:
                return HttpResponse("No query provided.", status=400)
            
            if not is_valid_openai_key(key):
                # Dummy reply
                answer = f"Dummy reply to '{query}': This would be a real answer if a valid OpenAI API key was provided."
                ChatMessage.objects.create(pdf=uploaded_pdf, query=query, answer=answer)
                return JsonResponse({"answer": answer})
            
            # Load vector store
            embeddings = OpenAIEmbeddings(openai_api_key=os.getenv('OPENAI_API_KEY'))
            store_path = os.path.join('vector_stores', str(pdf_id))
            vector_store = FAISS.load_local(store_path, embeddings, allow_dangerous_deserialization=True)
            
            # Set up LLM and RAG chain
            llm = ChatOpenAI(
                model_name="gpt-3.5-turbo",
                openai_api_key=os.getenv('OPENAI_API_KEY'),
                temperature=0.0
            )
            prompt_template = """Use the following pieces of context to answer the question. 
            If you don't know the answer, say you don't know.

            {context}

            Question: {question}
            Answer:"""
            PROMPT = PromptTemplate(
                template=prompt_template, input_variables=["context", "question"]
            )
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=vector_store.as_retriever(search_kwargs={"k": 5}),
                chain_type_kwargs={"prompt": PROMPT}
            )
            
            # For conversational: Include recent history in prompt (last 3 messages)
            history = ChatMessage.objects.filter(pdf=uploaded_pdf).order_by('-timestamp')[:3]
            history_str = "\n".join([f"User: {msg.query}\nAI: {msg.answer}" for msg in reversed(history)])
            full_query = f"Previous conversation:\n{history_str}\n\nCurrent question: {query}" if history else query
            
            # Run query
            result = qa_chain.invoke({"query": full_query})
            answer = result['result']
            
            # Store in chat history
            ChatMessage.objects.create(pdf=uploaded_pdf, query=query, answer=answer)
            
            return JsonResponse({"answer": answer})
        except Exception as e:
            return HttpResponse(f"Error querying PDF: {str(e)}", status=500)
    
    # GET: Render chat interface with history
    messages = ChatMessage.objects.filter(pdf=uploaded_pdf)
    context = {
        'pdf_id': pdf_id,
        'pdf': uploaded_pdf,
        'messages': messages,
        'summary': uploaded_pdf.summary,  # Bonus: Show summary
        'entities': uploaded_pdf.entities.all()  # Bonus: Show entities
    }
    return render(request, 'query.html', context)

# Bonus: Get summary (if not already in query view)
def get_summary(request, pdf_id):
    try:
        uploaded_pdf = UploadedPDF.objects.get(id=pdf_id)
        return JsonResponse({"summary": uploaded_pdf.summary})
    except UploadedPDF.DoesNotExist:
        return HttpResponse("PDF not found.", status=404)

# Bonus: Extract entities (if not done on upload, or re-extract)
def extract_entities(request, pdf_id):
    try:
        uploaded_pdf = UploadedPDF.objects.get(id=pdf_id)
        entities = [{"type": e.entity_type, "text": e.entity_text, "count": e.count} for e in uploaded_pdf.entities.all()]
        return JsonResponse({"entities": entities})
    except UploadedPDF.DoesNotExist:
        return HttpResponse("PDF not found.", status=404)

# Bonus: List uploaded PDFs (to start new chat or select existing)
def list_pdfs(request):
    pdfs = UploadedPDF.objects.filter(processed=True)
    context = {'pdfs': pdfs}
    return render(request, 'list.html', context)  # Template to be added later