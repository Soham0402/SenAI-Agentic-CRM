from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import datetime

from database import get_db
import models
from bonus_features import generate_thread_summary, calculate_dynamic_churn_risk

router = APIRouter()

@router.get("/dashboard/stats")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Surfaces count matrices for core application state overview badges."""
    pending = db.query(models.Email).filter(models.Email.status == "Received").count()
    replied = db.query(models.Email).filter(models.Email.status == "Replied").count()
    escalated = db.query(models.Email).filter(models.Email.status == "Escalated").count()
    critical = db.query(models.Email).filter(models.Email.urgency == "Critical").count()
    spam = db.query(models.Email).filter(models.Email.category == "Spam").count()
    
    return {
        "pending": pending,
        "replied": replied,
        "escalated": escalated,
        "critical": critical,
        "spam_filtered": spam
    }

@router.get("/threads/{contact_email}")
def fetch_complete_thread_workspace(contact_email: str, db: Session = Depends(get_db)):
    """Returns chronological conversation rows with actions and summaries."""
    threads = db.query(models.Thread).filter(models.Thread.sender_email == contact_email).all()
    if not threads:
        raise HTTPException(status_code=404, detail="No active threads identified for this user address.")
        
    response_payload = []
    for thread in threads:
        emails = db.query(models.Email).filter(models.Email.thread_id == thread.thread_id).order_by(models.Email.timestamp.asc()).all()
        summary = generate_thread_summary(thread.thread_id, db) if len(emails) >= 3 else None
        
        email_data = []
        for e in emails:
            action = db.query(models.Action).filter(models.Action.email_id == e.id).first()
            email_data.append({
                "id": e.id,
                "sender": e.sender,  # <--- ADD THIS LINE
                "subject": e.subject,
                "body": e.body,
                "timestamp": e.timestamp,
                "category": e.category,
                "urgency": e.urgency,
                "sentiment_score": e.sentiment_score,
                "status": e.status,
                "agent_log": action.agent_reasoning_log if action else None,
                "proposed_draft": action.proposed_content if action else None
            })
            
        response_payload.append({
            "thread_id": thread.thread_id,
            "subject": thread.subject,
            "status": thread.status,
            "assigned_to": thread.assigned_to,
            "executive_summary": summary,
            "emails": email_data
        })
        
    return response_payload

@router.patch("/drafts/{action_id}")
def edit_proposed_draft_reply(action_id: int, new_content: dict, db: Session = Depends(get_db)):
    """
    Bonus Feature 3: Implements a Human-in-the-Loop tracking model.
    Logs the changes made by a human agent to train or fine-tune prompts later.
    """
    action = db.query(models.Action).filter(models.Action.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Target agent action row not found.")
        
    original_text = action.proposed_content
    updated_text = new_content.get("body")
    
    # Calculate structured diff payload
    audit_diff = {
        "original_draft": original_text,
        "revised_draft": updated_text,
        "delta_modifications_detected": original_text != updated_text
    }
    
    # Update draft content and track the audit footprint
    action.proposed_content = updated_text
    
    new_log = models.AuditLog(
        entity_type="Action_Draft",
        entity_id=str(action_id),
        action="Human_Draft_Modification",
        performed_by="human_agent_operator",
        diff=audit_diff
    )
    db.add(new_log)
    db.commit()
    return {"status": "success", "message": "Draft payload updated and modifications logged."}

@router.get("/analytics/sentiment-trend")
def query_sentiment_trends(sender: str = None, db: Session = Depends(get_db)):
    """Generates time-series moving averages mapping client sentiment stability over time."""
    query = db.query(models.Email.timestamp, models.Email.sentiment_score).filter(models.Email.sentiment_score.isnot(None))
    if sender:
        query = query.filter(models.Email.sender == sender)
        
    results = query.order_by(models.Email.timestamp.asc()).all()
    return [{"timestamp": r[0].isoformat(), "sentiment_score": r[1]} for r in results]

@router.get("/analytics/category-breakdown")
def get_category_breakdown(db: Session = Depends(get_db)):
    """Analytics: Category distribution."""
    results = db.query(models.Email.category, func.count(models.Email.id)).group_by(models.Email.category).all()
    return {category: count for category, count in results}

@router.get("/audit/{entity_type}/{entity_id}")
def get_audit_history(entity_type: str, entity_id: str, db: Session = Depends(get_db)):
    """Fetches full audit history for any entity."""
    logs = db.query(models.AuditLog).filter(models.AuditLog.entity_type == entity_type, models.AuditLog.entity_id == entity_id).all()
    return logs

@router.get("/contacts/{email}")
def get_contact_profile_api(email: str, db: Session = Depends(get_db)):
    """Fetches Contact profile."""
    contact = db.query(models.Contact).filter(models.Contact.email == email).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact

@router.patch("/contacts/{email}/status")
def update_contact_status(email: str, status_update: dict, db: Session = Depends(get_db)):
    """Updates contact status (VIP, Blocked, etc.)."""
    contact = db.query(models.Contact).filter(models.Contact.email == email).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    contact.status = status_update.get("status", contact.status)
    db.commit()
    return {"message": f"Status updated to {contact.status}"}
    
@router.get("/intelligence/reputation")
def get_reputation(company_name: str, db: Session = Depends(get_db)):
    """Latest scraped public sentiment for company."""
    # Assuming fetch_web_intelligence is imported from scraper
    from scraper import fetch_web_intelligence
    return fetch_web_intelligence(company_name, db)