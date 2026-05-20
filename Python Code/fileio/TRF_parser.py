"""
trf_parser.py
─────────────
Parses binary .trf files (Rational Acoustics / MtxVec format).

Header format (little-endian, 110 bytes total):
  I       index
  4d      Xr, Yr, Xactual, YActual
  2s      char_str
  3d      Hz_Resolution, Start_Freq, End_Freq
  11f     fComplex, fLength, ... (9 unused floats)
  4s      caption

Data from byte 110: alternating float64 real/imag pairs if complex,
or plain float64 values if real.

Returns dict: header, columns, freq, mag, n_rows, warnings
"""

import struct
import math

_HEADER_FMT  = '<I4d2s3d11f4s'
_HEADER_SIZE = struct.calcsize(_HEADER_FMT)   # 110


def parse_trf(data):
    """Parse raw bytes of a .trf file. Returns result dict."""
    if not data or len(data) < _HEADER_SIZE + 8:
        return _blank(['file too short'])

    try:
        h = struct.unpack(_HEADER_FMT, data[:_HEADER_SIZE])
    except struct.error as e:
        return _blank(['header unpack failed: ' + str(e)])

    Hz_Resolution = h[6]
    Start_Freq    = h[7]
    End_Freq      = h[8]
    fComplex      = h[9]
    fLength       = int(h[10])
    is_complex    = round(fComplex) == 1

    header = {
        'Hz_Resolution': str(round(Hz_Resolution, 6)) + ' Hz',
        'Start_Freq':    str(round(Start_Freq, 4))    + ' Hz',
        'End_Freq':      str(round(End_Freq, 4))      + ' Hz',
        'fComplex':      'yes' if is_complex else 'no',
        'fLength':       str(fLength),
    }

    data_bytes = data[_HEADER_SIZE:]
    n_doubles  = len(data_bytes) // 8
    expected   = fLength * (2 if is_complex else 1)

    if n_doubles < expected:
        return _blank(['data section too short'])

    raw = struct.unpack('<' + str(n_doubles) + 'd', data_bytes)

    freq, mag = [], []
    for i in range(fLength):
        f = Start_Freq + i * Hz_Resolution
        if is_complex:
            re, im = raw[i * 2], raw[i * 2 + 1]
            m = math.sqrt(re * re + im * im)
        else:
            m = abs(raw[i])
        freq.append(round(f, 4))
        mag.append(round(20.0 * math.log10(max(m, 1e-12)), 4))

    return {
        'header'  : header,
        'columns' : ['Frequency [Hz]', 'Magnitude [dB]'],
        'freq'    : freq,
        'mag'     : mag,
        'n_rows'  : fLength,
        'warnings': [],
    }


def _blank(warnings):
    return {
        'header': {}, 'columns': [], 'freq': [], 'mag': [],
        'n_rows': 0,  'warnings': warnings,
    }
