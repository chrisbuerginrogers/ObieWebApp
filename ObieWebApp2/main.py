"""
main.py -- ObieWebApp2 entry point (Pyodide).
"""

import js
from pyodide.ffi import create_proxy
from py.files import on_file_data, on_clear


def _start_trf_reader():
    js.window.obieInitPlotControls('plot', js.JSON.parse(
        '{"xLabel":"Frequency [Hz]","yLabel":"Magnitude [dB]",'
        '"xLog":true,"yLog":false,"xMin":200,"xMax":7000}'
    ))
    cfg = js.Object.new()
    cfg.dropZoneId  = 'dropzone'
    cfg.pickerBtnId = 'file-pick-btn'
    cfg.fileInputId = 'file-input'
    cfg.onData      = create_proxy(on_file_data)
    js.window.obieInitFileLoader(cfg)

    clear_btn = js.document.getElementById('clear-btn')
    if clear_btn:
        clear_btn.addEventListener('click', create_proxy(on_clear))

    from py.dom import set_status
    set_status('Drop TRF or TSV files here, or click to choose.', 'info')


# -- Dispatcher ------------------------------------------------------------
page = getattr(js.window, 'OBIE_PAGE', '')
if page == 'trf-reader':
    _start_trf_reader()
