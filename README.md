# QUEL Light - Stage Node Backend

Python FastAPI backend for 2D → 3D conversion using Meta SAM 3D.

## 🚀 Quick Start

### Local Development

1. **Install dependencies:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Create storage directories:**
```bash
mkdir -p storage/uploads storage/models storage/renders
```

3. **Run server:**
```bash
python main.py
```

Server will start at `http://localhost:8000`

### Test the API

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

---

## 📦 Deployment to Render.com

### Prerequisites
- GitHub account
- render.com account (free tier available)

### Step 1: Push to GitHub

```bash
cd python-backend
git init
git add .
git commit -m "Initial Python backend"
git remote add origin https://github.com/YOUR_USERNAME/quel-python-backend.git
git push -u origin main
```

### Step 2: Deploy on Render.com

1. **Go to render.com and sign in**

2. **Click "New +" → "Web Service"**

3. **Connect your GitHub repository**

4. **Configure the service:**
   - **Name:** `quel-stage-backend`
   - **Region:** Choose closest to your users
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

5. **Environment Variables:**
   Add these in the "Environment" tab:
   ```
   BASE_URL=https://YOUR_APP_NAME.onrender.com
   LOG_LEVEL=INFO
   ```

6. **Instance Type:**
   - **Free tier:** 512MB RAM (good for testing)
   - **Starter ($7/month):** 1GB RAM (recommended)
   - **Standard ($25/month):** 4GB RAM (for production)

7. **Click "Create Web Service"**

Render.com will:
- Build your application
- Deploy it
- Provide a URL like `https://quel-stage-backend.onrender.com`

### Step 3: Update Next.js

In your Next.js project, update `.env.local`:

```bash
PYTHON_BACKEND_URL=https://quel-stage-backend.onrender.com
```

---

## 🔧 Configuration

### For GPU Support (Optional)

If using render.com's paid tiers with GPU:

1. Uncomment GPU-related packages in `requirements.txt`:
   ```
   torch==2.5.1+cu118
   torchvision==0.20.1+cu118
   ```

2. Add to render.com environment:
   ```
   DEVICE=cuda
   ```

### For Actual SAM 3D (When Available)

1. Uncomment in `requirements.txt`:
   ```
   transformers==4.47.0
   accelerate==0.35.0
   ```

2. Update `services/sam3d_service.py`:
   - Replace `_create_mock_3d_model()` with actual SAM 3D inference
   - Load model from Hugging Face Hub

---

## 📊 Monitoring

### Render.com Dashboard
- View logs in real-time
- Monitor memory/CPU usage
- See deployment history

### Health Checks

Render.com automatically pings `/health` endpoint:
```bash
curl https://your-app.onrender.com/health
```

---

## 💰 Pricing

### Render.com Tiers

| Tier | RAM | CPU | Price | Best For |
|------|-----|-----|-------|----------|
| Free | 512MB | Shared | $0 | Testing, low traffic |
| Starter | 1GB | Shared | $7/mo | Small apps, demos |
| Standard | 4GB | 1 vCPU | $25/mo | Production, moderate traffic |
| Pro | 8GB | 2 vCPU | $85/mo | High traffic, GPU optional |

**Free tier limitations:**
- Spins down after 15 min inactivity (cold start ~30s)
- 750 hours/month free

**Recommendation:**
- Start with **Free** for testing
- Upgrade to **Starter** for production
- Use **Standard** if you need consistent performance

---

## 🔐 Security

### CORS Configuration

Update `main.py` CORS settings for your domain:

```python
allow_origins=[
    "http://localhost:3000",
    "https://your-domain.com",
    "https://*.vercel.app",
]
```

### API Keys (Optional)

Add authentication:

```python
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.environ.get("API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")
```

---

## 📁 Project Structure

```
python-backend/
├── main.py                 # FastAPI app entry point
├── routers/
│   └── stage_node.py      # /convert and /render endpoints
├── services/
│   ├── sam3d_service.py   # 2D → 3D conversion
│   └── render_service.py  # 3D rendering
├── storage/               # File storage (gitignored)
│   ├── uploads/          # Uploaded images
│   ├── models/           # Generated 3D models
│   └── renders/          # Rendered images
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
└── README.md             # This file
```

---

## 🐛 Troubleshooting

### "Module not found" error
```bash
pip install -r requirements.txt --force-reinstall
```

### CORS errors
Check `allow_origins` in `main.py` includes your frontend URL

### Out of memory on Render.com
- Upgrade to Starter tier ($7/mo)
- Optimize model loading (lazy load)
- Reduce batch sizes

### Cold starts (Free tier)
- Use Starter tier for persistent service
- Or implement warm-up pings from frontend

---

## 📚 API Documentation

Once running, visit:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Endpoints

#### POST `/api/stage/convert`
Convert 2D image to 3D model

**Request:**
```json
{
  "image_base64": "data:image/png;base64,...",
  "node_id": "stage_123",
  "user_id": "user_456"
}
```

**Response:**
```json
{
  "success": true,
  "model_id": "model_stage_123_20250212",
  "model_url": "http://localhost:8000/models/model_123.glb",
  "preview_url": "http://localhost:8000/renders/model_123_preview.png",
  "vertices_count": 1234,
  "faces_count": 2468
}
```

#### POST `/api/stage/render`
Render 3D model at specific angle

**Request:**
```json
{
  "model_id": "model_stage_123_20250212",
  "pitch": 12.0,
  "yaw": 32.0,
  "distance": 2.8,
  "resolution": {"width": 1024, "height": 1024}
}
```

**Response:**
```json
{
  "success": true,
  "image_base64": "data:image/png;base64,...",
  "render_time_ms": 245
}
```

---

## 🔄 Updates

### To update your deployment:

1. **Make changes locally**
2. **Commit and push:**
   ```bash
   git add .
   git commit -m "Update feature"
   git push
   ```
3. **Render.com auto-deploys** from GitHub

---

## 📝 Notes

- **Current implementation uses MOCK 3D models (cubes)**
- **Replace with actual SAM 3D when model is available**
- **PyRender rendering is also mocked (gradients)**
- **GPU recommended for production SAM 3D inference**

---

## 🆘 Support

- **Render.com Docs:** https://render.com/docs
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Issues:** Create issue in your GitHub repo