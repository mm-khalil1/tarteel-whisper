// Recite page. Opened by the portal as /?from_surah=63&to_surah=64
// (optional: from_ayah, to_ayah, hide=1). Records the student, sends the audio
// to /api/check, colors each word, and on "Done" posts the result to the portal.

const params = new URLSearchParams(location.search);
const range = {
  from_surah: params.get("from_surah"),
  to_surah: params.get("to_surah") || params.get("from_surah"),
  from_ayah: params.get("from_ayah") || "1",
  to_ayah: params.get("to_ayah"),
};
const $ = (id) => document.getElementById(id);
const arabicDigits = (n) => String(n).replace(/\d/g, (d) => "٠١٢٣٤٥٦٧٨٩"[d]);

let config = {};
let wordEls = [];   // span per expected word, in order
let lastResult = null;
let recorder = null;
let timer = null;

function setStatus(text) { $("status").textContent = text; }
function showError(text) { $("error").textContent = text; $("error").hidden = false; }

async function init() {
  if (!range.from_surah) return showError("No surah selected. Open this page with ?from_surah=…&to_surah=…");
  $("hide").checked = params.get("hide") === "1";
  $("hide").onchange = () => $("passage").classList.toggle("hidden-text", $("hide").checked);
  $("hide").onchange();

  const q = new URLSearchParams(Object.entries(range).filter(([, v]) => v));
  const [cfg, res] = await Promise.all([fetch("/api/config"), fetch(`/api/passage?${q}`)]);
  config = await cfg.json();
  if (!res.ok) return showError((await res.json()).detail || "Could not load the passage.");
  renderPassage(await res.json());
  $("record").disabled = false;
  setStatus("Press start, then recite.");
}

function renderPassage(p) {
  const names = p.surahs.map((s) => s.name_en);
  $("title").textContent = names.length > 1 ? `${names[0]} – ${names.at(-1)}` : names[0];
  $("subtitle").textContent = p.pages.length > 1 ? `Pages ${p.pages[0]}–${p.pages.at(-1)}` : `Page ${p.pages[0]}`;
  const el = $("passage");
  el.innerHTML = "";
  wordEls = [];
  let surah = null, page = null;
  for (const a of p.ayahs) {
    if (a.surah !== surah) {
      surah = a.surah;
      const s = p.surahs.find((x) => x.n === surah);
      const h = document.createElement("div");
      h.className = "surah-head";
      h.textContent = `سورة ${s.name_ar}`;
      el.append(h);
    }
    for (const w of a.words) {
      if (page !== null && w.page !== page) {
        const b = document.createElement("span");
        b.className = "page-break";
        b.textContent = `— page ${w.page} —`;
        el.append(b);
      }
      page = w.page;
      const span = document.createElement("span");
      span.className = "w";
      span.textContent = w.text;
      wordEls.push(span);
      el.append(span, " ");
    }
    const no = document.createElement("span");
    no.className = "ayah-no";
    no.textContent = `﴿${arabicDigits(a.ayah)}﴾`;
    el.append(no, " ");
  }
}

// --- recording ---------------------------------------------------------------

$("record").onclick = async () => {
  if (recorder) return recorder.stop();
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    return showError("Microphone access was blocked. Allow the microphone and try again.");
  }
  const chunks = [];
  recorder = new MediaRecorder(stream);
  recorder.ondataavailable = (e) => chunks.push(e.data);
  recorder.onstop = async () => {
    stream.getTracks().forEach((t) => t.stop());
    clearInterval(timer);
    recorder = null;
    $("record").classList.remove("recording");
    $("record-label").textContent = "Start reciting";
    await submit(await toWav(new Blob(chunks)));
  };
  recorder.start();
  resetMarks();
  $("record").classList.add("recording");
  $("record-label").textContent = "Stop";
  const t0 = Date.now();
  timer = setInterval(() => {
    const s = Math.floor((Date.now() - t0) / 1000);
    setStatus(`Recording… ${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`);
  }, 250);
};

$("upload").onchange = async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  resetMarks();
  await submit(await toWav(file));
};

