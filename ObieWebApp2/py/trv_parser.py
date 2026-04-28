"""
trv_parser.py
─────────────
Permissive parser for TRV / TRF transfer-function data files.

The exact TRV format used by the Oberlin Acoustics workshop has not been
seen by this code yet, so the parser is intentionally flexible:

  * Comment / metadata lines starting with  #  ;  %  //  are skipped
    (and stored in the `header` dict).
  * `key: value`  or  `key = value`  lines are stored as header metadata.
  * The first non-numeric data row is treated as column names.
  * Delimiters are auto-detected (tab → comma → semicolon → whitespace).
  * 2-column data is treated as (frequency, magnitude).
  * 3-column data is treated as (frequency, magnitude, phase).
  * 4+ columns: first is frequency, rest are kept in `extra_cols`.

The result is a plain dict suitable for handing to JS/Plotly.

Designed to run unchanged on CPython 3 *and* MicroPython (PyScript-mpy).
No numpy, no f-strings, no walrus.
"""

# ───────────────────────────────────────────────────────────────────────
# Constants
# ───────────────────────────────────────────────────────────────────────
COMMENT_PREFIXES = ('#', ';', '%', '//')
DELIM_PRIORITY   = ('\t', ',', ';')   # whitespace is the fallback

# ───────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────
def _is_number(tok):
    """True if `tok` looks like a (signed, scientific) float."""
    s = tok.strip()
    if not s:
        return False
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


def _detect_delim(line):
    """Pick the most likely column delimiter for one data line."""
    for d in DELIM_PRIORITY:
        if d in line:
            return d
    return None     # → split on whitespace


def _split(line, delim):
    if delim is None:
        return line.split()
    return [c.strip() for c in line.split(delim)]


def _looks_like_metadata(line):
    """Return (key, value) if line is `key: value` or `key = value`,
    otherwise None."""
    for sep in (':', '='):
        if sep in line:
            k, v = line.split(sep, 1)
            k, v = k.strip(), v.strip()
            if k and v and not _is_number(k):
                return (k, v)
    return None


# ───────────────────────────────────────────────────────────────────────
# Main entry point
# ───────────────────────────────────────────────────────────────────────
def parse_trv(text):
    """Parse a TRV file's text. Returns a dict:
        {
          'header'     : { 'name': 'Violin #3', ... },     # metadata
          'columns'    : ['Frequency [Hz]', 'Magnitude'],  # column names
          'freq'       : [ ... ],                          # 1st col
          'mag'        : [ ... ],                          # 2nd col
          'phase'      : [ ... ] or None,                  # 3rd col if any
          'extra_cols' : [ [...], [...] ],                 # any 4+
          'n_rows'     : int,
          'warnings'   : [ '...' ],
        }
    Always returns a dict, even on malformed input — caller checks
    `n_rows == 0` to detect total failure.
    """
    if text is None:
        return _blank(['empty input'])

    header   = {}
    columns  = None
    rows     = []          # list of lists of floats
    warnings = []
    delim    = None

    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        # ── Comment / metadata ─────────────────────────────────────
        if line.startswith(COMMENT_PREFIXES):
            stripped = line.lstrip('#;%/').strip()
            kv = _looks_like_metadata(stripped)
            if kv:
                header[kv[0]] = kv[1]
            elif stripped:
                header.setdefault('_comments', []).append(stripped)
            continue

        # ── Delimiter detection (once) ─────────────────────────────
        if delim is None:
            delim = _detect_delim(line)

        toks = _split(line, delim)
        toks = [t for t in toks if t != '']
        if not toks:
            continue

        # ── If no numbers yet → treat as header row ────────────────
        if not _is_number(toks[0]):
            kv = _looks_like_metadata(line)
            if kv and not rows:
                header[kv[0]] = kv[1]
                continue
            if columns is None and not rows:
                columns = toks
                continue
            warnings.append('skipped non-numeric row: ' + line[:60])
            continue

        # ── Numeric data row ───────────────────────────────────────
        try:
            nums = [float(t) for t in toks]
        except ValueError:
            warnings.append('parse error: ' + line[:60])
            continue
        rows.append(nums)

    # ── Assemble columns ───────────────────────────────────────────
    if not rows:
        return _blank(warnings + ['no numeric data found'])

    n_cols = max(len(r) for r in rows)
    cols   = [[] for _ in range(n_cols)]
    for r in rows:
        for i in range(n_cols):
            cols[i].append(r[i] if i < len(r) else float('nan'))

    if columns is None or len(columns) < n_cols:
        defaults = ['Frequency [Hz]', 'Magnitude', 'Phase [deg]']
        columns = [defaults[i] if i < 3 else 'Col ' + str(i + 1)
                   for i in range(n_cols)]

    out = {
        'header'    : header,
        'columns'   : columns,
        'freq'      : cols[0],
        'mag'       : cols[1] if n_cols >= 2 else [],
        'phase'     : cols[2] if n_cols >= 3 else None,
        'extra_cols': cols[3:] if n_cols > 3 else [],
        'n_rows'    : len(rows),
        'warnings'  : warnings,
    }
    return out


# ───────────────────────────────────────────────────────────────────────
def _blank(warnings):
    return {
        'header': {}, 'columns': [], 'freq': [], 'mag': [],
        'phase': None, 'extra_cols': [], 'n_rows': 0,
        'warnings': warnings,
    }
