import os
import json
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from dotenv import load_dotenv

import models
from rag import retrieve_relevant_context
from scraper import fetch_web_intelligence

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Structured JSON Schema to feed Gemini (forces output compliance)
CLASSIFICATION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "category": {"type": "STRING", "description": "Must be: Complaint | Inquiry | Bug Report | Feature Request | Compliance | Legal | Billing | Spam | Internal | Other"},
        "sentiment": {"type": "STRING", "description": "Must be: Positive | Neutral | Negative | Mixed"},
        "sentiment_score": {"type": "NUMBER", "description": "Float between -1.0 (very negative) and +1.0 (very positive)"},
        "urgency": {"type": "STRING", "description": "Must be: Critical | High | Medium | Low"},
        "requires_human": {"type": "BOOLEAN"},
        "escalation_reason": {"type": "STRING", "nullable": True},
        "suggested_reply": {"type": "STRING", "nullable": True, "description": "Draft response ONLY if requires_human is false, otherwise null"},
        "confidence": {"type": "NUMBER"},
        "detected_entities": {
            "type": "OBJECT",
            "properties": {
                "order_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
                "ticket_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
                "monetary_amounts": {"type": "ARRAY", "items": {"type": "STRING"}},
                "deadlines": {"type": "ARRAY", "items": {"type": "STRING"}},
                "products_mentioned": {"type": "ARRAY", "items": {"type": "STRING"}}
            }
        }
    },
    "required": ["category", "sentiment", "sentiment_score", "urgency", "requires_human", "confidence", "detected_entities"]
}

def analyze_and_classify_email(email_id: int, db: Session) -> dict:
    # 1. Fetch Email and historical context from DB
    email_record = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not email_record:
        return {"error": "Email record not found."}

    # Fetch past threads for conversation tracking
    historical_emails = db.query(models.Email).filter(
        models.Email.thread_id == email_record.thread_id,
        models.Email.id < email_id
    ).order_by(models.Email.timestamp.asc()).all()

    thread_history_text = "\n".join([f"From: {e.sender} | Body: {e.body}" for e in historical_emails])

    # 2. Extract Top 3 RAG context chunks matching this email's core message
    rag_hits = retrieve_relevant_context(f"{email_record.subject} {email_record.body}", db, limit=3)
    rag_context = "\n".join([f"Source [{h['source_doc']}]: {h['chunk_text']}" for h in rag_hits])

    # 3. Handle Web Intelligence Triggering Conditions
    market_intelligence = None
    email_text_upper = f"{email_record.subject} {email_record.body}".upper()
    
    # Conditional Trigger Check
    is_reputation_threat = any(kw in email_text_upper for kw in ["REVIEW", "TRUSTPILOT", "G2", "TWITTER", "POST PUBLICLY"])
    is_high_risk_complaint = (email_record.category == "Complaint" and email_record.urgency in ["High", "Critical"])
    
    if is_reputation_threat or is_high_risk_complaint:
        # Determine company based on sender domain extensions
        company_domain = email_record.sender.split("@")[-1].split(".")[0]
        market_intelligence = fetch_web_intelligence(company_domain, db)

    # 4. Construct Prompt
    prompt = f"""
    You are an advanced multi-layer CRM operations engineering intelligence tool. 
    Analyze the incoming target email carefully based on past thread histories, policy configurations, and optional external market metrics.

    === TARGET EMAIL ===
    From: {email_record.sender}
    Subject: {email_record.subject}
    Body: {email_record.body}

    === CONVERSATION THREAD HISTORY ===
    {thread_history_text if thread_history_text else "No prior history on this thread."}

    === INTERNAL COMPANY POLICY DOCUMENTS (RAG) ===
    {rag_context}

    === EXTERNAL PUBLIC MARKET INTELLIGENCE ===
    {json.dumps(market_intelligence) if market_intelligence else "No reputation data triggered."}

    === INSTRUCTIONS ===
    - Resolve conflicting signals gracefully: if user is happy with tech but furious about pricing billing, set category as Billing or Complaint.
    - If confidence falls below 0.70 or urgency is Critical, force 'requires_human' to true.
    - If drafting a response ('suggested_reply'), you MUST explicitly cite your source document from the RAG parameters provided.
    """

    # Change model='gemini-1.5-pro' to 'gemini-2.5-flash'
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CLASSIFICATION_SCHEMA,
            temperature=0.1
        )
    )

    result_json = json.loads(response.text)

    # 6. Synchronize Data Back down into PostgreSQL models
    email_record.category = result_json.get("category", email_record.category)
    email_record.sentiment_score = result_json.get("sentiment_score")
    email_record.urgency = result_json.get("urgency", email_record.urgency)
    email_record.requires_human = result_json.get("requires_human", email_record.requires_human)
    email_record.confidence = result_json.get("confidence")
    email_record.raw_entities = result_json.get("detected_entities")
    email_record.status = "Processing"
    db.commit()

    return result_json