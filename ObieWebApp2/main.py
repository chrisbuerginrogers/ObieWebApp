"""
main.py — ObieWebApp2 top-level entry point.

Each tool's HTML page sets `window.OBIE_PAGE` to a short page name and
loads this file. We dispatch to the right per-tool entry function.

Real work lives in the per-tool modules under  py/.
"""

import sys
# Make sure the virtual-fs root is on the import path so `from py.foo
# import ...` works under both Pyodide and MicroPython.
if '/' not in sys.path:
    sys.path.insert(0, '/')
if '.' not in sys.path:
    sys.path.insert(0, '.')

import js


def run():
    page = getattr(js.window, 'OBIE_PAGE', '')
    if not page:
        return                              # landing page — nothing to do

    if page == 'trv-reader':
        from py.trv_reader_app import start
        start()
    # ── Add new tools here, one elif per page ──
    # elif page == 'modal-analysis':
    #     from py.modal_analysis_app import start; start()


run()
