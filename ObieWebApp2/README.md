# ObieWebApp 2

A modular browser-based toolkit for analyzing the vibrational
characteristics of violins. Built for the **Oberlin Acoustics Workshop**.

Everything runs **locally in the browser** — no uploads, no server-side
work — using **MicroPython** via [PyScript](https://pyscript.net/) and
[Plotly](https://plotly.com/javascript/) for charts.

---

## Structure

```
ObieWebApp2/
├── index.html              ← Landing page
├── main.py                 ← Top-level dispatcher (~25 lines, only high-level calls)
├── README.md
├── css/                    ← All styles
│   ├── theme.css           ← Shared light-brown theme
│   ├── index.css           ← Landing-page-specific
│   └── trv-reader.css      ← TRV-reader-specific
├── js/                     ← All JavaScript
│   ├── plotly-helpers.js   ← Theme + layout factory (stateless)
│   ├── plot-controls.js    ← Plot state, axis controls, show-data API
│   └── file-loader.js      ← Drop-zone + file-picker helper
├── py/                     ← All MicroPython modules (each < 200 lines)
│   ├── __init__.py
│   ├── trv_parser.py       ← Permissive TRV parser
│   ├── plot_bridge.py      ← Python → JS plot bridge
│   └── trv_reader_app.py   ← TRV-reader page wiring
├── html/                   ← All tool pages (everything except index.html)
│   └── trv-reader.html
└── sample-data/
    └── violin_test.trv     ← Synthetic file for trying the reader
```

Adding a new tool = drop `py/<tool>_app.py`, `html/<tool>.html`, plus
optional CSS/JS, and add one `elif` to `main.py`.

---

## Running locally

PyScript needs the files served over HTTP (file:// won't work). From
the project root:

```bash
python3 -m http.server 8000
```

Then visit <http://localhost:8000/>.

> Recommended browser: **Chrome** or **Edge**. The first load will
> download MicroPython (~200 KB) and is cached afterwards.

---

## Trying the TRV Reader

1. Open the landing page → click **TRV File Reader**.
2. Drop `sample-data/violin_test.trv` (or any TRV file) onto the drop
   zone, or click **Choose file…**.
3. The frequency response renders as an orange line on the plot.
4. Use the side panel to toggle **log/linear** axes (default: log/log)
   or set explicit min/max ranges.

---

## TRV file format

The bundled parser is **permissive** and handles common conventions:

- **Comment lines** starting with `#`, `;`, `%`, or `//` are skipped
  (and stored as header metadata).
- **`key: value`** or **`key = value`** lines populate the header
  panel.
- **Auto-detected delimiters**: tab → comma → semicolon → whitespace.
- **2 columns** → `(frequency, magnitude)`.
- **3 columns** → `(frequency, magnitude, phase)`.
- **4+ columns** → first is frequency; the rest are kept in
  `extra_cols` for future tools.

If your real TRV files use a stricter or quirkier format, edit
`py/trv_parser.py` (it's <180 lines and self-contained).

---

## Adding the next tool

1. Create `py/<tool>_app.py` with a `start()` function.
2. Create `html/<tool>.html` (copy `trv-reader.html` as a template;
   just change the title, page id, and file mapping).
3. Add an `elif page == "<tool>": ...` branch in `main.py`.
4. Add a `<a class="tool-card" href="./html/<tool>.html">…</a>` to
   `index.html`.
