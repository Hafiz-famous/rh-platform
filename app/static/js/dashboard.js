// app/static/js/dashboard.js
(() => {
  "use strict";

  const $  = (sel, r = document) => r.querySelector(sel);
  const $$ = (sel, r = document) => Array.from(r.querySelectorAll(sel));

  // ---------- Horodatage (et mise à jour chaque minute) ----------
  function updateNowLabel() {
    try {
      const el = $("#nowLabel");
      if (el) el.textContent = new Date().toLocaleString();
    } catch {}
  }
  updateNowLabel();
  setInterval(updateNowLabel, 60_000);

  // Reload si un autre onglet demande un refresh complet
  window.addEventListener("storage", (ev) => {
    if (ev.key === "rh_refresh") location.reload();
  });

  // ---------- Helpers ----------
  const mkChart = (canvas, cfg) => {
    if (!canvas || !window.Chart) return null;
    return new Chart(canvas, cfg);
  };

  // GET JSON sans cache (+ cache-buster)
  async function apiGet(url) {
    const u = new URL(url, window.location.origin);
    u.searchParams.set("_", Date.now().toString()); // anti-cache robuste
    const res = await fetch(u.toString(), {
      method: "GET",
      cache: "no-store",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    try { return await res.json(); } catch { return {}; }
  }

  // Normalise divers formats en [{label, value}]
  function normalizePairs(d) {
    if (!d) return [];
    if (Array.isArray(d)) {
      return d.map((x) => ({
        label: x.label ?? x.department ?? x.dept ?? x.name ?? "",
        value: Number(x.value ?? x.total ?? x.amount ?? x.cost ?? 0),
      }));
    }
    if (Array.isArray(d.items))   return normalizePairs(d.items);
    if (Array.isArray(d.data))    return normalizePairs(d.data);
    if (Array.isArray(d.rows))    return normalizePairs(d.rows);
    if (Array.isArray(d.results)) return normalizePairs(d.results);

    if (Array.isArray(d.labels) && Array.isArray(d.values)) {
      return d.labels.map((lbl, i) => ({
        label: lbl,
        value: Number(d.values[i] ?? 0),
      }));
    }

    if (typeof d === "object") {
      return Object.entries(d).map(([k, v]) => ({
        label: k,
        value: Number(v) || 0,
      }));
    }
    return [];
  }

  const arr = (a) => (Array.isArray(a) ? a : []);

  // ---------- 1) KPIs ----------
  async function loadKpis() {
    try {
      const s = await apiGet("/api/dashboard/stats");

      const present = s.present_today ?? s.present ?? 0;
      const hours   = Number(s.hours_today ?? s.hours ?? 0);
      const lpend   = s.leave_pending ?? s.leaves_pending ?? 0;
      const otpend  = s.overtime_pending ?? s.ot_pending ?? 0;

      const k1 = $("#kpi-present");
      const k2 = $("#kpi-hours");
      const k3 = $("#kpi-leaves-pending");
      const k4 = $("#kpi-ot-pending");
      if (k1) k1.textContent = String(present);
      if (k2) k2.textContent = hours.toFixed(2);
      if (k3) k3.textContent = String(lpend);
      if (k4) k4.textContent = String(otpend);

      const sub1 = $("#kpi-present-sub");
      if (sub1) {
        if (s.present_vs_yesterday != null) {
          const v = Number(s.present_vs_yesterday);
          sub1.textContent = `${v >= 0 ? "+" : ""}${v} vs hier`;
        } else sub1.textContent = "—";
      }

      const sub2 = $("#kpi-hours-sub");
      if (sub2) {
        if (s.hours_vs_yesterday != null) {
          const v = Number(s.hours_vs_yesterday);
          sub2.textContent = `${v >= 0 ? "+" : ""}${v.toFixed(2)} h vs hier`;
        } else sub2.textContent = "—";
      }
    } catch (err) {
      console.warn("KPIs error:", err);
      $("#kpi-present")        && ($("#kpi-present").textContent        = "0");
      $("#kpi-hours")          && ($("#kpi-hours").textContent          = "0.00");
      $("#kpi-leaves-pending") && ($("#kpi-leaves-pending").textContent = "0");
      $("#kpi-ot-pending")     && ($("#kpi-ot-pending").textContent     = "0");
      $("#kpi-present-sub")    && ($("#kpi-present-sub").textContent    = "—");
      $("#kpi-hours-sub")      && ($("#kpi-hours-sub").textContent      = "—");
    }
  }

  // ---------- 2) Liste des présents (Admin/Manager) ----------
  async function loadPresentList() {
    const wrapper    = $("#presentList");
    const empty      = $("#presentEmpty");
    const countLabel = $("#presentCountLabel");
    if (!wrapper || !empty || !countLabel) return;

    try {
      const data = await apiGet("/api/present-today");

      // NEW: tolère l'ancien format (tableau) et le nouveau ({count, items})
      const items = Array.isArray(data) ? data : (data.items || []);
      const count = Array.isArray(data) ? data.length : (data.count ?? items.length);

      countLabel.textContent = String(count);
      wrapper.innerHTML = "";
      if (!items.length) {
        empty.classList.remove("d-none");
        return;
      }
      empty.classList.add("d-none");

      for (const it of items) {
        const li = document.createElement("li");
        li.className = "list-group-item d-flex align-items-center justify-content-between";

        const left = document.createElement("div");
        left.innerHTML = `
          <div class="fw-semibold">${it.name ?? ""}</div>
          <div class="text-muted small">${(it.email ?? "")} · ${(it.department ?? "—")}</div>
        `;

        const right = document.createElement("div");
        const t = it.check_in ? new Date(it.check_in) : null;
        right.innerHTML = `
          <span class="badge text-bg-light me-2">
            <i class="bi bi-box-arrow-in-right me-1"></i>${
              t ? t.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"
            }
          </span>
          <span class="badge text-bg-secondary">${it.source || "manual"}</span>
        `;

        li.appendChild(left);
        li.appendChild(right);
        wrapper.appendChild(li);
      }
    } catch (err) {
      console.warn("present-today error:", err);
      wrapper.innerHTML = "";
      empty.classList.remove("d-none");
      countLabel.textContent = "—";
    }
  }

  // ---------- 3) Graphiques ----------
  let charts = { presence: null, overtime: null, dept: null };

  async function buildPresenceChart() {
    const canvas = $("#presenceChart");
    if (!canvas || !window.Chart) return;

    try {
      const d = await apiGet("/api/charts/presence?days=14");
      const labels = arr(d.labels || d.dates);
      const values = arr(d.values || d.counts);

      charts.presence?.destroy?.();
      charts.presence = mkChart(canvas, {
        type: "line",
        data: { labels, datasets: [{ label: "Présents", data: values, tension: 0.35, fill: false }] },
        options: {
          responsive: true, maintainAspectRatio: false,
          scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
          plugins: { legend: { display: false }, tooltip: { mode: "index", intersect: false } },
        },
      });

      const range = $("#presenceRangeLabel");
      if (labels.length && range) {
        range.textContent = `${labels[0]} → ${labels[labels.length - 1]}`;
      }
    } catch (err) {
      console.error("presence chart error:", err);
    }
  }

  async function buildOvertimeChart() {
    const canvas = $("#overtimeChart");
    if (!canvas || !window.Chart) return;

    try {
      const d = await apiGet("/api/charts/overtime?days=14");
      const labels = arr(d.labels || d.dates);
      const values = arr(d.values || d.hours);

      charts.overtime?.destroy?.();
      charts.overtime = mkChart(canvas, {
        type: "bar",
        data: { labels, datasets: [{ label: "Heures sup", data: values }] },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true } },
        },
      });
    } catch (err) {
      console.error("overtime chart error:", err);
    }
  }

  async function buildDeptCostsChart() {
    const canvas = $("#deptChart");
    if (!canvas || !window.Chart) return;

    try {
      const d = await apiGet("/api/charts/department-costs");
      const pairs  = normalizePairs(d);
      const labels = pairs.map((x) => x.label);
      const values = pairs.map((x) => x.value);

      charts.dept?.destroy?.();
      charts.dept = mkChart(canvas, {
        type: "bar",
        data: { labels, datasets: [{ label: "Coût", data: values }] },
        options: {
          indexAxis: "x",
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true } },
        },
      });
    } catch (err) {
      console.error("dept costs error:", err);
    }
  }

  // ---------- 4) Effet "reveal on scroll" ----------
  function initReveal() {
    const els = $$("[data-reveal]");
    if (!els.length) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.classList.add("in-view");
            io.unobserve(e.target);
          }
        }
      },
      { threshold: 0.12 }
    );
    els.forEach((el) => io.observe(el));
  }

  // ---------- 5) Effet Ripple ----------
  function addRipple(e) {
    const host = e.currentTarget;
    const r = document.createElement("span");
    r.className = "ripple";
    const rect = host.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    r.style.width = r.style.height = size + "px";
    r.style.left = e.clientX - rect.left - size / 2 + "px";
    r.style.top = e.clientY - rect.top - size / 2 + "px";
    host.appendChild(r);
    setTimeout(() => r.remove(), 650);
  }
  function initRipples() {
    $$(".btn, .kpi-card").forEach((el) => {
      el.classList.add("ripple-host");
      el.addEventListener("click", addRipple, { passive: true });
    });
  }

  // ---------- 6) Initialisation & rafraîchissements ----------
  function refreshAll() {
    loadKpis();
    loadPresentList();
  }

  document.addEventListener("DOMContentLoaded", () => {
    // Data initiale
    refreshAll();
    buildPresenceChart();
    buildOvertimeChart();
    buildDeptCostsChart();

    // UI
    initReveal();
    initRipples();

    // Auto-refresh des KPIs et de la liste des présents (60 s)
    setInterval(refreshAll, 60_000);

    // NEW: rafraîchir quand l’onglet redevient actif / visible
    window.addEventListener("focus", refreshAll);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") refreshAll();
    });

    // NEW: rafraîchir les graphiques toutes les 5 min
    setInterval(buildPresenceChart,   300_000);
    setInterval(buildOvertimeChart,   300_000);
    setInterval(buildDeptCostsChart,  300_000);
  });
})();

