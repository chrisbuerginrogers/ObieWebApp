"""
plot_bridge.py
──────────────
Thin Python → JavaScript bridge for plotting.

JS exposes:
  window.obieShowData(x, y, xLabel, yLabel)
  window.obieClearPlot()

We keep this file *very* small so main.py / trv_reader_app.py remain
high-level and readable.

Compatible with both PyScript-Pyodide and PyScript-MicroPython.
"""

import js


def _to_jslist(seq):
    """Convert a Python list of floats to a JS Array.
    On both Pyodide and MicroPython PyScript, passing a Python list
    directly to a JS function yields a JS Array, but using to_js where
    available is more robust for nested data.
    """
    try:
        from pyscript.ffi import to_js   # works on both interpreters
        return to_js(list(seq))
    except ImportError:
        return list(seq)


def show(parsed):
    """Push the parsed TRV dict onto the page's Plotly canvas."""
    if not parsed or parsed.get('n_rows', 0) == 0:
        js.window.obieClearPlot()
        return

    cols   = parsed.get('columns') or []
    x_lbl  = cols[0] if len(cols) > 0 else 'Frequency [Hz]'
    y_lbl  = cols[1] if len(cols) > 1 else 'Magnitude'

    js.window.obieShowData(
        _to_jslist(parsed.get('freq', [])),
        _to_jslist(parsed.get('mag',  [])),
        x_lbl, y_lbl,
    )


def clear():
    js.window.obieClearPlot()