// Browsers record webm/ogg/mp4; decode here and send 16 kHz mono WAV so the
// server needs no ffmpeg.
async function toWav(blob) {
  const ctx = new AudioContext();
  const decoded = await ctx.decodeAudioData(await blob.arrayBuffer());
  ctx.close();
  const rate = 16000;
  const offline = new OfflineAudioContext(1, Math.ceil(decoded.duration * rate), rate);
  const src = offline.createBufferSource();
  src.buffer = decoded;
  src.connect(offline.destination);
  src.start();
  const pcm = (await offline.startRendering()).getChannelData(0);

  const buf = new DataView(new ArrayBuffer(44 + pcm.length * 2));
  const str = (o, s) => [...s].forEach((c, i) => buf.setUint8(o + i, c.charCodeAt(0)));
  str(0, "RIFF"); buf.setUint32(4, 36 + pcm.length * 2, true); str(8, "WAVE");
  str(12, "fmt "); buf.setUint32(16, 16, true); buf.setUint16(20, 1, true); buf.setUint16(22, 1, true);
  buf.setUint32(24, rate, true); buf.setUint32(28, rate * 2, true); buf.setUint16(32, 2, true); buf.setUint16(34, 16, true);
  str(36, "data"); buf.setUint32(40, pcm.length * 2, true);
  pcm.forEach((v, i) => buf.setInt16(44 + i * 2, Math.max(-1, Math.min(1, v)) * 0x7fff, true));
  return new Blob([buf], { type: "audio/wav" });
}

async function submit(wav) {
  $("record").disabled = true;
  $("error").hidden = true;
  setStatus("Checking your recitation…");
  const form = new FormData();
  form.append("audio", wav, "recitation.wav");
  Object.entries(range).forEach(([k, v]) => v && form.append(k, v));
  try {
    const res = await fetch("/api/check", { method: "POST", body: form });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    showResult(await res.json());
  } catch (err) {
    showError(`Could not check the recitation: ${err.message}`);
    setStatus("");
  } finally {
    $("record").disabled = false;
  }
}

// --- results -----------------------------------------------------------------

function resetMarks() {
  wordEls.forEach((el) => { el.className = "w"; el.title = ""; el.onclick = null; });
  document.querySelectorAll(".extra-mark").forEach((m) => m.remove());
  $("summary").hidden = true;
  $("done").hidden = true;
}

function showResult(r) {
  lastResult = r;
  $("hide").checked = false;
  $("hide").onchange();
  r.words.forEach((w, i) => {
    const el = wordEls[i];
    el.className = `w w-${w.status}`;
    if (w.status === "wrong") el.title = `Heard: ${w.heard}`;
    if (w.status === "missed") el.title = "Missed";
    el.onclick = el.title ? () => setStatus(`${w.text} — ${el.title}`) : null;
  });
  // One "+" per spot, e.g. a basmala or a repeated phrase.
  const extras = new Map();
  r.extras.forEach((e) => extras.set(e.after, [...(extras.get(e.after) || []), e.heard]));
  for (const [after, heard] of extras) {
    const m = document.createElement("span");
    m.className = "extra-mark";
    m.textContent = "+";
    m.title = `Extra: ${heard.join(" ")}`;
    m.onclick = () => setStatus(m.title);
    if (after < 0) wordEls[0].before(m); else wordEls[after].after(m);
  }

  const wrong = r.words.filter((w) => w.status === "wrong").length;
  const missed = r.words.filter((w) => w.status === "missed").length;
  $("sum-mistakes").textContent = r.total_mistakes === 0 ? "No mistakes, mā shā’ Allāh!"
    : `${r.total_mistakes} mistake${r.total_mistakes > 1 ? "s" : ""}`;
  $("sum-detail").textContent = `${wrong} wrong · ${missed} missed · ${r.total_words} words · ${r.duration_s}s`;
  $("sum-points").textContent = `★ ${r.total_points}/${r.max_points}`;
  $("sum-pages").innerHTML = r.pages
    .map((p) => `<span class="page-chip">Page ${p.page}: ${p.mistakes} mistake${p.mistakes === 1 ? "" : "s"} · <b>${"★".repeat(p.points) || "—"}</b></span>`)
    .join("");
  $("summary").hidden = false;
  $("summary").scrollIntoView({ behavior: "smooth" });
  setStatus("Tap a red word to see what was heard. Try again or press Done.");
  $("record-label").textContent = "Try again";
  $("done").hidden = !portalWindow();
}

// --- hand the result back to the portal -------------------------------------

function portalWindow() {
  if (!config.portal_origin) return null;
  if (window.parent !== window) return window.parent;
  return window.opener || null;
}

$("done").onclick = () => {
  const target = portalWindow();
  if (!target || !lastResult) return;
  const { words, extras, transcript, ...summary } = lastResult;
  target.postMessage(
    {
      type: "recitation:result",
      result: {
        ...summary,
        mistakes: words.filter((w) => w.status !== "correct"),
      },
    },
    config.portal_origin,
  );
  if (window.opener) window.close();
};

init().catch((e) => showError(`Something went wrong: ${e.message}`));
