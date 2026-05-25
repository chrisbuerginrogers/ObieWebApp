"""
convolution_unitTest.py

Verify that convolve_with_frf produces valid mono and stereo output
from the sample TRF file and Tchaikovsky.wav.
"""

from test_header import ROOT, load
import numpy as np
from processing.convolution import convolve_with_frf

cfg      = load()
_SAMPLES = ROOT / cfg['data']['base_dir']
wav_path = _SAMPLES / 'Tchaikovsky.wav'
frf_path = _SAMPLES / 'Betts Strad RHV20 H_001.trf'

# ── Checks ────────────────────────────────────────────────────────────────────
def _check(label, ok):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    if not ok:
        raise AssertionError(label)

# ── Mono ──────────────────────────────────────────────────────────────────────
print("\n=== Convolution: mono ===")
audio_mono, sr = convolve_with_frf(wav_path, frf_path)

_check("returns float32",          audio_mono.dtype == np.float32)
_check("mono shape is 1-D",        audio_mono.ndim  == 1)
_check("sample rate is positive",  sr > 0)
_check("output has samples",       len(audio_mono) > 0)
_check("peak <= 0.9",              np.max(np.abs(audio_mono)) <= 0.9 + 1e-6)
_check("not silent",               np.max(np.abs(audio_mono)) > 1e-6)
_check("no NaN or Inf",            np.all(np.isfinite(audio_mono)))

# ── Stereo ────────────────────────────────────────────────────────────────────
print("\n=== Convolution: stereo ===")
audio_stereo, sr2 = convolve_with_frf(wav_path, (frf_path, frf_path))

_check("returns float32",          audio_stereo.dtype == np.float32)
_check("stereo shape is (N, 2)",   audio_stereo.ndim  == 2 and audio_stereo.shape[1] == 2)
_check("same sample rate",         sr2 == sr)
_check("same length as mono",      audio_stereo.shape[0] == len(audio_mono))
_check("peak <= 0.9",              np.max(np.abs(audio_stereo)) <= 0.9 + 1e-6)
_check("not silent",               np.max(np.abs(audio_stereo)) > 1e-6)
_check("no NaN or Inf",            np.all(np.isfinite(audio_stereo)))
_check("channels match (same FRF)", np.allclose(audio_stereo[:, 0], audio_stereo[:, 1]))

print()
