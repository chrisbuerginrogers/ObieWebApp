"""
dsp.py — DSP core for ObieWebApp2 (Convolve It tool).

Public functions
----------------
  load_frf(filename_js, data_js)   — parse .trf/.csv FRF  → onFRFResult
  convolve(frf_f, frf_db, wav, …)  — Y(f)=H(f)X(f)        → onConvolveResult
  compute_spectrum(samples, sr)    — Hann-windowed dB       → onSpectrumResult
  compute_wav_spectrum(samples, sr)                         → onWavSpectrumResult
"""

import js
import numpy as np
from math import isfinite
from pyscript.ffi import to_js
from trf_fileio import parse_trf


# ── FRF CSV parser ────────────────────────────────────────────────────────

def _parse_csv(text: str):
    """Parse two-column FRF CSV. Returns (freqs, dbs, info) or raises."""
    freqs, dbs = [], []
    for ln in text.strip().split('\n'):
        ln = ln.strip()
        if not ln or (ln[0].isalpha() and ln[0] not in 'eE'):
            continue
        parts = ln.split(',')
        if len(parts) >= 2:
            try:
                f, d = float(parts[0]), float(parts[1])
                if f > 0 and isfinite(f) and isfinite(d):
                    freqs.append(f)
                    dbs.append(d)
            except ValueError:
                pass
    if len(freqs) < 4:
        raise ValueError('Too few valid rows — check CSV format (Frequency,dB)')
    info = f'✓ {len(freqs)} pts · {freqs[0]:.0f}–{freqs[-1]:.0f} Hz'
    return freqs, dbs, info


# ── FRF loader — dispatches by extension ──────────────────────────────────

def load_frf(filename_js, data_js):
    """
    Parse an FRF file from raw bytes.
      .trf  → binary parser  (trf_fileio.parse_trf)
      .csv  → CSV text parser (_parse_csv)
    Fires window.onFRFResult(freqs, dbs, info) or window.onFRFError(msg).
    """
    try:
        filename = str(filename_js)
        ext      = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        raw      = bytes(data_js.to_py())

        if ext == 'trf':
            result = parse_trf(raw)
            if result['n_rows'] == 0:
                warns = result.get('warnings') or []
                js.window.onFRFError(warns[0] if warns else 'No data in TRF file')
                return
            freqs = result['freq']
            dbs   = result['mag']
            n     = result['n_rows']
            end   = freqs[0] + (n - 1) * (freqs[-1] - freqs[0]) / max(n - 1, 1)
            info  = f'✓ {n} pts · {freqs[0]:.0f}–{freqs[-1]:.0f} Hz'
        elif ext == 'csv':
            freqs, dbs, info = _parse_csv(raw.decode('utf-8', errors='replace'))
        else:
            js.window.onFRFError(f'Unsupported: .{ext} — use .trf or .csv')
            return

        js.window.onFRFResult(to_js(freqs), to_js(dbs), info)

    except Exception as exc:
        js.window.onFRFError(str(exc)[:120])


# ── Min-phase reconstruction ──────────────────────────────────────────────

def _build_min_phase(H_mag: np.ndarray, N: int) -> np.ndarray:
    eps   = 1e-12
    log_m = np.log(np.maximum(H_mag, eps))
    full  = (np.concatenate([log_m, log_m[-2:0:-1]]) if N % 2 == 0
             else np.concatenate([log_m, log_m[:0:-1]]))
    cep   = np.fft.ifft(full).real
    win   = np.zeros(N)
    win[0] = 1.0; win[1:N//2] = 2.0
    if N % 2 == 0: win[N//2] = 1.0
    return np.exp(np.fft.rfft(win * cep))


# ── Convolution ────────────────────────────────────────────────────────────

def convolve(frf_freqs_js, frf_db_js, wav_js, sr_val, phase_mode_js, gain_db_js):
    """Y(f) = H(f) · X(f). All heavy lifting in Python/numpy."""
    try:
        frf_f  = np.asarray(frf_freqs_js.to_py(), dtype=np.float64)
        frf_db = np.asarray(frf_db_js.to_py(),    dtype=np.float64)
        wav    = np.asarray(wav_js.to_py(),        dtype=np.float64)
        sr     = int(sr_val)
        mode   = str(phase_mode_js)
        gain   = 10.0 ** (float(gain_db_js) / 20.0)
        N      = len(wav)

        js.window.setProgMsg('FFT of input signal…')
        X     = np.fft.rfft(wav)
        freqs = np.fft.rfftfreq(N, 1.0 / sr)

        js.window.setProgMsg('Interpolating FRF onto FFT bins…')
        frf_mag = np.power(10.0, frf_db / 20.0)
        log_f   = np.log10(np.maximum(frf_f,  1e-3))
        log_q   = np.log10(np.maximum(freqs,  1e-3))
        H_mag   = np.interp(log_q, log_f, frf_mag,
                            left=frf_mag[0], right=frf_mag[-1]) * gain

        js.window.setProgMsg(f'Building {mode} filter…')
        H = (_build_min_phase(H_mag, N) if mode == 'minphase'
             else H_mag.astype(np.complex128))

        js.window.setProgMsg('IFFT…')
        y = np.fft.irfft(X * H, N)

        peak = np.max(np.abs(y))
        if peak > 1e-12:
            y = y / peak * 0.95
        y = np.clip(y, -1.0, 1.0)

        js.window.onConvolveResult(to_js(y), sr)

    except Exception as exc:
        js.window.onConvolveError(str(exc)[:120])
        raise


# ── Spectrum ───────────────────────────────────────────────────────────────

def compute_spectrum(samples_js, sr_val):
    _spectrum(samples_js, sr_val, 'onSpectrumResult')

def compute_wav_spectrum(samples_js, sr_val):
    _spectrum(samples_js, sr_val, 'onWavSpectrumResult')

def _spectrum(samples_js, sr_val, cb):
    try:
        sig   = np.asarray(samples_js.to_py(), dtype=np.float64)
        sr    = int(sr_val)
        if len(sig) < 64:
            return
        win   = np.hanning(len(sig))
        mag   = np.abs(np.fft.rfft(sig * win)) * 2.0 / win.sum()
        freqs = np.fft.rfftfreq(len(sig), 1.0 / sr)
        db    = 20.0 * np.log10(mag + 1e-12)
        getattr(js.window, cb)(to_js(freqs), to_js(db))
    except Exception as exc:
        print(f'[dsp._spectrum → {cb}]', exc)
