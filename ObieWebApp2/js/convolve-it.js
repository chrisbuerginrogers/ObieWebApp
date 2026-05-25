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

const DEFAULT_WAV_URL = '../../sample-data/1-Tchaikovsky-short.wav';
const SPEC_FMIN = 200, SPEC_FMAX = 7000;

// Two mutually-exclusive players; labels come from button's data-label attr.
const player = new AudioPlayer({ wav: 'play-wav-btn', out: 'play-btn' });

// ── Plot initialisation ───────────────────────────────────────────────
Plotly.newPlot('frf-plot', [],
  plotLayout('FRF · Magnitude', 'Frequency (Hz)', 'dB', { xaxis: { type: 'log' } }), pcfg);
Plotly.newPlot('wav-plot', [],
  plotLayout('Input · Spectrogram',  'Time (s)', 'Frequency (Hz)'), pcfg);
Plotly.newPlot('out-plot', [],
  plotLayout('Convolved Output',     'Time (s)', 'Amplitude'),      pcfg);
Plotly.newPlot('spec-plot', [],
  plotLayout('Output · Spectrogram', 'Time (s)', 'Frequency (Hz)'), pcfg);

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
  if (window.pyWavSpectrogram) window.pyWavSpectrogram(wavSamples, wavSR);
  checkReady();
}

// ── Plots ─────────────────────────────────────────────────────────────
function plotSpectrogram(divId, times, freqs, flatZ, nFreqs, nTimes, title) {
  const arr = Array.from(flatZ);
  const z   = [];
  for (let i = 0; i < nFreqs; i++)
    z.push(arr.slice(i * nTimes, (i + 1) * nTimes));
  Plotly.react(divId, [{
    x: times, y: freqs, z,
    type: 'heatmap',
    colorscale: 'Plasma',
    showscale: false,
    zsmooth: 'fast',
    hoverinfo: 'skip',
  }], plotLayout(title, 'Time (s)', 'Frequency (Hz)', {
    margin: { l: 50, r: 12, t: 28, b: 38 },
  }), pcfg);
}

window.onWavSpectrogramResult = function(times, freqs, flatZ, nFreqs, nTimes) {
  const nF = +nFreqs, nT = +nTimes;
  plotSpectrogram('wav-plot', Array.from(times), Array.from(freqs),
                  flatZ, nF, nT, 'Input · Spectrogram');
};
window.onOutSpectrogramResult = function(times, freqs, flatZ, nFreqs, nTimes) {
  const nF = +nFreqs, nT = +nTimes;
  plotSpectrogram('spec-plot', Array.from(times), Array.from(freqs),
                  flatZ, nF, nT, 'Output · Spectrogram');
};

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

function plotWaveform(divId, samples, sr, color, title) {
  const n = samples.length, step = Math.max(1, Math.floor(n / 5000));
  const x = [], y = [];
  for (let i = 0; i < n; i += step) { x.push(i / sr); y.push(samples[i]); }
  Plotly.react(divId, [{
    x, y, type: 'scatter', mode: 'lines',
    line: { color, width: 1 }, showlegend: false,
  }], plotLayout(title, 'Time (s)', 'Amplitude'), pcfg);
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
  if (window.pyOutSpectrogram) window.pyOutSpectrogram(outSamples, outSR);
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

// ── Output device selection ───────────────────────────────────────────
async function enumerateOutputDevices() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const sel = document.getElementById('out-device-sel');
    if (!sel) return;
    const savedId = window.ciSavedOutputDeviceId || '';
    sel.innerHTML = '<option value="">Default output</option>';
    devices
      .filter(d => d.kind === 'audiooutput' && d.deviceId !== 'default')
      .forEach(d => {
        const o = document.createElement('option');
        o.value       = d.deviceId;
        o.textContent = d.label || `Speaker (${d.deviceId.slice(0, 8)}…)`;
        if (d.deviceId === savedId) o.selected = true;
        sel.appendChild(o);
      });
    if (savedId) await player.setSinkId(savedId);
  } catch (e) {
    console.warn('Output device enumeration failed:', e.message);
  }
}

document.getElementById('out-device-sel')?.addEventListener('change', async function () {
  await player.setSinkId(this.value);
});

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
  if (wavSamples && window.pyWavSpectrogram) window.pyWavSpectrogram(wavSamples, wavSR);
};

// ── Boot ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  enumerateOutputDevices();
  loadDefaultWAV();
});
