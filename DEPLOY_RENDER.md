# Deploying Neural Analytics to Render (Free Tier)

This guide walks you through deploying Neural Analytics v2.0 to Render.com using their free tier.

---

## Prerequisites

- GitHub account with your forked repo (piyush080205/datadict)
- Render.com account (free tier)
- Cohere API key
- Git push access to your repo

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Render Static Site (Frontend)          │
│  - React + Vite build                   │
│  - Hosted at *.onrender.com             │
│  - Calls API endpoint                   │
└─────────────────────────────────────────┘
          ↓ API calls (HTTPS)
┌─────────────────────────────────────────┐
│  Render Web Service (Backend)           │
│  - FastAPI + Gunicorn                   │
│  - Python 3.11                          │
│  - Free tier (spins down after 15 min)  │
└─────────────────────────────────────────┘
          ↓ SQL queries
┌─────────────────────────────────────────┐
│  Render PostgreSQL (Database)           │
│  - Free tier instance                   │
│  - Persistent storage                   │
└─────────────────────────────────────────┘
```

---

## Step 1: Update Backend for Production

### Add Gunicorn to requirements.txt

```bash
echo "gunicorn[uvicorn]>=21.0" >> backend/requirements.txt
```

Or manually add to `backend/requirements.txt`:
```
gunicorn[uvicorn]>=21.0
```

### Update main.py for CORS

Edit `backend/main.py` to accept the production frontend URL:

```python
import os

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Commit changes

```bash
git add backend/requirements.txt backend/main.py
git commit -m "chore: Prepare for Render deployment"
git push origin main
```

---

## Step 2: Set Up on Render

### 2.1 Create Database

