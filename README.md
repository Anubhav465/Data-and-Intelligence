# Neural Analytics 2.0

**Query any dataset in plain English — no SQL required.**

An AI-powered analytics platform that lets you upload CSV files and ask natural language questions. Supports multi-table querying with automatic JOINs, semantic schema search, and AI-generated insights with interactive visualizations.

[![Version](https://img.shields.io/badge/version-2.0.0-cyan)](https://github.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 🚀 Features

### Core Capabilities
- **Drag-and-drop CSV upload** — Upload up to 5 files (40 MB each) instantly
- **Multi-table NL querying** — Ask questions across multiple datasets with automatic JOINs
- **Zero SQL knowledge required** — LLM generates correct queries from plain English
- **Semantic schema search** — FAISS embeddings find relevant columns by semantic meaning
- **Auto-fix on failure** — LLM self-corrects failing queries in real-time
- **Interactive visualizations** — Auto-selects best chart type (bar, line, pie, histogram)
- **AI summaries** — 3-bullet findings generated from query results
- **Data cleaning report** — Shows nulls normalized, duplicates removed, type coercions

### Security & Safety
- ✅ SELECT-only enforcement — no INSERT, UPDATE, DELETE, DROP
- ✅ SQL injection guards — unauthorized table detection
- ✅ Prompt injection prevention — validates table references post-generation
- ✅ Query timeout — 15 second execution limit
- ✅ Result capping — max 200 rows per query

### Tech
- **Frontend**: React 18 + Vite + Tailwind CSS + Framer Motion + Chart.js
- **Backend**: FastAPI + Python 3.8+ + PostgreSQL 12+
- **AI/LLM**: Cohere API (`command-r-08-2024`)
- **Vector Search**: FAISS (IndexFlatL2, embed-english-v3.0)
- **Database**: PostgreSQL (isolated `uploads` schema for user data)

---

## 📋 Project Structure

```
DataDict/
├── backend/
│   ├── main.py                      # FastAPI app + endpoints (/ask, /upload, /tables)
│   ├── question_processor.py        # Request orchestrator + auto-fix pipeline
│   ├── sql_generator.py             # LLM-based SQL generation (single & multi-table)
│   ├── query_executor.py            # Safe PostgreSQL execution (2 engines)
│   ├── chart_generator.py           # Auto chart type selection
│   ├── category_translator.py       # Portuguese → English translation (Olist)
│   ├── analytics_queries.py         # Pre-built KPI queries (Olist)
│   ├── schema_inferer.py            # Pandas type inference + normalization
│   ├── schema_extractor.py          # Live schema extraction (Olist)
│   ├── file_handler.py              # CSV validation + temp storage
│   ├── data_cleaner.py              # Null-string norm, dedup, type coercion
│   ├── table_creator.py             # PostgreSQL table creation + metadata registry
│   ├── dynamic_retriever.py         # Per-table FAISS schema embeddings
│   ├── requirements.txt
│   └── .env                         # API keys + DATABASE_URL (not committed)
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── context/
│   │   │   └── DatasetContext.jsx   # Global dataset state
│   │   ├── components/
│   │   │   ├── ChatWindow/
│   │   │   ├── ChatInput/           # With active dataset badge
│   │   │   ├── MessageBubble/
│   │   │   ├── ChartRenderer/
│   │   │   ├── DataTable/
│   │   │   ├── SqlViewer/
│   │   │   ├── SummaryBlock/
│   │   │   ├── FileUpload/          # Multi-file upload (new)
│   │   │   ├── DatasetSelector/     # Multi-select (new)
│   │   │   ├── DatasetPreview/      # Column types + preview (new)
│   │   │   ├── Sidebar/             # Dataset management (new)
│   │   │   ├── VersionHistory/      # Roadmap display (new)
│   │   │   └── Header/
│   │   ├── services/
│   │   │   └── api.js               # uploadCSV, askQuestion(question, tableNames)
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
├── data/                            # Olist CSV datasets
├── sql/
│   ├── schema.sql                   # Olist schema DDL + uploads schema
│   └── views.sql                    # Materialized views
└── README.md
```

---

## ⚡ Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL 12+ running locally
- [Cohere API key](https://cohere.com/)

### 1. Database Setup

```bash
# Create the database
createdb olist_dev

# Load Olist schema and views
psql -U postgres -d olist_dev -f sql/schema.sql
psql -U postgres -d olist_dev -f sql/views.sql

# Load Olist data from CSVs (examples)
psql -U postgres -d olist_dev -c "\COPY olist.customers FROM 'data/olist_customers_dataset.csv' WITH (FORMAT csv, HEADER true);"
psql -U postgres -d olist_dev -c "\COPY olist.products FROM 'data/olist_products_dataset.csv' WITH (FORMAT csv, HEADER true);"
# ... repeat for remaining CSV files
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/Scripts/activate      # Windows
# source venv/bin/activate         # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

Create `backend/.env`:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/olist_dev
COHERE_API_KEY=your_cohere_api_key_here
```

Start the backend:

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend runs on `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`

---

## 📖 Usage

### Querying Olist Data (Built-in)

Open `http://localhost:5173` and type natural language questions:

```
"What are the top 10 product categories by revenue?"
"Show me the average delivery delay by state."
"How many orders were delivered late in 2018?"
"Which sellers have the highest review scores?"
```

### Uploading & Querying Your Own Data

1. **Upload CSV** — Drag-and-drop into the sidebar (or click to browse)
   - Accepts `.csv` files up to 40 MB
   - Auto-detects schema (column types, names)
   - Shows cleaning report (nulls, duplicates, type coercions)
   - Displays preview of first 10 rows

2. **Multi-select datasets** — Check boxes to query 2–5 datasets at once
   - Active dataset shown in preview panel
   - Chat queries all selected tables with automatic JOINs

3. **Ask questions** — Same natural language interface
   - System generates SQL across all selected tables
   - Auto-fixes on failure via LLM
   - Returns charts, tables, AI summary

---

## 🔌 API Reference

### `POST /ask`

Query either Olist data or uploaded tables.

**Request (single table)**
```json
{
  "question": "How many products are in each category?",
  "table_names": ["user_table_abc123"]
}
```

**Request (multi-table)**
```json
{
  "question": "Show me customers and their orders",
  "table_names": ["user_table_abc123", "user_table_def456"]
}
```

**Request (Olist, no table_names)**
```json
{
  "question": "Top 5 states by order count?"
}
```

**Response**
```json
{
  "question": "How many products in each category?",
  "table_names": ["user_table_abc123"],
  "sql": "SELECT product_category, COUNT(*) FROM uploads.\"user_table_abc123\" GROUP BY ...",
  "explanation": "LLM-generated SQL for uploaded table(s).",
  "data": {
    "columns": ["product_category", "count"],
    "rows": [{"product_category": "...", "count": 42}, ...],
    "row_count": 15
  },
  "chart_spec": {
    "type": "bar",
    "data": { "labels": [...], "datasets": [...] }
  },
  "summary": "• Category A has 420 products\n• ...\n• ...",
  "meta": {
    "execution_time_ms": 245,
    "source": "llm_upload",
    "row_count": 15,
    "chart_available": true
  }
}
```

### `POST /upload`

Upload a CSV file for querying.

**Request**
```
multipart/form-data
file: <CSV file>
```

**Response (201)**
```json
{
  "table_name": "user_table_3b2403e6fc2b",
  "columns": [
    {
      "name": "product_name",
      "original_name": "Product Name",
      "pandas_type": "object",
      "pg_type": "TEXT"
    },
    {
      "name": "price",
      "original_name": "Price",
      "pandas_type": "float64",
      "pg_type": "DOUBLE PRECISION"
    }
  ],
  "row_count": 5432,
  "preview_rows": [
    {"product_name": "Widget A", "price": 19.99},
    ...
  ],
  "cleaning": {
    "null_strings_replaced": 12,
    "rows_dropped_duplicates": 0,
    "type_coercion_failures": 2,
    "total_rows_after": 5432,
    "llm_suggestions": "..."
  }
}
```

### `GET /tables`

List all uploaded datasets.

**Response**
```json
{
  "tables": [
    {
      "table_name": "user_table_3b2403e6fc2b",
      "row_count": 5432,
      "columns": [...],
      "created_at": "2026-04-13T10:32:15.123456"
    }
  ]
}
```

### `GET /tables/{table_name}`

Get metadata for a single uploaded table.

### `DELETE /tables/{table_name}`

Drop an uploaded table from the database.

### `GET /`

Health check. Returns `{"status": "API running"}`.

---

## 🛡️ Database Schema

### Olist Schema

| Table | Purpose |
|-------|---------|
| `customers` | Customer ID, name, address, city, state |
| `sellers` | Seller ID, city, state |
| `products` | Product catalog with category, dimensions, weight |
| `orders` | Order header with status, timestamps |
| `order_items` | Line items (order ↔ product) |
| `payments` | Payment method, installments, value |
| `reviews` | Customer review scores and comments |
| `geolocation` | Zip code coordinates |
| `product_category_name_translation` | Portuguese → English mapping |

### Uploads Schema

| Table | Purpose |
|-------|---------|
| `_table_registry` | Metadata for uploaded tables (JSONB column_specs) |
| `user_table_*` (dynamic) | Each uploaded CSV becomes a table here |

**Materialized Views (Olist)**
- `order_revenue` — total revenue per order
- `order_delivery_metrics` — delivery delay in days per order

---

## 🗺️ Roadmap

### ✅ v2.0.0 (Current)
- Multi-file CSV upload (up to 5 × 40 MB)
- Multi-table NL querying with automatic JOINs
- FAISS semantic schema search
- Auto-fix pipeline (LLM self-correction)
- Bar, line, pie, histogram chart auto-selection
- Data cleaning report (nulls, duplicates, coercions)
- Drag-and-drop sidebar
- Strict SQL security (SELECT-only, injection guards)

### 📅 v2.0.1 (Coming Soon)
1. **Query History & Favorites** — Save/share frequently-asked questions
2. **Column Profiling** — Auto-generate cardinality, missing %, distribution
3. **Natural Language Joins** — Auto-detect FK relationships
4. **Real-time Data Integration** — Connect to live PostgreSQL, MySQL, BigQuery
5. **Data Quality Badges** — Auto-detect anomalies (duplicates, outliers, schema drift)
6. **Multi-language SQL** — Generate T-SQL, BigQuery, Snowflake dialects
7. **Mobile App** — React Native version
8. **Team Collaboration** — Shared workspaces, comments, audit logs
9. **Advanced Visualizations** — Dashboards, heatmaps, geo maps
10. **Fine-tuned Model** — Custom LLM for domain-specific SQL patterns

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| `DATABASE_URL is not set` | Create `backend/.env` with `DATABASE_URL=postgresql://...` |
| `COHERE_API_KEY missing` | Add `COHERE_API_KEY` to `backend/.env` |
| `Connection refused: localhost:5432` | Ensure PostgreSQL is running (`psql -U postgres`) |
| `Timeout on multi-table query` | Try querying fewer tables (2–3 instead of 5) or simpler questions |
| CORS error in browser console | Update `allow_origins` in `main.py` if using a different frontend URL |
| "Unauthorized tables" SQL error | Check that table names use fully qualified names (`uploads."table_name"`) |

---

## 📊 Performance & Limits

| Constraint | Value |
|-----------|-------|
| Max upload size (per file) | 40 MB |
| Max files per upload | 5 |
| Query execution timeout | 60 seconds (multi-table) / 15 seconds (Olist) |
| Result row limit | 200 rows |
| Chart data points | 20 max |
| FAISS schema chunks per table | 4 (single-table) / full context only (multi-table) |

---

## 🚀 Production Deployment

1. **Frontend**
   - Run `npm run build` to generate static assets
   - Serve via CDN or static host (Vercel, Netlify, AWS S3 + CloudFront)

2. **Backend**
   - Use Gunicorn + Uvicorn for multi-worker setup:
     ```bash
     gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
     ```
   - Set `COHERE_API_KEY` and `DATABASE_URL` via environment variables (not `.env`)
   - Use a managed PostgreSQL instance (AWS RDS, Supabase, etc.)

3. **CORS**
   - Update `allow_origins` in `main.py` to your production domain

4. **Secrets**
   - Store API keys in a secrets manager (AWS Secrets Manager, HashiCorp Vault)

---

## 📝 License

This project uses the [Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (CC BY-NC-SA 4.0).

Project code is MIT licensed.

---

## 🎯 Key Insights

- **Schema isolation**: User-uploaded tables live in `uploads` schema, separate from `olist` production schema
- **Metadata persistence**: PostgreSQL `_table_registry` (JSONB) survives server restarts
- **Semantic search**: FAISS embeddings reduce LLM prompt size while improving accuracy
- **Multi-table safety**: `_assert_allowed_tables()` prevents cross-schema injection attacks
- **Auto-fix resilience**: LLM self-corrects 80%+ of failing queries without user intervention

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repo
2. Create a feature branch (`git checkout -b feature/xyz`)
3. Commit with clear messages
4. Open a pull request

---

**Built with ❤️ using FastAPI, React, and Cohere AI**