// ------- Chart.js polish (version SAFE) -------
if (window.Chart) {
  try {
    const D = Chart.defaults;

    D.animation = Object.assign({}, D.animation, {
      duration: 900,
      easing: "easeOutCubic",
    });

    if (D.transitions && D.transitions.active) {
      D.transitions.active.animation = Object.assign(
        {},
        D.transitions.active.animation || {},
        { duration: 200 }
      );
    }

    if (D.elements && D.elements.line) {
      D.elements.line.tension = 0.38;
    }
    if (D.elements && D.elements.point) {
      D.elements.point.radius = 3;
      D.elements.point.hoverRadius = 6;
    }

    if (D.plugins) {
      D.plugins.tooltip = Object.assign({}, D.plugins.tooltip, {
        mode: "index",
        intersect: false,
        displayColors: false,
      });
      if (D.plugins.legend && D.plugins.legend.labels) {
        D.plugins.legend.labels.usePointStyle = true;
      }
    }

    D.font = Object.assign({}, D.font, {
      family: getComputedStyle(document.body).fontFamily,
    });

    Chart.register({
      id: "glow-point",
      afterDatasetsDraw(chart) {
        try {
          const { ctx, tooltip } = chart;
          const act = tooltip && tooltip.getActiveElements ? tooltip.getActiveElements() : [];
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
      },
    });
  } catch (err) {
    console.warn("Chart polish désactivé (SAFE):", err);
  }
}
