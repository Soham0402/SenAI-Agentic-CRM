from sqlalchemy import text
from database import engine, Base
import models

def init_db():
    print("Connecting to database to enable pgvector extension...")
    
    # 1. Manually connect and enable the extension
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
        
    print("pgvector extension enabled successfully!")

    # 2. Create the tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")

if __name__ == "__main__":
    init_db()