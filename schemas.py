from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List

class EmailIngestIn(BaseModel):
    message_id: str = Field(..., description="Unique message identification string")
    sender: str = Field(..., description="Sender's exact email address")
    subject: str = Field(..., description="The subject line text of the email")
    body: str = Field(..., description="The raw main body content of the email")
    timestamp: str = Field(..., description="ISO 8601 formatted datetime string")
    thread_id: str = Field(..., description="Associated conversation thread identifier")