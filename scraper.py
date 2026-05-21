import datetime
from sqlalchemy.orm import Session
import models

def check_robots_txt(url: str) -> bool:
    """
    Mandatory compliance check before touching an external domain.
    """
    # Simple simulated compliance rule
    if "blocked-bot" in url:
        return False
    return True

def fetch_web_intelligence(company_name: str, db: Session) -> dict:
    """
    Retrieves company reputation signals. Checks the DB cache first 
    to preserve downstream rate limits.
    """
    target_url = f"https://www.trustpilot.com/review/{company_name.lower().replace(' ', '')}.com"
    
    if not check_robots_txt(target_url):
        return {"error": "Scraping disallowed by target domain robots.txt compliance rules."}

    # Check for unexpired cache entry (Valid for 6 hours)
    now = datetime.datetime.utcnow()
    cached = db.query(models.WebIntelligenceCache).filter(
        models.WebIntelligenceCache.target_entity == company_name,
        models.WebIntelligenceCache.expires_at > now
    ).first()

    if cached:
        return cached.scraped_data

    # Scraping Simulation: Returns data formatted exactly like public scrapers
    # In a real environment, you would use httpx + BeautifulSoup here.
    simulated_scraped_data = {
        "source": "Trustpilot/G2 Scraper Engine",
        "company": company_name,
        "star_rating": 3.4 if "retail-co" in company_name.lower() else 4.5,
        "recent_review_count": 142,
        "common_complaint_themes": [
            "Delayed customer support response windows",
            "Slow loading times on main reporting dashboards",
            "Billing platform synchronization issues"
        ],
        "market_sentiment": "Deteriorating due to unresolved infrastructure latency issues."
    }

    # Persist scraped data inside database cache layer
    new_cache = models.WebIntelligenceCache(
        source_url=target_url,
        target_entity=company_name,
        scraped_data=simulated_scraped_data,
        scraped_at=now,
        expires_at=now + datetime.timedelta(hours=6)
    )
    db.add(new_cache)
    db.commit()

    return simulated_scraped_data