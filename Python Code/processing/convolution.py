"""
convolution.py

Convolve a WAV file with one FRF/AvC/AvR (mono output) or two (stereo output).

Supported FRF formats: .AvC (complex), .AvR (magnitude), .trf (magnitude dB)

For complex FRFs (.AvC) both magnitude and phase are used.
For magnitude-only formats (.AvR, .trf) zero phase is assumed, which gives a
symmetric (linear-phase) impulse response — good enough for timbral shaping.

Usage:
    from processing.convolution import convolve_with_frf

    # Mono
    audio, sr = convolve_with_frf('Tchaikovsky.wav', 'Violin.AvC')

    # Stereo
    audio, sr = convolve_with_frf('Tchaikovsky.wav', ('Left.AvC', 'Right.AvC'))
"""

import numpy as np
from pathlib import Path
from scipy.signal import fftconvolve
import scipy.io.wavfile as _wavfile


def _load_frf(path):
    """
    Load an FRF file. Returns (freqs_hz, H_complex) where H_complex is a
    complex64 array — magnitude-only files get zero imaginary part.
    """
    path = Path(path)
    ext  = path.suffix.lower()

    if ext == '.avc':
        from fileio.avc_fileio import parse_avc
        d = parse_avc(path.read_bytes())
        return d['freqs'], d['H_complex'].astype(np.complex128)

    elif ext == '.avr':
        from fileio.avc_fileio import parse_avr
        d = parse_avr(path.read_bytes())
        return d['freqs'], d['data'].astype(np.complex128)

    elif ext == '.trf':
        from fileio.trf_fileio import parse_trf
        d = parse_trf(path.read_bytes())
        freqs   = np.array(d['freq'],  dtype=np.float64)
        mag_lin = 10.0 ** (np.array(d['mag'], dtype=np.float64) / 20.0)
        return freqs, mag_lin.astype(np.complex128)

    else:
        raise ValueError(f"Unsupported FRF format '{path.suffix}' — use .AvC, .AvR, or .trf")


def _frf_to_ir(freqs, H_complex, sample_rate, ir_length):
    """
    Build a real-valued impulse response from a band-limited FRF.

    Interpolates H onto the full rfft frequency grid for ir_length samples,
    IFFTs to the time domain, and applies a Hann window to taper ringing.
    The result is normalised to unit peak.
    """
    fft_freqs = np.fft.rfftfreq(ir_length, d=1.0 / sample_rate)

    H_real = np.interp(fft_freqs, freqs, H_complex.real, left=0.0, right=0.0)
    H_imag = np.interp(fft_freqs, freqs, H_complex.imag, left=0.0, right=0.0)

    ir = np.fft.irfft(H_real + 1j * H_imag, n=ir_length)
    ir *= np.hanning(ir_length)

    peak = np.max(np.abs(ir))
    if peak > 0:
        ir /= peak
    return ir.astype(np.float32)


def _read_wav(path):
    """Read a WAV file and return (audio_float32_mono, sample_rate)."""
    sr, data = _wavfile.read(str(path))

    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.uint8:
        data = (data.astype(np.float32) - 128.0) / 128.0
    else:
        data = data.astype(np.float32)

    if data.ndim > 1:
        data = data.mean(axis=1)

    peak = np.max(np.abs(data))
    if peak > 0:
        data /= peak
    return data, sr


def convolve_with_frf(wav_path, frf_paths, ir_length=8192):
    """
    Convolve a WAV file with one or two FRF files.

    Parameters
    ----------
    wav_path   : str or Path  — source audio file (.wav)
    frf_paths  : str/Path           → mono output
                 (left_path, right_path) → stereo float32 (N, 2) output
    ir_length  : impulse response length in samples
                 8192 ≈ 170 ms @ 48 kHz, which captures violin body resonances well

    Returns
    -------
    (audio_out, sample_rate)
    audio_out is float32 ndarray, shape (N,) mono or (N, 2) stereo, peak ≤ 0.9
    """
    audio, sr = _read_wav(wav_path)

    if isinstance(frf_paths, (str, Path)):
        freqs, H = _load_frf(frf_paths)
        ir  = _frf_to_ir(freqs, H, sr, ir_length)
        out = fftconvolve(audio, ir)[:len(audio)].astype(np.float32)
    else:
        left_path, right_path = frf_paths
        freqs_l, H_l = _load_frf(left_path)
        freqs_r, H_r = _load_frf(right_path)
        ir_l = _frf_to_ir(freqs_l, H_l, sr, ir_length)
        ir_r = _frf_to_ir(freqs_r, H_r, sr, ir_length)
        ch_l = fftconvolve(audio, ir_l)[:len(audio)].astype(np.float32)
        ch_r = fftconvolve(audio, ir_r)[:len(audio)].astype(np.float32)
        out  = np.column_stack([ch_l, ch_r])

    peak = np.max(np.abs(out))
    if peak > 0:
        out = (out / peak * 0.9).astype(np.float32)

    return out, sr
