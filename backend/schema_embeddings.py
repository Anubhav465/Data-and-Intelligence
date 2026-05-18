import os
import faiss
import numpy as np
import cohere
from dotenv import load_dotenv
from schema_extractor import extract_schema

load_dotenv()

co = cohere.Client(os.getenv("COHERE_API_KEY"))

def chunk_schema(schema_text):
    chunks = schema_text.split("\n\n")
    return chunks


def generate_embeddings(chunks):
    response = co.embed(
        texts=chunks,
        model="embed-english-v3.0",
        input_type="search_document"
    )
    return np.array(response.embeddings).astype("float32")


def build_faiss_index(vectors):
    dimension = vectors.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(vectors)
    return index


def save_index(index):
    faiss.write_index(index, "schema_index.faiss")


def save_chunks(chunks):
    with open("schema_chunks.txt", "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(chunk + "\n---\n")


if __name__ == "__main__":
    print("Extracting schema...")
    schema_text = extract_schema()

    print("Chunking...")
    chunks = chunk_schema(schema_text)

    print("Generating embeddings...")
    vectors = generate_embeddings(chunks)

    print("Building FAISS index...")
    index = build_faiss_index(vectors)

    print("Saving index...")
    save_index(index)
    save_chunks(chunks)

    print("Done. Schema embeddings ready.")