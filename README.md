# Somnia — Mystical Night
Machine Learning-Based Sleep Disorder Classification Web Application

This starter project follows the supplied SRS: registration/login, a protected personal dashboard, assessments, saved history, a model training pipeline, general sleep-hygiene information, and a non-diagnostic disclaimer.

## Technology
- Frontend: HTML, CSS, JavaScript (responsive; no build step)
- Backend: Python + Flask
- Database: SQLite
- Machine learning: scikit-learn Pipeline (preprocessing + Random Forest)
- Model artifact: `backend/sleep_model.joblib`

> Important: This is an academic awareness prototype, not a medical diagnostic tool. Predictions depend on the dataset and model. Do not enter real sensitive health information into an unreviewed student deployment.

## 1. Requirements
Use Python 3.10–3.13 if possible for easiest library compatibility. From the project root:

### Windows PowerShell
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 2. Add your dataset
Place your verified CSV dataset at:
`backend/sleep_health.csv`

The commonly used Sleep Health and Lifestyle dataset has columns such as:
`Gender, Age, Occupation, Sleep Duration, Quality of Sleep, Physical Activity Level, Stress Level, BMI Category, Blood Pressure, Heart Rate, Daily Steps, Sleep Disorder`

Column names vary by dataset version. Inspect your file before training. The target column must be `Sleep Disorder` (or edit `TARGET_COLUMN` in `train_model.py`). Do not treat blank target labels as a confirmed disorder class; this starter script drops rows with a missing target.

## 3. Train and evaluate the ML model
From inside `backend` with the virtual environment activated:
```powershell
python train_model.py
```
This prints accuracy, precision, recall, F1-score, a confusion matrix, and saves `sleep_model.joblib` plus `model_metrics.json`.

The script intentionally fails with a clear message if the dataset is missing or the target column cannot be found. It does not invent predictions or use the paper's published accuracy as your result.

## 4. Run the web app
Still inside `backend`:
```powershell
python app.py
```
Open: http://127.0.0.1:5000

The website can load without a trained model, but the assessment endpoint will ask you to train the model and add the dataset first. Authentication and the dashboard can still be explored.

## 5. Test
- Register a test account.
- Log in and open dashboard.
- Submit an assessment only after model training succeeds.
- Verify the result appears in history.
- Register a second account and check that the first user's history is not visible.
- Test on desktop and a mobile browser.

## Folder structure
```text
somnia-mystical-night/
├── README.md
├── backend/
│   ├── app.py
│   ├── train_model.py
│   ├── requirements.txt
│   ├── sleep_health.csv       # add your verified dataset
│   ├── sleep_model.joblib     # generated after training
│   ├── model_metrics.json     # generated after training
│   └── somnia.db              # generated automatically
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── docs/
    └── CAPSTONE_CHECKLIST.md
```

## Before public deployment
Set a strong random `SECRET_KEY` environment variable, enable HTTPS, configure secure cookies, add CSRF protection/rate limiting, review privacy requirements, and use a production WSGI server. The Flask development server is for local development only.
