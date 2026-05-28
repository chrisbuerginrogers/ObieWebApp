"""
main.py — Acquire tool entry point.
Registers Python functions as JS-callable proxies.
"""

import js
from pyscript.ffi import create_proxy
from config import configure, load, save
from acquire_logic import (
    apply_settings as _apply_settings_impl,
    init_positions,
    process_audio,
    delete_last_hit,
    clear_position,
    jump_to_position,
    update_cutoff,
    export_wav,
    export_trf,
    stop_audio,
    arm,
) 

configure('obieWebApp_acquire', {
    "run": {
        "threshold":      0.05,
        "cutoff_hz":      10000.0,
        "pre_trig_s":          0.01,
        "post_trig_s":         0.30,
        "time_cutoff_s":       0.30,
        "mic_time_cutoff_s":   0.30,
        "taps":           5,
        "positions":      12,
        "prefix":         "H",
        "mic_cal":        1.0,
        "ham_cal":        1.0,
        "swap_channels":  False,
        "soundcard":      "",
        "instrument":     "",
    },
})

cfg = load()


def _save_run_settings(*_args):  # *_args absorbs the browser event passed by addEventListener
    def _get(eid):
        el = js.document.getElementById(eid)
        return el.value if el else ''

    def _checked(eid):
        el = js.document.getElementById(eid)
        return bool(el.checked) if el else False

    save('run', {
        'threshold':     float(_get('inp-threshold')   or 0.05),
        'cutoff_hz':     float(_get('inp-cutoff')      or 10000),
        'pre_trig_s':    float(_get('inp-pre')         or 0.01),
        'post_trig_s':   float(_get('inp-post')        or 0.30),
        'time_cutoff_s':     float(_get('inp-time-cutoff')     or 0.30),
        'mic_time_cutoff_s': float(_get('inp-mic-time-cutoff') or 0.30),
        'taps':          int(float(_get('inp-taps')    or 5)),
        'positions':     int(float(_get('inp-positions') or 12)),
        'prefix':        _get('inp-prefix')    or 'H',
        'mic_cal':       float(_get('inp-mic-cal') or 1.0),
        'ham_cal':       float(_get('inp-ham-cal') or 1.0),
        'swap_channels': _checked('inp-swap-channels'),
        'soundcard':     _get('inp-soundcard') or '',
        'instrument':    _get('inp-instrument') or '',
    })


def apply_settings(*args, **kwargs):
    _apply_settings_impl(*args, **kwargs)
    _save_run_settings()


_save_proxy = create_proxy(_save_run_settings)
_el = js.document.getElementById('inp-instrument')
if _el:
    _el.addEventListener('change', _save_proxy)


def _set(eid, val):
    el = js.document.getElementById(eid)
    if el is not None and val is not None:
        el.value = str(val)


_r = cfg['run']
_set('inp-threshold',   _r['threshold'])
_set('inp-cutoff',      _r['cutoff_hz'])
_set('inp-pre',         _r['pre_trig_s'])
_set('inp-post',        _r['post_trig_s'])
_set('inp-time-cutoff',     _r.get('time_cutoff_s',     0.30))
_set('inp-mic-time-cutoff', _r.get('mic_time_cutoff_s', 0.30))
_set('inp-taps',        _r['taps'])
_set('inp-positions',   _r['positions'])
_set('inp-prefix',      _r['prefix'])
_set('inp-mic-cal',     _r['mic_cal'])
_set('inp-ham-cal',     _r['ham_cal'])
_el_swap = js.document.getElementById('inp-swap-channels')
if _el_swap is not None:
    _el_swap.checked = bool(_r.get('swap_channels', False))
_set('inp-soundcard',   _r['soundcard'])
_set('inp-instrument',  _r.get('instrument', ''))

# ── Expose Python functions to JS ─────────────────────────────────────────────
js.window.pyApplySettings    = create_proxy(apply_settings)
js.window.pyInitPositions    = create_proxy(init_positions)
js.window.pyProcessAudio     = create_proxy(process_audio)
js.window.pyDeleteLastHit    = create_proxy(delete_last_hit)
js.window.pyClearPosition    = create_proxy(clear_position)
js.window.pyJumpToPosition   = create_proxy(jump_to_position)
js.window.pyUpdateCutoff     = create_proxy(update_cutoff)
js.window.pyExportWAV        = create_proxy(export_wav)
js.window.pyExportTRF        = create_proxy(export_trf)
js.window.pyStopAudio        = create_proxy(stop_audio)
js.window.pyArm              = create_proxy(arm)

if js.window.onPyReady:
    js.window.onPyReady()
js.document.getElementById("loading").classList.add("gone")
