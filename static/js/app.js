/* ===========================================================================
   Crop Recommendation System — front end
   Keeps sliders and number boxes in sync, calls /predict, and reveals the
   results in one orchestrated sequence.
   =========================================================================== */

(function () {
  "use strict";

  const FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"];
  const DEFAULTS = {};

  const form    = document.getElementById("form");
  const goBtn   = document.getElementById("go");
  const goText  = document.getElementById("go-text");
  const errBox  = document.getElementById("error");
  const results = document.getElementById("results");

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


  /* ------------------------------------------------ crop selector */

const cropSelect = document.getElementById("crop-select");

if (cropSelect) {
  cropSelect.addEventListener("change", function () {

    const crop = cropSelect.value;

    if (!crop) return;

    fetch("/crop-profile/" + encodeURIComponent(crop))
      .then(function (response) {
        return response.json();
      })
      .then(function (data) {

        if (!data.ok) {
          showError(data.error || "Could not load crop values.");
          return;
        }

        FEATURES.forEach(function (f) {

          const value = data.values[f];

          const rng = document.getElementById("rng-" + f);
          const num = document.getElementById("num-" + f);

          if (!rng || !num || value === undefined) return;

          num.value = value;

          rng.value = clamp(rng, parseFloat(value));

          paintTrack(rng);
        });

        hideError();
      })
      .catch(function () {
        showError("Could not load the selected crop profile.");
      });
  });
}

  /* ---------------------------------------------------------------- presets */

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
    results.innerHTML = emptyState();
  });

  /* ------------------------------------------------------------------ errors */

  function showError(msg) {
    errBox.textContent = msg;
    errBox.classList.add("show");
  }

  function hideError() {
    errBox.classList.remove("show");
    errBox.textContent = "";
  }

  /* ------------------------------------------------------------------ submit */

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
        render(res.body);
      })
      .catch(function () {
        showError("Could not reach the server. Is app.py still running?");
      })
      .finally(function () { setBusy(false); });
  });

  function setBusy(on) {
    goBtn.disabled = on;
    goBtn.classList.toggle("is-busy", on);
    goText.textContent = on ? "Scoring your field" : "Recommend a crop";
  }

  /* ------------------------------------------------------------------ render */

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function emptyState() {
    return '' +
      '<div class="empty">' +
      '  <svg class="sprout-mark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '    <path d="M12 21v-9"/><path d="M12 12C12 8 9 5 5 5c0 4 3 7 7 7z"/><path d="M12 14c0-3.3 2.7-6 6-6 0 3.3-2.7 6-6 6z"/>' +
      '  </svg>' +
      '  <h3>Nothing scored yet</h3>' +
      '  <p>Set your readings on the left and press <strong>Recommend a crop</strong>. You\'ll see each model\'s answer and the top three crops.</p>' +
      '</div>';
  }

  function render(data) {
    const top = data.recommendations[0];
    const c = data.consensus;

    let dots = "";
    for (let i = 0; i < c.total; i++) {
      dots += '<span class="vote-dot' + (i < c.agree ? " on" : "") + '"></span>';
    }

    /* --- consensus strip --- */
    let html = '' +
      '<div class="consensus reveal ' + (c.agree >= c.total - 1 ? "" : "weak") + '" style="--d:0ms">' +
      '  <span class="votes-dots" aria-hidden="true">' + dots + '</span>' +
      '  <span>' + esc(c.text) + '</span>' +
      '</div>';

    /* --- top-3 ranking --- */
    html += '<div class="section-title reveal" style="--d:60ms">' +
            '<span>Plant this first, then this, then this</span>' +
            '<small>combined score from all ' + c.total + ' models</small></div>';

    html += '<div class="ranks">';
    data.recommendations.forEach(function (r, i) {
      html += '' +
        '<article class="rank r' + r.rank + ' reveal" data-score="' + r.score + '" style="--d:' + (110 + i * 90) + 'ms">' +
        '  <div class="rank-fill" aria-hidden="true"></div>' +
        '  <div class="rank-no">' + r.rank + '</div>' +
        '  <div class="rank-body">' +
        '    <h3>' + esc(r.crop) + '</h3>' +
        '    <p>' + esc(r.note) + '</p>' +
        '  </div>' +
        '  <div class="rank-score">' +
        '    <b data-count="' + r.score + '">0.0%</b>' +
        '    <span>' + esc(r.vote_text) + '</span>' +
        '  </div>' +
        '</article>';
    });
    html += "</div>";

    /* --- per-model answers --- */
    html += '<div class="section-title reveal" style="--d:400ms">' +
            '<span>What each model said on its own</span>' +
            '<small>test accuracy shown beside the name</small></div>';

    html += '<div class="model-grid">';
    data.model_predictions.forEach(function (m, i) {
      const matches = m.prediction === top.crop;
      const second = m.top3[1];
      html += '' +
        '<article class="model reveal' + (matches ? " match" : "") + '" style="--d:' + (450 + i * 70) + 'ms">' +
        '  <div class="model-top">' +
        '    <span class="model-name">' + esc(m.name) + '</span>' +
        '    <span class="model-acc">' + m.accuracy.toFixed(2) + '%</span>' +
        '  </div>' +
        '  <div class="model-pred">' + esc(m.prediction) + '</div>' +
        '  <div class="conf-track"><div class="conf-fill" data-w="' + m.confidence + '"></div></div>' +
        '  <div class="model-foot">' +
        '    <span>' + m.confidence.toFixed(1) + '% sure</span>' +
        '    <span>next: ' + esc(second ? second.crop : "—") + '</span>' +
        '  </div>' +
        '  <p class="model-note">' + esc(m.note) + '</p>' +
        '</article>';
    });
    html += "</div>";

    /* --- chart --- */
    html += '<div class="section-title reveal" style="--d:800ms">' +
            '<span>How the crops scored</span>' +
            '<small>top ' + data.chart.length + ' of 22</small></div>';

    const maxVal = Math.max.apply(null, data.chart.map(function (d) { return d.probability; })) || 1;

    html += '<div class="chart-card reveal" style="--d:850ms">';
    data.chart.forEach(function (d, i) {
      const rel = (d.probability / maxVal) * 100;
      html += '' +
        '<div class="bar-row' + (i === 0 ? " top" : "") + '">' +
        '  <div class="bar-label">' + esc(d.crop) + '</div>' +
        '  <div class="bar-track"><div class="bar-fill" data-w="' + rel.toFixed(2) + '"></div></div>' +
        '  <div class="bar-val">' + d.probability.toFixed(2) + '%</div>' +
        '</div>';
    });
    html += '<p class="chart-foot">Bars show the combined score. Each model votes with a weight equal to its test accuracy, so stronger models pull the ranking more.</p>';
    html += "</div>";

    results.innerHTML = html;
    animate();
    if (window.innerWidth <= 940) {
      results.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
    }
  }

  /* ---------------------------------------------------------- animation pass */

  function animate() {
    // Bars grow, cards fill, numbers count up — after the cards have landed.
    const delay = reduceMotion ? 0 : 520;

    setTimeout(function () {
      // confidence bars and chart bars
      document.querySelectorAll(".conf-fill, .bar-fill").forEach(function (el) {
        el.style.width = el.dataset.w + "%";
      });

      // ranking cards paint from the left by their score
      document.querySelectorAll(".rank").forEach(function (card) {
        const fill = card.querySelector(".rank-fill");
        if (fill) fill.style.width = (parseFloat(card.dataset.score) || 0) + "%";
      });

      // percentages tick up to their value
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
})();
