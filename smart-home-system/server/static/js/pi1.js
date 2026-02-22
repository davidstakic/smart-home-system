async function loadPi1State() {
    try {
      // const res = await fetch("/api/PI1/state");
      const data = await res.json();
  
      document.getElementById("door_button_value").innerText =
        data.door_button ? "Pressed" : "Not pressed";
      document.getElementById("door_motion_value").innerText =
        data.door_motion ? "Motion" : "No motion";
      document.getElementById("door_membrane_value").innerText =
        data.door_membrane ? "Pressed" : "Not pressed";
      document.getElementById("door_distance_value").innerText =
        data.door_distance != null ? `${data.door_distance.toFixed(1)} cm` : "–";
      document.getElementById("door_light_value").innerText =
        data.door_light ? "ON" : "OFF";
      document.getElementById("door_buzzer_value").innerText =
        data.door_buzzer ? "ACTIVE" : "SILENT";
      document.getElementById("alarm_state_value").innerText =
        data.alarm_state ? "ALARM" : "NORMAL";
    } catch (e) {
      console.error(e);
    }
  }
  
  async function controlLight(action) {
    await fetch("/api/actuator/light", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ action })
    });
    // setTimeout(loadPi1State, 500);
  }
  
  async function controlBuzzer(action, times, duration) {
    await fetch("/api/actuator/buzzer", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ action, times, duration })
    });
  }
  
  // loadPi1State();
  // setInterval(loadPi1State, 3000);
  