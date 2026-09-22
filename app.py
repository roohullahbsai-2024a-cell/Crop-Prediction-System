"""
Crop Recommendation System — local Flask server.

Serves five trained classifiers (Random Forest, XGBoost, SVM, Decision Tree, KNN)
behind one endpoint. Every request returns:
  1. what each of the five models predicted, on its own
  2. a combined top-3 ranking (accuracy-weighted soft vote)
  3. the probability curve used to build that ranking

Run:  python app.py      ->  http://127.0.0.1:5000
"""

import os
import warnings
import logging
import pandas as pd
import numpy as np
import joblib
from flask import Flask, render_template, request, jsonify

warnings.filterwarnings("ignore")          # silence sklearn version notices
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("crop-app")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")

# ─────────────────────────────────────────────────────────────────────────────
# Feature contract — order matters. Models were trained on exactly this order.
# ─────────────────────────────────────────────────────────────────────────────
FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]

# Valid ranges taken from the training data (2200 rows). Used for the sliders
# and for rejecting readings the models have never seen.
FEATURE_META = {
    "N":           {"label": "Nitrogen",    "unit": "kg/ha", "min": 0,    "max": 140,  "step": 1,    "default": 90},
    "P":           {"label": "Phosphorus",  "unit": "kg/ha", "min": 5,    "max": 145,  "step": 1,    "default": 42},
    "K":           {"label": "Potassium",   "unit": "kg/ha", "min": 5,    "max": 205,  "step": 1,    "default": 43},
    "temperature": {"label": "Temperature", "unit": "°C",    "min": 8.0,  "max": 44.0, "step": 0.1,  "default": 20.9},
    "humidity":    {"label": "Humidity",    "unit": "%",     "min": 14.0, "max": 100.0,"step": 0.1,  "default": 82.0},
    "ph":          {"label": "Soil pH",     "unit": "",      "min": 3.5,  "max": 10.0, "step": 0.01, "default": 6.50},
    "rainfall":    {"label": "Rainfall",    "unit": "mm",    "min": 20.0, "max": 300.0,"step": 0.1,  "default": 202.9},
}
DATASET_PATH = os.path.join(BASE_DIR, "Crop_recommendation.csv")

CROP_PROFILES = {}
# ─────────────────────────────────────────────────────────────────────────────
# Model registry.
# `weight` = measured test accuracy from the comparison run. Better models get
# a bigger say in the combined vote. This is plain accuracy-weighted soft
# voting — no magic numbers invented.
# ─────────────────────────────────────────────────────────────────────────────
MODEL_REGISTRY = [
    {"key": "xgb", "name": "XGBoost",       "file": "xgb_model.pkl", "weight": 0.9955,
     "note": "Gradient-boosted trees. Best score on the test set."},
    {"key": "rf",  "name": "Random Forest", "file": "rf_model.pkl",  "weight": 0.9932,
     "note": "300 trees voting together. Very steady on new data."},
    {"key": "svm", "name": "SVM",           "file": "svm_model.pkl", "weight": 0.9886,
     "note": "RBF kernel. Draws clean borders between crop groups."},
    {"key": "dt",  "name": "Decision Tree", "file": "dt_model.pkl",  "weight": 0.9818,
     "note": "One readable tree. Fast, but the least stable of the five."},
    {"key": "knn", "name": "KNN",           "file": "knn_model.pkl", "weight": 0.9750,
     "note": "Looks at the 3 most similar fields in the training data."},
]

