"""
main.py — TRF Reader entry point.

Wires Python file-parsing callbacks into the JS UI.
Uses the @when decorator for DOM event binding where possible;
create_proxy only for the file-data callback (called by JS, not a DOM event).

Flat imports work because py-config maps each shared module to VFS root:
  "../../py/files.py" → "./files.py"  (and likewise dom, trf_fileio, tsv_parser)
"""

import js
from pyscript.ffi import create_proxy
from pyscript import when
from files import on_file_data, on_clear
from dom import set_status

# ── Initialise plot + axis controls ──────────────────────────────────────
js.window.obieInitPlotControls('plot', js.JSON.parse(
    '{"xLabel":"Frequency [Hz]","yLabel":"Magnitude [dB]",'
    '"xLog":true,"yLog":false,"xMin":200,"xMax":7000}'
))

# ── Wire file loader (drag-drop + file-picker) ────────────────────────────
# obieInitFileLoader lives in JS; it needs the Python callback as a proxy.
cfg = js.Object.new()
cfg.dropZoneId  = 'dropzone'
cfg.pickerBtnId = 'file-pick-btn'
cfg.fileInputId = 'file-input'
cfg.onData      = create_proxy(on_file_data)
js.window.obieInitFileLoader(cfg)

# ── Clear button — use @when instead of addEventListener ──────────────────
@when('click', '#clear-btn')
def handle_clear(event):
    on_clear(event)

# ── Ready ─────────────────────────────────────────────────────────────────
js.document.getElementById('loading').classList.add('gone')
set_status('Drop TRF or TSV files here, or click to choose.', 'info')
