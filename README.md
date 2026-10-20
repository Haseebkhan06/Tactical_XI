# Tactical_XI ⚽

Tactical_XI is a football analytics project I'm building to explore match data and understand what's happening on the pitch beyond just the scoreline.

The idea is to turn football event data into useful tactical insights, from pressing patterns to ball recoveries and sequences of play.

### What it does

- Match catalogue using StatsBomb Open Data
- Pressing analysis and match sequences
- Ball recovery insights
- FastAPI backend with a React frontend
- PostgreSQL database for match and report data
- JWT authentication for protected endpoints
- Caching and scheduled background tasks
- PDF reports for match analysis

### Tech stack

**Backend:** Python, FastAPI, SQLAlchemy  
**Frontend:** React, TypeScript, Vite  
**Database:** PostgreSQL  
**Other tools:** JWT, APScheduler, ReportLab, pytest

### Getting started

Clone the repository and set up the Python environment:

```bash
git clone <https://github.com/Haseebkhan06/Tactical_XI.git>
cd Tactical_XI

python -m venv .venv
```

On Windows, activate it with:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Configure your `.env` file with the required database and authentication settings, then start the backend:

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8011
```

Open [Swagger UI](http://127.0.0.1:8011/docs) to explore the API.

To run the frontend, open another terminal:

```bash
cd frontend
npm install
npm run dev
```

### Testing

Run the test suite with:

```bash
python -m pytest
```

Currently, all 7 tests are passing, with around 41% code coverage.

---
