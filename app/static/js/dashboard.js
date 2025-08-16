// app/static/js/dashboard.js
(() => {
  const $ = (sel) => document.querySelector(sel);

  // horodatage
  const now = new Date();
  $("#nowLabel").textContent = now.toLocaleString();

  // auto-refresh si un autre onglet pointe
  window.addEventListener("storage", (ev) => {
    if (ev.key === "rh_refresh") location.reload();
  });

  // helpers charts
  const mkChart = (canvas, cfg) => new Chart(canvas, cfg);

  // 1) KPIs & compteurs
  fetch("/api/dashboard/stats")
    .then(r => r.json())
    .then(s => {
      // on suppose ces clés ; fallback si manquantes
      $("#kpi-present").textContent = s.present_today ?? s.present ?? "0";
      $("#kpi-hours").textContent   = (s.hours_today ?? 0).toFixed(2);
      $("#kpi-leaves-pending").textContent = s.leave_pending ?? s.leaves_pending ?? "0";
      $("#kpi-ot-pending").textContent     = s.overtime_pending ?? s.ot_pending ?? "0";

      // petites sous-infos si l’API les fournit
      if (s.present_vs_yesterday != null) {
        const sign = s.present_vs_yesterday >= 0 ? "+" : "";
        $("#kpi-present-sub").textContent = `${sign}${s.present_vs_yesterday} vs hier`;
      } else {
        $("#kpi-present-sub").textContent = "—";
      }
      if (s.hours_vs_yesterday != null) {
        const sign = s.hours_vs_yesterday >= 0 ? "+" : "";
        $("#kpi-hours-sub").textContent = `${sign}${s.hours_vs_yesterday.toFixed(2)} h vs hier`;
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
      $("#kpi-hours-sub").textContent = "—";
    });

  // 2) Présence 14 jours
  fetch("/api/charts/presence?days=14")
    .then(r => r.json())
    .then(d => {
      const labels = d.labels || [];
      const values = d.values || [];
      mkChart($("#presenceChart"), {
        type: "line",
        data: {
          labels,
          datasets: [{
            label: "Présents",
            data: values,
            tension: .35,
            fill: false
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: { beginAtZero: true, ticks: { precision: 0 } }
          },
          plugins: {
            legend: { display: false },
            tooltip: { mode: "index", intersect: false }
          }
        }
      });
      if (labels.length) {
        $("#presenceRangeLabel").textContent = `${labels[0]} → ${labels[labels.length-1]}`;
      }
    });

  // 3) Heures sup 14 jours
  fetch("/api/charts/overtime?days=14")
    .then(r => r.json())
    .then(d => {
      mkChart($("#overtimeChart"), {
        type: "bar",
        data: {
          labels: d.labels || [],
          datasets: [{ label: "Heures sup", data: d.values || [] }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true } }
        }
      });
    });

  // 4) Coûts par département (mois en cours)
  fetch("/api/charts/department-costs")
    .then(r => r.json())
    .then(d => {
      mkChart($("#deptChart"), {
        type: "bar",
        data: {
          labels: (d || []).map(x => x.department || x.dept),
          datasets: [{ label: "Coût", data: (d || []).map(x => x.cost) }]
        },
        options: {
          indexAxis: window.innerWidth < 768 ? "x" : "x",
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true } }
        }
      });
    });
})();
