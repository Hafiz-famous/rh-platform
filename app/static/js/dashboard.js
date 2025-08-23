// app/static/js/dashboard.js
(() => {
  const $ = (sel) => document.querySelector(sel);

  // Horodatage
  try {
    const now = new Date();
    const el = $("#nowLabel");
    if (el) el.textContent = now.toLocaleString();
  } catch {}

  // Auto-refresh si un autre onglet pointe
  window.addEventListener("storage", (ev) => {
    if (ev.key === "rh_refresh") location.reload();
  });

  // Helpers charts
  const mkChart = (canvas, cfg) => new Chart(canvas, cfg);

  // -------- Utils de normalisation ----------

  // Transforme divers formats en [{label, value}, ...]
  function normalizePairs(d) {
    if (!d) return [];
    // déjà un tableau d'objets ?
    if (Array.isArray(d)) {
      return d.map(x => ({
        label: x.label ?? x.department ?? x.dept ?? x.name ?? "",
        value: Number(x.value ?? x.total ?? x.amount ?? x.cost ?? 0)
      }));
    }
    // propriétés classiques contenant un tableau
    if (Array.isArray(d.items))   return normalizePairs(d.items);
    if (Array.isArray(d.data))    return normalizePairs(d.data);
    if (Array.isArray(d.rows))    return normalizePairs(d.rows);
    if (Array.isArray(d.results)) return normalizePairs(d.results);

    // {labels: [...], values: [...]}
    if (Array.isArray(d.labels) && Array.isArray(d.values)) {
      return d.labels.map((lbl, i) => ({ label: lbl, value: Number(d.values[i] ?? 0) }));
    }

    // Objet clé->valeur { "Informatique": 1234, "RH": 987 }
    if (typeof d === "object") {
      return Object.entries(d).map(([k, v]) => ({ label: k, value: Number(v) || 0 }));
    }

    return [];
  }

  function arr(arrLike) {
    return Array.isArray(arrLike) ? arrLike : [];
  }

  // -------- 1) KPIs & compteurs ----------
  fetch("/api/dashboard/stats")
    .then(r => r.json())
    .then(s => {
      $("#kpi-present").textContent        = s.present_today ?? s.present ?? "0";
      $("#kpi-hours").textContent          = Number(s.hours_today ?? 0).toFixed(2);
      $("#kpi-leaves-pending").textContent = s.leave_pending ?? s.leaves_pending ?? "0";
      $("#kpi-ot-pending").textContent     = s.overtime_pending ?? s.ot_pending ?? "0";

      if (s.present_vs_yesterday != null) {
        const v = Number(s.present_vs_yesterday);
        $("#kpi-present-sub").textContent = `${v >= 0 ? "+" : ""}${v} vs hier`;
      } else {
        $("#kpi-present-sub").textContent = "—";
      }
      if (s.hours_vs_yesterday != null) {
        const v = Number(s.hours_vs_yesterday || 0);
        $("#kpi-hours-sub").textContent = `${v >= 0 ? "+" : ""}${v.toFixed(2)} h vs hier`;
      } else {
        $("#kpi-hours-sub").textContent = "—";
      }
    })
    .catch(() => {
      $("#kpi-present").textContent = "0";
      $("#kpi-hours").textContent   = "0.00";
      $("#kpi-leaves-pending").textContent = "0";
      $("#kpi-ot-pending").textContent     = "0";
      $("#kpi-present-sub").textContent = "—";
      $("#kpi-hours-sub").textContent   = "—";
    });

  // -------- 2) Présence 14 jours ----------
  fetch("/api/charts/presence?days=14")
    .then(r => r.json())
    .then(d => {
      const labels = arr(d.labels || d.dates);
      const values = arr(d.values || d.counts);
      mkChart($("#presenceChart"), {
        type: "line",
        data: { labels, datasets: [{ label: "Présents", data: values, tension: .35, fill: false }] },
        options: {
          responsive: true, maintainAspectRatio: false,
          scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
          plugins: { legend: { display: false }, tooltip: { mode: "index", intersect: false } }
        }
      });
      if (labels.length) {
        $("#presenceRangeLabel").textContent = `${labels[0]} → ${labels[labels.length - 1]}`;
      }
    })
    .catch(err => console.error("presence chart error:", err));

  // -------- 3) Heures sup 14 jours ----------
  fetch("/api/charts/overtime?days=14")
    .then(r => r.json())
    .then(d => {
      const labels = arr(d.labels || d.dates);
      const values = arr(d.values || d.hours);
      mkChart($("#overtimeChart"), {
        type: "bar",
        data: { labels, datasets: [{ label: "Heures sup", data: values }] },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true } }
        }
      });
    })
    .catch(err => console.error("overtime chart error:", err));

  // -------- 4) Coûts par département (mois en cours) ----------
  fetch("/api/charts/department-costs")
    .then(r => r.json())
    .then(d => {
      const pairs  = normalizePairs(d);
      const labels = pairs.map(x => x.label);
      const values = pairs.map(x => x.value);

      mkChart($("#deptChart"), {
        type: "bar",
        data: { labels, datasets: [{ label: "Coût", data: values }] },
        options: {
          indexAxis: "x",
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true } }
        }
      });
    })
    .catch(err => console.error("dept costs error:", err));
})();
// ------- Chart.js polish (version SAFE) -------
if (window.Chart) {
  try {
    const D = Chart.defaults;

    // Animations globales (merge sans casser l'existant)
    D.animation = Object.assign({}, D.animation, {
      duration: 900,
      easing: "easeOutCubic"
    });

    // Cette clé peut ne pas exister selon la version -> on garde
    if (D.transitions && D.transitions.active) {
      D.transitions.active.animation = Object.assign(
        {},
        D.transitions.active.animation || {},
        { duration: 200 }
      );
    }

    // Style des éléments
    if (D.elements && D.elements.line) {
      D.elements.line.tension = 0.38;
    }
    if (D.elements && D.elements.point) {
      D.elements.point.radius = 3;
      D.elements.point.hoverRadius = 6;
    }

    // Tooltips/legend safe
    if (D.plugins) {
      D.plugins.tooltip = Object.assign({}, D.plugins.tooltip, {
        mode: "index",
        intersect: false,
        displayColors: false
      });
      if (D.plugins.legend && D.plugins.legend.labels) {
        D.plugins.legend.labels.usePointStyle = true;
      }
    }

    // Police = celle du site
    D.font = Object.assign({}, D.font, {
      family: getComputedStyle(document.body).fontFamily
    });

    // Plugin "lueur" autour du point actif (protégé)
    Chart.register({
      id: "glow-point",
      afterDatasetsDraw(chart) {
        try {
          const { ctx, tooltip } = chart;
          const act = tooltip && tooltip.getActiveElements
            ? tooltip.getActiveElements()
            : [];
          if (!act || !act.length) return;
          const e = act[0];
          const meta = chart.getDatasetMeta(e.datasetIndex);
          const pt = meta && meta.data ? meta.data[e.index] : null;
          if (!pt) return;
          ctx.save();
          ctx.globalAlpha = 0.22;
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 14, 0, Math.PI * 2);
          ctx.fillStyle = "#000";
          ctx.fill();
          ctx.restore();
        } catch (_) { /* no-op */ }
      }
    });
  } catch (err) {
    console.warn("Chart polish désactivé (SAFE):", err);
  }
}
