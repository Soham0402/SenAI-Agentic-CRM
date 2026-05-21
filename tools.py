import json
from sqlalchemy.orm import Session
import models
from rag import retrieve_relevant_context

def search_knowledge_base(query: str, db: Session) -> str:
    """RAG tool to search across internal policies (pricing, SLA, refunds, compliance)."""
    hits = retrieve_relevant_context(query, db, limit=2)
    return json.dumps([{"source": h["source_doc"], "text": h["chunk_text"]} for h in hits])

def get_contact_profile(email: str, db: Session) -> str:
    """Fetches CRM profile indicators including VIP standing, contract value, and calculated churn risks."""
    contact = db.query(models.Contact).filter(models.Contact.email == email).first()
    if not contact:
        return f"No contact record found for email: {email}"
    return json.dumps({
        "email": contact.email,
        "name": contact.name,
        "status": contact.status,
        "account_value": contact.account_value,
        "churn_risk_score": contact.churn_risk_score
    })

def create_internal_ticket(title: str, body: str, assignee: str, db: Session) -> str:
    """Generates an internal engineering, operations, or compliance ticket tracking task."""
    return f"SUCCESS: Internal Ticket created tracking '{title}', explicitly assigned to '{assignee}' queue."

def flag_for_legal(email_id: int, issue_type: str, db: Session) -> str:
    """Routes high-risk corporate legal liabilities directly to the corporate legal desk."""
    email_rec = db.query(models.Email).filter(models.Email.id == email_id).first()
    if email_rec:
        email_rec.status = "Escalated"
        # Update associated conversation thread matrix status
        thread = db.query(models.Thread).filter(models.Thread.thread_id == email_rec.thread_id).first()
        if thread:
            thread.status = "Escalated"
            thread.assigned_to = "legal@internal.com"
        db.commit()
    return f"CRITICAL: Email {email_id} flagged for Legal review. Operational queue moved to legal@internal.com."

def escalate_to_human(email_id: int, reason: str, priority: str, db: Session) -> str:
    """Escalates complex configurations or critical client issues directly to standard human support queues."""
    email_rec = db.query(models.Email).filter(models.Email.id == email_id).first()
    if email_rec:
        email_rec.status = "Escalated"
        thread = db.query(models.Thread).filter(models.Thread.thread_id == email_rec.thread_id).first()
        if thread:
            thread.status = "Escalated"
            thread.assigned_to = "human-support-triage@internal.com"
        db.commit()
    return f"SUCCESS: Email {email_id} escalated to human team due to: {reason}. Priority level set to {priority}."