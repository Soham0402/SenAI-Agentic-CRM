from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import html

from database import get_db
import models
import schemas
from heuristics import run_heuristic_filter
from rag import retrieve_relevant_context
from classifier import analyze_and_classify_email

app = FastAPI(title="SenAI Agentic CRM Platform")

@app.get("/rag/search")
def debug_rag_search(q: str, db: Session = Depends(get_db)):
    """
    Debug endpoint: Interrogate internal documentation directly to verify 
    vector retrieval accuracy and distance scores.
    """
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' cannot be empty.")
        
    hits = retrieve_relevant_context(q, db, limit=3)
    return {"query": q, "results": hits}

@app.post("/api/ingest", status_code=status.HTTP_201_CREATED)
def ingest_email(payload: schemas.EmailIngestIn, db: Session = Depends(get_db)):
    # 1. Process string structural anomalies and unescape HTML sequences
    body_clean = html.unescape(payload.body.strip())
    subject_clean = payload.subject.strip()
    
    # Validation against completely blank transmissions
    if not subject_clean and not body_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Malformed Content: Email subject and body cannot both be empty."
        )
        
    # Prevent buffer issues by truncating payloads longer than 10k characters
    if len(body_clean) > 10000:
        body_clean = body_clean[:10000] + "... [Truncated for Processing]"

    # Safely transform incoming string timestamps into native DateTime objects
    try:
        dt_timestamp = datetime.fromisoformat(payload.timestamp.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid ISO format detected within incoming timestamp."
        )

    # 2. Idempotency Assertion: Avoid redundant operations on existing unique message IDs
    existing_email = db.query(models.Email).filter(models.Email.message_id == payload.message_id).first()
    if existing_email:
        return {
            "status": "ignored", 
            "reason": "Duplicate message_id bypassed safely via Idempotency protection.", 
            "job_id": f"job_dup_{payload.message_id}"
        }

    # 3. Contextual Lookup: Provision clean missing profiles automatically
    contact = db.query(models.Contact).filter(models.Contact.email == payload.sender).first()
    if not contact:
        contact = models.Contact(
            email=payload.sender,
            name=payload.sender.split("@")[0].replace(".", " ").title(),
            status="Active",
            account_value=2400000.0 if "bigcorp" in payload.sender else 500.0
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)

    # 4. Trigger the Low-Latency Layer 1 Synchronous Filter
    h_results = run_heuristic_filter(subject_clean, body_clean, payload.sender)

    # 5. Thread Structuring: Bind related records chronologically
    thread = db.query(models.Thread).filter(models.Thread.thread_id == payload.thread_id).first()
    if not thread:
        thread = models.Thread(
            thread_id=payload.thread_id,
            subject=subject_clean,
            sender_email=payload.sender,
            first_seen_at=dt_timestamp,
            last_updated_at=dt_timestamp,
            status="Open" if not h_results["is_spam"] else "Ignored"
        )
        db.add(thread)
        db.commit()
        db.refresh(thread)
    else:
        # Gracefully handle out-of-order timestamp indexing
        if dt_timestamp > thread.last_updated_at:
            thread.last_updated_at = dt_timestamp
        if dt_timestamp < thread.first_seen_at:
            thread.first_seen_at = dt_timestamp
        db.commit()

    # 6. Persist Email Data Model Entries
    new_email = models.Email(
        thread_id=payload.thread_id,
        message_id=payload.message_id,
        sender=payload.sender,
        subject=subject_clean,
        body=body_clean,
        timestamp=dt_timestamp,
        category=h_results["category"],
        urgency=h_results["urgency"],
        requires_human=True if h_results["is_security"] or h_results["urgency"] == "Critical" else False,
        status="Received" if not h_results["is_spam"] else "Ignored"
    )
    db.add(new_email)
    
    # Track interaction timestamps
    contact.last_contact_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": "processing" if not h_results["is_spam"] else "ignored",
        "reason": "Queued for LLM Processing Layer" if not h_results["is_spam"] else "Filtered out by System Heuristics",
        "job_id": f"job_{payload.message_id}"
    }

@app.post("/api/process/{email_id}")
def process_email_intelligence(email_id: int, db: Session = Depends(get_db)):
    """
    Processes an ingested email through Layer 2 LLM parsing and updates
    structural entities along with web intelligence data.
    """
    classification = analyze_and_classify_email(email_id, db)
    if "error" in classification:
        raise HTTPException(status_code=404, detail=classification["error"])
        
    return {
        "status": "success",
        "email_id": email_id,
        "analysis_results": classification
    }