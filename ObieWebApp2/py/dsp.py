"""
dsp.py — DSP core for Convolve It.
Exposes: parse_frf_csv(), convolve(), compute_spectrum(), compute_wav_spectrum()
"""

import numpy as np
from math import isfinite


def parse_frf_csv(text_js):
    """
    Parse a FRF CSV file (two columns: Frequency_Hz, FRF_dB).
    Fires onFRFResult(freqs, dbs, info_str) or onFRFError(msg).
    """
    import js
    try:
        lines = str(text_js).strip().split('\n')
        freqs, dbs = [], []
        for ln in lines:
            ln = ln.strip()
            if not ln or (ln[0].isalpha() and ln[0] not in 'eE'):
                continue   # skip header rows
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
            js.window.onFRFError('Too few valid rows — check file format')
            return
        info = f'✓ {len(freqs)} pts · {freqs[0]:.0f}–{freqs[-1]:.0f} Hz'
        from pyodide.ffi import to_js
        js.window.onFRFResult(to_js(freqs), to_js(dbs), info)
    except Exception as exc:
        js.window.onFRFError(str(exc)[:80])



def _build_min_phase(H_mag: np.ndarray, N: int) -> np.ndarray:
    """
    Complex rfft-format filter (length N//2+1) with magnitude == H_mag
    and minimum-phase response reconstructed via the real cepstrum method.
    """
    eps = 1e-12
    log_m = np.log(np.maximum(H_mag, eps))

    # Hermitian-symmetric log-magnitude of length N
    if N % 2 == 0:
        full_log = np.concatenate([log_m, log_m[-2:0:-1]])
    else:
        full_log = np.concatenate([log_m, log_m[:0:-1]])

    cepstrum = np.fft.ifft(full_log).real

    # Causal window: fold negative quefrencies onto positive side
    win = np.zeros(N)
    win[0] = 1.0
    win[1 : N // 2] = 2.0
    if N % 2 == 0:
        win[N // 2] = 1.0

    return np.exp(np.fft.rfft(win * cepstrum))   # |result| ≈ H_mag


def convolve(frf_freqs_js, frf_db_js, wav_js,
             sr_val, phase_mode_js, gain_db_js):
    """
    Frequency-domain convolution: Y(f) = H(f) · X(f)

    Parameters (all passed from JavaScript)
    ---------------------------------------
    frf_freqs_js : iterable – FRF frequency points in Hz
    frf_db_js    : iterable – FRF magnitude in dB
    wav_js       : iterable – audio samples (float ±1)
    sr_val       : int      – sample rate
    phase_mode_js: str      – 'minphase' | 'zerophase'
    gain_db_js   : float    – output trim gain in dB
    """
    import js
    try:
        frf_f  = np.array(list(frf_freqs_js), dtype=np.float64)
        frf_db = np.array(list(frf_db_js),    dtype=np.float64)
        wav    = np.array(list(wav_js),        dtype=np.float64)
        sr     = int(sr_val)
        mode   = str(phase_mode_js)
        gain   = 10.0 ** (float(gain_db_js) / 20.0)
        N      = len(wav)

        js.window.setProgMsg('FFT of input signal…')
        X     = np.fft.rfft(wav)
        freqs = np.fft.rfftfreq(N, 1.0 / sr)

        js.window.setProgMsg('Interpolating FRF…')
        frf_mag = np.power(10.0, frf_db / 20.0)

        # Log-space interpolation — better for acoustic frequency data
        log_f = np.log10(np.maximum(frf_f,   1e-3))
        log_q = np.log10(np.maximum(freqs,   1e-3))
        H_mag = np.interp(log_q, log_f, frf_mag,
                          left=frf_mag[0], right=frf_mag[-1])
        H_mag *= gain

        js.window.setProgMsg(f'Building {mode} filter…')
        H = _build_min_phase(H_mag, N) if mode == 'minphase' \
            else H_mag.astype(np.complex128)

        js.window.setProgMsg('Multiplying spectra…')
        Y = X * H

        js.window.setProgMsg('IFFT…')
        y = np.fft.irfft(Y, N)

        # Normalise to 0.95, then apply gain trim and clip to ±1
        peak = np.max(np.abs(y))
        if peak > 1e-12:
            y = y / peak * 0.95
        y = np.clip(y * gain, -1.0, 1.0)

        from pyodide.ffi import to_js
        js.window.onConvolveResult(to_js(y.tolist()), sr)

    except Exception as exc:
        js.window.onConvolveError(str(exc)[:120])
        raise


def compute_spectrum(samples_js, sr_val):
    """Hann-windowed magnitude spectrum in dB — fires onSpectrumResult."""
    _spectrum_inner(samples_js, sr_val, 'onSpectrumResult')


def compute_wav_spectrum(samples_js, sr_val):
    """Same as compute_spectrum but fires onWavSpectrumResult."""
    _spectrum_inner(samples_js, sr_val, 'onWavSpectrumResult')


def _spectrum_inner(samples_js, sr_val, callback_name):
    import js
    try:
        samples = np.array(list(samples_js), dtype=np.float64)
        sr      = int(sr_val)
        if len(samples) < 64:
            return
        win   = np.hanning(len(samples))
        mag   = np.abs(np.fft.rfft(samples * win)) * 2.0 / win.sum()
        freqs = np.fft.rfftfreq(len(samples), 1.0 / sr)
        db    = 20.0 * np.log10(mag + 1e-12)
        from pyodide.ffi import to_js
        getattr(js.window, callback_name)(to_js(freqs.tolist()), to_js(db.tolist()))
    except Exception as exc:
        print(f'[dsp.{callback_name}]', exc)
