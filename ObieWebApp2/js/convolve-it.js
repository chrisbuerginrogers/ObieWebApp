/* ─────────────────────────────────────────────────────────────────────
 * convolve-it.js  —  UI wiring for the Convolve It tool
 *
 * Requires (loaded before this file):
 *   plotly-theme.js   — cssVar(), plotLayout(), pcfg, COL
 *   audio.js          — decodeWAV(), encodeWAV(), AudioPlayer
 *
 * All file parsing (TRF binary + CSV) and all DSP runs in Python.
 * This file manages: state, plot rendering, FRF/WAV file dispatch,
 * convolution trigger, and the two audio players.
 * ───────────────────────────────────────────────────────────────────── */

// ── Global state ──────────────────────────────────────────────────────
let frfFreqs = null, frfDb = null;
let wavSamples = null, wavSR = 44100;
let outSamples = null, outSR = 44100;
let phaseMode  = 'minphase';
let wavSpecFreqs = null, wavSpecDb = null;
let outSpecFreqs = null, outSpecDb = null;

const DEFAULT_WAV_URL = '../../sample-data/1-Tchaikovsky-short.wav';
const SPEC_FMIN = 200, SPEC_FMAX = 7000;

// Two mutually-exclusive players; labels come from button's data-label attr.
const player = new AudioPlayer({ wav: 'play-wav-btn', out: 'play-btn' });

// ── Plot initialisation ───────────────────────────────────────────────
Plotly.newPlot('frf-plot', [],
  plotLayout('FRF · Magnitude', 'Frequency (Hz)', 'dB', { xaxis: { type: 'log' } }), pcfg);
Plotly.newPlot('wav-plot', [],
  plotLayout('Input Waveform',    'Time (s)',       'Amplitude'), pcfg);
Plotly.newPlot('out-plot', [],
  plotLayout('Convolved Output',  'Time (s)',       'Amplitude'), pcfg);
Plotly.newPlot('spec-plot', [],
  plotLayout('Spectrum 200–7000 Hz', 'Frequency (Hz)', 'dB'), pcfg);

// ── FRF loading — always goes to Python ───────────────────────────────
function loadFRF(input) {
  const file = input.files[0]; if (!file) return;
  setSt('frf-status', 'reading…');
  const reader = new FileReader();
  reader.onerror = () => setSt('frf-status', 'read error', 'err');
  reader.onload  = e => {
    if (!window.pyLoadFRF) {
      setSt('frf-status', 'Python not ready — try again', 'err'); return;
    }
    // Always send as Uint8Array; Python dispatches by file extension.
    window.pyLoadFRF(file.name, new Uint8Array(e.target.result));
  };
  reader.readAsArrayBuffer(file);
}

// Callbacks from Python
window.onFRFResult = function(freqs, dbs, info) {
  frfFreqs = Array.from(freqs);
  frfDb    = Array.from(dbs);
  setSt('frf-status', info, 'ok');
  plotFRF(); checkReady();
};
window.onFRFError = function(msg) {
  setSt('frf-status', 'error: ' + msg, 'err');
  frfFreqs = frfDb = null;
};

// ── WAV loading ───────────────────────────────────────────────────────
async function loadDefaultWAV() {
  setSt('wav-status', 'fetching default WAV…');
  try {
    const resp = await fetch(DEFAULT_WAV_URL);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await storeWAV(await resp.arrayBuffer(), '1-Tchaikovsky-short.wav');
  } catch (e) {
    setSt('wav-status', 'default fetch failed — load manually (' + e.message + ')');
  }
}

async function loadWAV(input) {
  const file = input.files[0]; if (!file) return;
  setSt('wav-status', 'decoding…');
  try {
    await storeWAV(await file.arrayBuffer(), file.name);
  } catch (e) {
    setSt('wav-status', 'error: ' + e.message.slice(0, 40), 'err');
    wavSamples = null;
  }
}

async function storeWAV(arrayBuffer, name) {
  const { samples, sr } = await decodeWAV(arrayBuffer);
  wavSamples = samples;  // Float32Array — zero-copy path into Python
  wavSR      = sr;
  const dur  = (samples.length / sr).toFixed(2);
  setSt('wav-status', `✓ ${name} · ${dur} s · ${(sr / 1000).toFixed(1)} kHz`, 'ok');
  document.getElementById('play-wav-btn').style.display = '';
  plotWAV();
  if (window.pyWavSpectrum) window.pyWavSpectrum(wavSamples, wavSR);
  checkReady();
}

// ── Plots ─────────────────────────────────────────────────────────────
function plotFRF() {
  if (!frfFreqs) return;
  const fin  = frfDb.filter(isFinite);
  const yMax = Math.max(6,  Math.ceil( (Math.max(...fin) + 3) / 6) * 6);
  const yMin = Math.min(-6, Math.floor((Math.min(...fin) - 3) / 6) * 6);
  Plotly.react('frf-plot', [{
    x: frfFreqs, y: frfDb, type: 'scatter', mode: 'lines',
    line: { color: COL.frf, width: 1.5 }, showlegend: false,
  }], plotLayout('FRF · Magnitude', 'Frequency (Hz)', 'dB',
    { xaxis: { type: 'log' }, yaxis: { range: [yMin, yMax] } }), pcfg);
}

function plotWAV() {
  if (!wavSamples) return;
  const n = wavSamples.length, step = Math.max(1, Math.floor(n / 5000));
  const x = [], y = [];
  for (let i = 0; i < n; i += step) { x.push(i / wavSR); y.push(wavSamples[i]); }
  Plotly.react('wav-plot', [{
    x, y, type: 'scatter', mode: 'lines',
    line: { color: COL.wav, width: 1 }, showlegend: false,
  }], plotLayout('Input Waveform', 'Time (s)', 'Amplitude'), pcfg);
}

