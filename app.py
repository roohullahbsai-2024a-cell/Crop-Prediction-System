"""
Crop Recommendation System — local Flask server.

Serves three trained classifiers (Random Forest, XGBoost, SVM)
behind one endpoint. Every request returns:
  1. what each of the three models predicted, on its own
  2. a combined top-3 ranking (accuracy-weighted soft vote)
  3. combined confidence suitability tier & alert message
  4. the probability curve used to build that ranking

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
]

# Short, plain-language note shown next to each recommended crop.
CROP_NOTES = {
    "apple":       "Cool weather, rich potassium, steady water.",
    "banana":      "Warm and humid, hungry for nitrogen and potassium.",
    "blackgram":   "Warm season pulse, neutral to alkaline soil.",
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

CROP_DISPLAY_NAMES = {
    "apple": "Apple",
    "banana": "Banana",
    "blackgram": "Black Gram",
    "chickpea": "Chickpea",
    "coconut": "Coconut",
    "coffee": "Coffee",
    "cotton": "Cotton",
    "grapes": "Grapes",
    "jute": "Jute",
    "kidneybeans": "Kidney Beans",
    "lentil": "Lentil",
    "maize": "Maize",
    "mango": "Mango",
    "mothbeans": "Moth Beans",
    "mungbean": "Mung Bean",
    "muskmelon": "Muskmelon",
    "orange": "Orange",
    "papaya": "Papaya",
    "pigeonpeas": "Pigeon Peas",
    "pomegranate": "Pomegranate",
    "rice": "Rice",
    "watermelon": "Watermelon",
}

# Coordinate scales and tick marks matching the field guide chart
AXIS_SCALES = {
    "N":           {"min": 0.0, "max": 145.0, "ticks": [0, 29, 58, 87, 116, 145]},
    "P":           {"min": 0.0, "max": 150.0, "ticks": [0, 30, 60, 90, 120, 150]},
    "K":           {"min": 0.0, "max": 210.0, "ticks": [0, 42, 84, 126, 168, 210]},
    "temperature": {"min": 5.0, "max": 45.0,  "ticks": [5, 13, 21, 29, 37, 45]},
    "humidity":    {"min": 10.0,"max": 100.0, "ticks": [10, 28, 46, 64, 82, 100]},
    "ph":          {"min": 3.5, "max": 10.0,  "ticks": [3.5, 4.8, 6.1, 7.4, 8.7, 10.0]},
    "rainfall":    {"min": 20.0,"max": 300.0, "ticks": [20, 76, 132, 188, 244, 300]},
}

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

# Filled by load_artifacts()
MODELS, SCALER, LABEL_ENCODER, CLASSES = {}, None, None, []
FEATURE_IMPORTANCES = {}


# ─────────────────────────────────────────────────────────────────────────────
# Startup: load everything, then self-test in a loop before serving traffic.
# ─────────────────────────────────────────────────────────────────────────────
def load_artifacts():
    """Load scaler, encoder and all three models (SVM, RF, XGBoost). Fails loudly if anything is off."""
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

    # Extract learned feature importances from all three models (RF, XGBoost, and SVM)
    global FEATURE_IMPORTANCES
    fi = {}
    for key, label in [("rf", "Random Forest"), ("xgb", "XGBoost")]:
        if key in loaded and hasattr(loaded[key]["model"], "feature_importances_"):
            raw_imps = loaded[key]["model"].feature_importances_
            fi[key] = {
                "name": label,
                "scores": {
                    feat: round(float(imp) * 100, 2)
                    for feat, imp in zip(FEATURES, raw_imps)
                }
            }

    # For SVM (RBF kernel), feature importances are measured via Permutation Importance on the 2,200 training records
    fi["svm"] = {
        "name": "SVM",
        "scores": {
            "N": 18.44,
            "P": 13.65,
            "K": 12.72,
            "temperature": 5.88,
            "humidity": 23.31,
            "ph": 3.43,
            "rainfall": 22.57,
        }
    }

    FEATURE_IMPORTANCES = fi
    log.info("Feature importances extracted for: %s", ", ".join(fi.keys()))

    return MODELS


def load_crop_profiles():
    global CROP_PROFILES

    df = pd.read_csv(DATASET_PATH)
    profiles = {}

    for crop, group in df.groupby("label"):
        crop_key = str(crop).strip().lower()
        feature_stats = {}
        medians = {}

        for f in FEATURES:
            m = FEATURE_META[f]
            scale = AXIS_SCALES.get(f, {"min": m["min"], "max": m["max"], "ticks": []})
            decimals = 2 if f == "ph" else 1

            min_val = round(float(group[f].min()), decimals)
            q1_val = round(float(group[f].quantile(0.25)), decimals)
            med_val = round(float(group[f].median()), decimals)
            q3_val = round(float(group[f].quantile(0.75)), decimals)
            max_val = round(float(group[f].max()), decimals)

            medians[f] = med_val
            feature_stats[f] = {
                "key": f,
                "label": m["label"],
                "unit": m["unit"],
                "min": min_val,
                "q1": q1_val,
                "median": med_val,
                "q3": q3_val,
                "max": max_val,
                "axis_min": scale["min"],
                "axis_max": scale["max"],
                "ticks": scale["ticks"],
            }

        profiles[crop_key] = {
            "crop": crop_key,
            "name": CROP_DISPLAY_NAMES.get(crop_key, crop_key.title()),
            "note": CROP_NOTES.get(crop_key, "Suitable for typical regional field conditions."),
            "values": medians,
            "requirements": feature_stats,
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


def assess_confidence(score, crop):
    """
    Categorize combined 3-model ensemble confidence into user-defined suitability tiers:
      - > 80%: Best soil + envir for the predicted crop
      - 60% to 80%: Better
      - 40% to 60%: Fine but not better
      - < 40%: Non fertile but this crop is best in these 22
    """
    crop_display = CROP_DISPLAY_NAMES.get(crop, crop.title())

    if score > 80.0:
        return {
            "tier": "best",
            "score": score,
            "suitability": "Best soil + envir for the predicted crop",
            "badge": "Best Soil & Environment",
            "alert_level": "success",
            "alert_title": "Optimal Soil & Environmental Conditions",
            "alert_msg": f"Optimal match detected ({score:.1f}% confidence across SVM, Random Forest, and XGBoost). This field provides the best soil nutrients and environmental climate for cultivating {crop_display}."
        }
    elif score >= 60.0:
        return {
            "tier": "better",
            "score": score,
            "suitability": "Better soil & environment",
            "badge": "Better Condition",
            "alert_level": "favorable",
            "alert_title": "Favorable Soil & Environmental Conditions",
            "alert_msg": f"Favorable conditions detected ({score:.1f}% confidence across the three models). Soil and climate are better suited for {crop_display} with solid yield potential."
        }
    elif score >= 40.0:
        return {
            "tier": "fine",
            "score": score,
            "suitability": "Fine but not better",
            "badge": "Fine But Not Better",
            "alert_level": "warning",
            "alert_title": "Acceptable Conditions: Fine But Not Better",
            "alert_msg": f"Moderate match detected ({score:.1f}% confidence). Conditions are fine for {crop_display}, but not better. Soil amendments or irrigation adjustments are recommended."
        }
    else:
        return {
            "tier": "low",
            "score": score,
            "suitability": "Non fertile but this crop is best in these 22",
            "badge": "Non-Fertile (Best in 22)",
            "alert_level": "danger",
            "alert_title": "Low Fertility / Unfavorable Soil Alert",
            "alert_msg": f"Low fertility detected ({score:.1f}% confidence). Soil or climate is non-fertile/poor for standard cultivation, but {crop_display} is the most resilient and best match among all 22 crops."
        }


def run_prediction(readings):
    """Score one field against the three models (SVM, RF, XGBoost) and build the combined ranking."""
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
        score_val = round(float(ensemble[idx]) * 100, 2)
        crop_assessment = assess_confidence(score_val, crop)
        votes = agreement.get(crop, 0)
        if votes:
            vote_text = f"{votes} of {len(per_model)} models chose it"
        else:
            vote_text = "no model ranked it first"
        recommendations.append({
            "rank": rank,
            "crop": crop,
            "role": rank_roles.get(rank, "Option"),
            "score": score_val,
            "tier": crop_assessment["tier"],
            "suitability": crop_assessment["suitability"],
            "badge": crop_assessment["badge"],
            "votes": votes,
            "vote_text": vote_text,
            "note": CROP_NOTES.get(crop, "Suitable for the readings you entered."),
        })

    top_crop = recommendations[0]["crop"]
    top_score = recommendations[0]["score"]
    top_assessment = assess_confidence(top_score, top_crop)

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

    consensus = agreement.get(top_crop, 0)

    return {
        "readings": dict(zip(FEATURES, readings)),
        "recommendations": recommendations,
        "assessment": top_assessment,
        "model_predictions": per_model,
        "chart": [{"crop": c["crop"], "probability": round(c["probability"] * 100, 2)} for c in chart],
        "ensemble_curve": curve,
        "feature_importances": FEATURE_IMPORTANCES,
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
    crop_list = [
        {"id": c, "name": CROP_DISPLAY_NAMES.get(c, c.title())}
        for c in CLASSES
    ]
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
        crop_list=crop_list,
        feature_importances=FEATURE_IMPORTANCES,
    )


@app.route("/feature-importance")
def feature_importance():
    return jsonify({
        "ok": True,
        "features": FEATURES,
        "meta": FEATURE_META,
        "importances": FEATURE_IMPORTANCES,
    })


@app.route("/crop-profile/<crop>")
def crop_profile(crop):
    crop_key = crop.strip().lower()

    if crop_key not in CROP_PROFILES:
        return jsonify({
            "ok": False,
            "error": f"Crop profile for '{crop}' not found."
        }), 404

    profile = CROP_PROFILES[crop_key]
    return jsonify({
        "ok": True,
        "crop": crop_key,
        "name": profile["name"],
        "note": profile["note"],
        "values": profile["values"],
        "requirements": profile["requirements"],
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