1. Go to [render.com](https://render.com)
2. Sign in / Create account
3. Go to **Dashboard** → **New** → **PostgreSQL**
4. Fill in:
   - **Name**: `neural-analytics-db`
   - **Database**: `neural_analytics`
   - **User**: `postgres` (auto-generated)
   - **Region**: Pick closest to you
   - **Plan**: Free
5. Click **Create Database**
6. Wait ~2 minutes for provisioning
7. **Copy the full "Internal Database URL"** (you'll need this later)

### 2.2 Deploy Backend

1. Go to **Dashboard** → **New** → **Web Service**
2. Connect GitHub repository:
   - Click **Connect GitHub**
   - Authorize Render
   - Select `piyush080205/datadict`
3. Configure service:
   - **Name**: `neural-analytics-api`
   - **Region**: Same as database (if possible)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: 
     ```
     pip install -r backend/requirements.txt
     ```
   - **Start Command**:
     ```
     cd backend && gunicorn --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 main:app
     ```
   - **Plan**: Free
4. Click **Create Web Service**
5. Go to **Environment** tab and add:
   - `DATABASE_URL` = (paste the Internal Database URL from step 2.1)
   - `COHERE_API_KEY` = (your Cohere API key)
   - `FRONTEND_URL` = (leave blank for now, we'll update after frontend is deployed)
6. Click **Save**

**Note the backend URL** (looks like `https://neural-analytics-api.onrender.com`)

### 2.3 Initialize Database

Once backend is deployed:

1. Go to **Logs** tab and wait for "Server started"
2. Open a terminal and run database migrations:

```bash
# Install psql locally first, then:
psql -h [DATABASE_HOST] -U [DATABASE_USER] -d neural_analytics -f sql/schema.sql

# You'll be prompted for the database password (from step 2.1)
```

Alternatively, use Render's in-browser **PostgreSQL Shell**:
1. In Render dashboard, go to your database
2. Click **Shell**
3. Run SQL from `sql/schema.sql` and `sql/views.sql`

### 2.4 Deploy Frontend

1. Go to **Dashboard** → **New** → **Static Site**
2. Connect GitHub:
   - Select `piyush080205/datadict` repo
3. Configure:
   - **Name**: `neural-analytics-frontend`
   - **Branch**: `main`
   - **Build Command**:
     ```
     cd frontend && npm install && npm run build
     ```
   - **Publish Directory**: `frontend/dist`
4. Click **Create Static Site**
5. Wait for build to complete (~3-5 minutes)

**Note the frontend URL** (looks like `https://neural-analytics-frontend.onrender.com`)

### 2.5 Update Backend CORS

Now that frontend is deployed:

1. Go back to backend web service
2. Go to **Environment** tab
3. Update `FRONTEND_URL`:
   - Value: `https://neural-analytics-frontend.onrender.com`
4. Click **Save**
5. Backend will restart automatically

---

## Step 3: Verify Deployment

1. Open your frontend URL in a browser:
   ```
   https://neural-analytics-frontend.onrender.com
   ```

2. Test basic functionality:
   - Click on Sidebar → Upload a CSV
   - Ask a question
   - Check that charts render

3. Check API health:
   ```bash
   curl https://neural-analytics-api.onrender.com/
   # Should return: {"status": "API running"}
   ```

4. Monitor logs:
   - Backend: Render Dashboard → neural-analytics-api → Logs
   - Frontend: Render Dashboard → neural-analytics-frontend → Logs

---

## Limitations & Tips

### Free Tier Constraints

| Resource | Limit |
|----------|-------|
| Web Service | Spins down after 15 min inactivity (cold start ~30s) |
| Database | 1 GB storage, limited compute |
| Static Site | Unlimited bandwidth |
| Memory | 512 MB |

### Performance Tips

1. **Cold Start** — First request after inactivity takes ~30s (normal for free tier)
2. **Query Timeout** — Keep under 60s to avoid timeout
3. **File Uploads** — Max 40 MB (limited by Render's request size)
4. **Concurrent Users** — Free tier supports ~5-10 concurrent requests

### Troubleshooting

| Issue | Solution |
|-------|----------|
| **502 Bad Gateway** | Backend crashed or cold-starting. Check logs. |
| **CORS error in browser** | Verify `FRONTEND_URL` is set correctly in backend. |
| **Database connection refused** | Check `DATABASE_URL` is correct and database is running. |
| **CSV upload fails** | Check file size < 40 MB. |
| **"Internal Server Error"** | Check backend logs for Python errors. |

---

## Upgrading to Paid Tier (Optional)

When you're ready for more power:

1. **Backend Web Service** → Click **Modify Plan** → Select **Starter** or higher
   - Removes spin-down (always on)
   - 2 GB RAM
   - 0.5 vCPU
   - ~$7/month

2. **PostgreSQL** → Click **Modify Plan** → Select **Starter** or higher
   - 10 GB storage
   - Better performance
   - ~$15/month

---

## Updating Your App

To deploy updates:

1. Make changes locally
2. Push to GitHub:
   ```bash
   git add .
   git commit -m "Update feature XYZ"
   git push origin main
   ```
3. Render automatically redeploys:
   - Frontend: Rebuilds static site
   - Backend: Rebuilds and restarts

---

## Environment Variables Reference

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | PostgreSQL connection string | Auto-generated by Render |
| `COHERE_API_KEY` | Your Cohere API key | Get from cohere.com |
| `FRONTEND_URL` | Frontend domain | Set after frontend deployment |
| `PYTHON_VERSION` | `3.11` | Optional, defaults to 3.10 |

---

## Next Steps

1. **Monitor** — Set up email alerts in Render Dashboard → Account Settings → Alerts
2. **Custom Domain** — Add your own domain (paid feature)
3. **SSL/TLS** — Automatic, provided by Render
4. **Backups** — Enable automatic PostgreSQL backups (paid feature)

---

## Support & Resources

- **Render Docs**: https://render.com/docs
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/
- **React Build Guide**: https://vitejs.dev/guide/build.html
- **PostgreSQL on Render**: https://render.com/docs/databases

---

**Deployed! 🚀** Your Neural Analytics app is now live on Render.
