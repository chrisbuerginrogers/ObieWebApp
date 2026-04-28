"""
trv_reader_app.py
─────────────────
The TRV-reader page's Python entry point.

Responsibilities:
  1. Initialize the JS plot + plot controls on the page.
  2. Wire the file loader (drag-drop / picker) so that when the user
     selects a TRV file, we parse it and push the data to the plot.
  3. Render the parsed header metadata and any warnings to the DOM.

Each of those steps is one short function — most of the heavy lifting
lives in py/trv_parser.py and py/plot_bridge.py.
"""

import js
from py.trv_parser import parse_trv
from py import plot_bridge

try:
    from pyscript.ffi import create_proxy
except ImportError:                          # CPython fallback for tests
    def create_proxy(f): return f


PLOT_DIV = 'plot'


# ─── Status helper ─────────────────────────────────────────────────────
def _set_status(msg, kind='info'):
    el = js.document.getElementById('status-msg')
    if el is None:
        return
    el.textContent = msg
    el.className = kind         # 'ok' | 'err' | 'info'


# ─── Render header metadata into the side panel ────────────────────────
def _render_header(header):
    box = js.document.getElementById('hdr-box')
    if box is None:
        return
    if not header:
        box.innerHTML = '<span class="muted">no metadata</span>'
        return

    rows_html = []
    for k, v in header.items():
        if k == '_comments':
            for c in v:
                rows_html.append(
                    '<tr><td class="k">#</td><td class="v">' + _esc(c) + '</td></tr>'
                )
        else:
            rows_html.append(
                '<tr><td class="k">' + _esc(str(k)) +
                '</td><td class="v">' + _esc(str(v)) + '</td></tr>'
            )
    box.innerHTML = '<table class="hdr-table">' + ''.join(rows_html) + '</table>'


def _esc(s):
    """Minimal HTML escape (avoids needing the `html` stdlib in mpy)."""
    return (s.replace('&', '&amp;').replace('<', '&lt;')
              .replace('>', '&gt;').replace('"', '&quot;'))


# ─── File-info panel ───────────────────────────────────────────────────
def _render_fileinfo(filename, size_bytes):
    el = js.document.getElementById('file-info')
    if el is None:
        return
    pretty_size = js.window.obieFormatSize(size_bytes)
    el.innerHTML = (
        '<div class="name">' + _esc(filename) + '</div>'
        '<div class="meta">' + pretty_size + '</div>'
    )


# ─── File-loaded callback ──────────────────────────────────────────────
def on_file_text(filename, size_bytes, text):
    """Called from JS once a file's text has been read."""
    _render_fileinfo(filename, size_bytes)

    if text is None:
        _set_status('Could not read file.', 'err')
        plot_bridge.clear()
        return

    _set_status('Parsing ' + filename + ' …', 'info')
    parsed = parse_trv(text)

    n = parsed.get('n_rows', 0)
    if n == 0:
        _set_status('No numeric data found in file.', 'err')
        _render_header(parsed.get('header', {}))
        plot_bridge.clear()
        return

    _render_header(parsed.get('header', {}))
    plot_bridge.show(parsed)

    warns = parsed.get('warnings') or []
    suffix = (' · ' + str(len(warns)) + ' warning(s)') if warns else ''
    _set_status('Loaded ' + str(n) + ' rows' + suffix, 'ok')


# ─── Page entry point ──────────────────────────────────────────────────
def start():
    """Called by main.py once the DOM is ready."""
    # 1. Initialize the plot with default LOG/LOG axes
    js.window.obieInitPlotControls(PLOT_DIV, js.JSON.parse(
        '{"xLabel":"Frequency [Hz]","yLabel":"Magnitude",'
        '"xLog":true,"yLog":true}'
    ))

    # 2. Wire file loader (drag-drop + picker)
    cfg = js.Object.new()
    cfg.dropZoneId  = 'dropzone'
    cfg.pickerBtnId = 'file-pick-btn'
    cfg.fileInputId = 'file-input'
    cfg.onText      = create_proxy(on_file_text)
    js.window.obieInitFileLoader(cfg)

    _set_status('Drop a TRV file here, or click to choose one.', 'info')