# Short, plain-language note shown next to each recommended crop.
CROP_NOTES = {
    "apple":       "Cool weather, rich potassium, steady water.",
    "banana":      "Warm and humid, hungry for nitrogen and potassium.",
    "blackgram":   "Short-season pulse, does well on modest rainfall.",
    "chickpea":    "Dry, cool finish suits it. Low water need.",
    "coconut":     "Coastal heat and high humidity all year.",
    "coffee":      "Mild temperature, shade, and slightly acid soil.",
    "cotton":      "Long warm season with moderate rain.",
    "grapes":      "Very high potassium, dry air at ripening.",
    "jute":        "Warm, wet, and humid. Loves heavy rainfall.",
    "kidneybeans": "Cool nights, light soil, careful watering.",
    "lentil":      "Low water, cool season pulse.",
    "maize":       "Balanced nutrients, warm days, medium rain.",
    "mango":       "Hot weather, dry spell before flowering.",
    "mothbeans":   "Very drought-hardy. Good on poor, dry land.",
    "mungbean":    "Quick summer pulse, needs warmth not much rain.",
    "muskmelon":   "Hot and dry air, sandy soil, controlled water.",
    "orange":      "Mild climate, good drainage, moderate feeding.",
    "papaya":      "Warm, humid, frost-free, well-drained soil.",
    "pigeonpeas":  "Deep roots, handles dry spells well.",
    "pomegranate": "Hot dry summer, tolerates poor soil.",
    "rice":        "Standing water, high humidity, heavy rainfall.",
    "watermelon":  "Hot sun, sandy soil, steady irrigation.",
}

app = Flask(__name__)

# Filled by load_artifacts()
MODELS, SCALER, LABEL_ENCODER, CLASSES = {}, None, None, []


# ─────────────────────────────────────────────────────────────────────────────
# Startup: load everything, then self-test in a loop before serving traffic.
# ─────────────────────────────────────────────────────────────────────────────
def load_artifacts():
    """Load scaler, encoder and all five models. Fails loudly if anything is off."""
    global MODELS, SCALER, LABEL_ENCODER, CLASSES

    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
    le_path = os.path.join(MODEL_DIR, "label_encoder.pkl")

    for p in (scaler_path, le_path):
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing required file: {p}")

    SCALER = joblib.load(scaler_path)
    LABEL_ENCODER = joblib.load(le_path)
    CLASSES = list(LABEL_ENCODER.classes_)

    assert len(CLASSES) == 22, f"Expected 22 crops, found {len(CLASSES)}"
    assert getattr(SCALER, "n_features_in_", 7) == 7, "Scaler was not fitted on 7 features"
    log.info("Scaler + label encoder loaded (%d crops)", len(CLASSES))

    loaded = {}
    for spec in MODEL_REGISTRY:
        path = os.path.join(MODEL_DIR, spec["file"])
        if not os.path.exists(path):
            log.warning("SKIPPING %s — file not found: %s", spec["name"], spec["file"])
            continue
        model = joblib.load(path)
        if not hasattr(model, "predict_proba"):
            log.warning("SKIPPING %s — no predict_proba, cannot rank crops", spec["name"])
            continue
        loaded[spec["key"]] = {**spec, "model": model}
        log.info("Loaded %-14s (%s)", spec["name"], spec["file"])

    if not loaded:
        raise RuntimeError("No usable models found in ./models")

    MODELS = loaded
    return MODELS


def load_crop_profiles():
    global CROP_PROFILES

    df = pd.read_csv(DATASET_PATH)

    feature_columns = [
        "N",
        "P",
        "K",
        "temperature",
        "humidity",
        "ph",
        "rainfall"
    ]

    # Find the crop/label column
    label_column = "label"

    profiles = {}

    for crop, group in df.groupby(label_column):
        profiles[crop] = {
            feature: round(float(group[feature].median()), 2)
            for feature in feature_columns
        }

    CROP_PROFILES = profiles

