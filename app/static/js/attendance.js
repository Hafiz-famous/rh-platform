// app/static/js/attendance.js
(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);

  // Fallback ESGIS Avedji (remplace les coords si besoin)
  const DEFAULT_COORDS = {
    lat: 6.1723,   // <-- mets vos coordonnées exactes ici si nécessaire
    lon: 1.2103,
    label: "ESGIS Avedji (fallback)"
  };

  let coords = null; // {lat, lon}

  function setStatus(txt) {
    const el = $("#geoLabel");
    if (el) el.textContent = txt;
  }

  function showToast(msg, ok = true) {
    try {
      const tpl = document.getElementById("toast-template");
      if (!tpl) return alert(msg);
      const toast = tpl.cloneNode(true);
      toast.id = "";
      toast.classList.toggle("text-bg-success", ok);
      toast.classList.toggle("text-bg-danger", !ok);
      toast.querySelector(".toast-body").textContent = msg;
      document.querySelector(".toast-container").appendChild(toast);
      if (window.bootstrap?.Toast) new bootstrap.Toast(toast, { delay: 2500 }).show();
      else alert(msg);
    } catch {
      alert(msg);
    }
  }

  async function punch(action) {
    const btn = action === "checkin" ? $("#btn-checkin") : $("#btn-checkout");
    const sp  = btn?.querySelector(".spinner-border");
    sp?.classList.remove("d-none"); btn?.setAttribute("disabled", "disabled");

    try {
      const token = new URLSearchParams(location.search).get("t") || null;
      const res = await fetch("/attendance/punch", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify({
          action,
          lat: coords?.lat ?? null,
          lon: coords?.lon ?? null,
          token
        })
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) throw new Error(data.error || `Erreur ${res.status}`);

      showToast(action === "checkin" ? "Check-in réussi ✅" : "Check-out réussi ✅", true);
      // Optionnel: rafraîchir d'autres onglets du dashboard
      try { localStorage.setItem("rh_refresh", String(Date.now())); } catch {}
    } catch (e) {
      showToast(`Échec: ${e.message || e}`, false);
    } finally {
      sp?.classList.add("d-none"); btn?.removeAttribute("disabled");
    }
  }

  function initButtons() {
    const ci = $("#btn-checkin");
    const co = $("#btn-checkout");
    if (ci) ci.addEventListener("click", () => punch("checkin"));
    if (co) co.addEventListener("click", () => punch("checkout"));
  }

  function initGeolocation() {
    // Si le template fournit des valeurs par data-attr, on les lit en priorité
    const host = $("#geoLabel");
    const dl = host?.dataset.defaultLat, dlo = host?.dataset.defaultLon;

    const fallback = () => {
      coords = {
        lat: dl ? Number(dl) : DEFAULT_COORDS.lat,
        lon: dlo ? Number(dlo) : DEFAULT_COORDS.lon
      };
      setStatus(`Géolocalisation: ${DEFAULT_COORDS.label}`);
    };

    if (!("geolocation" in navigator)) {
      setStatus("Géolocalisation indisponible (utilisation d’un point fixe).");
      fallback();
      return;
    }

    // Timeout de sécurité: si rien au bout de 6s -> fallback ESGIS
    const to = setTimeout(() => {
      setStatus("Géolocalisation lente, utilisation d’un point fixe.");
      fallback();
    }, 6000);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        clearTimeout(to);
        coords = {
          lat: pos.coords.latitude,
          lon: pos.coords.longitude
        };
        setStatus(`Géolocalisation OK (${coords.lat.toFixed(5)}, ${coords.lon.toFixed(5)})`);
      },
      (_err) => {
        clearTimeout(to);
        fallback();
      },
      { enableHighAccuracy: true, maximumAge: 10000, timeout: 5000 }
    );
  }

  document.addEventListener("DOMContentLoaded", () => {
    initButtons();
    initGeolocation();
  });
})();
