"""
dom.py
──────
Shared DOM helper functions for ObieWebApp2 pages.
"""

import js


def set_status(msg, kind='info'):
    el = js.document.getElementById('status-msg')
    if el:
        el.textContent = msg
        el.className = kind


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace('"', '&quot;'))


def render_header(header):
    box = js.document.getElementById('hdr-box')
    if not box:
        return
    if not header:
        box.innerHTML = '<span class="muted">no metadata</span>'
        return
    rows = ['<tr><td class="k">' + esc(str(k)) +
            '</td><td class="v">' + esc(str(v)) + '</td></tr>'
            for k, v in header.items()]
    box.innerHTML = '<table class="hdr-table">' + ''.join(rows) + '</table>'


def render_fileinfo(filename, size_bytes):
    el = js.document.getElementById('file-info')
    if el:
        el.innerHTML = ('<div class="name">' + esc(filename) + '</div>'
                        '<div class="meta">'
                        + js.window.obieFormatSize(size_bytes) + '</div>')
