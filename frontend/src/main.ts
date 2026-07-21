import { Streamlit } from "streamlit-component-lib"

const root = document.getElementById("root")!
const btn = document.createElement("button")
const statusEl = document.createElement("span")
statusEl.style.marginLeft = "8px"
root.append(btn, statusEl)

let screenRec: MediaRecorder | null = null
let voiceRec: MediaRecorder | null = null
let screenChunks: Blob[] = []
let voiceChunks: Blob[] = []
let streams: MediaStream[] = []
let startedAt = 0

function setIdle(label: string) {
  btn.textContent = "● Record feedback"
  statusEl.textContent = label
}
setIdle("")

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

async function start() {
  try {
    const screen = await navigator.mediaDevices.getDisplayMedia({ video: true })
    let mic: MediaStream | null = null
    try {
      mic = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      statusEl.textContent = "no mic — video only"
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
    btn.textContent = "■ Stop"
    statusEl.textContent = "REC"
    Streamlit.setComponentValue({ status: "recording", startedAt })
  } catch (err) {
    if (screenRec && screenRec.state !== "inactive") screenRec.stop()
    if (voiceRec && voiceRec.state !== "inactive") voiceRec.stop()
    streams.forEach((s) => s.getTracks().forEach((t) => t.stop()))
    streams = []
    screenRec = null
    voiceRec = null
    setIdle(`blocked: ${(err as Error).name}`)
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
  statusEl.textContent = "saving…"
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
  setIdle("saved")
}

btn.addEventListener("click", () => {
  if (screenRec && screenRec.state === "recording") stop()
  else start()
})

Streamlit.setComponentReady()
Streamlit.setFrameHeight(48)
