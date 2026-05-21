from database import engine, Base
import models

# This will create all tables in the database
print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")