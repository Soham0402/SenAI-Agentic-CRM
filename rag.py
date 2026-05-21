import os
from sqlalchemy.orm import Session
from sqlalchemy import text
from google import genai
from google.genai import types
from typing import List, Dict, Any
from dotenv import load_dotenv

import models

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def get_query_embedding(query: str) -> List[float]:

    response = client.models.embed_content(
        model="gemini-embedding-2",
        contents=query,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY"
        )
    )

    return response.embeddings[0].values


def retrieve_relevant_context(
    query: str,
    db: Session,
    limit: int = 3
) -> List[Dict[str, Any]]:

    query_vector = get_query_embedding(query)

    sql_query = text("""
        SELECT
            id,
            source_doc,
            chunk_text,
            (1 - (embedding <=> :vector::vector)) AS similarity
        FROM knowledge_chunks
        ORDER BY embedding <=> :vector::vector
        LIMIT :limit
    """)

    results = db.execute(
        sql_query,
        {
            "vector": str(query_vector),
            "limit": limit
        }
    ).fetchall()

    context_list = []

    for row in results:

        context_list.append({
            "id": row.id,
            "source_doc": row.source_doc,
            "chunk_text": row.chunk_text,
            "similarity": float(row.similarity)
        })

    return context_list