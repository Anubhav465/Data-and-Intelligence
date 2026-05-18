# backend/category_translator.py
import os
import pandas as pd

# FIXED PATH - CSV is in ../data/ folder (project root)
TRANSLATION_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),   # goes up one level to olist-ai-analytics/
    "data",
    "product_category_name_translation.csv"
)

_translation_map = None


def load_translation_map():
    global _translation_map
    if _translation_map is not None:
        return _translation_map

    print(f"[Category Translator] Looking for CSV at: {TRANSLATION_FILE}")

    if not os.path.exists(TRANSLATION_FILE):
        print(f"[Category Translator] ❌ CSV NOT FOUND at {TRANSLATION_FILE}")
        print("   Please make sure the file is here: olist-ai-analytics/data/product_category_name_translation.csv")
        _translation_map = {}
        return _translation_map

    try:
        df = pd.read_csv(TRANSLATION_FILE)
        _translation_map = {
            str(k).strip().lower(): str(v).strip()
            for k, v in zip(df["product_category_name"], df["product_category_name_english"])
        }
        print(f"[Category Translator] ✅ Successfully loaded {len(_translation_map)} English translations.")
    except Exception as e:
        print(f"[Category Translator] ❌ Error reading CSV: {e}")
        _translation_map = {}

    return _translation_map


def translate_categories(rows: list, columns: list):
    if not rows or not columns:
        return rows

    translation_map = load_translation_map()
    if not translation_map:
        return rows

    # Detect any column that contains category data
    category_columns = [
        col for col in columns
        if any(kw in col.lower() for kw in ["category", "categoria", "product_category", "cat"])
    ]

    if not category_columns:
        print("[Category Translator] No category column found in results.")
        return rows

    print(f"[Category Translator] Found category columns: {category_columns}")

    translated_count = 0
    new_rows = []

    for row in rows:
        new_row = row.copy()
        for col in category_columns:
            value = new_row.get(col)
            if value is not None:
                key = str(value).strip().lower()
                if key in translation_map:
                    new_row[col] = translation_map[key]
                    translated_count += 1
        new_rows.append(new_row)

    print(f"[Category Translator] ✅ Translated {translated_count} category names to English.")
    return new_rows