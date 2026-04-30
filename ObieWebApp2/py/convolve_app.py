"""
convolve_app.py — Convolve It entry point.
Imports DSP functions and exposes them to JavaScript.
"""

import js
from pyodide.ffi import create_proxy
from dsp import parse_frf_csv, convolve, compute_spectrum, compute_wav_spectrum

js.window.pyParseFRF    = create_proxy(parse_frf_csv)
js.window.pyConvolve    = create_proxy(convolve)
js.window.pySpectrum    = create_proxy(compute_spectrum)
js.window.pyWavSpectrum = create_proxy(compute_wav_spectrum)
js.document.getElementById('loading').classList.add('gone')

# Signal JS that Python is ready — JS will re-trigger WAV spectrum if needed
js.window.onPythonReady()
