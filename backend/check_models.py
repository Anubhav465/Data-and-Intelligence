# backend/check_models.py
import os
import cohere
from dotenv import load_dotenv

load_dotenv()
co = cohere.Client(os.getenv("COHERE_API_KEY"))

models = co.models.list()
for m in models.models:
    print(m.name)