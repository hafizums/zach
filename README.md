# AI 3D Explainer Shorts Generator

## Setup

### Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
# source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Running Tests
```bash
cd backend
pytest
```

### Development Commands
- Backend test: `cd backend && pytest`
- Frontend build: `cd frontend && npm run build`
