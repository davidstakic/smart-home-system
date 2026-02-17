async function loadPi2State() {
  try {
    const res = await fetch("/api/PI2/state");
    const data = await res.json();

    // 4SD – string vrednost, npr. "0015"
    document.getElementById("display4sd_value").innerText =
      data.display4sd != null ? String(data.display4sd).trim() : "–";

    document.getElementById("kitchen_button_value").innerText =
      data.kitchen_button ? "PRESSED" : "IDLE";

    const motionEl = document.getElementById("door_motion_value");
    const motionDot = document.getElementById("door_motion_status");
    const motionActive = !!data.door_motion;
    motionEl.innerText = motionActive ? "MOTION" : "NO MOTION";
    motionDot.classList.toggle("status-on", motionActive);

    document.getElementById("door_button_value").innerText =
      data.door_button ? "OPEN" : "CLOSED";

    const dist = data.door_distance;
    document.getElementById("door_distance_value").innerText =
      dist != null ? `${dist.toFixed(1)} cm` : "–";

    const temp = data.kitchen_temp;
    document.getElementById("kitchen_temp_value").innerText =
      temp != null ? `${temp.toFixed(1)} °C` : "–";

    const hum = data.kitchen_hum;
    document.getElementById("kitchen_hum_value").innerText =
      hum != null ? `${hum.toFixed(1)} %` : "–";

    const gyro = data.gyroscope;
    document.getElementById("gyroscope_value").innerText =
      gyro != null ? String(gyro) : "–";

    const people = data.people_count;
    document.getElementById("people_count_value").innerText =
      people != null ? people : "–";
  } catch (e) {
    console.error("PI2 state error:", e);
  }
}

loadPi2State();
setInterval(loadPi2State, 3000);

async function submitPi2TimerConfig(event) {
  event.preventDefault();
  const initInput = document.getElementById("initial_seconds");
  const btnInput = document.getElementById("btn_increment");
  const msgEl = document.getElementById("pi2_timer_message");

  const initialSeconds = Number(initInput.value);
  const btnIncrement = Number(btnInput.value);

  if (Number.isNaN(initialSeconds) || Number.isNaN(btnIncrement)) {
    msgEl.textContent = "Unesite ispravne numeričke vrednosti.";
    msgEl.className = "form-message form-message-error";
    return false;
  }

  try {
    const res = await fetch("/api/PI2/timer-config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        initial_seconds: initialSeconds,
        btn_increment: btnIncrement
      })
    });

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const data = await res.json();
    if (data.success) {
      msgEl.textContent = "Podešavanja stoperice su sačuvana.";
      msgEl.className = "form-message form-message-success";
    } else {
      msgEl.textContent = data.message || "Nije uspelo čuvanje podešavanja.";
      msgEl.className = "form-message form-message-error";
    }
  } catch (e) {
    console.error("Timer config error:", e);
    msgEl.textContent = "Došlo je do greške pri slanju podešavanja.";
    msgEl.className = "form-message form-message-error";
  }

  return false;
}
