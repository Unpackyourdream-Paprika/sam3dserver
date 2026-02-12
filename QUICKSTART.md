# 🚀 Quick Start Guide

## Step 1: Install Dependencies

```bash
cd /Users/meshedwell2/python-backend

# Create virtual environment
python3 -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

## Step 2: Create Storage Folders

```bash
mkdir -p storage/uploads storage/models storage/renders
```

## Step 3: Start Python Server

```bash
python main.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 4: Update Next.js Environment

In `/Users/meshedwell2/quel-light/.env.local`, add:

```bash
PYTHON_BACKEND_URL=http://localhost:8000
```

## Step 5: Start Next.js

```bash
cd /Users/meshedwell2/quel-light
npm run dev
```

## Test It!

1. Open `http://localhost:3000`
2. Go to Visual Editor
3. Create a **Stage Node**
4. Upload an image
5. Wait for 3D conversion (creates a cube for now)
6. Click "Render Selected Angle"
7. See the result!

---

## Troubleshooting

### "Connection refused"
- Make sure Python backend is running on port 8000
- Check `PYTHON_BACKEND_URL` in `.env.local`

### "Module not found"
```bash
pip install -r requirements.txt --force-reinstall
```

### Port 8000 already in use
```bash
# Change port in main.py or kill existing process
lsof -ti:8000 | xargs kill -9
```

---

## What's Next?

Currently using **MOCK** 3D models (cubes). To use **real SAM 3D**:

1. Wait for Meta to release SAM 3D model weights
2. Uncomment model loading in `services/sam3d_service.py`
3. Update `_create_mock_3d_model()` with actual inference

---

## Deploy to Render.com

See [README.md](README.md#deployment-to-rendercom) for full guide.

Quick version:
```bash
# 1. Push to GitHub
git init
git add .
git commit -m "Initial commit"
git push

# 2. Deploy on render.com
# - Connect GitHub repo
# - Set start command: uvicorn main:app --host 0.0.0.0 --port $PORT
# - Add env: BASE_URL=https://your-app.onrender.com

# 3. Update Next.js .env.local
PYTHON_BACKEND_URL=https://your-app.onrender.com
```

Done! 🎉