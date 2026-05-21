import os
import glob
from database import SessionLocal
import models
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

def chunk_text(text: str, max_chars: int = 1000, overlap: int = 150):

    chunks = []
    start = 0

    while start < len(text):

        end = start + max_chars
        chunks.append(text[start:end])

        start += (max_chars - overlap)

    return chunks


def seed_knowledge_base():

    db = SessionLocal()

    # Clear old vectors
    db.query(models.KnowledgeChunk).delete()
    db.commit()

    print("Beginning Markdown ingestion...")

    md_files = glob.glob("knowledge_base/*.md")

    for file_path in md_files:

        doc_name = os.path.basename(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = chunk_text(content)

        print(f"Processing '{doc_name}' -> {len(chunks)} chunks")

        for idx, chunk in enumerate(chunks):

            if not chunk.strip():
                continue

            try:

                response = client.models.embed_content(
                    model="gemini-embedding-2",
                    contents=chunk,
                    config=types.EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT"
                    )
                )

                # FIXED LINE
                embedding_vector = response.embeddings[0].values

                db_chunk = models.KnowledgeChunk(
                    source_doc=doc_name,
                    chunk_text=chunk,
                    embedding=embedding_vector
                )

                db.add(db_chunk)

                print(f"Inserted chunk {idx+1}")

            except Exception as e:

                print(f"Embedding failed for chunk {idx+1}: {e}")

    db.commit()
    db.close()

    print("Knowledge base seeded successfully!")


if __name__ == "__main__":
    seed_knowledge_base()