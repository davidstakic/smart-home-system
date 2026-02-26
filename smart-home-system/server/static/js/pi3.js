async function loadPi3State() {
    try {
      const res = await fetch("/api/PI3/state");
      const data = await res.json();
  
      const bt = data.bedroom_temp;
      document.getElementById("bedroom_temp_value").innerText =
        bt != null ? `${bt.toFixed(1)} °C` : "–";
  
      const bh = data.bedroom_hum;
      document.getElementById("bedroom_hum_value").innerText =
        bh != null ? `${bh.toFixed(1)} %` : "–";
  
      const mt = data.master_temp;
      document.getElementById("master_temp_value").innerText =
        mt != null ? `${mt.toFixed(1)} °C` : "–";
  
      const mh = data.master_hum;
      document.getElementById("master_hum_value").innerText =
        mh != null ? `${mh.toFixed(1)} %` : "–";
  
      const rgb = data.rgbled;
      document.getElementById("rgbled_value").innerText =
        rgb != null ? String(rgb) : "–";
  
      const lcd = data.lcdmessage;
      document.getElementById("lcdmessage_value").innerText =
        lcd != null ? String(lcd) : "–";
  
      const motionVal = data.livingroom_motion;
      const motionEl = document.getElementById("livingroom_motion_value");
      const motionDot = document.getElementById("livingroom_motion_status");
      const motionActive = !!motionVal;
      motionEl.innerText = motionActive ? "MOTION" : "NO MOTION";
      motionDot.classList.toggle("status-on", motionActive);
  
      // IR log – za sada koristiš samo poslednju vrednost; backend može kasnije da doda /api/PI3/ir-log
      const ir = data.bedroom_ir;
      const tbody = document.getElementById("bedroom_ir_table_body");
      tbody.innerHTML = "";
      if (ir == null) {
        const tr = document.createElement("tr");
        tr.innerHTML = "<td colspan='2'>Nema podataka.</td>";
        tbody.appendChild(tr);
      } else {
        const tr = document.createElement("tr");
        const now = new Date().toLocaleTimeString();
        tr.innerHTML = `<td>${now}</td><td>${String(ir)}</td>`;
        tbody.appendChild(tr);
      }
    } catch (e) {
      console.error("PI3 state error:", e);
    }
  }
  
  loadPi3State();
  setInterval(loadPi3State, 3000);
  
  async function setRgbColor(color) {
    try {
      const res = await fetch("/api/PI3/rgb", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ color })
      });
  
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (e) {
      console.error("RGB request error:", e);
    }
  }

  async function submitLcdMessage(event) {
    event.preventDefault();
    const input = document.getElementById("lcd_input");
    const statusEl = document.getElementById("lcd_message_status");
    const text = input.value.trim();
  
    if (!text) {
      statusEl.textContent = "Unesite poruku.";
      statusEl.className = "form-message form-message-error";
      return false;
    }
  
    try {
      const res = await fetch("/api/PI3/lcd", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
      });
  
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
  
      const data = await res.json();
      if (data.success) {
        statusEl.textContent = "Poruka je poslata na LCD.";
        statusEl.className = "form-message form-message-success";
        input.value = "";
        loadPi3State();
      } else {
        statusEl.textContent = data.message || "Nije uspelo slanje poruke.";
        statusEl.className = "form-message form-message-error";
      }
    } catch (e) {
      console.error("LCD request error:", e);
      statusEl.textContent = "Došlo je do greške pri slanju poruke.";
      statusEl.className = "form-message form-message-error";
    }
  
    return false;
  }
  
  