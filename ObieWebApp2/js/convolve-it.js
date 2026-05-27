/* ─────────────────────────────────────────────────────────────────────
 * convolve-it.js  —  UI wiring for the Convolve It tool
 *
 * Requires (loaded before this file):
 *   plotly-theme.js   — cssVar(), plotLayout(), pcfg, COL
 *   audio.js          — encodeWAV(), AudioPlayer
 *
 * All file parsing, WAV decoding, and DSP run in Python (dsp.py / files.py).
 * This file manages: playback state, plot rendering, and UI interactions.
 * ───────────────────────────────────────────────────────────────────── */

// ── Playback state (JS-only — needed by AudioPlayer) ─────────────────
let wavSamples = null, wavSR = 44100;
let outSamples = null, outSR = 44100;
let frfLoaded  = false;

const DEFAULT_WAV_URL = '../../sample-data/1-Tchaikovsky-short.wav';

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

// ── FRF loading ───────────────────────────────────────────────────────
function loadFRF(input) {
  const file = input.files[0]; if (!file) return;
  setSt('frf-status', 'reading…');
  const reader = new FileReader();
  reader.onerror = () => setSt('frf-status', 'read error', 'err');
  reader.onload  = e => {
    if (!window.pyLoadFRF) {
      setSt('frf-status', 'Python not ready — try again', 'err'); return;
    }
    window.pyLoadFRF(file.name, new Uint8Array(e.target.result));
  };
  reader.readAsArrayBuffer(file);
}

window.onFRFResult = function(freqs, dbs, info) {
  frfLoaded = true;
  setSt('frf-status', info, 'ok');
  plotFRF(Array.from(freqs), Array.from(dbs));
  checkReady();
};
window.onFRFError = function(msg) {
  frfLoaded = false;
  setSt('frf-status', 'error: ' + msg, 'err');
  checkReady();
};

// ── WAV loading ───────────────────────────────────────────────────────
async function loadDefaultWAV() {
  setSt('wav-status', 'fetching default WAV…');
  try {
    const resp = await fetch(DEFAULT_WAV_URL);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    window.pyLoadWAV('1-Tchaikovsky-short.wav', new Uint8Array(await resp.arrayBuffer()));
  } catch (e) {
    setSt('wav-status', 'default fetch failed — load manually (' + e.message + ')');
  }
}

async function loadWAV(input) {
  const file = input.files[0]; if (!file) return;
  setSt('wav-status', 'loading…');
  try {
    window.pyLoadWAV(file.name, new Uint8Array(await file.arrayBuffer()));
  } catch (e) {
    setSt('wav-status', 'error: ' + e.message.slice(0, 40), 'err');
  }
}

window.onWavResult = function(samplesArr, sr, info) {
  wavSamples = new Float32Array(samplesArr);
  wavSR      = +sr;
  setSt('wav-status', info, 'ok');
  document.getElementById('play-wav-btn').style.display = '';
  checkReady();
};
window.onWavError = function(msg) {
  wavSamples = null;
  setSt('wav-status', 'error: ' + msg, 'err');
  checkReady();
};

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
  plotSpectrogram('wav-plot', Array.from(times), Array.from(freqs),
                  flatZ, +nFreqs, +nTimes, 'Input · Spectrogram');
};
window.onOutSpectrogramResult = function(times, freqs, flatZ, nFreqs, nTimes) {
  plotSpectrogram('spec-plot', Array.from(times), Array.from(freqs),
                  flatZ, +nFreqs, +nTimes, 'Output · Spectrogram');
};

function plotFRF(freqs, dbs) {
  const fin  = dbs.filter(isFinite);
  const yMax = Math.max(6,  Math.ceil( (Math.max(...fin) + 3) / 6) * 6);
  const yMin = Math.min(-6, Math.floor((Math.min(...fin) - 3) / 6) * 6);
  Plotly.react('frf-plot', [{
    x: freqs, y: dbs, type: 'scatter', mode: 'lines',
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
  document.getElementById('conv-btn').disabled = !(frfLoaded && wavSamples !== null);
}

function runConvolution() {
  if (!wavSamples) return;
  player.stopAll();
  ['conv-btn', 'play-btn', 'save-btn'].forEach(id => {
    const el = document.getElementById(id); if (el) el.disabled = true;
  });
  setProgMsg('Computing…');
  const gainDb = +document.getElementById('gain-sl').value;
  setTimeout(() => {
    if (!window.pyConvolve) {
      clearProgMsg(); setProgMsg('Python not ready — please wait…');
      setTimeout(clearProgMsg, 4000);
      document.getElementById('conv-btn').disabled = false;
      return;
    }
    try {
      window.pyConvolve(gainDb);
    } catch (e) {
      clearProgMsg(); setProgMsg('Error: ' + e.message.slice(0, 60));
      setTimeout(clearProgMsg, 5000);
      document.getElementById('conv-btn').disabled = false;
    }
  }, 30);
}

window.onConvolveResult = function(samplesArr, sr) {
  outSamples = new Float32Array(samplesArr); outSR = +sr;
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
};

window.onConvolveError = function(msg) {
  clearProgMsg(); setProgMsg('Error: ' + msg);
  setTimeout(clearProgMsg, 6000);
  document.getElementById('conv-btn').disabled = false;
};

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

// Python signals ready — trigger default WAV load now that pyLoadWAV is registered.
window.onPythonReady = function() {
  loadDefaultWAV();
};

// ── Boot ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  enumerateOutputDevices();
});
