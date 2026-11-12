# AI Career & Resume Optimizer Agent

Upload a resume and a job description; get a match score, strengths, and missing skills.

## Run backend
```
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```
