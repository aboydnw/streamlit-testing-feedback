import { RenderData, Streamlit } from "streamlit-component-lib"

type UiState = "idle" | "preflight" | "rec" | "saving" | "saved"

const root = document.getElementById("root")!
root.style.cssText = "font-size:14px;line-height:1.4"

let screenRec: MediaRecorder | null = null
let voiceRec: MediaRecorder | null = null
let screenChunks: Blob[] = []
let voiceChunks: Blob[] = []
let streams: MediaStream[] = []
let startedAt = 0
let timerId: number | null = null
let lastZip: string | null = null

const SOFT_LIMIT_MS = 10 * 60 * 1000

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader()
    r.onload = () => resolve((r.result as string).split(",")[1])
    r.onerror = reject
    r.readAsDataURL(blob)
  })
}

function stopRecorder(rec: MediaRecorder, chunks: Blob[]): Promise<Blob> {
  return new Promise((resolve) => {
    rec.onstop = () => resolve(new Blob(chunks, { type: rec.mimeType }))
    rec.stop()
  })
}

function fmtElapsed(ms: number): string {
  const s = Math.floor(ms / 1000)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`
}

function render(state: UiState, detail = "") {
  if (timerId !== null && state !== "rec") {
    clearInterval(timerId)
    timerId = null
  }
  if (state === "idle") {
    root.innerHTML = `<button id="go">● Record feedback</button><span id="note" style="margin-left:8px;opacity:.7"></span>`
    document.getElementById("note")!.textContent = detail
    document.getElementById("go")!.addEventListener("click", () => render("preflight"))
    Streamlit.setFrameHeight(48)
  } else if (state === "preflight") {
    root.innerHTML = `
      <div style="border:1px solid #ccc;border-radius:6px;padding:10px">
        <div>Records your <b>screen</b> and <b>microphone</b> into this project's
        <code>.feedback/</code> folder for analysis.</div>
        <div style="margin-top:6px"><b>Narrate out loud as you go — your voice is
        the most valuable signal.</b></div>
        <div style="margin-top:10px">
          <button id="start">Start recording</button>
          <button id="cancel" style="margin-left:8px">Cancel</button>
        </div>
      </div>`
    document.getElementById("start")!.addEventListener("click", start)
    document.getElementById("cancel")!.addEventListener("click", () => render("idle"))
    Streamlit.setFrameHeight(180)
  } else if (state === "rec") {
    root.innerHTML = `<button id="stop">■ Stop</button>
      <span style="margin-left:8px;color:#d33">●</span>
      <span id="elapsed" style="margin-left:4px">0:00</span>
      <span id="warn" style="margin-left:8px;color:#d33"></span>`
    document.getElementById("stop")!.addEventListener("click", stop)
    timerId = window.setInterval(() => {
      const elapsed = Date.now() - startedAt
      document.getElementById("elapsed")!.textContent = fmtElapsed(elapsed)
      if (elapsed > SOFT_LIMIT_MS) {
        document.getElementById("warn")!.textContent = "long recording — consider stopping"
      }
    }, 1000)
    Streamlit.setFrameHeight(48)
  } else if (state === "saving") {
    root.innerHTML = `<span>saving…</span>`
    Streamlit.setFrameHeight(48)
  } else if (state === "saved") {
    render("idle", lastZip ? `✓ saved ${lastZip}` : "✓ saved")
  }
}

async function start() {
  try {
    const screen = await navigator.mediaDevices.getDisplayMedia({ video: true })
    let mic: MediaStream | null = null
    try {
      mic = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      /* video-only */
    }
    streams = mic ? [screen, mic] : [screen]
    startedAt = Date.now()
    screenChunks = []
    voiceChunks = []
    screenRec = new MediaRecorder(screen, { mimeType: "video/webm" })
    screenRec.ondataavailable = (e) => screenChunks.push(e.data)
    screenRec.start(1000)
    if (mic) {
      voiceRec = new MediaRecorder(mic, { mimeType: "audio/webm" })
      voiceRec.ondataavailable = (e) => voiceChunks.push(e.data)
      voiceRec.start(1000)
    } else {
      voiceRec = null
    }
    screen.getVideoTracks()[0].addEventListener("ended", stop)
    render("rec")
    Streamlit.setComponentValue({ status: "recording", startedAt })
  } catch (err) {
    if (screenRec && screenRec.state !== "inactive") screenRec.stop()
    if (voiceRec && voiceRec.state !== "inactive") voiceRec.stop()
    streams.forEach((s) => s.getTracks().forEach((t) => t.stop()))
    streams = []
    screenRec = null
    voiceRec = null
    render("idle", `blocked: ${(err as Error).name}`)
  }
}

async function stop() {
  if (!screenRec || screenRec.state === "inactive") return
  const duration_ms = Date.now() - startedAt
  const stops: Promise<Blob>[] = [stopRecorder(screenRec, screenChunks)]
  if (voiceRec && voiceRec.state !== "inactive") {
    stops.push(stopRecorder(voiceRec, voiceChunks))
  }
  const [screenBlob, voiceBlob] = await Promise.all(stops)
  streams.forEach((s) => s.getTracks().forEach((t) => t.stop()))
  render("saving")
  const recording_b64 = await blobToBase64(screenBlob)
  const voice_b64 = voiceBlob ? await blobToBase64(voiceBlob) : null
  Streamlit.setComponentValue({
    status: "stopped",
    startedAt,
    duration_ms,
    app_url: document.referrer,
    recording_b64,
    voice_b64,
  })
  render("saved")
}

function onRender(event: Event) {
  const data = (event as CustomEvent<RenderData>).detail
  const zip = (data.args["last_zip"] as string | null) ?? null
  if (zip && zip !== lastZip) {
    lastZip = zip
    if (!screenRec || screenRec.state === "inactive") render("saved")
  }
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender)
Streamlit.setComponentReady()
render("idle")
