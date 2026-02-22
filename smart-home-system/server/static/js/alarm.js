async function loadAlarmState() {
    try {
      const res = await fetch("/api/alarm/state");
      const data = await res.json();
  
      const alarmState = data.alarm_state;
      const peopleCount = data.people_count;
  
      const alarmEl = document.getElementById("alarm_state_value");
      const alarmDot = document.getElementById("alarm_status_dot");
  
      if (alarmState == null) {
        alarmEl.innerText = "UNKNOWN";
        alarmDot.classList.remove("status-on");
      } else {
        const active = !!alarmState;
        alarmEl.innerText = active ? "ALARM" : "NORMAL";
        alarmDot.classList.toggle("status-on", active);
      }
  
      const pcEl = document.getElementById("people_count_value");
      pcEl.innerText = peopleCount != null ? peopleCount : "–";
    } catch (e) {
      console.error("Alarm state error:", e);
    }
  }
  
  async function loadPeopleSeries() {
    try {
      const res = await fetch("/api/people/series?window=1m");
      const data = await res.json();
      const tbody = document.getElementById("people_series_body");
      tbody.innerHTML = "";
  
      if (!data || data.length === 0) {
        const tr = document.createElement("tr");
        tr.innerHTML = "<td colspan='2'>Nema podataka.</td>";
        tbody.appendChild(tr);
        return;
      }
  
      data.slice(-50).forEach((point) => {
        const tr = document.createElement("tr");
        const t = new Date(point.time);
        tr.innerHTML =
          `<td>${t.toLocaleString()}</td>` +
          `<td>${point.value}</td>`;
        tbody.appendChild(tr);
      });
    } catch (e) {
      console.error("People series error:", e);
    }
  }
  
  async function loadAlarmEvents() {
    try {
      const res = await fetch("/api/alarm/events");
      const data = await res.json();
      const tbody = document.getElementById("alarm_events_body");
      tbody.innerHTML = "";
  
      if (!data || data.length === 0) {
        const tr = document.createElement("tr");
        tr.innerHTML = "<td colspan='5'>Nema podataka.</td>";
        tbody.appendChild(tr);
        return;
      }
  
      data.slice(0, 50).forEach((evt) => {
        const tr = document.createElement("tr");
        const t = new Date(evt.time);
        tr.innerHTML =
          `<td>${t.toLocaleString()}</td>` +
          `<td>${evt.pi_id || "-"}</td>` +
          `<td>${evt.measurement}</td>` +
          `<td>${evt.field}</td>` +
          `<td>${evt.value}</td>`;
        tbody.appendChild(tr);
      });
    } catch (e) {
      console.error("Alarm events error:", e);
    }
  }
  
  function tickAlarm() {
    loadAlarmState();
    loadPeopleSeries();
    loadAlarmEvents();
  }
  
  tickAlarm();
  setInterval(tickAlarm, 5000);

  async function submitAlarmPin(event) {
    event.preventDefault();
    const input = document.getElementById("alarm_pin_input");
    const msgEl = document.getElementById("alarm_pin_message");
    const pin = input.value.trim();
  
    if (!pin) {
      msgEl.textContent = "Unesite PIN.";
      msgEl.className = "form-message form-message-error";
      return false;
    }
  
    try {
      const res = await fetch("/api/alarm/deactivate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin })
      });
  
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
  
      const data = await res.json();
      console.log(data)
      if (data.success) {
        msgEl.textContent = "Alarm je isključen.";
        msgEl.className = "form-message form-message-success";
        input.value = "";
        // osveži prikaz stanja
        loadAlarmState();
      } else {
        msgEl.textContent = data.message || "PIN nije ispravan.";
        msgEl.className = "form-message form-message-error";
      }
    } catch (e) {
      console.error("PIN error:", e);
      msgEl.textContent = "Došlo je do greške pri slanju PIN-a.";
      msgEl.className = "form-message form-message-error";
    }
  
    return false;
  }  
  
  async function submitAlarmArm(event) {
    event.preventDefault();
    const pinInput = document.getElementById("alarm_arm_pin");
    const msgEl = document.getElementById("alarm_arm_message");
    const pin = pinInput.value.trim();
  
    if (!pin) {
      msgEl.textContent = "Unesite PIN.";
      msgEl.className = "form-message form-message-error";
      return false;
    }
  
    try {
      const res = await fetch("/api/alarm/arm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin, armed: true })
      });
  
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
  
      const data = await res.json();
      if (data.success) {
        msgEl.textContent = "Sistem je aktiviran.";
        msgEl.className = "form-message form-message-success";
        loadAlarmState();
      } else {
        msgEl.textContent = data.message || "PIN nije ispravan ili sistem nije aktiviran.";
        msgEl.className = "form-message form-message-error";
      }
    } catch (e) {
      console.error("Alarm arm error:", e);
      msgEl.textContent = "Došlo je do greške pri aktiviranju sistema.";
      msgEl.className = "form-message form-message-error";
    }
  
    return false;
  }
  
  async function submitAlarmDisarm() {
    const pinInput = document.getElementById("alarm_arm_pin");
    const msgEl = document.getElementById("alarm_arm_message");
    const pin = pinInput.value.trim();
  
    if (!pin) {
      msgEl.textContent = "Unesite PIN.";
      msgEl.className = "form-message form-message-error";
      return;
    }
  
    try {
      const res = await fetch("/api/alarm/arm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin, armed: false })
      });
  
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
  
      const data = await res.json();
      if (data.success) {
        msgEl.textContent = "Sistem je deaktiviran.";
        msgEl.className = "form-message form-message-success";
        loadAlarmState();
      } else {
        msgEl.textContent = data.message || "PIN nije ispravan ili sistem nije deaktiviran.";
        msgEl.className = "form-message form-message-error";
      }
    } catch (e) {
      console.error("Alarm disarm error:", e);
      msgEl.textContent = "Došlo je do greške pri deaktiviranju sistema.";
      msgEl.className = "form-message form-message-error";
    }
  }
  