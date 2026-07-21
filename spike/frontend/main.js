function send(type, data) {
  window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type: type }, data), "*");
}
function setValue(value) {
  send("streamlit:setComponentValue", { dataType: "json", value: value });
}

const btn = document.getElementById("btn");
const statusEl = document.getElementById("status");
let screenRec = null, voiceRec = null;
let screenChunks = [], voiceChunks = [];
let streams = [], startedAt = null;

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result.split(",")[1]);
    r.onerror = reject;
    r.readAsDataURL(blob);
  });
}

function stopRecorder(rec, chunks) {
  return new Promise((resolve) => {
    rec.onstop = () => resolve(new Blob(chunks, { type: rec.mimeType }));
    rec.stop();
  });
}

async function start() {
  try {
    const screen = await navigator.mediaDevices.getDisplayMedia({ video: true });
    const mic = await navigator.mediaDevices.getUserMedia({ audio: true });
    streams = [screen, mic];
    startedAt = Date.now();
    screenChunks = []; voiceChunks = [];
    screenRec = new MediaRecorder(screen, { mimeType: "video/webm" });
    voiceRec = new MediaRecorder(mic, { mimeType: "audio/webm" });
    screenRec.ondataavailable = (e) => screenChunks.push(e.data);
    voiceRec.ondataavailable = (e) => voiceChunks.push(e.data);
    screenRec.start(1000);
    voiceRec.start(1000);
    screen.getVideoTracks()[0].addEventListener("ended", stop);
    btn.textContent = "Stop recording";
    statusEl.textContent = " REC";
    setValue({ status: "recording", startedAt: startedAt });
  } catch (err) {
    statusEl.textContent = " BLOCKED: " + err.name + " — " + err.message;
  }
}

async function stop() {
  if (!screenRec || screenRec.state === "inactive") return;
  const stoppedAt = Date.now();
  const [screenBlob, voiceBlob] = await Promise.all([
    stopRecorder(screenRec, screenChunks),
    stopRecorder(voiceRec, voiceChunks),
  ]);
  streams.forEach((s) => s.getTracks().forEach((t) => t.stop()));
  statusEl.textContent = " encoding…";
  const [recording_b64, voice_b64] = await Promise.all([
    blobToBase64(screenBlob),
    blobToBase64(voiceBlob),
  ]);
  setValue({
    status: "stopped",
    startedAt: startedAt,
    duration_ms: stoppedAt - startedAt,
    recording_b64: recording_b64,
    voice_b64: voice_b64,
  });
  btn.textContent = "Start recording";
  statusEl.textContent = " sent";
}

btn.addEventListener("click", () => {
  if (screenRec && screenRec.state === "recording") stop();
  else start();
});

send("streamlit:componentReady", { apiVersion: 1 });
send("streamlit:setFrameHeight", { height: 60 });
