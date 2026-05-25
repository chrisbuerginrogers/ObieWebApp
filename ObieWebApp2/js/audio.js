/* ─────────────────────────────────────────────────────────────────────
 * audio.js  —  WAV decode · encode · playback
 *
 * Exports (global):
 *   decodeWAV(arrayBuffer)  → Promise<{ samples: Float32Array, sr: number }>
 *   encodeWAV(samples, sr)  → ArrayBuffer   (16-bit PCM mono)
 *   AudioPlayer             – class for managing ≤N exclusive audio streams
 * ───────────────────────────────────────────────────────────────────── */

/**
 * Decode any browser-supported audio format via AudioContext.
 * Returns the mono (channel 0) Float32Array and the sample rate.
 * The AudioContext is closed immediately after decoding to free resources.
 */
async function decodeWAV(arrayBuffer) {
  const ctx = new AudioContext();
  const buf = await ctx.decodeAudioData(arrayBuffer);
  await ctx.close();
  return { samples: buf.getChannelData(0), sr: buf.sampleRate };
}

/**
 * Encode a Float32Array as a 16-bit PCM mono WAV ArrayBuffer.
 * Suitable for Blob → download or AudioContext playback.
 */
function encodeWAV(samples, sr) {
  const dataLen = samples.length * 2;           // 16-bit = 2 bytes/sample
  const buf = new ArrayBuffer(44 + dataLen);
  const v   = new DataView(buf);

  function str(off, s) {
    for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i));
  }

  str(0,  'RIFF');  v.setUint32(4,  36 + dataLen, true);
  str(8,  'WAVE');
  str(12, 'fmt ');  v.setUint32(16, 16,  true);
                    v.setUint16(20, 1,   true);    // PCM
                    v.setUint16(22, 1,   true);    // mono
                    v.setUint32(24, sr,  true);    // sample rate
                    v.setUint32(28, sr * 2, true); // byte rate
                    v.setUint16(32, 2,   true);    // block align
                    v.setUint16(34, 16,  true);    // bits/sample
  str(36, 'data');  v.setUint32(40, dataLen, true);

  let off = 44;
  for (let i = 0; i < samples.length; i++) {
    v.setInt16(off, Math.max(-1, Math.min(1, samples[i])) * 0x7FFF, true);
    off += 2;
  }
  return buf;
}

/**
 * Manages multiple named, mutually-exclusive audio streams.
 *
 * Usage:
 *   const player = new AudioPlayer({ wav: 'play-wav-btn', out: 'play-btn' });
 *   player.toggle('wav', samples, sr);   // play or stop
 *   player.stop('out');
 *   player.stopAll();
 *
 * Button text is updated automatically via the btnId registered at construction.
 */
class AudioPlayer {
  constructor(btnIds) {
    // btnIds: { key: elementId }
    this._tracks = {};
    this._ctx    = null;
    this._sinkId = '';   // '' = browser default

    for (const [key, btnId] of Object.entries(btnIds)) {
      this._tracks[key] = { source: null, playing: false, btnId };
    }
  }

  _getCtx() {
    if (!this._ctx) {
      this._ctx = new (window.AudioContext || window.webkitAudioContext)();
      if (this._sinkId && typeof this._ctx.setSinkId === 'function')
        this._ctx.setSinkId(this._sinkId).catch(() => {});
    }
    if (this._ctx.state === 'suspended') this._ctx.resume();
    return this._ctx;
  }

  /** Route output to a specific device. Pass '' for the browser default. */
  async setSinkId(deviceId) {
    this._sinkId = deviceId || '';
    if (this._ctx && typeof this._ctx.setSinkId === 'function')
      await this._ctx.setSinkId(this._sinkId).catch(e =>
        console.warn('AudioPlayer.setSinkId:', e.message));
  }

  /** Start playing key. Stops all other tracks first. */
  start(key, samples, sr) {
    this.stopAll();
    const ctx = this._getCtx();
    const buf = ctx.createBuffer(1, samples.length, sr);
    buf.copyToChannel(
      samples instanceof Float32Array ? samples : new Float32Array(samples), 0
    );
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.connect(ctx.destination);
    src.onended = () => {
      this._tracks[key].playing = false;
      this._tracks[key].source  = null;
      this._updateBtn(key);
    };
    src.start();
    this._tracks[key].source  = src;
    this._tracks[key].playing = true;
    this._updateBtn(key);
  }

  stop(key) {
    const t = this._tracks[key]; if (!t) return;
    if (t.source) { try { t.source.stop(); } catch (_) {} t.source = null; }
    t.playing = false;
    this._updateBtn(key);
  }

  stopAll() {
    for (const key of Object.keys(this._tracks)) this.stop(key);
  }

  toggle(key, samples, sr) {
    this._tracks[key]?.playing ? this.stop(key) : this.start(key, samples, sr);
  }

  isPlaying(key) { return !!this._tracks[key]?.playing; }

  /** Override button text per state. labels: { play, stop } */
  _updateBtn(key) {
    const { btnId, playing } = this._tracks[key];
    const btn = document.getElementById(btnId); if (!btn) return;
    // Derive label from existing text: strip ▶/■ prefix, swap symbol.
    const base = btn.dataset.label || btn.textContent.replace(/^[▶■]\s*/, '');
    btn.dataset.label = base;
    btn.textContent   = (playing ? '■ Stop ' : '▶ Play ') + base;
    btn.classList.toggle('active', playing);
  }
}