def self_test(max_attempts=3):
    """
    Review loop: push known samples through the whole pipeline and check the
    output is sane before the server accepts a single request. Same idea as the
    assertions in the training notebook, moved into serving.
    """
    probes = [
        # (readings, expected crop, why)
        ([90, 42, 43, 20.9, 82.0, 6.5, 202.9], "rice",   "classic paddy profile"),
        ([20, 130, 200, 22.6, 92.5, 5.9, 112.6], "grapes", "very high K"),
        ([40, 72, 77, 17.1, 16.9, 7.0, 88.6],  "chickpea", "dry and cool"),
    ]

    for attempt in range(1, max_attempts + 1):
        failures = []
        for readings, expected, why in probes:
            try:
                result = run_prediction(readings)
            except Exception as exc:                       # noqa: BLE001
                failures.append(f"{why}: crashed — {exc}")
                continue

            top3 = [c["crop"] for c in result["recommendations"]]
            total = sum(c["probability"] for c in result["ensemble_curve"])

            if expected not in top3:
                failures.append(f"{why}: expected '{expected}' in top-3, got {top3}")
            if not (0.98 <= total <= 1.02):
                failures.append(f"{why}: probabilities sum to {total:.3f}, not ~1.0")
            if len(result["model_predictions"]) != len(MODELS):
                failures.append(f"{why}: only {len(result['model_predictions'])} models answered")

        if not failures:
            log.info("Self-test passed on attempt %d — all %d probes OK", attempt, len(probes))
            return True

        log.warning("Self-test attempt %d failed:", attempt)
        for f in failures:
            log.warning("   - %s", f)
        if attempt < max_attempts:
            log.warning("Reloading artifacts and retrying...")
            load_artifacts()

    log.error("Self-test still failing after %d attempts. Serving anyway — "
              "check that the .pkl files match the training run.", max_attempts)
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Prediction
# ─────────────────────────────────────────────────────────────────────────────
def validate(payload):
    """Turn raw form input into a clean 7-value list, or raise ValueError."""
    readings = []
    for feat in FEATURES:
        raw = payload.get(feat, None)
        if raw is None or raw == "":
            raise ValueError(f"{FEATURE_META[feat]['label']} is empty. Enter a value to continue.")
        try:
            val = float(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{FEATURE_META[feat]['label']} must be a number.")
        if not np.isfinite(val):
            raise ValueError(f"{FEATURE_META[feat]['label']} must be a real number.")

        lo, hi = FEATURE_META[feat]["min"], FEATURE_META[feat]["max"]
        if val < lo or val > hi:
            raise ValueError(
                f"{FEATURE_META[feat]['label']} is {val:g}. "
                f"Keep it between {lo:g} and {hi:g} — the models never saw values outside that."
            )
        readings.append(val)
    return readings


def run_prediction(readings):
    """Score one field against all five models and build the combined ranking."""
    x = np.asarray(readings, dtype=float).reshape(1, -1)
    x_scaled = SCALER.transform(x)

    per_model = []
    weighted_sum = np.zeros(len(CLASSES), dtype=float)
    weight_total = 0.0
    agreement = {}

    for spec in MODEL_REGISTRY:
        entry = MODELS.get(spec["key"])
        if entry is None:
            continue

        proba = np.asarray(entry["model"].predict_proba(x_scaled)[0], dtype=float)
        # Guard: some models can return a shorter vector if classes were sparse.
        if proba.shape[0] != len(CLASSES):
            padded = np.zeros(len(CLASSES))
            padded[: proba.shape[0]] = proba
            proba = padded

        best_idx = int(np.argmax(proba))
        best_crop = CLASSES[best_idx]

        order = np.argsort(proba)[::-1][:3]
        per_model.append({
            "key": entry["key"],
            "name": entry["name"],
            "note": entry["note"],
            "accuracy": round(entry["weight"] * 100, 2),
            "prediction": best_crop,
            "confidence": round(float(proba[best_idx]) * 100, 2),
            "top3": [
                {"crop": CLASSES[i], "probability": round(float(proba[i]) * 100, 2)}
                for i in order
            ],
        })

        agreement[best_crop] = agreement.get(best_crop, 0) + 1
        weighted_sum += proba * entry["weight"]
        weight_total += entry["weight"]

    ensemble = weighted_sum / weight_total if weight_total else weighted_sum

    ranked = np.argsort(ensemble)[::-1]
    recommendations = []
    rank_roles = {1: "Best match", 2: "Second choice", 3: "Third choice"}
    for rank, idx in enumerate(ranked[:3], start=1):
        crop = CLASSES[idx]
        votes = agreement.get(crop, 0)
        if votes:
            vote_text = f"{votes} of {len(per_model)} models chose it"
        else:
            vote_text = "no model ranked it first"
        recommendations.append({
            "rank": rank,
            "crop": crop,
            "role": rank_roles.get(rank, "Option"),
            "score": round(float(ensemble[idx]) * 100, 2),
            "votes": votes,
            "vote_text": vote_text,
            "note": CROP_NOTES.get(crop, "Suitable for the readings you entered."),
        })

    # Curve for the chart: every crop with a non-trivial score, max 8 bars.
    curve = [
        {"crop": CLASSES[i], "probability": round(float(ensemble[i]), 6)}
        for i in range(len(CLASSES))
    ]
    ranked_curve = sorted(curve, key=lambda d: d["probability"], reverse=True)
    # Keep crops worth looking at: anything above 0.05%, but always show at
    # least 4 bars and never more than 7.
    chart = [d for d in ranked_curve[:7] if d["probability"] >= 0.0005]
    if len(chart) < 4:
        chart = ranked_curve[:4]

    top_crop = recommendations[0]["crop"]
    consensus = agreement.get(top_crop, 0)

    return {
        "readings": dict(zip(FEATURES, readings)),
        "recommendations": recommendations,
        "model_predictions": per_model,
        "chart": [{"crop": c["crop"], "probability": round(c["probability"] * 100, 2)} for c in chart],
        "ensemble_curve": curve,
        "consensus": {
            "agree": consensus,
            "total": len(per_model),
            "text": _consensus_text(consensus, len(per_model), top_crop),
        },
    }


def _consensus_text(agree, total, crop):
    if total == 0:
        return "No models answered."
    if agree == total:
        return f"All {total} models picked {crop}. Strong match."
    if agree >= total - 1:
        return f"{agree} of {total} models picked {crop}. Good match."
    if agree >= 2:
        return f"{agree} of {total} models picked {crop}. Check the second option too."
    return f"The models disagree. {crop} wins on weighted score, but look at all three options."


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template(
        "index.html",
        features=FEATURES,
        meta=FEATURE_META,
        models=[
            {"key": m["key"], "name": m["name"]}
            for m in MODEL_REGISTRY
            if m["key"] in MODELS
        ],
        crop_count=len(CLASSES),
        crops=CLASSES,
    )


@app.route("/crop-profile/<crop>")
def crop_profile(crop):
    crop = crop.lower()

    if crop not in CROP_PROFILES:
        return jsonify({
            "ok": False,
            "error": "Crop profile not found."
        }), 404

    return jsonify({
        "ok": True,
        "crop": crop,
        "values": CROP_PROFILES[crop]
    })

@app.route("/predict", methods=["POST"])
def predict():
    payload = request.get_json(silent=True) or request.form.to_dict()
    try:
        readings = validate(payload)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    try:
        result = run_prediction(readings)
    except Exception as exc:                               # noqa: BLE001
        log.exception("Prediction failed")
        return jsonify({"ok": False, "error": f"Could not score this field: {exc}"}), 500

    return jsonify({"ok": True, **result})


@app.route("/health")
def health():
    return jsonify({
        "ok": True,
        "models_loaded": [m["name"] for m in MODEL_REGISTRY if m["key"] in MODELS],
        "crops": len(CLASSES),
        "features": FEATURES,
    })


if __name__ == "__main__":
    print("\n" + "=" * 62)
    print("  CROP RECOMMENDATION SYSTEM — starting up")
    print("=" * 62)

    load_artifacts()
    load_crop_profiles()
    self_test()

    print("=" * 62)
    print("  Ready.  Open  http://127.0.0.1:5000")
    print("=" * 62 + "\n")

    app.run(host="127.0.0.1", port=5000, debug=False)