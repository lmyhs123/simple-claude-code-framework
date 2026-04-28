# 开发说明

## 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 前端

```bash
cd frontend
npm install
npm run dev
```

