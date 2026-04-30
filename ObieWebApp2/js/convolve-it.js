// ── Plotly theme (inherits ObieWebApp2 light palette) ────────────────
// Colours are read from CSS variables at runtime so they follow theme.css
function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function plotLayout(title, xl, yl, extra = {}) {
  return {
    paper_bgcolor: 'transparent',
    plot_bgcolor:  'transparent',
    font:  { size: 10, family: 'inherit' },
    title: { text: title, font: { size: 11 }, pad: { t: 2, b: 0 } },
    xaxis: { title: xl, gridcolor: cssVar('--border'),
             zerolinecolor: cssVar('--border'), tickfont: { size: 9 },
             ...(extra.xaxis || {}) },
    yaxis: { title: yl, gridcolor: cssVar('--border'),
             zerolinecolor: cssVar('--border'), tickfont: { size: 9 },
             ...(extra.yaxis || {}) },
    margin: { l: 50, r: 12, t: 28, b: 38 },
    autosize: true, showlegend: false,
  };
}
const pcfg = { responsive: true, displayModeBar: false };

// Accent colours (warm tones that sit well on light background)
const COL = { frf: '#7c4dbe', wav: '#2e7d32', out: '#e65100', spec: '#1565c0' };

// Init empty plots
Plotly.newPlot('frf-plot', [],
  plotLayout('FRF · Magnitude', 'Frequency (Hz)', 'dB',
             { xaxis: { type: 'log' } }), pcfg);
Plotly.newPlot('wav-plot', [],
  plotLayout('Input Waveform', 'Time (s)', 'Amplitude'), pcfg);
Plotly.newPlot('out-plot', [],
  plotLayout('Convolved Output', 'Time (s)', 'Amplitude'), pcfg);
Plotly.newPlot('spec-plot', [],
  plotLayout('Output Spectrum', 'Frequency (Hz)', 'dB',
             { xaxis: { type: 'log' } }), pcfg);

// ── Global state ─────────────────────────────────────────────────────
let frfFreqs = null, frfDb = null;
let wavSamples = null, wavSR = 44100;
let outSamples = null, outSR = 44100;
let phaseMode = 'minphase';
let audioCtx = null;

// Two independent players
const player = {
  wav: { source: null, playing: false, btnId: 'play-wav-btn' },
  out: { source: null, playing: false, btnId: 'play-btn'     },
};

function getAudioCtx() {
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  if (audioCtx.state === 'suspended') audioCtx.resume();
  return audioCtx;
}

function startPlayer(key, samples, sr) {
  // Stop both first so only one ever plays at a time
  stopPlayer('wav'); stopPlayer('out');
  const ctx = getAudioCtx();
  const buf = ctx.createBuffer(1, samples.length, sr);
  buf.copyToChannel(samples instanceof Float32Array ? samples : new Float32Array(samples), 0);
  const src = ctx.createBufferSource();
  src.buffer = buf;
  src.connect(ctx.destination);
  src.onended = () => { player[key].playing = false; player[key].source = null; updatePlayBtn(key); };
  src.start();
  player[key].source  = src;
  player[key].playing = true;
  updatePlayBtn(key);
}

function stopPlayer(key) {
  if (player[key].source) { try { player[key].source.stop(); } catch(e) {} player[key].source = null; }
  player[key].playing = false;
  updatePlayBtn(key);
}

function updatePlayBtn(key) {
  const btn = document.getElementById(player[key].btnId);
  if (!btn) return;
  const isWav = key === 'wav';
  btn.textContent = player[key].playing
    ? (isWav ? '■ Stop WAV'    : '■ Stop')
    : (isWav ? '▶ Play WAV'    : '▶ Play Result');
  btn.classList.toggle('active', player[key].playing);
}

// ── TRF Binary Parser (exact format from file-loader.js) ─────────────
function parseTRF(buffer) {
  const v = new DataView(buffer);
  let off = 0;
  const LE = true;

  off += 4;                                        // index (uint32)
  off += 8 * 4;                                    // Xr, Yr, Xactual, YActual (4×float64)
  off += 2;                                        // char_str (2 bytes)
  const Hz_Resolution = v.getFloat64(off, LE); off += 8;
  const Start_Freq    = v.getFloat64(off, LE); off += 8;
  const End_Freq      = v.getFloat64(off, LE); off += 8;
  const fComplex      = v.getFloat32(off, LE); off += 4;
  const fLength       = Math.round(v.getFloat32(off, LE)); off += 4;
  off += 4 * 9;                                    // 9 unused float32 fields
  off += 4;                                        // caption (4 bytes)
  // off is now 110 — data starts here

  const isComplex = Math.round(fComplex) === 1;
  const freqs = [], dbVals = [];

  for (let i = 0; i < fLength; i++) {
    const re = v.getFloat64(off, LE); off += 8;
    const im = isComplex ? v.getFloat64(off, LE) : 0; if (isComplex) off += 8;
    const mag = Math.sqrt(re * re + im * im);
    freqs.push(Start_Freq + i * Hz_Resolution);
    dbVals.push(mag > 1e-12 ? 20 * Math.log10(mag) : -240);
  }
  return { freqs, dbVals, Hz_Resolution, Start_Freq, End_Freq, fLength };
}

