"""
main.py — Convolve It entry point.
"""

import js
from pyscript.ffi import create_proxy
from pyscript import when
from config import configure, load, save
from dsp import load_frf, convolve, compute_wav_spectrogram, compute_out_spectrogram

configure('obieWebApp_convolveIt', {
    "settings": {
        "phase_mode": "minphase",
        "gain":       0,
    },
    "audio": {
        "output_device_id": "",
    },
})

cfg = load()

js.window.pyLoadFRF     = create_proxy(load_frf)
js.window.pyConvolve    = create_proxy(convolve)
js.window.pyWavSpectrogram = create_proxy(compute_wav_spectrogram)
js.window.pyOutSpectrogram = create_proxy(compute_out_spectrogram)


# ── Persist settings on every control change ──────────────────────────────
def _active_phase_mode():
    btns = js.document.querySelectorAll('#phase-toggle button')
    for i in range(btns.length):
        btn = btns.item(i)
        if btn.classList.contains('active'):
            s     = btn.getAttribute('onclick') or ''
            start = s.find("'") + 1
            end   = s.find("'", start)
            if start > 0 and end > start:
                return s[start:end]
    return 'minphase'


def _save_settings(_event=None):
    gain_el = js.document.getElementById('gain-sl')
    dev_el  = js.document.getElementById('out-device-sel')
    save('settings', {
        'phase_mode': _active_phase_mode(),
        'gain':       int(gain_el.value) if gain_el else 0,
    })
    save('audio', {
        'output_device_id': dev_el.value if dev_el else '',
    })


_save_proxy = create_proxy(_save_settings)

_btns = js.document.querySelectorAll('#phase-toggle button')
for _i in range(_btns.length):
    _btns.item(_i).addEventListener('click', _save_proxy)

_el = js.document.getElementById('gain-sl')
if _el:
    _el.addEventListener('change', _save_proxy)

_el = js.document.getElementById('out-device-sel')
if _el:
    _el.addEventListener('change', _save_proxy)


# ── Restore saved settings ────────────────────────────────────────────────
_s = cfg['settings']

# Pass saved output device ID to JS so enumerateOutputDevices() can pre-select it
js.window.ciSavedOutputDeviceId = cfg['audio']['output_device_id']

# Gain slider + display
_gain_el = js.document.getElementById('gain-sl')
if _gain_el:
    _gain_el.value = str(_s['gain'])
    _sign = '+' if _s['gain'] >= 0 else ''
    _disp = js.document.getElementById('gain-disp')
    if _disp:
        _disp.textContent = f"{_sign}{_s['gain']} dB"

# Phase mode — call setPhaseMode so JS internal state matches
_saved_mode = _s['phase_mode']
_btns = js.document.querySelectorAll('#phase-toggle button')
for _i in range(_btns.length):
    _btn = _btns.item(_i)
    _onclick = _btn.getAttribute('onclick') or ''
    if f"'{_saved_mode}'" in _onclick:
        js.window.setPhaseMode(_saved_mode, _btn)
        break


# ── Gain slider readout (live update on drag) ─────────────────────────────
@when('input', '#gain-sl')
def update_gain_display(event):
    v    = int(js.document.getElementById('gain-sl').value)
    sign = '+' if v >= 0 else ''
    js.document.getElementById('gain-disp').textContent = f'{sign}{v} dB'


js.document.getElementById('loading').classList.add('gone')
js.window.onPythonReady()
