// app/static/js/attendance.js
(() => {
  // -------- utils --------
  const $ = (s) => document.querySelector(s);

  // Toast Bootstrap (nécessite <div id="toast-zone" class="toast-container ..."> dans base.html)
  function showToast(message, variant = "success", delay = 3000) {
    let zone = $("#toast-zone");
    if (!zone) {
      // fallback si le conteneur n'existe pas
      zone = document.createElement("div");
      zone.id = "toast-zone";
      zone.className = "toast-container position-fixed bottom-0 end-0 p-3";
      document.body.appendChild(zone);
    }
    const el = document.createElement("div");
    el.className = `toast align-items-center text-bg-${variant} border-0`;
    el.setAttribute("role", "alert");
    el.setAttribute("aria-live", "assertive");
    el.setAttribute("aria-atomic", "true");
    el.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">${message}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>`;
    zone.appendChild(el);
    const t = new bootstrap.Toast(el, { delay });
    t.show();
    el.addEventListener("hidden.bs.toast", () => el.remove());
  }

  // Bouton -> spinner + disabled
  function setBusy(btn, busy) {
    if (!btn) return;
    btn.disabled = !!busy;
    if (busy) {
      if (!btn.dataset.originalHtml) btn.dataset.originalHtml = btn.innerHTML;
      btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${btn.dataset.originalHtml}`;
    } else if (btn.dataset.originalHtml) {
      btn.innerHTML = btn.dataset.originalHtml;
      delete btn.dataset.originalHtml;
    }
  }

  // Géoloc promesse (lat/lon null si indispo)
  window.rhUtils = window.rhUtils || {};
  window.rhUtils.getPosition = function getPosition() {
    return new Promise((resolve) => {
      if (!("geolocation" in navigator)) return resolve({ lat: null, lon: null });
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
        ()    => resolve({ lat: null, lon: null }),
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
      );
    });
  };

  // -------- logique de pointage --------
  const btnIn  = $("#btn-checkin")  || $("#btnCheckIn");
  const btnOut = $("#btn-checkout") || $("#btnCheckOut");

  async function punch(action, btn) {
    try {
      setBusy(btn, true);

      const { lat, lon } = await window.rhUtils.getPosition();
      const params = new URLSearchParams(window.location.search);
      const token = params.get("token");

      const payload = { action, lat, lon };
      if (token) payload.token = token;

      const res = await fetch("/attendance/punch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      let data = {};
      try { data = await res.json(); } catch { /* ignore */ }

      if (!res.ok || !data.ok) {
        const msg = (data && data.error) ? data.error : `Erreur pointage (${res.status})`;
        showToast(msg, "danger", 4000);
        return;
      }

      // Succès : toast, rafraîchit dashboard (autre onglet), redirige en douceur
      showToast(`Pointage ${action} OK (id ${data.attendance_id})`, "success");
      localStorage.setItem("rh_refresh", Date.now().toString());
      setTimeout(() => { window.location.href = "/"; }, 900);

      // anti double-clic simple
      if (action === "checkin"  && btnIn)  btnIn.disabled  = true;
      if (action === "checkout" && btnOut) btnOut.disabled = true;

    } catch (e) {
      showToast("Erreur réseau, réessayez.", "danger");
    } finally {
      setBusy(btn, false);
    }
  }

  btnIn  && btnIn.addEventListener("click",  () => punch("checkin",  btnIn));
  btnOut && btnOut.addEventListener("click", () => punch("checkout", btnOut));

  // Bonus : Ctrl+Enter = checkin, Shift+Enter = checkout
  document.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.ctrlKey && btnIn)  punch("checkin",  btnIn);
    if (e.key === "Enter" && e.shiftKey && btnOut) punch("checkout", btnOut);
  });
})();
