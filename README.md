# Amplytics — working prototype

A prototype that lets a household set an electricity target, record daily
consumption, view target-pace calculations, a baseline projection, and
(optionally) ML predictions from saved models.

**Important honesty statement**

- The included data is **synthetic** (see `scripts/generate_synthetic_data.py`
  and `data/raw/synthetic_metadata.json`). Any model metrics printed by
  `scripts/train_models.py` describe only that synthetic distribution.
- Models are **not** retrained when the user enters a record. Retraining is a
  separate step (`scripts/train_models.py`).
- The ML outputs are **estimates**, not confirmed future bills.
- Baseline projection and ML prediction are **displayed separately**.
- Rule-based alerts and ML alerts are **displayed separately**.
- The app never ingests real sensor data. All measured records are entered by
  the user (or imported).
- Appliance estimates are shown for information and are **not** added to
  meter-based daily records.

  ## Languages
  Python 3.11+
  HTML (Jinja2 templates)
  CSS (Tailwind utility classes)
  JavaScript (vanilla ES2015+)
  SQL (SQLite dialect)
  CSV
  JSON
  
  ## Backend / web stack
  Web framework -->	fastapi
  ASGI server	  --> uvicorn[standard]
  Templating	  --> jinja2
  Form parsing	--> python-multipart
  Sessions	    -->starlette.middleware.sessions (via itsdangerous)
  Static files	--> StaticFiles (Starlette)
  API docs	    --> FastAPI auto-generated

  ## Frontend stack
  Tailwind CSS 3
  Inter font
  Chart.js 4
  Vanilla JS

  ## Storage
  SQLite 3
  Python sqlite3
  CSV files
  JSON file
  Joblib binaries

  ## Data processing
  pandas
  numpy
  Python stdlib

  ## Machine learning stack
  Framework   --->   scikit-learn
  Linear Regression
  Logistic Regression
  Preprocessing
  Pipeline
  Grouped splitting
  Regression metrics
  Classification metrics
  Serialisation

  ## Two ML Models
  Model A — Linear Regression
  Model B — Logistic Regression

## Project Setup Step By Step Instructions:

# 1. Create and activate a virtual environment
python -m venv .venv                 # Create Virtual Environment
source .venv/bin/activate            # Run in mac-OS/Linux
.venv\Scripts\activate               # Run in Windows (Power Shell)

# 2. Install dependencies  # Install Python Dependencies
pip install -r requirements.txt

# 3. Launch the app   # Run The Fast-API App
uvicorn web.main:app --reload