// ── FRF loading — routes CSV vs TRF by extension ──────────────────────
function loadFRF(input) {
  const file = input.files[0]; if (!file) return;
  setSt('frf-status', 'reading…');
  const ext = file.name.split('.').pop().toLowerCase();

  if (ext === 'trf') {
    const reader = new FileReader();
    reader.onload = e => {
      try {
        const { freqs, dbVals, Hz_Resolution, Start_Freq, End_Freq, fLength } =
          parseTRF(e.target.result);
        frfFreqs = freqs; frfDb = dbVals;
        setSt('frf-status',
          `✓ ${fLength} pts · ${Start_Freq.toFixed(0)}–${End_Freq.toFixed(0)} Hz · ${Hz_Resolution.toFixed(3)} Hz/pt`, 'ok');
        plotFRF(); checkReady();
      } catch(err) {
        setSt('frf-status', 'parse error: ' + err.message.slice(0, 40), 'err');
      }
    };
    reader.onerror = () => setSt('frf-status', 'read error', 'err');
    reader.readAsArrayBuffer(file);
  } else {
    // CSV path
    const reader = new FileReader();
    reader.onload = e => {
      const lines = e.target.result.trim().split('\n');
      frfFreqs = []; frfDb = [];
      for (const ln of lines) {
        if (/[a-df-zA-DF-Z]/.test(ln.charAt(0))) continue;
        const p = ln.split(',');
        if (p.length >= 2) {
          const f = parseFloat(p[0]), d = parseFloat(p[1]);
          if (isFinite(f) && isFinite(d) && f > 0) { frfFreqs.push(f); frfDb.push(d); }
        }
      }
      if (frfFreqs.length < 4) {
        setSt('frf-status', 'parse error — check file format', 'err');
        frfFreqs = frfDb = null; return;
      }
      const flo = frfFreqs[0].toFixed(0), fhi = frfFreqs[frfFreqs.length - 1].toFixed(0);
      setSt('frf-status', `✓ ${frfFreqs.length} pts · ${flo}–${fhi} Hz`, 'ok');
      plotFRF(); checkReady();
    };
    reader.onerror = () => setSt('frf-status', 'read error', 'err');
    reader.readAsText(file);
  }
}

function plotFRF() {
  if (!frfFreqs) return;
  const fin = frfDb.filter(v => isFinite(v));
  const dbMax = Math.max(6,  Math.ceil( (Math.max(...fin) + 3) / 6) * 6);
  const dbMin = Math.min(-6, Math.floor((Math.min(...fin) - 3) / 6) * 6);
  Plotly.react('frf-plot', [{
    x: frfFreqs, y: frfDb, type: 'scatter', mode: 'lines',
    line: { color: COL.frf, width: 1.5 }
  }], plotLayout('FRF · Magnitude', 'Frequency (Hz)', 'dB', {
    xaxis: { type: 'log' }, yaxis: { range: [dbMin, dbMax] }
  }), pcfg);
}

// ── WAV loading ────────────────────────────────────────────────────────
async function loadWAV(input) {
  const file = input.files[0]; if (!file) return;
  setSt('wav-status', 'decoding…');
  try {
    const arrBuf = await file.arrayBuffer();
    const tmpCtx = new AudioContext();
    const audioBuf = await tmpCtx.decodeAudioData(arrBuf);
    await tmpCtx.close();
    wavSR = audioBuf.sampleRate;
    wavSamples = audioBuf.getChannelData(0);   // mono: first channel
    const dur = (wavSamples.length / wavSR).toFixed(2);
    setSt('wav-status',
      `${dur} s · ${(wavSR / 1000).toFixed(1)} kHz · ${audioBuf.numberOfChannels}ch`, 'ok');
    document.getElementById('play-wav-btn').style.display = '';
    plotWAV(); checkReady();
  } catch(e) {
    setSt('wav-status', 'error: ' + e.message.slice(0, 40), 'err');
    wavSamples = null;
  }
}

function plotWAV() {
  if (!wavSamples) return;
  const n = wavSamples.length, step = Math.max(1, Math.floor(n / 5000));
  const x = [], y = [];
  for (let i = 0; i < n; i += step) { x.push(i / wavSR); y.push(wavSamples[i]); }
  Plotly.react('wav-plot', [{
    x, y, type: 'scatter', mode: 'lines', line: { color: COL.wav, width: 1 }
  }], plotLayout('Input Waveform', 'Time (s)', 'Amplitude'), pcfg);
}

function checkReady() {
  document.getElementById('conv-btn').disabled = !(frfFreqs && wavSamples);
}

// ── Phase mode ─────────────────────────────────────────────────────────
function setPhaseMode(mode, btn) {
  phaseMode = mode;
  document.querySelectorAll('#phase-toggle button')
    .forEach(b => b.classList.toggle('active', b === btn));
}

