import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"))

def extract_schema():
    query = """
    SELECT
        table_name,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema = 'olist'
    ORDER BY table_name;
    """

    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = result.fetchall()

    schema_dict = {}

    for table, column, dtype in rows:
        if table not in schema_dict:
            schema_dict[table] = []
        schema_dict[table].append(f"{column} ({dtype})")

    formatted_schema = []

    for table, columns in schema_dict.items():
        formatted_schema.append(
            f"Table: {table}\nColumns:\n" + "\n".join(columns)
        )

    return "\n\n".join(formatted_schema)


if __name__ == "__main__":
    schema_text = extract_schema()
    print(schema_text)