import os
import json
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
import models

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def generate_thread_summary(thread_id: str, db: Session) -> str:
    """
    Bonus Feature 1: Automatically generates a crisp, 3-sentence executive
    summary for long conversation threads.
    """
    emails = db.query(models.Email).filter(
        models.Email.thread_id == thread_id
    ).order_by(models.Email.timestamp.asc()).all()
    
    if len(emails) < 3:
        return "Summary generation skipped: Thread history requires higher conversation volume."
        
    compiled_body = "\n".join([f"Sender: {e.sender} | Body: {e.body}" for e in emails])
    
    prompt = f"""
    Analyze the following customer service email thread conversation.
    Provide a strict, exactly 3-sentence high-level executive summary of the core issues and current status.
    Do not add extra formatting, labels, or bullet points.
    
    === CONVERSATION THREAD ===
    {compiled_body}
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash', 
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2)
    )
    return response.text.strip()

def calculate_dynamic_churn_risk(email_addr: str, db: Session) -> float:
    """
    Bonus Feature 2: Calculates customer churn risk based on consecutive 
    negative interactions and unanswered critical complaints.
    """
    contact = db.query(models.Contact).filter(models.Contact.email == email_addr).first()
    if not contact:
        return 0.0
        
    emails = db.query(models.Email).filter(
        models.Email.sender == email_addr
    ).order_by(models.Email.timestamp.desc()).limit(5).all()
    
    if not emails:
        return 0.0
        
    # Heuristic math based on sentiment trend degradation
    negative_count = sum(1 for e in emails if e.sentiment_score and e.sentiment_score < -0.4)
    has_unresolved_complaint = any(e.category == "Complaint" and e.status != "Replied" for e in emails)
    
    base_risk = (negative_count / len(emails)) * 0.7
    if has_unresolved_complaint:
        base_risk += 0.3
        
    final_risk = min(max(base_risk, 0.0), 1.0)
    
    # Update relational schema properties
    contact.churn_risk_score = final_risk
    db.commit()
    return final_risk