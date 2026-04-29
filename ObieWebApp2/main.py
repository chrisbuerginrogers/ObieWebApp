"""
main.py -- ObieWebApp2 entry point (Pyodide).
JS (plot-controls.js) owns trace storage and the file-list UI.
Python handles file reading, binary parsing, and status/header display.
"""

import js
from pyodide.ffi import create_proxy, to_js
from py.trf_parser import parse_trf


# -- DOM helpers -----------------------------------------------------------
def _set_status(msg, kind='info'):
    el = js.document.getElementById('status-msg')
    if el:
        el.textContent = msg
        el.className = kind


def _esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace('"', '&quot;'))


def _render_header(header):
    box = js.document.getElementById('hdr-box')
    if not box:
        return
    if not header:
        box.innerHTML = '<span class="muted">no metadata</span>'
        return
    rows = ['<tr><td class="k">' + _esc(str(k)) +
            '</td><td class="v">' + _esc(str(v)) + '</td></tr>'
            for k, v in header.items()]
    box.innerHTML = '<table class="hdr-table">' + ''.join(rows) + '</table>'


def _render_fileinfo(filename, size_bytes):
    el = js.document.getElementById('file-info')
    if el:
        el.innerHTML = ('<div class="name">' + _esc(filename) + '</div>'
                        '<div class="meta">'
                        + js.window.obieFormatSize(size_bytes) + '</div>')


# -- TRF reader ------------------------------------------------------------
def _on_trf_data(filename, size_bytes, js_uint8array):
    _render_fileinfo(filename, size_bytes)
    if js_uint8array is None:
        _set_status('Could not read: ' + filename, 'err')
        return

    raw    = bytes(js_uint8array.to_py())
    parsed = parse_trf(raw)
    _render_header(parsed.get('header', {}))

    n = parsed.get('n_rows', 0)
    if n == 0:
        warns = parsed.get('warnings') or []
        _set_status(warns[0] if warns else 'No data: ' + filename, 'err')
        return

    label = filename.rsplit('/', 1)[-1].rsplit('\\', 1)[-1]
    if label.lower().endswith('.trf'):
        label = label[:-4]

    js.window.obieAddTrace(to_js(parsed['freq']), to_js(parsed['mag']), label)
    _set_status('Loaded ' + label, 'ok')


def _on_clear(event):
    js.window.obieClearPlot()
    box = js.document.getElementById('hdr-box')
    if box:
        box.innerHTML = '<span class="muted">no file loaded</span>'
    _set_status('Drop TRF files here, or click to choose.', 'info')


def _start_trf_reader():
    js.window.obieInitPlotControls('plot', js.JSON.parse(
        '{"xLabel":"Frequency [Hz]","yLabel":"Magnitude [dB]",'
        '"xLog":true,"yLog":true,"xMin":200,"xMax":7000}'
    ))
    cfg = js.Object.new()
    cfg.dropZoneId  = 'dropzone'
    cfg.pickerBtnId = 'file-pick-btn'
    cfg.fileInputId = 'file-input'
    cfg.onData      = create_proxy(_on_trf_data)
    js.window.obieInitFileLoader(cfg)

    clear_btn = js.document.getElementById('clear-btn')
    if clear_btn:
        clear_btn.addEventListener('click', create_proxy(_on_clear))

    _set_status('Drop TRF files here, or click to choose.', 'info')


# -- Dispatcher ------------------------------------------------------------
page = getattr(js.window, 'OBIE_PAGE', '')
if page == 'trf-reader':
    _start_trf_reader()
