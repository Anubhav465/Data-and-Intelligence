from functools import lru_cache

# Cache up to 128 recent questions
@lru_cache(maxsize=128)
def cached_process_question(question: str):
    from question_processor import process_question
    return process_question(question)