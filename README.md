<<<<<<< HEAD
# Crop Recommendation System — local app

A Flask app that serves your five trained classifiers behind one page. Enter
seven field readings, get every model's individual answer plus a combined
top-three crop ranking.

---

## What you get

- **Five models answer separately** — XGBoost, Random Forest, SVM, Decision Tree, KNN.
  Each shows its own pick, how sure it is, and its runner-up.
- **A top-three ranking** — an accuracy-weighted soft vote across all five. Each model
  votes with a weight equal to its measured test accuracy, so XGBoost (0.9955) pulls
  slightly harder than KNN (0.9750).
- **A consensus strip** — tells you at a glance whether the models agreed or split.
- **A score chart** — how the leading crops compared on the combined score.
- **Startup self-tests** — the server pushes three known field profiles through the full
  pipeline before it accepts a single request, and retries up to three times if a check
  fails. If a `.pkl` is stale or mismatched you find out at boot, not from a bad
  recommendation.

---

## Folder layout

```
crop-app/
├── app.py                  Flask server + prediction logic
├── requirements.txt
├── README.md
├── models/
│   ├── rf_model.pkl
│   ├── xgb_model.pkl
│   ├── svm_model.pkl
│   ├── dt_model.pkl
│   ├── knn_model.pkl
│   ├── scaler.pkl          StandardScaler fitted on the 7 features
│   └── label_encoder.pkl   22 crop names
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    └── js/app.js
```

---

## Run it

```bash
cd crop-app

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000**

You should see this in the terminal before it starts serving:

```
INFO | Scaler + label encoder loaded (22 crops)
INFO | Loaded XGBoost        (xgb_model.pkl)
INFO | Loaded Random Forest  (rf_model.pkl)
INFO | Loaded SVM            (svm_model.pkl)
INFO | Loaded Decision Tree  (dt_model.pkl)
INFO | Loaded KNN            (knn_model.pkl)
INFO | Self-test passed on attempt 1 — all 3 probes OK
```

---

## Version pinning matters

The `.pkl` files were saved with **scikit-learn 1.7.2**. `requirements.txt` pins that
exact version. If you install a different one, sklearn raises
`InconsistentVersionWarning` on load — usually harmless, but on a major version jump the
unpickled tree structures can silently misbehave. Keep the pin, or re-export the models
from a notebook running your new version.

---

## Endpoints

| Route | Method | What it does |
|---|---|---|
| `/` | GET | The page |
| `/predict` | POST | JSON in, predictions out |
| `/health` | GET | Which models loaded, how many crops |

Example call:

```bash
curl -X POST http://127.0.0.1:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"N":90,"P":42,"K":43,"temperature":20.9,"humidity":82,"ph":6.5,"rainfall":202.9}'
```

Response shape:

```json
{
  "ok": true,
  "recommendations": [
    {"rank": 1, "crop": "rice", "score": 96.9, "votes": 5, "note": "..."}
  ],
  "model_predictions": [
    {"name": "XGBoost", "prediction": "rice", "confidence": 99.37, "top3": [...]}
  ],
  "chart": [{"crop": "rice", "probability": 96.9}],
  "consensus": {"agree": 5, "total": 5, "text": "All 5 models picked rice. Strong match."}
}
```

---

## Input ranges

Values outside these ranges are rejected, because the models were never trained on them
and their output there is guesswork.

| Reading | Range | Unit |
|---|---|---|
| Nitrogen | 0 – 140 | kg/ha |
| Phosphorus | 5 – 145 | kg/ha |
| Potassium | 5 – 205 | kg/ha |
| Temperature | 8 – 44 | °C |
| Humidity | 14 – 100 | % |
| Soil pH | 3.5 – 10 | — |
| Rainfall | 20 – 300 | mm |

---

## Notes on the design

- The page loads two fonts from Google Fonts. Offline, it falls back to a clean system
  sans and still looks right — nothing breaks.
- Motion only ever runs in response to a click. Bars grow, percentages tick up, cards
  land in sequence. `prefers-reduced-motion` turns all of it off.
- Works down to a phone screen; the form stacks above the results.

---

## If you want to go further

- **Production serving:** Flask's dev server is single-threaded. Use
  `waitress-serve --port=5000 app:app` on Windows or `gunicorn -w 2 app:app` on
  Linux/macOS.
- **Log real inputs** to a CSV so you can see whether live readings drift away from the
  training distribution. That drift, not model choice, is what degrades accuracy first.
- **Handle the unknown case:** if the top combined score falls below roughly 40%, the
  field probably doesn't resemble anything in the training set. Right now the app still
  gives its best guess — you may want to say "no confident match" instead.
=======
# Crop-Recommendation-System
>>>>>>> 320294559724688c695a9ea28b03ae35c81102b5