function plotWaveform(divId, samples, sr, color, title) {
  const n = samples.length, step = Math.max(1, Math.floor(n / 5000));
  const x = [], y = [];
  for (let i = 0; i < n; i += step) { x.push(i / sr); y.push(samples[i]); }
  Plotly.react(divId, [{
    x, y, type: 'scatter', mode: 'lines',
    line: { color, width: 1 }, showlegend: false,
  }], plotLayout(title, 'Time (s)', 'Amplitude'), pcfg);
}

window.onWavSpectrumResult = function(freqs, db) {
  wavSpecFreqs = Array.from(freqs); wavSpecDb = Array.from(db); plotSpectra();
};
window.onSpectrumResult = function(freqs, db) {
  outSpecFreqs = Array.from(freqs); outSpecDb = Array.from(db); plotSpectra();
};
function plotSpectra() {
  const traces = [];
  if (wavSpecFreqs) traces.push({
    x: wavSpecFreqs, y: wavSpecDb, type: 'scatter', mode: 'lines',
    name: 'Input', line: { color: COL.wav, width: 1.5 },
  });
  if (outSpecFreqs) traces.push({
    x: outSpecFreqs, y: outSpecDb, type: 'scatter', mode: 'lines',
    name: 'Convolved', line: { color: COL.out, width: 1.5 },
  });
  if (!traces.length) return;
  Plotly.react('spec-plot', traces,
    plotLayout('Spectrum 200–7000 Hz', 'Frequency (Hz)', 'dB', {
      xaxis: { type: 'log', range: [Math.log10(SPEC_FMIN), Math.log10(SPEC_FMAX)] },
    }), pcfg);
}

// ── Convolution ───────────────────────────────────────────────────────
function checkReady() {
  document.getElementById('conv-btn').disabled = !(frfFreqs && wavSamples);
}

function setPhaseMode(mode, btn) {
  phaseMode = mode;
  document.querySelectorAll('#phase-toggle button')
    .forEach(b => b.classList.toggle('active', b === btn));
}

function runConvolution() {
  if (!frfFreqs || !wavSamples) return;
  player.stopAll();
  ['conv-btn', 'play-btn', 'save-btn'].forEach(id => {
    const el = document.getElementById(id); if (el) el.disabled = true;
  });
  setProgMsg('Computing…');
  const gainDb = +document.getElementById('gain-sl').value;
  // Defer one tick so the browser can repaint "Computing…" before blocking.
  setTimeout(() => {
    if (!window.pyConvolve) {
      clearProgMsg(); setProgMsg('Python not ready — please wait…');
      setTimeout(clearProgMsg, 4000);
      document.getElementById('conv-btn').disabled = false;
      return;
    }
    try {
      window.pyConvolve(frfFreqs, frfDb, wavSamples, wavSR, phaseMode, gainDb);
    } catch (e) {
      clearProgMsg(); setProgMsg('Error: ' + e.message.slice(0, 60));
      setTimeout(clearProgMsg, 5000);
      document.getElementById('conv-btn').disabled = false;
    }
  }, 30);
}

window.onConvolveResult = function(samplesArr, sr) {
  outSamples = new Float32Array(samplesArr); outSR = sr;
  clearProgMsg();
  document.getElementById('conv-btn').disabled = false;
  document.getElementById('result-card').style.display = '';
  document.getElementById('play-btn').disabled  = false;
  document.getElementById('save-btn').disabled  = false;
  document.getElementById('out-info').textContent =
    `${(outSamples.length / outSR).toFixed(2)} s · ` +
    `${(outSR / 1000).toFixed(1)} kHz · ` +
    `${outSamples.length.toLocaleString()} samples`;
  plotWaveform('out-plot', outSamples, outSR, COL.out, 'Convolved Output');
  if (window.pySpectrum) window.pySpectrum(outSamples, outSR);
};

window.onConvolveError = function(msg) {
  clearProgMsg(); setProgMsg('Error: ' + msg);
  setTimeout(clearProgMsg, 6000);
  document.getElementById('conv-btn').disabled = false;
};

// Python calls this to update the progress label mid-computation.
window.setProgMsg = setProgMsg;

// ── Audio playback & export ───────────────────────────────────────────
function togglePlayWAV() { player.toggle('wav', wavSamples, wavSR); }
function togglePlay()    { player.toggle('out', outSamples, outSR); }

function saveWAV() {
  if (!outSamples) return;
  const url = URL.createObjectURL(
    new Blob([encodeWAV(outSamples, outSR)], { type: 'audio/wav' })
  );
  const a = document.createElement('a');
  a.href = url;
  a.download = 'convolved_' +
    new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19) + '.wav';
  a.click();
  URL.revokeObjectURL(url);
}

// ── UI helpers ────────────────────────────────────────────────────────
function setSt(id, txt, cls) {
  const el = document.getElementById(id);
  el.textContent = txt;
  el.className   = 'file-status' + (cls ? ' ' + cls : '');
}
function setProgMsg(m)  { document.getElementById('prog-msg').textContent = m; }
function clearProgMsg() { document.getElementById('prog-msg').textContent = ''; }

// Python signals ready after registering all proxies.
// Re-trigger WAV spectrum if audio arrived before Python was ready.
window.onPythonReady = function() {
  if (wavSamples && window.pyWavSpectrum) window.pyWavSpectrum(wavSamples, wavSR);
};

// ── Boot ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', loadDefaultWAV);
