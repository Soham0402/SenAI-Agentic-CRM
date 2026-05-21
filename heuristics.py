import re
from typing import Dict, Any

def run_heuristic_filter(subject: str, body: str, sender: str) -> Dict[str, Any]:
    """
    Executes synchronous string parsing for immediate categorization in sub-10ms.
    """
    text_to_check = f"{subject} {body}".upper()
    sender_lower = sender.lower()
    
    # 1. Internal Email Routing Flag
    is_internal = sender_lower.endswith("@internal.com") or sender_lower.endswith("@mycompany.com")
    
    # 2. Heuristic Spam Blocklist matching
    spam_keywords = ["SEO PITCH", "BOOST YOUR SEO", "NIGERIAN PRINCE", "INHERITANCE OF", "MARKETING-GURU"]
    is_spam = any(kw in text_to_check for kw in spam_keywords) or "MARKETING-GURU.IO" in sender_lower
    
    # 3. Security Breach & High Risk Isolation
    security_keywords = ["ALERT: SUSPICIOUS LOGIN", "RANSOMWARE", "WE HAVE YOUR DATA - PAY NOW", "EXFILTRATED"]
    is_security = any(kw in text_to_check for kw in security_keywords) or "1A2B3C4D5E6F" in text_to_check
    
    # 4. Keyword Urgency Evaluation
    urgency_keywords = ["URGENT", "P0", "LEGAL", "CEASE AND DESIST", "CRITICAL BUG"]
    has_urgency_words = any(kw in text_to_check for kw in urgency_keywords)
    
    urgency = "Low"
    if is_security or "P0" in text_to_check or "CEASE AND DESIST" in text_to_check:
        urgency = "Critical"
    elif has_urgency_words:
        urgency = "High"
        
    category = "Other"
    if is_spam:
        category = "Spam"
    elif is_internal:
        category = "Internal"
        
    return {
        "category": category,
        "urgency": urgency,
        "is_security": is_security,
        "is_spam": is_spam,
        "is_internal": is_internal
    }