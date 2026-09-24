/* ===========================================================================
   Crop Recommendation System — front end
   Manages the dual-view interface:
   1. Static Crop Requirements Guide (boxplots, percentiles, workable ranges)
   2. Multi-Model Recommendations (accuracy-weighted soft voting & charts)
   =========================================================================== */

(function () {
  "use strict";

  const FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"];
  const DEFAULTS = {};

  const form       = document.getElementById("form");
  const goBtn      = document.getElementById("go");
  const goText     = document.getElementById("go-text");
  const errBox     = document.getElementById("error");
  const results    = document.getElementById("results");
  const cropSelect = document.getElementById("crop-select");

  let currentCropProfile = null;
  let currentPredictionData = null;
  let activeView = "guide"; // 'guide' | 'prediction'

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ------------------------------------------------ slider / number syncing */

  function paintTrack(rng) {
    const min = parseFloat(rng.min), max = parseFloat(rng.max);
    const pct = ((parseFloat(rng.value) - min) / (max - min)) * 100;
    rng.style.setProperty("--fill", pct.toFixed(2) + "%");
  }

  function clamp(el, value) {
    const min = parseFloat(el.min), max = parseFloat(el.max);
    if (isNaN(value)) return parseFloat(el.value) || min;
    return Math.min(max, Math.max(min, value));
  }

  FEATURES.forEach(function (f) {
    const rng = document.getElementById("rng-" + f);
    const num = document.getElementById("num-" + f);
    if (!rng || !num) return;

    DEFAULTS[f] = num.value;
    paintTrack(rng);

    rng.addEventListener("input", function () {
      num.value = rng.value;
      paintTrack(rng);
    });

    num.addEventListener("input", function () {
      const v = parseFloat(num.value);
      if (!isNaN(v)) {
        rng.value = clamp(rng, v);
        paintTrack(rng);
      }
    });

    num.addEventListener("blur", function () {
      const v = clamp(num, parseFloat(num.value));
      num.value = v;
      rng.value = v;
      paintTrack(rng);
    });
  });

  /* ------------------------------------------------ crop guide & selector */

  function loadCropGuide(crop, updateInputs) {
    if (!crop) return;

    fetch("/crop-profile/" + encodeURIComponent(crop))
      .then(function (response) {
        return response.json();
      })
      .then(function (data) {
        if (!data.ok) {
          showError(data.error || "Could not load crop profile.");
          return;
        }

        currentCropProfile = data;

        if (updateInputs && data.values) {
          FEATURES.forEach(function (f) {
            const value = data.values[f];
            const rng = document.getElementById("rng-" + f);
            const num = document.getElementById("num-" + f);
            if (!rng || !num || value === undefined) return;
            num.value = value;
            rng.value = clamp(rng, parseFloat(value));
            paintTrack(rng);
          });
        }

        activeView = "guide";
        renderView();
        hideError();
      })
      .catch(function () {
        showError("Could not load the crop guide. Is app.py running?");
      });
  }

  if (cropSelect) {
    cropSelect.addEventListener("change", function () {
      loadCropGuide(cropSelect.value, true);
    });
  }

  /* -------------------------------------------------------------- presets */

  document.querySelectorAll(".chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      const vals = chip.dataset.preset.split(",");
      FEATURES.forEach(function (f, i) {
        const rng = document.getElementById("rng-" + f);
        const num = document.getElementById("num-" + f);
        num.value = vals[i];
        rng.value = vals[i];
        paintTrack(rng);
      });
      hideError();
      form.requestSubmit();
    });
  });

  document.getElementById("reset").addEventListener("click", function () {
    FEATURES.forEach(function (f) {
      const rng = document.getElementById("rng-" + f);
      const num = document.getElementById("num-" + f);
      num.value = DEFAULTS[f];
      rng.value = DEFAULTS[f];
      paintTrack(rng);
    });
    hideError();
    if (currentCropProfile) {
      activeView = "guide";
      renderView();
    } else {
      results.innerHTML = emptyState();
    }
  });

  /* ---------------------------------------------------------------- errors */

  function showError(msg) {
    errBox.textContent = msg;
    errBox.classList.add("show");
  }

  function hideError() {
    errBox.classList.remove("show");
    errBox.textContent = "";
  }

  /* ---------------------------------------------------------------- submit */

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    hideError();

    const payload = {};
    for (let i = 0; i < FEATURES.length; i++) {
      const f = FEATURES[i];
      const raw = document.getElementById("num-" + f).value;
      if (raw === "") {
        showError("Fill in every reading before scoring the field.");
        document.getElementById("num-" + f).focus();
        return;
      }
      payload[f] = raw;
    }

    setBusy(true);

    fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
      .then(function (res) {
        if (!res.ok || !res.body.ok) {
          showError(res.body.error || "Scoring failed. Check the server window for details.");
          return;
        }
        currentPredictionData = res.body;
        activeView = "prediction";
        renderView();
      })
      .catch(function () {
        showError("Could not reach the server. Is app.py still running?");
      })
      .finally(function () { setBusy(false); });
  });

  function setBusy(on) {
    goBtn.disabled = on;
    goBtn.classList.toggle("is-busy", on);
    goText.textContent = on ? "Scoring your field" : "Recommend a Crop";
  }

  /* -------------------------------------------------------------- renders */

  function esc(s) {
    return String(s || "").replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function emptyState() {
    return '' +
      '<div class="empty">' +
      '  <svg class="sprout-mark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '    <path d="M12 21v-9"/><path d="M12 12C12 8 9 5 5 5c0 4 3 7 7 7z"/><path d="M12 14c0-3.3 2.7-6 6-6 0 3.3-2.7 6-6 6z"/>' +
      '  </svg>' +
      '  <h3>Nothing selected yet</h3>' +
      '  <p>Pick a crop above to see acceptable ranges, or enter field readings to score.</p>' +
      '</div>';
  }

  function renderView() {
    if (!results) return;

    const cropName = currentCropProfile ? esc(currentCropProfile.name) : "Blank Data";

    const switcherHtml = '' +
      '<div class="results-switcher">' +
      '  <button type="button" class="results-tab-btn ' + (activeView === "guide" ? "active" : "") + '" id="tab-guide">' +
      '    <span>Static Crop Guide (' + cropName + ')</span>' +
      '  </button>' +
      '  <button type="button" class="results-tab-btn ' + (activeView === "prediction" ? "active" : "") + '" id="tab-pred">' +
      '    <span>Model Recommendations</span>' +
      '  </button>' +
      '</div>';

    if (activeView === "guide" && currentCropProfile) {
      results.innerHTML = switcherHtml + renderCropGuide(currentCropProfile);
    } else if (activeView === "prediction" && currentPredictionData) {
      results.innerHTML = switcherHtml + renderPrediction(currentPredictionData);
      animatePrediction();
    } else if (activeView === "prediction" && !currentPredictionData) {
      form.requestSubmit();
      return;
    }

    // Attach tab events
    const tabGuide = document.getElementById("tab-guide");
    const tabPred  = document.getElementById("tab-pred");
    if (tabGuide) {
      tabGuide.addEventListener("click", function () {
        activeView = "guide";
        renderView();
      });
    }
    if (tabPred) {
      tabPred.addEventListener("click", function () {
        if (!currentPredictionData) {
          form.requestSubmit();
        } else {
          activeView = "prediction";
          renderView();
        }
      });
    }

    if (window.innerWidth <= 960 && activeView === "prediction") {
      results.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
    }
  }

  /* ---------------------------------------------------- Feature Icons */

  const FEATURE_ICONS = {
    N: '<span class="field-icon-bullet icon-n"><svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 21v-8"></path><path d="M12 13C12 9 9 6 5 6c0 4 3 7 7 7z"></path></svg></span>',
    P: '<span class="field-icon-bullet icon-p">P</span>',
    K: '<span class="field-icon-bullet icon-k">K</span>',
    temperature: '<span class="field-icon-bullet icon-temp"><svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"></path></svg></span>',
    humidity: '<span class="field-icon-bullet icon-hum"><svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"></path></svg></span>',
    ph: '<span class="field-icon-bullet icon-ph">pH</span>',
    rainfall: '<span class="field-icon-bullet icon-rain"><svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"></path><line x1="8" y1="19" x2="8" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line><line x1="16" y1="19" x2="16" y2="21"></line></svg></span>'
  };

  /* Per-feature color palettes for the box plot */
  const FEAT_COLORS = {
    N:           { box: '#16a34a', boxFill: '#bbf7d0', boxFill2: '#4ade80', whisker: '#15803d', median: '#ffffff', medianStroke: '#14532d' },
    P:           { box: '#2563eb', boxFill: '#bfdbfe', boxFill2: '#60a5fa', whisker: '#1d4ed8', median: '#ffffff', medianStroke: '#1e3a8a' },
    K:           { box: '#7c3aed', boxFill: '#ddd6fe', boxFill2: '#a78bfa', whisker: '#6d28d9', median: '#ffffff', medianStroke: '#4c1d95' },
    temperature: { box: '#ea580c', boxFill: '#fed7aa', boxFill2: '#fb923c', whisker: '#c2410c', median: '#ffffff', medianStroke: '#7c2d12' },
    humidity:    { box: '#0891b2', boxFill: '#a5f3fc', boxFill2: '#22d3ee', whisker: '#0e7490', median: '#ffffff', medianStroke: '#164e63' },
    ph:          { box: '#d97706', boxFill: '#fde68a', boxFill2: '#fbbf24', whisker: '#b45309', median: '#ffffff', medianStroke: '#78350f' },
    rainfall:    { box: '#0284c7', boxFill: '#bae6fd', boxFill2: '#38bdf8', whisker: '#075985', median: '#ffffff', medianStroke: '#0c4a6e' }
  };

  /* ---------------------------------------------------- Boxplot SVG Builder */

  function buildBoxPlotSvg(req, featKey) {
    const padL = 34;
    const padR = 566;
    const plotW = padR - padL;
    const axisMin = req.axis_min;
    const axisMax = req.axis_max;
    const span = (axisMax - axisMin) || 1;
    const c = FEAT_COLORS[featKey] || { box: '#16a34a', boxFill: '#bbf7d0', boxFill2: '#4ade80', whisker: '#15803d', median: '#ffffff', medianStroke: '#14532d' };
    const gradId = 'bp-grad-' + (featKey || 'def');

    function toX(v) {
      const clamped = Math.max(axisMin, Math.min(axisMax, v));
      return padL + ((clamped - axisMin) / span) * plotW;
    }

    const minX = toX(req.min);
    const q1X  = toX(req.q1);
    const medX = toX(req.median);
    const q3X  = toX(req.q3);
    const maxX = toX(req.max);
    const boxW = Math.max(6, q3X - q1X);

    // Axis ticks
    let ticksSvg = '';
    (req.ticks || []).forEach(function (t) {
      const tx = toX(t);
      ticksSvg += '<line x1="' + tx.toFixed(1) + '" y1="18" x2="' + tx.toFixed(1) + '" y2="24" stroke="#1a2e1e" stroke-width="1.6"/>';
      ticksSvg += '<text x="' + tx.toFixed(1) + '" y="36" font-size="11.5" fill="#1a2e1e" text-anchor="middle" font-family="var(--sans)" font-weight="700" letter-spacing="-0.2">' + t + '</text>';
    });

    return '' +
      '<svg class="guide-chart-svg" viewBox="0 0 600 44" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Range chart">' +
      '  <defs>' +
      '    <linearGradient id="' + gradId + '" x1="0" y1="0" x2="0" y2="1">' +
      '      <stop offset="0%" stop-color="' + c.boxFill2 + '" stop-opacity="0.95"/>' +
      '      <stop offset="100%" stop-color="' + c.boxFill + '" stop-opacity="0.85"/>' +
      '    </linearGradient>' +
      '  </defs>' +
      '  <!-- Baseline axis -->' +
      '  <line x1="' + padL + '" y1="18" x2="' + padR + '" y2="18" stroke="#1a2e1e" stroke-width="2"/>' +
      '  <!-- Ticks -->' +
      ticksSvg +
      '  <!-- Workable range whisker line -->' +
      '  <line x1="' + minX.toFixed(1) + '" y1="18" x2="' + maxX.toFixed(1) + '" y2="18" stroke="' + c.whisker + '" stroke-width="2.4" stroke-linecap="round"/>' +
      '  <!-- Min cap -->' +
      '  <line x1="' + minX.toFixed(1) + '" y1="11" x2="' + minX.toFixed(1) + '" y2="25" stroke="' + c.whisker + '" stroke-width="2.4" stroke-linecap="round"/>' +
      '  <!-- Max cap -->' +
      '  <line x1="' + maxX.toFixed(1) + '" y1="11" x2="' + maxX.toFixed(1) + '" y2="25" stroke="' + c.whisker + '" stroke-width="2.4" stroke-linecap="round"/>' +
      '  <!-- IQR box with gradient fill -->' +
      '  <rect x="' + q1X.toFixed(1) + '" y="10" width="' + boxW.toFixed(1) + '" height="16" rx="3.5" fill="url(#' + gradId + ')" stroke="' + c.box + '" stroke-width="2"/>' +
      '  <!-- Median line -->' +
      '  <line x1="' + medX.toFixed(1) + '" y1="10" x2="' + medX.toFixed(1) + '" y2="26" stroke="' + c.medianStroke + '" stroke-width="3.5" stroke-linecap="round"/>' +
      '  <line x1="' + medX.toFixed(1) + '" y1="10" x2="' + medX.toFixed(1) + '" y2="26" stroke="' + c.median + '" stroke-width="1.8" stroke-linecap="round" opacity="0.85"/>' +
      '</svg>';
  }

  /* ---------------------------------------------------- Render Crop Guide */

  function renderCropGuide(profile) {
    let rowsHtml = "";

    FEATURES.forEach(function (f) {
      const req = profile.requirements[f];
      if (!req) return;

      const icon = FEATURE_ICONS[f] || "";
      const unitStr = req.unit ? " " + esc(req.unit) : "";
      const idealText = "Ideal " + req.q1 + "–" + req.q3 + unitStr;
      const workableText = "Workable " + req.min + "–" + req.max + unitStr;

      rowsHtml += '' +
        '<div class="guide-feature-box feat-' + f + '">' +
        '  <div class="guide-feature-head">' +
        '    <div class="guide-feature-title-group">' +
        '      ' + icon +
        '      <span class="guide-feature-name">' + esc(req.label) + '</span>' +
        '    </div>' +
        '    <div class="guide-feature-badges">' +
        '      <span class="guide-feature-ideal">' + esc(idealText) + '</span>' +
        '      <span class="guide-feature-workable">' + esc(workableText) + '</span>' +
        '    </div>' +
        '  </div>' +
        '  <div class="guide-chart-box">' +
        buildBoxPlotSvg(req, f) +
        '  </div>' +
        '</div>';
    });

    return '' +
      '<div class="static-crop-guide reveal" style="--d:0ms">' +
      '  <div class="guide-header-top">' +
      '    <span class="guide-tag">CROP REQUIREMENTS</span>' +
      '    <span class="guide-badge">Static crop guide</span>' +
      '  </div>' +
      '  <h3 class="guide-title">Acceptable range for ' + esc(profile.name) + '</h3>' +
      '  <p class="guide-subtitle">' + esc(profile.note) + '</p>' +
      rowsHtml +
      '  <div class="guide-legend">' +
      '    <div class="legend-item">' +
      '      <span class="legend-swatch-box" aria-hidden="true"></span>' +
      '      <span>Most suitable range (Q1–Q3)</span>' +
      '    </div>' +
      '    <div class="legend-item">' +
      '      <span class="legend-swatch-line" aria-hidden="true"></span>' +
      '      <span>Typical value (Median)</span>' +
      '    </div>' +
      '    <div class="legend-item">' +
      '      <span class="legend-swatch-whisker" aria-hidden="true"></span>' +
      '      <span>Workable range (Min–Max)</span>' +
      '    </div>' +
      '  </div>' +
      '</div>';
  }

  /* ---------------------------------------------------- Render Prediction */

  function renderAlertBox(assessment) {
    if (!assessment) return "";
    const tier = assessment.tier || "best";

    let iconSvg = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21v-9"></path><path d="M12 12C12 8 9 5 5 5c0 4 3 7 7 7z"></path><path d="M12 14c0-3.3 2.7-6 6-6 0 3.3-2.7 6-6 6z"></path></svg>';

    return '' +
      '<div class="confidence-alert alert-' + esc(tier) + ' reveal" style="--d:0ms" role="region" aria-label="Confidence & Suitability Alert">' +
      '  <div class="alert-top">' +
      '    <div class="alert-title-wrap">' +
      '      <span class="alert-icon-circle" aria-hidden="true">' + iconSvg + '</span>' +
      '      <div class="alert-header-info">' +
      '        <h4 class="alert-heading">' + esc(assessment.alert_title) + '</h4>' +
      '      </div>' +
      '    </div>' +
      '  </div>' +
      '  <p class="alert-msg-body">' + esc(assessment.alert_msg) + '</p>' +
      '</div>';
  }

  /* ---------------------------------------------------- Feature Importance */

  const FEATURE_INFO = {
    N:           { short: "N",    name: "Nitrogen",    unit: "kg/ha" },
    P:           { short: "P",    name: "Phosphorus",  unit: "kg/ha" },
    K:           { short: "K",    name: "Potassium",   unit: "kg/ha" },
    temperature: { short: "Temp", name: "Temperature", unit: "°C" },
    humidity:    { short: "Hum",  name: "Humidity",    unit: "%" },
    ph:          { short: "pH",   name: "Soil pH",     unit: "" },
    rainfall:    { short: "Rain", name: "Rainfall",    unit: "mm" }
  };

  const DEFAULT_IMPORTANCES = {
    rf:  { name: "Random Forest", scores: { N: 10.33, P: 14.94, K: 17.68, temperature: 6.78, humidity: 21.37, ph: 5.02, rainfall: 23.88 } },
    xgb: { name: "XGBoost",       scores: { N: 13.00, P: 15.84, K: 19.59, temperature: 12.79, humidity: 15.28, ph: 9.50, rainfall: 13.99 } },
    svm: { name: "SVM",           scores: { N: 18.44, P: 13.65, K: 12.72, temperature: 5.88, humidity: 23.31, ph: 3.43, rainfall: 22.57 } }
  };

  function renderFeatureImportance(fiData) {
    const data = fiData || DEFAULT_IMPORTANCES;
    const rfScores  = (data.rf && data.rf.scores)   ? data.rf.scores  : DEFAULT_IMPORTANCES.rf.scores;
    const xgbScores = (data.xgb && data.xgb.scores) ? data.xgb.scores : DEFAULT_IMPORTANCES.xgb.scores;
    const svmScores = (data.svm && data.svm.scores) ? data.svm.scores : DEFAULT_IMPORTANCES.svm.scores;

    // Maximum importance in dataset is ~23.9%, so scale to 26% max height
    const maxScale = 26.0;

    let barsHtml = "";
    let axisHtml = "";
    FEATURES.forEach(function (f) {
      const meta   = FEATURE_INFO[f] || { short: f, name: f, unit: "" };
      const rfVal  = rfScores[f]  || 0;
      const xgVal  = xgbScores[f] || 0;
      const svmVal = svmScores[f] || 0;

      const rfHeightPct  = Math.min(100, (rfVal / maxScale) * 100);
      const xgHeightPct  = Math.min(100, (xgVal / maxScale) * 100);
      const svmHeightPct = Math.min(100, (svmVal / maxScale) * 100);

      barsHtml += '' +
        '<div class="fi-bars-group">' +
        '  <!-- RF Bar (Purple) -->' +
        '  <div class="fi-bar-item">' +
        '    <span class="fi-bar-val rf-val">' + rfVal.toFixed(1) + '%</span>' +
        '    <div class="fi-bar-track">' +
        '      <div class="fi-bar bar-rf" data-h="' + rfHeightPct.toFixed(1) + '" style="height: 0%" title="RF (Random Forest): ' + rfVal.toFixed(2) + '%">' +
        '        <span class="fi-bar-sublabel">RF</span>' +
        '      </div>' +
        '    </div>' +
        '  </div>' +
        '  <!-- XG Bar (Blue) -->' +
        '  <div class="fi-bar-item">' +
        '    <span class="fi-bar-val xg-val">' + xgVal.toFixed(1) + '%</span>' +
        '    <div class="fi-bar-track">' +
        '      <div class="fi-bar bar-xg" data-h="' + xgHeightPct.toFixed(1) + '" style="height: 0%" title="XG (XGBoost): ' + xgVal.toFixed(2) + '%">' +
        '        <span class="fi-bar-sublabel">XG</span>' +
        '      </div>' +
        '    </div>' +
        '  </div>' +
        '  <!-- SVM Bar (Green) -->' +
        '  <div class="fi-bar-item">' +
        '    <span class="fi-bar-val svm-val">' + svmVal.toFixed(1) + '%</span>' +
        '    <div class="fi-bar-track">' +
        '      <div class="fi-bar bar-svm" data-h="' + svmHeightPct.toFixed(1) + '" style="height: 0%" title="SVM (Support Vector Machine): ' + svmVal.toFixed(2) + '%">' +
        '        <span class="fi-bar-sublabel">SVM</span>' +
        '      </div>' +
        '    </div>' +
        '  </div>' +
        '</div>';

      axisHtml += '' +
        '<div class="fi-axis-item">' +
        '  <b class="fi-feat-code">' + esc(meta.short) + '</b>' +
        '  <span class="fi-feat-name">' + esc(meta.name) + '</span>' +
        '</div>';
    });

    return '' +
      '<div class="section-title reveal" style="--d:800ms">' +
      '  <div class="title-left">' +
      '    <span class="title-bullet-icon purple">' +
      '      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.3"><rect x="3" y="12" width="4" height="9"></rect><rect x="10" y="6" width="4" height="15"></rect><rect x="17" y="2" width="4" height="19"></rect></svg>' +
      '    </span>' +
      '    <span>Which Numerical Feature is Important</span>' +
      '  </div>' +
      '  <small>Three-model feature importance comparison (RF vs XGBoost vs SVM)</small>' +
      '</div>' +
      '<div class="fi-card reveal" style="--d:850ms">' +
      '  <div class="fi-head">' +
      '    <div class="fi-title-desc">' +
      '      <h4>Three-Model Decision Weights by Numerical Feature</h4>' +
      '      <p>Grouped importance scores showing how each numerical feature guides Random Forest, XGBoost, and SVM</p>' +
      '    </div>' +
      '    <div class="fi-legend">' +
      '      <div class="fi-legend-chip rf-chip">' +
      '        <span class="fi-chip-box rf-box"></span>' +
      '        <span><b>RF</b> Random Forest</span>' +
      '      </div>' +
      '      <div class="fi-legend-chip xg-chip">' +
      '        <span class="fi-chip-box xg-box"></span>' +
      '        <span><b>XG</b> XGBoost</span>' +
      '      </div>' +
      '      <div class="fi-legend-chip svm-chip">' +
      '        <span class="fi-chip-box svm-box"></span>' +
      '        <span><b>SVM</b> Support Vector</span>' +
      '      </div>' +
      '    </div>' +
      '  </div>' +
      '  <div class="fi-chart-wrapper">' +
      '    <div class="fi-plot-area">' +
      '      <div class="fi-grid-lines" aria-hidden="true">' +
      '        <div class="fi-grid-line"><span class="grid-num">25%</span></div>' +
      '        <div class="fi-grid-line"><span class="grid-num">20%</span></div>' +
      '        <div class="fi-grid-line"><span class="grid-num">15%</span></div>' +
      '        <div class="fi-grid-line"><span class="grid-num">10%</span></div>' +
      '        <div class="fi-grid-line"><span class="grid-num">5%</span></div>' +
      '        <div class="fi-grid-line fi-baseline"><span class="grid-num">0%</span></div>' +
      '      </div>' +
      '      <div class="fi-bars-row">' +
      barsHtml +
      '      </div>' +
      '    </div>' +
      '    <div class="fi-axis-row">' +
      axisHtml +
      '    </div>' +
      '  </div>' +
      '  <div class="fi-insight-banner">' +
      '    <span class="fi-insight-badge">Key Finding</span>' +
      '    <p><b>Rainfall</b> (RF 23.9%, SVM 22.6%) and <b>Humidity</b> (SVM 23.3%, RF 21.4%) dominate model decisions, <b>Potassium</b> (XG 19.6%) strongly guides XGBoost, and <b>Nitrogen</b> (SVM 18.4%) plays a pivotal role in SVM boundary classification.</p>' +
      '  </div>' +
      '</div>';
  }

  /* ---------------------------------------------------- Render Prediction */

  function renderAlertBox(assessment) {
    if (!assessment) return "";
    const tier = assessment.tier || "best";

    let iconSvg = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21v-9"></path><path d="M12 12C12 8 9 5 5 5c0 4 3 7 7 7z"></path><path d="M12 14c0-3.3 2.7-6 6-6 0 3.3-2.7 6-6 6z"></path></svg>';

    return '' +
      '<div class="confidence-alert alert-' + esc(tier) + ' reveal" style="--d:0ms" role="region" aria-label="Confidence & Suitability Alert">' +
      '  <div class="alert-top">' +
      '    <div class="alert-title-wrap">' +
      '      <span class="alert-icon-circle" aria-hidden="true">' + iconSvg + '</span>' +
      '      <div class="alert-header-info">' +
      '        <h4 class="alert-heading">' + esc(assessment.alert_title) + '</h4>' +
      '      </div>' +
      '    </div>' +
      '  </div>' +
      '  <p class="alert-msg-body">' + esc(assessment.alert_msg) + '</p>' +
      '</div>';
  }

  /* ------------------------------- Why This Crop is Best Reasoning */

  const CROP_REASONS = {
    apple: {
      lead: "Apple is your best choice because your field provides the cool temperate climate, steady soil moisture, and rich potassium reserves essential for bud development, blossom density, and firm fruit formation.",
      moisture: "Apples require well-distributed, steady moisture without waterlogging, keeping roots aerated during fruit enlargement.",
      npk: "High potassium content supports sugar transport, cellular turgor, and cold resilience, while moderate nitrogen prevents excessive canopy growth.",
      climate: "Cool daytime temperatures and cold nocturnal chill hours satisfy dormancy breaking and optimal fruit coloring.",
      ph: "Slightly acidic to neutral soil promotes ideal micronutrient solubility (zinc, iron, and boron) vital for pome fruit health."
    },
    banana: {
      lead: "Banana is your best choice because your field delivers generous warmth, tropical air moisture, and heavy nitrogen and potassium availability that fuel rapid stem growth and heavy harvest bunches.",
      moisture: "Elevated rainfall and humid conditions maintain high leaf transpiration rates and prevent dry-season moisture stress.",
      npk: "Heavy nitrogen feeding accelerates pseudostem leaf emergence while high potassium builds strong bunches and sweet pulp.",
      climate: "Consistent tropical warmth allows uninterrupted year-round vegetative cycles and rapid finger filling.",
      ph: "Slightly acid to neutral soil texture prevents chlorosis and optimizes vigorous root foraging."
    },
    blackgram: {
      lead: "Black Gram is your best choice because it thrives in warm weather and well-drained neutral-to-alkaline soil, leveraging symbiotic rhizobia to produce nutrient-dense pulses with low water reliance.",
      moisture: "Handles moderate showers efficiently and tolerates drier spells during pod development without yield collapse.",
      npk: "Efficient pulse nutrition: fixes atmospheric nitrogen organically, utilizing available phosphorus for strong taproots.",
      climate: "Warm seasonal temperatures stimulate quick germination and continuous floral flushes.",
      ph: "Neutral to mildly alkaline soil ensures optimal nodule bacterial viability and rapid nutrient absorption."
    },
    chickpea: {
      lead: "Chickpea is your best choice because your field exhibits low moisture retention and mild temperatures, providing the dry conditions necessary to prevent Ascochyta blight and pod rot.",
      moisture: "Highly efficient water use; excess water harms chickpeas, making lower rainfall fields ideal for heavy pod set.",
      npk: "Thrives with minimal nitrogen supplementation, requiring moderate phosphorus for vigorous root and nodule development.",
      climate: "Cool night temperatures and sunny days during vegetative and pod-filling stages maximize grain weight.",
      ph: "Neutral to slightly alkaline soil facilitates optimal root nodulation and calcium/magnesium uptake."
    },
    coconut: {
      lead: "Coconut is your best choice because your field provides coastal warmth, sustained high relative humidity, and steady moisture reserves that power continuous palm frond growth and nut production.",
      moisture: "High humidity and continuous moisture provide steady sap flow and year-round flower spathe emergence.",
      npk: "Potassium and chloride tolerance allow high yield efficiency and sturdy trunk vascular development.",
      climate: "Warm maritime temperatures without freezing risk maintain continuous crown photosynthesis.",
      ph: "Wide pH tolerance allows robust nutrient cycling in well-drained loamy to sandy field soils."
    },
    coffee: {
      lead: "Coffee is your best choice because your field features mild temperatures, gentle moisture distribution, and acidic soil, creating the ideal microclimate for slow, aromatic bean development.",
      moisture: "Consistent moderate rainfall with balanced humidity supports healthy leaf flush and cherry swelling.",
      npk: "Balanced potassium and nitrogen feed heavy branch bearing while preventing premature leaf drop.",
      climate: "Mild subtropical temperatures protect delicate blossom clusters from heat scorch.",
      ph: "Naturally prefers acidic soil where iron, manganese, and phosphorus remain easily accessible to deep roots."
    },
    cotton: {
      lead: "Cotton is your best choice because your land exhibits a warm sunny climate, moderate seasonal rain, and fertile soil that allow long vegetative growth followed by dry boll maturation.",
      moisture: "Moderate rainfall during early squaring followed by sun prevents boll rotting and leaf shedding.",
      npk: "Balanced N-P-K reserves sustain continuous sympodial branching and heavy seed-cotton boll filling.",
      climate: "High thermal units ensure vigorous seedling emergence and rapid boll opening.",
      ph: "Deep, well-aerated neutral soil allows taproots to explore deep moisture reserves."
    },
    grapes: {
      lead: "Grapes are your best choice because your soil possesses high potassium availability and dry ripening atmospheric conditions, which stimulate sugar accumulation and protect vines from mildew.",
      moisture: "Moderate controlled water input prevents berry splitting while dry air during ripening concentrates Brix sugars.",
      npk: "High potassium directly controls stomatal aperture, vine winter-hardiness, and grape cluster sweetness.",
      climate: "Warm sunny days and moderate evenings promote clean cluster maturation and vine wood lignification.",
      ph: "Neutral to calcareous soil allows deep root infiltration and prevents micronutrient deficiencies."
    },
    jute: {
      lead: "Jute is your best choice because your field offers high atmospheric humidity, heavy seasonal rainfall, and tropical warmth, accelerating the elongation of soft, lustrous bast fibers.",
      moisture: "Loves abundant rainfall and humid air, which drive fast vegetative stem growth and thick fiber bark.",
      npk: "Responds strongly to nitrogen and potassium, producing tall, unbranched stalks with top-grade tensile fiber.",
      climate: "Tropical temperatures between 24°C and 35°C provide optimal conditions for fast 120-day stem harvests.",
      ph: "Slightly acidic to neutral loamy soil supports quick root anchorage and steady moisture holding."
    },
    kidneybeans: {
      lead: "Kidney Beans are your best choice because your field offers cool nighttime temperatures, light well-aerated soil, and gentle moisture, fostering high pod setting without waterlogging.",
      moisture: "Requires steady but light irrigation; sensitive to wet feet, making well-drained soil ideal.",
      npk: "Moderate fertility with available phosphorus powers early root branching and high pod density.",
      climate: "Cool temperate nights prevent blossom drop and allow uniform seed sizing inside pods.",
      ph: "Neutral pH optimizes rhizobium nodule effectiveness and prevents manganese toxicity."
    },
    lentil: {
      lead: "Lentil is your best choice because it thrives under cool season temperatures and modest water availability, converting limited soil moisture into high-protein pulse grains with minimal inputs.",
      moisture: "Very drought-hardy once established; excessive moisture damages lentils, so your field conditions protect against blight.",
      npk: "Fixes its own nitrogen while drawing on moderate phosphorus reserves for root anchoring.",
      climate: "Cool vegetative phase followed by warm, dry maturity promotes even pod ripening.",
      ph: "Tolerates slightly alkaline to neutral soils, ensuring good symbiotic bacterial vigor."
    },
    maize: {
      lead: "Maize is your best choice because your soil provides balanced nitrogen and phosphorus alongside warm sunny days and moderate rainfall, powering fast vegetative growth and well-filled cobs.",
      moisture: "Adequate rainfall during tasseling and silking ensures full kernel pollination and heavy ear weight.",
      npk: "Heavy nitrogen feeder with high phosphorus demands for strong brace roots and kernel starch filling.",
      climate: "Warm temperatures drive rapid C4 photosynthetic efficiency and robust stalk thickness.",
      ph: "Neutral, organic-rich soil maintains high cation exchange capacity for steady nutrient feeding."
    },
    mango: {
      lead: "Mango is your best choice because your field combines warm tropical weather, well-drained soil, and seasonal moisture levels that support vigorous vegetative flushes followed by dry flower induction.",
      moisture: "Moderate rainfall during fruit enlargement paired with dry pre-bloom spell triggers abundant panicles.",
      npk: "Deep taproots extract subsoil potassium and micronutrients, ensuring sweet, aromatic pulp with firm skin.",
      climate: "High heat and frost-free sunshine maximize photosynthetic canopy and pest-free fruit ripening.",
      ph: "Tolerates a wide range from slightly acidic to neutral soils with deep drainage."
    },
    mothbeans: {
      lead: "Moth Beans are your best choice because of their unmatched drought resilience. Your field's moisture and temperature parameters allow moth beans to thrive where other crops would suffer moisture stress.",
      moisture: "Exceptional survival in low rainfall conditions; dense creeping foliage traps soil moisture and prevents erosion.",
      npk: "Low nutrient requirement; enriches depleted soils by biological nitrogen fixation.",
      climate: "Hot, arid sunshine accelerates maturation and yields nutritious grain and livestock forage.",
      ph: "Adaptable across slightly acidic to alkaline sandy loam fields."
    },
    mungbean: {
      lead: "Mung Bean is your best choice because your field offers warm summer temperatures and low-to-moderate rain, allowing this fast-maturing pulse to complete its cycle in 60-70 days with minimal irrigation.",
      moisture: "Thrives in moderate showers; dry harvesting weather protects delicate pods from shattering.",
      npk: "Enhances soil fertility through nitrogen fixation while drawing lightly on available phosphorus.",
      climate: "Warm temperatures stimulate uniform flowering and synchronized pod maturity.",
      ph: "Neutral, well-aerated soil prevents waterlogging and fosters active root nodules."
    },
    muskmelon: {
      lead: "Muskmelon is your best choice because your field provides hot sunny conditions, low atmospheric humidity, and warm soil, which are critical for high sugar sweetness, firm netting, and rot-free melons.",
      moisture: "Controlled water during vine growth followed by drier ripening conditions prevents split fruit and watery flavor.",
      npk: "Potassium and phosphorus availability drives heavy floral set and builds dense, fragrant orange flesh.",
      climate: "High sunshine hours and warm soil temperatures maximize sugar translocation into fruit.",
      ph: "Prefers neutral to slightly alkaline sandy loam for unrestricted lateral root run."
    },
    orange: {
      lead: "Orange is your best choice because your land exhibits mild subtropical weather, good soil drainage, and moderate nutrient feeding, ensuring sweet juice development and healthy citrus tree canopy.",
      moisture: "Steady soil moisture with distinct seasonal cues promotes uniform blooming and juicy fruit sizing.",
      npk: "Balanced nitrogen and potassium feeding maintains thick, dark green leaves and disease-resistant rinds.",
      climate: "Mild daytime temperatures and cool nights stimulate natural citrus peel degreening and sugar-acid balance.",
      ph: "Slightly acidic to neutral soil prevents micronutrient chlorosis in zinc and iron."
    },
    papaya: {
      lead: "Papaya is your best choice because your area offers warm frost-free climate, high humidity, and well-draining soil, supporting rapid trunk growth, continuous flowering, and heavy fruit clusters.",
      moisture: "Requires generous moisture but zero water stagnation; warm humid air accelerates fruit swelling.",
      npk: "Heavy feeder needing steady nitrogen and potassium to sustain simultaneous fruiting and top flowering.",
      climate: "Thrives in year-round tropical heat, ensuring uninterrupted weekly harvest cycles.",
      ph: "Well-aerated soil with neutral pH prevents Phytophthora root rot."
    },
    pigeonpeas: {
      lead: "Pigeon Peas are your best choice because their deep taproots thrive in semi-arid soils with moderate rainfall, providing drought tolerance, subsoil nutrient uptake, and superior nitrogen enrichment.",
      moisture: "Handles dry seasons with ease; deep roots tap subsoil moisture long after topsoil dries out.",
      npk: "Outstanding biological nitrogen fixer that leaves fields richer in organic nitrogen for future rotations.",
      climate: "Warm tropical days support long-duration vegetative branching and extensive podding.",
      ph: "Tolerates a wide pH span in deep alluvial, loamy, and medium black soils."
    },
    pomegranate: {
      lead: "Pomegranate is your best choice because your soil and warm dry climate provide the ideal semi-arid conditions needed for bright rind coloration, high aril sugar content, and minimal cracking.",
      moisture: "Drought-hardy shrub requiring moderate, regulated irrigation to maintain fruit skin elasticity.",
      npk: "Responds efficiently to potassium and zinc, producing deep red arils and rich antioxidant juice.",
      climate: "Hot dry summers ensure clean, disease-free fruit finish without fungal anthracnose.",
      ph: "Tolerates slightly alkaline, calcareous, and rocky soil profiles with ease."
    },
    rice: {
      lead: "Rice is your best choice because your field features heavy rainfall and elevated humidity with favorable water-holding capacity, creating the moist soil conditions essential for tillering and full panicle development.",
      moisture: "High rainfall and elevated relative humidity satisfy the heavy transpirational needs of semi-aquatic paddy growth.",
      npk: "Responds actively to high nitrogen for profuse tillering and balanced phosphorus for deep root anchorage.",
      climate: "Warm tropical temperatures sustain active photosynthesis during vegetative and grain-filling stages.",
      ph: "Slightly acidic to neutral soil prevents nutrient immobilization in saturated paddy beds."
    },
    watermelon: {
      lead: "Watermelon is your best choice because your field provides warm sun, sandy/loamy soil, and steady controlled moisture, allowing vines to expand rapidly and produce large, sweet, hydrated melons.",
      moisture: "Requires steady moisture during early vine run, transitioning to dry sunshine for maximum sugar concentration.",
      npk: "Potassium reserves support fruit expansion, firm rind integrity, and deep red carotenoid pigmentation.",
      climate: "Warm soil and hot sunshine drive rapid fruit swelling and high soluble solids content.",
      ph: "Mildly acidic to neutral sandy loam allows rapid root spreading and zero drainage stagnation."
    }
  };

  function renderBestCropReason(data) {
    const top = data.recommendations[0];
    const cropKey = (top.crop || "").toLowerCase().trim();
    const displayName = (top.crop || "").charAt(0).toUpperCase() + (top.crop || "").slice(1);
    const reasonInfo = CROP_REASONS[cropKey] || {
      lead: displayName + " is your best crop choice because your field readings provide the optimal moisture, climate, and soil nutrient profile needed for high crop yield.",
      moisture: "Your field's rainfall and humidity match this crop's transpiration and hydration needs.",
      npk: "The available Nitrogen, Phosphorus, and Potassium balance satisfies critical vegetative and root growth stages.",
      climate: "Temperature levels are well within the physiological comfort zone for steady growth.",
      ph: "Soil pH ensures efficient root nutrient uptake without chemical lockup."
    };

    const readings = data.readings || {};
    const c = data.consensus || { text: "High model agreement" };

    const rainVal = readings.rainfall !== undefined ? readings.rainfall + " mm" : "recorded level";
    const humVal = readings.humidity !== undefined ? readings.humidity + "%" : "recorded level";
    const tempVal = readings.temperature !== undefined ? readings.temperature + "°C" : "recorded level";
    const phVal = readings.ph !== undefined ? readings.ph : "recorded level";
    const npkVal = "N: " + (readings.N || 0) + ", P: " + (readings.P || 0) + ", K: " + (readings.K || 0) + " kg/ha";

    const consensusText = (c.text || "").replace(/\.+$/, "");

    return '' +
      '<div class="section-title reveal" style="--d:650ms">' +
      '  <div class="title-left">' +
      '    <span class="title-bullet-icon green">' +
      '      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.3"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"></path></svg>' +
      '    </span>' +
      '    <span>Why ' + esc(displayName) + ' is the Best Crop</span>' +
      '  </div>' +
      '  <small>Field suitability & agronomic explanation</small>' +
      '</div>' +
      '<div class="best-crop-card reveal" style="--d:700ms">' +
      '  <div class="best-crop-header">' +
      '    <div class="best-crop-badge">' +
      '      <span class="best-crop-badge-star">★</span>' +
      '      <span>Recommended Choice (Rank 1)</span>' +
      '    </div>' +
      '    <h3 class="best-crop-title">' + esc(displayName) + ' is your best crop choice</h3>' +
      '    <p class="best-crop-lead">' + esc(reasonInfo.lead) + '</p>' +
      '  </div>' +
      '  <div class="best-factors-grid">' +
      '    <div class="best-factor-box">' +
      '      <div class="factor-header">' +
      '        <span class="factor-icon-pill rain-pill">Moisture & Water</span>' +
      '        <span class="factor-val">' + esc(rainVal) + ' / ' + esc(humVal) + '</span>' +
      '      </div>' +
      '      <p class="factor-desc">' + esc(reasonInfo.moisture) + '</p>' +
      '    </div>' +
      '    <div class="best-factor-box">' +
      '      <div class="factor-header">' +
      '        <span class="factor-icon-pill npk-pill">Soil Nutrients (NPK)</span>' +
      '        <span class="factor-val">' + esc(npkVal) + '</span>' +
      '      </div>' +
      '      <p class="factor-desc">' + esc(reasonInfo.npk) + '</p>' +
      '    </div>' +
      '    <div class="best-factor-box">' +
      '      <div class="factor-header">' +
      '        <span class="factor-icon-pill temp-pill">Temperature Climate</span>' +
      '        <span class="factor-val">' + esc(tempVal) + '</span>' +
      '      </div>' +
      '      <p class="factor-desc">' + esc(reasonInfo.climate) + '</p>' +
      '    </div>' +
      '    <div class="best-factor-box">' +
      '      <div class="factor-header">' +
      '        <span class="factor-icon-pill ph-pill">Soil Reaction (pH)</span>' +
      '        <span class="factor-val">pH ' + esc(phVal) + '</span>' +
      '      </div>' +
      '      <p class="factor-desc">' + esc(reasonInfo.ph) + '</p>' +
      '    </div>' +
      '  </div>' +
      '  <div class="best-verdict-box">' +
      '    <span class="verdict-chip">AI Prediction</span>' +
      '    <p><b>Model Consensus:</b> ' + esc(consensusText) + '. ' + esc(displayName) + ' achieved the highest accuracy-weighted score of <b>' + top.score.toFixed(1) + '%</b> among all 22 evaluated crops.</p>' +
      '  </div>' +
      '</div>';
  }

  /* ------------------------------- Modern Visible Crop Score Bar Chart */

  function renderCropScoreChart(chartData) {
    if (!chartData || !chartData.length) return "";

    let rowsHtml = "";
    chartData.forEach(function (c, idx) {
      const rankNum = idx + 1;
      const rankClass = rankNum === 1 ? "top-1" : (rankNum === 2 ? "top-2" : (rankNum === 3 ? "top-3" : "top-other"));
      const cropName = esc(c.crop.charAt(0).toUpperCase() + c.crop.slice(1));
      const pct = Math.max(0, Math.min(100, c.probability));

      rowsHtml += '' +
        '<div class="score-bar-row ' + rankClass + '">' +
        '  <div class="crop-info-col">' +
        '    <span class="crop-rank-pill pill-' + rankClass + '">' + rankNum + '</span>' +
        '    <span class="crop-name-label">' + cropName + '</span>' +
        '  </div>' +
        '  <div class="score-track-col">' +
        '    <div class="score-track-container">' +
        '      <div class="score-bar-fill fill-' + rankClass + '" data-w="' + pct.toFixed(1) + '" style="width: 0%" title="' + cropName + ': ' + pct.toFixed(2) + '%">' +
        '        <span class="score-bar-glow"></span>' +
        '      </div>' +
        '    </div>' +
        '  </div>' +
        '  <div class="crop-score-col val-' + rankClass + '">' +
        '    <b data-count="' + pct.toFixed(1) + '">0.0%</b>' +
        '  </div>' +
        '</div>';
    });

    return '' +
      '<div class="section-title reveal" style="--d:720ms">' +
      '  <div class="title-left">' +
      '    <span class="title-bullet-icon orange">' +
      '      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.3"><rect x="3" y="12" width="4" height="9"></rect><rect x="10" y="6" width="4" height="15"></rect><rect x="17" y="2" width="4" height="19"></rect></svg>' +
      '    </span>' +
      '    <span>How All Crops Scored</span>' +
      '  </div>' +
      '  <small>Weighted confidence distribution across evaluated crops with visible 0%–100% scale</small>' +
      '</div>' +
      '<div class="score-chart-card reveal" style="--d:760ms">' +
      '  <div class="score-chart-head">' +
      '    <div class="score-chart-title-wrap">' +
      '      <h4>Comparative Prediction Confidence</h4>' +
      '      <p>Clear percentage scale comparing model agreement scores for top contender crops</p>' +
      '    </div>' +
      '    <div class="score-chart-legend">' +
      '      <span class="score-chip chip-rank-1"><span class="chip-dot dot-1"></span> Rank 1 (Top Match)</span>' +
      '      <span class="score-chip chip-rank-2"><span class="chip-dot dot-2"></span> Rank 2</span>' +
      '      <span class="score-chip chip-rank-3"><span class="chip-dot dot-3"></span> Rank 3</span>' +
      '      <span class="score-chip chip-rank-other"><span class="chip-dot dot-other"></span> Runner-ups</span>' +
      '    </div>' +
      '  </div>' +
      '  <!-- Visible Scale Ruler Axis -->' +
      '  <div class="score-scale-ruler">' +
      '    <div class="ruler-crop-spacer"></div>' +
      '    <div class="ruler-ticks-track">' +
      '      <div class="ruler-tick tick-first" style="left: 0%"><span class="ruler-line"></span><span class="ruler-text">0%</span></div>' +
      '      <div class="ruler-tick" style="left: 20%"><span class="ruler-line"></span><span class="ruler-text">20%</span></div>' +
      '      <div class="ruler-tick" style="left: 40%"><span class="ruler-line"></span><span class="ruler-text">40%</span></div>' +
      '      <div class="ruler-tick" style="left: 60%"><span class="ruler-line"></span><span class="ruler-text">60%</span></div>' +
      '      <div class="ruler-tick" style="left: 80%"><span class="ruler-line"></span><span class="ruler-text">80%</span></div>' +
      '      <div class="ruler-tick tick-last" style="left: 100%"><span class="ruler-line"></span><span class="ruler-text">100%</span></div>' +
      '    </div>' +
      '    <div class="ruler-val-spacer"></div>' +
      '  </div>' +
      '  <!-- Chart Rows with Integrated Vertical Scale Grid Lines -->' +
      '  <div class="score-chart-body">' +
      '    <div class="score-chart-gridlines" aria-hidden="true">' +
      '      <div class="chart-grid-col" style="left: 0%"></div>' +
      '      <div class="chart-grid-col" style="left: 20%"></div>' +
      '      <div class="chart-grid-col" style="left: 40%"></div>' +
      '      <div class="chart-grid-col" style="left: 60%"></div>' +
      '      <div class="chart-grid-col" style="left: 80%"></div>' +
      '      <div class="chart-grid-col" style="left: 100%"></div>' +
      '    </div>' +
      '    <div class="score-rows-list">' +
      rowsHtml +
      '    </div>' +
      '  </div>' +
      '</div>';
  }

  function renderPrediction(data) {
    const top = data.recommendations[0];
    const c = data.consensus;

    let html = '<div class="prediction-container">';

    /* --- Alert Banner (Confidence Tiers) --- */
    html += renderAlertBox(data.assessment);

    /* --- consensus pill bar --- */
    html += '' +
      '<div class="consensus-bar reveal" style="--d:70ms">' +
      '  <span class="consensus-icon-circle" aria-hidden="true">' +
      '    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.3"><path d="M12 21v-9"></path><path d="M12 12C12 8 9 5 5 5c0 4 3 7 7 7z"></path><path d="M12 14c0-3.3 2.7-6 6-6 0 3.3-2.7 6-6 6z"></path></svg>' +
      '  </span>' +
      '  <span class="consensus-text">' + esc(c.text) + '</span>' +
      '</div>';

    /* --- top-3 ranking --- */
    html += '<div class="section-title reveal" style="--d:120ms">' +
            '  <div class="title-left">' +
            '    <span class="title-bullet-icon green">' +
            '      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.3"><path d="M12 21v-9"></path><path d="M12 12C12 8 9 5 5 5c0 4 3 7 7 7z"></path></svg>' +
            '    </span>' +
            '    <span>Plant this first, then this, then this</span>' +
            '  </div>' +
            '  <small>(sorted by confidence score)</small>' +
            '</div>';

    const rankPills = {
      1: { text: "Best Match (Highest Score)", cls: "tag-best" },
      2: { text: "Good Match (Strong Score)", cls: "tag-strong" },
      3: { text: "Good Match (Solid Score)", cls: "tag-solid" }
    };

    html += '<div class="ranks">';
    data.recommendations.forEach(function (r, i) {
      const pInfo = rankPills[r.rank] || { text: "Viable Option", cls: "tag-solid" };
      html += '' +
        '<article class="rank r' + r.rank + ' reveal" data-score="' + r.score + '" style="--d:' + (160 + i * 90) + 'ms">' +
        '  <div class="rank-fill" aria-hidden="true"></div>' +
        '  <div class="rank-badge-box rank-badge-' + r.rank + '">' + r.rank + '</div>' +
        '  <div class="rank-body">' +
        '    <div class="rank-title-row">' +
        '      <h3 class="crop-name-' + r.rank + '">' + esc(r.crop) + '</h3>' +
        '      <span class="rank-badge-pill ' + pInfo.cls + '">' + esc(pInfo.text) + '</span>' +
        '    </div>' +
        '    <p class="rank-note">' + esc(r.note) + '</p>' +
        '  </div>' +
        '  <div class="rank-score score-' + r.rank + '">' +
        '    <b data-count="' + r.score + '">0.0%</b>' +
        '    <span>' + esc(r.vote_text) + '</span>' +
        '  </div>' +
        '</article>';
    });
    html += "</div>";

    /* --- per-model answers (collapsible dropdown) --- */
    html += '<div class="model-accordion-wrap reveal" style="--d:400ms">' +
            '  <button type="button" class="model-accordion-btn" id="modelAccordionBtn" onclick="toggleModelPredictions()" aria-expanded="false">' +
            '    <div class="model-accordion-btn-left">' +
            '      <span class="model-accordion-title">Which each model said on its own</span>' +
            '      <small class="model-accordion-subtitle">Test accuracy shown beside the name</small>' +
            '    </div>' +
            '    <div class="model-accordion-btn-right">' +
            '      <span class="model-accordion-tag" id="modelToggleTag">View Details</span>' +
            '      <svg class="model-accordion-chevron" id="modelAccordionChevron" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">' +
            '        <polyline points="6 9 12 15 18 9"/>' +
            '      </svg>' +
            '    </div>' +
            '  </button>' +
            '  <div class="model-accordion-content" id="modelAccordionContent">';

    const modelThemes = {
      xgb: { badge: "badge-blue", color: "blue-pred", fillClass: "fill-blue", note: "Gradient-boosted trees. Highest test set accuracy." },
      rf:  { badge: "badge-purple", color: "purple-pred", fillClass: "fill-purple", note: "300 trees voting together. High generalization stability." },
      svm: { badge: "badge-green", color: "green-pred", fillClass: "fill-green", note: "Radial Basis Function. Clean geometric boundaries." }
    };

    html += '<div class="model-cards-grid">';
    data.model_predictions.forEach(function (m, i) {
      const theme = modelThemes[m.key] || { badge: "badge-blue", color: "blue-pred", fillClass: "fill-blue", note: m.note };
      const matches = m.prediction === top.crop;
      html += '' +
        '<article class="model-card ' + (matches ? "match-top" : "") + '">' +
        '  <div class="model-card-top">' +
        '    <span class="model-card-name">' + esc(m.name) + '</span>' +
        '  </div>' +
        '  <div class="model-pred-val ' + theme.color + '">' + esc(m.prediction) + '</div>' +
        '  <p class="model-desc">' + esc(theme.note) + '</p>' +
        '  <div class="conf-track"><div class="conf-fill ' + theme.fillClass + '" data-w="' + m.confidence.toFixed(1) + '"></div></div>' +
        '  <div class="model-card-conf">' +
        '    <span>Confidence: <b>' + m.confidence.toFixed(2) + '%</b></span>' +
        (matches ? '    <span class="model-match-tag">✓ Agrees with Rank 1</span>' : '') +
        '  </div>' +
        '</article>';
    });
    html += '</div>'; // close .model-cards-grid
    html += '</div>'; // close .model-accordion-content
    html += '</div>'; // close .model-accordion-wrap

    /* --- WHY THIS CROP IS BEST (EXPLANATION WORDS) --- */
    html += renderBestCropReason(data);

    /* --- WHICH NUMERICAL FEATURE IS IMPORTANT (AT THE BOTTOM) --- */
    html += renderFeatureImportance(data.feature_importances);

    html += '</div>'; // close .prediction-container

    return html;
  }

  /* ------------------------------- Toggle Per-Model Predictions Dropdown */
  window.toggleModelPredictions = function () {
    const content = document.getElementById("modelAccordionContent");
    const chevron = document.getElementById("modelAccordionChevron");
    const tag     = document.getElementById("modelToggleTag");
    const btn     = document.getElementById("modelAccordionBtn");
    if (!content) return;
    const isOpen = content.classList.toggle("open");
    if (chevron) chevron.classList.toggle("open", isOpen);
    if (btn) btn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    if (tag) tag.textContent = isOpen ? "Hide Details" : "View Details";

    if (isOpen) {
      const fills = content.querySelectorAll(".conf-fill");
      fills.forEach(function (f) {
        const target = parseFloat(f.getAttribute("data-w")) || 0;
        f.style.width = target + "%";
      });
    }
  };

  /* ------------------------------------------------------- Animation pass */

  function animatePrediction() {
    const delay = reduceMotion ? 0 : 450;

    setTimeout(function () {
      // Horizontal confidence tracks and score bars
      document.querySelectorAll(".conf-fill, .bar-fill, .score-bar-fill").forEach(function (el) {
        el.style.width = el.dataset.w + "%";
      });

      // Rank cards background fill sweep by score
      document.querySelectorAll(".rank").forEach(function (card) {
        const fill = card.querySelector(".rank-fill");
        if (fill) fill.style.width = (parseFloat(card.dataset.score) || 0) + "%";
      });

      // Feature importance vertical bars rise
      document.querySelectorAll(".fi-bar").forEach(function (bar) {
        bar.style.height = bar.dataset.h + "%";
      });

      // Percentage numbers count up
      document.querySelectorAll("[data-count]").forEach(function (el) {
        countUp(el, parseFloat(el.dataset.count) || 0);
      });
    }, delay);
  }

  function countUp(el, target) {
    if (reduceMotion) { el.textContent = target.toFixed(1) + "%"; return; }
    const dur = 850;
    const start = performance.now();
    function tick(now) {
      const t = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = (target * eased).toFixed(1) + "%";
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  /* ---------------------------------------------------- Initial Auto-Load */

  const initialCrop = (cropSelect && cropSelect.value) ? cropSelect.value : "blackgram";
  loadCropGuide(initialCrop, true);

})();

