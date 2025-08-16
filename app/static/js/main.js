
(() => {
  const root = document.documentElement;
  const saved = localStorage.getItem("theme");
  if(saved){ root.setAttribute("data-theme", saved); }
  const btn = document.getElementById("btn-theme");
  const icon = document.getElementById("icon-theme");
  function refreshIcon(){
    const dark = root.getAttribute("data-theme") === "dark";
    if(icon){ icon.className = dark ? "bi bi-sun" : "bi bi-moon-stars"; }
  }
  refreshIcon();
  btn && btn.addEventListener("click", () => {
    const cur = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", cur);
    localStorage.setItem("theme", cur);
    refreshIcon();
  });

  // Toast helper
  window.showToast = (message, variant="primary") => {
    const zone = document.getElementById("toast-zone");
    const el = document.createElement("div");
    el.className = `toast align-items-center text-bg-${variant} border-0`;
    el.setAttribute("role", "alert");
    el.innerHTML = `<div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>`;
    zone.appendChild(el);
    const t = new bootstrap.Toast(el, { delay: 2500 });
    t.show();
    el.addEventListener("hidden.bs.toast", () => el.remove());
  };

  // Utilities for geolocation used on attendance.js
  window.rhUtils = {
    async getPosition(){
      return new Promise((resolve) => {
        if(!navigator.geolocation) return resolve({ lat:null, lon:null });
        navigator.geolocation.getCurrentPosition(
          (pos) => resolve({ lat:pos.coords.latitude, lon:pos.coords.longitude }),
          () => resolve({ lat:null, lon:null }),
          { enableHighAccuracy:true, timeout:5000 }
        );
      });
    }
  };
})();