// ── Gain ──────────────────────────────────────────────────────────────
function updGain() {
  const v = +document.getElementById('gain-sl').value;
  document.getElementById('gain-disp').textContent = (v >= 0 ? '+' : '') + v + ' dB';
}

// ── Convolution ────────────────────────────────────────────────────────
function runConvolution() {
  if (!frfFreqs || !wavSamples) return;
  stopPlayer('wav'); stopPlayer('out');
  ['conv-btn', 'play-btn', 'save-btn'].forEach(id => {
    const el = document.getElementById(id); if (el) el.disabled = true;
  });
  setProgMsg('Computing…');
  const gainDb = +document.getElementById('gain-sl').value;

  setTimeout(() => {
    if (window.pyConvolve) {
      try {
        window.pyConvolve(frfFreqs, frfDb, Array.from(wavSamples),
                          wavSR, phaseMode, gainDb);
      } catch(e) {
        clearProgMsg();
        document.getElementById('conv-btn').disabled = false;
        setProgMsg('Error: ' + e.message.slice(0, 60));
        setTimeout(clearProgMsg, 5000);
      }
    } else {
      clearProgMsg();
      document.getElementById('conv-btn').disabled = false;
      setProgMsg('Python not ready yet — please wait…');
      setTimeout(clearProgMsg, 4000);
    }
  }, 30);
}

// Called from Python
window.onConvolveResult = function(samplesArr, sr) {
  outSamples = new Float32Array(samplesArr);
  outSR = sr;
  clearProgMsg();
  document.getElementById('conv-btn').disabled = false;
  document.getElementById('result-card').style.display = '';
  const dur = (outSamples.length / outSR).toFixed(2);
  document.getElementById('out-info').textContent =
    `${dur} s · ${(outSR / 1000).toFixed(1)} kHz · ${outSamples.length.toLocaleString()} samples`;
  document.getElementById('play-btn').disabled = false;
  document.getElementById('save-btn').disabled = false;
  plotOutput();
};

window.onConvolveError = function(msg) {
  clearProgMsg();
  setProgMsg('Error: ' + msg);
  setTimeout(clearProgMsg, 6000);
  document.getElementById('conv-btn').disabled = false;
};

window.setProgMsg = setProgMsg;   // Python can call this mid-computation

function plotOutput() {
  if (!outSamples) return;
  const n = outSamples.length, step = Math.max(1, Math.floor(n / 5000));
  const x = [], y = [];
  for (let i = 0; i < n; i += step) { x.push(i / outSR); y.push(outSamples[i]); }
  Plotly.react('out-plot', [{
    x, y, type: 'scatter', mode: 'lines', line: { color: COL.out, width: 1 }
  }], plotLayout('Convolved Output', 'Time (s)', 'Amplitude'), pcfg);
  window.pySpectrum && window.pySpectrum(Array.from(outSamples), outSR);
}

window.onSpectrumResult = function(freqs, dbVals) {
  Plotly.react('spec-plot', [{
    x: Array.from(freqs), y: Array.from(dbVals),
    type: 'scatter', mode: 'lines', line: { color: COL.spec, width: 1.5 }
  }], plotLayout('Output · Magnitude Spectrum', 'Frequency (Hz)', 'dB',
                 { xaxis: { type: 'log' } }), pcfg);
};

// ── Playback ──────────────────────────────────────────────────────────
function togglePlayWAV() {
  if (player.wav.playing) stopPlayer('wav');
  else if (wavSamples)    startPlayer('wav', wavSamples, wavSR);
}

function togglePlay() {
  if (player.out.playing) stopPlayer('out');
  else if (outSamples)    startPlayer('out', outSamples, outSR);
}

// ── WAV export ────────────────────────────────────────────────────────
function saveWAV() {
  if (!outSamples) return;
  const buf = encodeWAV(outSamples, outSR);
  const url = URL.createObjectURL(new Blob([buf], { type: 'audio/wav' }));
  const a = document.createElement('a');
  const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  a.href = url; a.download = 'convolved_' + ts + '.wav'; a.click();
  URL.revokeObjectURL(url);
}

function encodeWAV(samples, sr) {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buf);
  const ws = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  ws(0, 'RIFF'); v.setUint32(4, 36 + samples.length * 2, true); ws(8, 'WAVE');
  ws(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true);
  v.setUint16(22, 1, true); v.setUint32(24, sr, true); v.setUint32(28, sr * 2, true);
  v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  ws(36, 'data'); v.setUint32(40, samples.length * 2, true);
  let o = 44;
  for (let i = 0; i < samples.length; i++) {
    v.setInt16(o, Math.max(-1, Math.min(1, samples[i])) * 0x7FFF, true); o += 2;
  }
  return buf;
}

// ── UI helpers ────────────────────────────────────────────────────────
function setSt(id, txt, cls) {
  const el = document.getElementById(id);
  el.textContent = txt;
  el.className = 'file-status' + (cls ? ' ' + cls : '');
}
function setProgMsg(m)  { document.getElementById('prog-msg').textContent = m; }
function clearProgMsg() { document.getElementById('prog-msg').textContent = ''; }
