"""
convolve_app.py — Convolve It entry point.
Imports DSP functions and exposes them to JavaScript.
"""

import js
from pyodide.ffi import create_proxy
from dsp import convolve, compute_spectrum

js.window.pyConvolve  = create_proxy(convolve)
js.window.pySpectrum  = create_proxy(compute_spectrum)
js.document.getElementById('loading').classList.add('gone')
