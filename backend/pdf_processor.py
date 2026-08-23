import os
import time
import datetime
import requests
import fitz  # PyMuPDF
from pymongo import MongoClient

def get_mongo_db():
    mongo_url = os.getenv("MONGO_URL", "mongodb://mongo:27017")
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
    if "/" in mongo_url.split("mongodb://")[-1]:
        return client.get_default_database()
    return client.get_database("investment_tools")

def query_llm(prompt: str, context: str = ""):
    llm_url = os.getenv("LLM_URL", "http://localhost:8080/v1/chat/completions")
    try:
        r = requests.post(
            llm_url,
            json={
                "messages": [
                    {"role": "system", "content": "You are an AI that analyzes French newspaper PDFs (like Kiosque à journaux) to extract economic and geopolitical insights."},
                    {"role": "user", "content": f"{context}\n\nTask: {prompt}"}
                ],
                "max_tokens": 1000,
                "temperature": 0.3,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"LLM Error: {e}")
        return ""

def process_pdf(file_path):
    # Extract text using PyMuPDF
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
    except Exception as e:
        print(f"Failed to read PDF {file_path}: {e}")
        return []

    # If the PDF is huge, we should chunk it. We'll use the LLM to identify the Sommaire (table of contents)
    first_pages = text[:5000] # Provide first 5000 chars to find sommaire
    
    sommaire_prompt = "Voici le début d'un document. Trouve le sommaire ou l'édito et liste les chapitres principaux qui parlent d'économie ou de géopolitique, ainsi que leurs numéros de page si possible."
    sommaire_extraction = query_llm(sommaire_prompt, first_pages)
    
    print("--- Extracted Sommaire ---")
    print(sommaire_extraction)
    
    # In a real pipeline, we'd split the PDF dynamically based on the parsed TOC.
    # For now, we split the text into raw chunks and ask the LLM if it contains economy/geopolitics
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    relevant_chapters = []
    
    for i, chunk in enumerate(chunks[:5]): # Limit to first 5 chunks for performance during demo
        cat_prompt = "Ce texte parle-t-il principalement d'économie, de finance ou de géopolitique internationale ? Réponds par 'OUI' ou 'NON' suivi d'un bref résumé."
        result = query_llm(cat_prompt, chunk)
        if result.startswith("OUI") or "OUI" in result[:10]:
            relevant_chapters.append({
                "chapter_index": i,
                "summary": result,
                "content": chunk[:1000] # store preview
            })
            
    return relevant_chapters

def run_worker():
    print("Starting PDF Processing Worker...")
    db = get_mongo_db()
    
    while True:
        try:
            # Find unprocessed PDFs
            msg = db.messages.find_one({
                "messageType": "documentMessage",
                "processed_for_insights": {"$exists": False}
            })
            
            if msg and 'media' in msg and 'filePath' in msg['media']:
                file_path = msg['media']['filePath']
                
                # Remap whatsapp-bot path to backend path
                # whatsapp-bot saves as /usr/src/app/downloads/...
                # backend mounts it at /app/downloads/...
                local_path = file_path.replace("/usr/src/app/downloads", "/app/downloads")
                
                print(f"Processing PDF: {local_path}")
                if os.path.exists(local_path):
                    chapters = process_pdf(local_path)
                    
                    db.messages.update_one(
                        {"_id": msg["_id"]},
                        {"$set": {
                            "processed_for_insights": True,
                            "extracted_chapters": chapters,
                            "processed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                        }}
                    )
                    print(f"Successfully processed {local_path}. Found {len(chapters)} relevant chapters.")
                else:
                    print(f"File not found: {local_path}")
                    db.messages.update_one(
                        {"_id": msg["_id"]},
                        {"$set": {"processed_for_insights": "error_file_missing"}}
                    )
            else:
                time.sleep(10) # No new PDFs, sleep
                
        except Exception as e:
            print(f"Worker Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_worker()
