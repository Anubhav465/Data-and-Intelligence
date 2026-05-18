import os
import faiss
import numpy as np
import cohere
from dotenv import load_dotenv

load_dotenv()

co = cohere.Client(os.getenv("COHERE_API_KEY"))

# Load FAISS index
index = faiss.read_index("schema_index.faiss")

# Load schema chunks
with open("schema_chunks.txt", "r", encoding="utf-8") as f:
    raw = f.read()

chunks = [c.strip() for c in raw.split("---") if c.strip()]


def embed_query(query):
    response = co.embed(
        texts=[query],
        model="embed-english-v3.0",
        input_type="search_query"
    )
    return np.array(response.embeddings).astype("float32")


def retrieve_relevant_schema(query, top_k=5):
    query_vector = embed_query(query)

    distances, indices = index.search(query_vector, top_k)

    relevant_chunks = [chunks[i] for i in indices[0]]

    return relevant_chunks


if __name__ == "__main__":
    test_query = "Which states have the highest delivery delays?"
    results = retrieve_relevant_schema(test_query)

    print("Relevant Schema:")
    print("=" * 50)
    for r in results:
        print(r)
        print("=" * 50)