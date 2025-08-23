(function () {
  const $  = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));

  const btnIn  = $("#btn-checkin");
  const btnOut = $("#btn-checkout");
  const geoLbl = $("#geo-status");

  // Utilitaires
  function setBusy(btn, busy=true){
    const sp = btn.querySelector(".spinner-border");
    if (busy){
      btn.disabled = true;
      sp && sp.classList.remove("d-none");
    } else {
      btn.disabled = false;
      sp && sp.classList.add("d-none");
    }
  }

  function toast(message, {ok=true}={}){
    const tpl = $("#toast-template").cloneNode(true);
    tpl.id = "";
    tpl.classList.remove("show");
    tpl.classList.toggle("text-bg-success", ok);
    tpl.classList.toggle("text-bg-danger", !ok);
    tpl.querySelector(".toast-body").textContent = message;
    $(".toast-container").appendChild(tpl);

    // Bootstrap toast
    const t = new bootstrap.Toast(tpl, { delay: 3500 });
    t.show();
    tpl.addEventListener("hidden.bs.toast", ()=> tpl.remove());
  }

  // Geolocation (promise + timeout)
  function getLocation(timeoutMs = 8000){
    return new Promise(resolve => {
      if (!("geolocation" in navigator)){
        resolve({ ok:false, reason:"unsupported" });
        return;
      }
      let done = false;
      const timer = setTimeout(()=>{
        if (!done){ done = true; resolve({ ok:false, reason:"timeout" }); }
      }, timeoutMs);

      navigator.geolocation.getCurrentPosition(
        pos => {
          if (done) return;
          clearTimeout(timer);
          done = true;
          const {latitude, longitude, accuracy} = pos.coords;
          resolve({ ok:true, lat:latitude, lng:longitude, accuracy });
        },
        err => {
          if (done) return;
          clearTimeout(timer);
          done = true;
          resolve({ ok:false, reason: err.code === 1 ? "denied" : "error" });
        },
        { enableHighAccuracy:true, maximumAge: 30_000, timeout: timeoutMs }
      );
    });
  }

  // Affiche l’état geo initial (non bloquant)
  (async function initGeo(){
    const res = await getLocation(1); // 1ms -> lit le cache s'il existe
    if (res.ok){
      geoLbl.textContent = `Géolocalisation : ${res.lat.toFixed(5)}, ${res.lng.toFixed(5)} (±${Math.round(res.accuracy)}m)`;
    } else {
      geoLbl.textContent = "Géolocalisation : non disponible (sera tentée au moment du pointage)";
    }
  })();

  // Appel API — adapte l’URL si besoin
  async function sendMark(action, coords){
    // On cible par défaut une API JSON /attendance/api/mark ; si tu as un autre endpoint, change ici.
    const url = "/attendance/api/mark";
    const body = {
      action,
      lat:  coords?.lat ?? null,
      lng:  coords?.lng ?? null,
      accuracy: coords?.accuracy ?? null,
      at:   new Date().toISOString()
    };

    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "include"
    });

    // On accepte application/json ou text/json
    const ct = r.headers.get("content-type") || "";
    const data = ct.includes("json") ? await r.json().catch(()=>({})) : {};
    if (!r.ok || data.ok === false){
      const msg = data.message || `Erreur ${r.status}`;
      throw new Error(msg);
    }
    return data;
  }

  async function handleAction(action, btn){
    try {
      setBusy(btn, true);
      // Essaye d’obtenir une position (mais ne bloque pas le pointage si KO)
      const geo = await getLocation();
      if (geo.ok){
        geoLbl.textContent = `Géolocalisation : ${geo.lat.toFixed(5)}, ${geo.lng.toFixed(5)} (±${Math.round(geo.accuracy)}m)`;
      } else {
        const reasons = {timeout:"temps dépassé", denied:"refusée", unsupported:"non supportée", error:"erreur"};
        geoLbl.textContent = `Géolocalisation : ${reasons[geo.reason] || "indisponible"}`;
      }

      const payload = await sendMark(action, geo.ok ? geo : null);
      const label = action === "checkin" ? "Check-in" : "Check-out";
      toast(`${label} enregistré ✅`, {ok:true});

      // Si l’API renvoie la durée/heure, tu peux mettre à jour des KPIs locaux ici.

    } catch (e){
      console.error(e);
      toast(e.message || "Erreur lors du pointage", {ok:false});
    } finally {
      setBusy(btn, false);
    }
  }

  btnIn?.addEventListener("click", ()=> handleAction("checkin", btnIn));
  btnOut?.addEventListener("click", ()=> handleAction("checkout", btnOut));
})();
