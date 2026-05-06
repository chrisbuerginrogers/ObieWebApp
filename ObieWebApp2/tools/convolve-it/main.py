"""
main.py — Convolve It entry point.

Exposes four Python functions to JS via create_proxy.
Uses @when for the gain slider readout (DOM event — no proxy needed).
"""

import js
from pyscript.ffi import create_proxy
from pyscript import when
from dsp import load_frf, convolve, compute_spectrum, compute_wav_spectrum

js.window.pyLoadFRF    = create_proxy(load_frf)
js.window.pyConvolve   = create_proxy(convolve)
js.window.pySpectrum   = create_proxy(compute_spectrum)
js.window.pyWavSpectrum = create_proxy(compute_wav_spectrum)


@when('input', '#gain-sl')
def update_gain_display(event):
    v    = int(js.document.getElementById('gain-sl').value)
    sign = '+' if v >= 0 else ''
    js.document.getElementById('gain-disp').textContent = f'{sign}{v} dB'


js.document.getElementById('loading').classList.add('gone')
js.window.onPythonReady()
