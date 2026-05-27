/* ─────────────────────────────────────────────────────────────────────
 * explore.js  —  Explore FRF tool
 *
 * Requires (loaded before this file):
 *   plotly-theme.js   — cssVar(), pcfg
 *   audio.js          — AudioPlayer
 * ───────────────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  // ── Colour palettes ────────────────────────────────────────────────────
  const PALETTES = {
    default:  ['#ff6f00','#2196f3','#4caf50','#e91e63','#9c27b0','#00bcd4','#ff5722','#8bc34a','#ffc107','#607d8b'],
    warm:     ['#b71c1c','#c62828','#d32f2f','#e64a19','#f57c00','#ff8f00','#f9a825','#f57f17'],
    cool:     ['#0d47a1','#1565c0','#0277bd','#00838f','#006064','#1b5e20','#33691e','#827717'],
    contrast: ['#000000','#e53935','#1e88e5','#43a047','#fb8c00','#8e24aa','#00acc1','#6d4c41'],
  };
  const BAND_COLORS = ['#e74c3c','#e67e22','#2ecc71','#3498db','#9b59b6','#1abc9c','#f39c12'];

  const BAND_PRESETS = {
    violin: {
      label: 'Violin Modes',
      bands: [
        {label:'A0',     f_lo:264,  f_hi:290 },
        {label:'CBR',    f_lo:380,  f_hi:420 },
        {label:'B1-',    f_lo:393,  f_hi:470 },
        {label:'B1+',    f_lo:473,  f_hi:593 },
        {label:'Transition Hill', f_lo:800, f_hi:1300},
        {label:'Bridge Hill',     f_lo:1750, f_hi:3000},
        {label:'Upper Hill',      f_lo:3000, f_hi:7000},
      ],
    },
    claude: {
      label: 'Claude Bands',
      bands: [
        {label:'Low',     f_lo:200,  f_hi:400 },
        {label:'Low-Mid', f_lo:400,  f_hi:900 },
        {label:'Mid',     f_lo:900,  f_hi:1600},
        {label:'Hi-Mid',  f_lo:1600, f_hi:3300},
        {label:'High',    f_lo:3300, f_hi:7000},
      ],
    },
  };

  const INTERPRET_REGIONS = [
    {label:'A0',               f_lo:264,  f_hi:290,  color:'#e74c3c'},
    {label:'CBR',              f_lo:380,  f_hi:420,  color:'#e67e22'},
    {label:'B1-',              f_lo:393,  f_hi:470,  color:'#f1c40f'},
    {label:'B1+',              f_lo:473,  f_hi:593,  color:'#2ecc71'},
    {label:'Transition Hill',  f_lo:800,  f_hi:1300, color:'#3498db'},
    {label:'Bridge Hill',      f_lo:1750, f_hi:3000, color:'#9b59b6'},
    {label:'Upper Hill',       f_lo:3000, f_hi:7000, color:'#e91e63'},
  ];
  const TYPICAL_RANGES = [
    {mode:'A0',               range:'264–290 Hz',   avg:'276 Hz'},
    {mode:'CBR',              range:'380–420 Hz',   avg:'400 Hz'},
    {mode:'B1-',              range:'393–470 Hz',   avg:'444 Hz'},
    {mode:'B1+',              range:'473–593 Hz',   avg:'541 Hz'},
    {mode:'Transition Hill',  range:'800–1300 Hz',  avg:''},
    {mode:'Bridge Hill',      range:'1750–3000 Hz', avg:''},
    {mode:'Upper Hill',       range:'3000–7000 Hz', avg:''},
  ];
  const STRING_MODES = [
    {label:'G0', freq:196}, {label:'D0', freq:294},
    {label:'A0', freq:440}, {label:'E0', freq:659},
  ];

  // ── State ──────────────────────────────────────────────────────────────
  let _datasets  = [];
  let _undoStack = [];
  let _nextId    = 0;
  let _palette   = PALETTES.default;
  let _templates = [];
  let _lists     = [];
  let _customBands = null;

  const _S = {
    xLog: true, xMin: 200, xMax: 7000,
    yLog: false, yMin: null, yMax: null,
    yDbRange: 38,
    smoothing: 0,
    normalize: false,
    bandPreset: '',
    lineWidth: 1.5,
  };

  // ── Helpers ────────────────────────────────────────────────────────────
  function $(id) { return document.getElementById(id); }
  function _esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ── Undo ───────────────────────────────────────────────────────────────
  function _saveUndo() {
    _undoStack.push(_datasets.map(d => ({...d, freqs:[...d.freqs], mags:[...d.mags]})));
    if (_undoStack.length > 20) _undoStack.shift();
    _syncUndoBtn();
  }
  function _syncUndoBtn() {
    const b = $('undo-btn'); if (b) b.disabled = !_undoStack.length;
  }

  // ── Smoothing (binary-search, O(n log n)) ─────────────────────────────
  function _smooth(freqs, mags, semitones) {
    if (!semitones) return mags;
    const ratio = Math.pow(2, semitones / 12);
    const n = freqs.length;
    const out = new Array(n);
    for (let i = 0; i < n; i++) {
      const fLo = freqs[i] / ratio, fHi = freqs[i] * ratio;
      let lo = 0, hi = n;
      while (lo < hi) { const m = (lo+hi)>>1; freqs[m] < fLo ? lo=m+1 : hi=m; }
      const s = lo; lo = 0; hi = n;
      while (lo < hi) { const m = (lo+hi)>>1; freqs[m] <= fHi ? lo=m+1 : hi=m; }
      const e = lo;
      let sum = 0; for (let j = s; j < e; j++) sum += mags[j];
      out[i] = e > s ? sum / (e - s) : mags[i];
    }
    return out;
  }

  // ── Normalize (shift max to 0 dB) ─────────────────────────────────────
  function _norm(mags) {
    const maxV = Math.max(...mags.filter(isFinite));
    if (!isFinite(maxV)) return mags;
    return mags.map(v => v - maxV);
  }

  // ── Band computation ───────────────────────────────────────────────────
  function _computeBands(freqs, mags, bands) {
    return bands.map(b => {
      const pts = freqs.reduce((acc, f, i) => {
        if (f >= b.f_lo && f <= b.f_hi && isFinite(mags[i])) acc.push([f, mags[i]]);
        return acc;
      }, []);
      if (!pts.length) return {...b, avg_db: 0, centroid: (b.f_lo + b.f_hi) / 2};
      const avg = pts.reduce((s, [,m]) => s + m, 0) / pts.length;
      let wsum = 0, wtot = 0;
      pts.forEach(([f, m]) => { const w = Math.pow(10, m / 20); wsum += f * w; wtot += w; });
      return {...b, avg_db: avg, centroid: wtot > 0 ? wsum / wtot : (b.f_lo + b.f_hi) / 2};
    });
  }

  // ── Render main plot ──────────────────────────────────────────────────
  function render() {
    const plotTraces = [];
    const bandShapes = [], bandTraces = [];

    _datasets.filter(d => d.visible).forEach(d => {
      let mags = _smooth(d.freqs, d.mags, _S.smoothing);
      if (_S.normalize) mags = _norm(mags);
      plotTraces.push({
        x: d.freqs, y: mags, type:'scatter', mode:'lines',
        name: d.name, line:{color:d.color, width:_S.lineWidth}, showlegend:false,
      });
    });
    if (!plotTraces.length)
      plotTraces.push({x:[], y:[], type:'scatter', mode:'lines', showlegend:false});

    // Bands
    const activeBands = _S.bandPreset === 'custom' && _customBands
      ? _customBands
      : (_S.bandPreset && BAND_PRESETS[_S.bandPreset]) ? BAND_PRESETS[_S.bandPreset].bands : null;

    if (activeBands && plotTraces[0].x.length > 0) {
      const ref = plotTraces[0];
      const bd  = _computeBands(ref.x, ref.y, activeBands);
      window._exploreLastBandData = bd;
      bd.forEach((b, i) => {
        const c = BAND_COLORS[i % BAND_COLORS.length];
        bandShapes.push({type:'rect', xref:'x', yref:'paper', x0:b.f_lo, x1:b.f_hi, y0:0, y1:1, fillcolor:c, opacity:0.1, line:{width:0}});
        bandTraces.push({x:[b.f_lo,b.f_hi], y:[b.avg_db,b.avg_db], type:'scatter', mode:'lines', line:{color:c,width:2.5}, showlegend:false, hovertemplate:`<b>${_esc(b.label)}</b><br>Avg: ${b.avg_db.toFixed(1)} dB<extra></extra>`});
      });
      _renderBandTable(bd);
    } else {
      window._exploreLastBandData = null;
      _renderBandTable(null);
    }

    // Y range
    const allMags = plotTraces.flatMap(t => t.y.filter(isFinite));
    let yRange;
    if (_S.yMin != null && _S.yMax != null) {
      yRange = [_S.yMin, _S.yMax];
    } else if (allMags.length) {
      const maxY = Math.max(...allMags);
      yRange = [maxY - _S.yDbRange, maxY + 2];
    }

    const border = cssVar('--border'), text = cssVar('--text');
    const xRange = (_S.xMin != null && _S.xMax != null)
      ? (_S.xLog ? [Math.log10(Math.max(_S.xMin,1)), Math.log10(_S.xMax)] : [_S.xMin, _S.xMax])
      : undefined;

    const layout = {
      paper_bgcolor:'transparent', plot_bgcolor:'transparent',
      font:{color:text, family:'inherit', size:12},
      margin:{l:65, r:16, t:12, b:50},
      showlegend:false, autosize:true,
      xaxis:{title:'Frequency (Hz)', type:_S.xLog?'log':'linear', range:xRange, gridcolor:border, zerolinecolor:border, linecolor:border},
      yaxis:{title:'Magnitude (dB)', type:_S.yLog?'log':'linear', range:yRange, gridcolor:border, zerolinecolor:border, linecolor:border},
      shapes: bandShapes,
    };

    Plotly.react('explore-plot', [...plotTraces, ...bandTraces], layout,
      {responsive:true, displayModeBar:true, displaylogo:false, modeBarButtonsToRemove:['sendDataToCloud']});
  }

  // ── Band table ─────────────────────────────────────────────────────────
  function _renderBandTable(bd) {
    const el = $('band-table'); if (!el) return;
    if (!bd || !bd.length) { el.innerHTML = '<span class="muted-txt">Select a band preset</span>'; return; }
    el.innerHTML = '<table class="band-tbl"><thead><tr><th>Band</th><th>Avg dB</th><th>Centroid</th></tr></thead><tbody>'
      + bd.map((b, i) => {
        const c = BAND_COLORS[i % BAND_COLORS.length];
        return `<tr><td><span class="band-dot" style="background:${c}"></span>${_esc(b.label)}</td><td>${b.avg_db.toFixed(1)}</td><td>${b.centroid.toFixed(0)} Hz</td></tr>`;
      }).join('') + '</tbody></table>';
  }

  // ── Dataset list ───────────────────────────────────────────────────────
  function _renderList() {
    const box = $('dataset-list'); if (!box) return;
    if (!_datasets.length) {
      box.innerHTML = '<div class="ds-empty">Drop FRF files here or use Browse / Search</div>';
      return;
    }
    box.innerHTML = _datasets.map(d =>
      `<div class="ds-row${d.visible?'':' ds-hidden'}" data-id="${d.id}">
        <input type="checkbox" class="ds-vis" data-id="${d.id}"${d.visible?' checked':''}>
        <span class="ds-swatch" data-id="${d.id}" style="background:${d.color}" title="Change colour"></span>
        <span class="ds-label" title="${_esc(d.name)}">${_esc(d.name)}</span>
        <button class="ds-play-btn" data-id="${d.id}" title="Convolve and play">▶</button>
      </div>`
    ).join('');

    box.querySelectorAll('.ds-vis').forEach(cb => cb.addEventListener('change', e => {
      const d = _datasets.find(x => x.id === +e.target.dataset.id);
      if (d) { d.visible = e.target.checked; _renderList(); render(); }
    }));
    box.querySelectorAll('.ds-swatch').forEach(sw => sw.addEventListener('click', e => {
      const d = _datasets.find(x => x.id === +e.target.dataset.id); if (!d) return;
      const inp = document.createElement('input'); inp.type='color'; inp.value=d.color;
      inp.addEventListener('input', ev => { d.color=ev.target.value; _renderList(); render(); });
      inp.click();
    }));
    box.querySelectorAll('.ds-play-btn').forEach(btn => btn.addEventListener('click', e => {
      _playDataset(+e.target.dataset.id);
    }));
  }

  // ── Play dataset ───────────────────────────────────────────────────────
  function _playDataset(id) {
    const d = _datasets.find(x => x.id === id); if (!d) return;
    if (!window.pyExploreConvolve) { alert('Python not ready — wait a moment.'); return; }
    const st = $('explore-status');
    if (st) st.textContent = `Convolving ${d.name}…`;
    window.pyExploreConvolve(new Float64Array(d.freqs), new Float64Array(d.mags));
  }

  window.onExploreConvolveResult = function(samplesArr, sr) {
    const samples = new Float32Array(samplesArr);
    const ctx = new AudioContext();
    const buf = ctx.createBuffer(1, samples.length, +sr);
    buf.copyToChannel(samples, 0);
    const src = ctx.createBufferSource();
    src.buffer = buf; src.connect(ctx.destination); src.start();
    src.onended = () => ctx.close();
    const st = $('explore-status');
    if (st) { st.textContent = 'Playing…'; src.onended = () => { ctx.close(); st.textContent=''; }; }
  };
  window.onExploreConvolveError = function(msg) {
    const st = $('explore-status');
    if (st) { st.textContent = 'Error: ' + msg; setTimeout(() => st.textContent='', 5000); }
  };

  // ── Dataset ops ────────────────────────────────────────────────────────
  window.expSeeAll   = () => { _saveUndo(); _datasets.forEach(d=>d.visible=true);  _renderList(); render(); };
  window.expSeeNone  = () => { _saveUndo(); _datasets.forEach(d=>d.visible=false); _renderList(); render(); };
  window.expReduce   = () => { _saveUndo(); _datasets=_datasets.filter(d=>d.visible); _renderList(); render(); };
  window.expClearAll = () => { _saveUndo(); _datasets=[]; _renderList(); render(); };
  window.expUndo     = () => {
    if (!_undoStack.length) return;
    _datasets = _undoStack.pop(); _syncUndoBtn(); _renderList(); render();
  };

  // ── Toolbar: New Test ─────────────────────────────────────────────────
  window.expNewTest = function(e) {
    e.stopPropagation();
    const m = $('new-test-menu'); if (!m) return;
    m.classList.toggle('open');
    document.body.addEventListener('click', () => m.classList.remove('open'), {once:true});
  };
  window.expPickTemplate = function(idx) {
    const t = _templates[idx]; if (!t) return;
    alert(`You picked template: ${t.name}\n\n${t.description}`);
    if (t.settings) {
      const s = t.settings;
      if (s.x_min  != null) _S.xMin     = s.x_min;
      if (s.x_max  != null) _S.xMax     = s.x_max;
      if (s.x_log  != null) _S.xLog     = s.x_log;
      if (s.y_log  != null) _S.yLog     = s.y_log;
      if (s.y_db_range != null) _S.yDbRange = s.y_db_range;
      if (s.smoothing  != null) _S.smoothing = s.smoothing;
      if (s.normalize  != null) _S.normalize = s.normalize;
      _syncControls();
      render();
    }
    $('new-test-menu').classList.remove('open');
  };

  window.expScratch = function() {
    alert('You pressed: Scratch\n\nThis starts a blank scratch session.');
  };

  // ── Toolbar: Settings ─────────────────────────────────────────────────
  window.expSettings = function(e) {
    e.stopPropagation();
    const m = $('settings-menu'); if (!m) return;
    m.classList.toggle('open');
    document.body.addEventListener('click', () => m.classList.remove('open'), {once:true});
  };
  window.expPreferences = function() {
    window.open('preferences.html', '_blank');
    $('settings-menu').classList.remove('open');
  };
  window.expLiveView = function() {
    window.open('liveview.html', '_blank');
    $('settings-menu').classList.remove('open');
  };

  // ── Toolbar: misc buttons ─────────────────────────────────────────────
  window.expFun            = () => alert('You pressed: Fun');
  window.expShortcuts      = () => alert('You pressed: Shortcuts');
  window.expHelp           = () => alert('You pressed: Help');
  window.expGettingStarted = () => alert('You pressed: Getting Started');

  // ── File ops ──────────────────────────────────────────────────────────
  window.expSearch = async function() {
    if (!window.showDirectoryPicker) {
      alert('Folder picker not supported in this browser.\nUse Browse to open individual files.');
      return;
    }
    try {
      const dir  = await window.showDirectoryPicker();
      const exts = new Set(['.trf','.trv','.avc','.avr','.csv']);
      const found = [];
      async function walk(dh) {
        for await (const [name, h] of dh.entries()) {
          if (h.kind === 'file') {
            const ext = name.substring(name.lastIndexOf('.')).toLowerCase();
            if (exts.has(ext)) found.push({handle:h, name});
          } else await walk(h);
        }
      }
      await walk(dir);
      if (!found.length) { alert('No TRF / AvC / AvR / CSV files found in that folder.'); return; }
      if (!window.pyExploreLoadFile) { alert('Python not ready — try again.'); return; }
      for (const f of found)
        window.pyExploreLoadFile(f.name, new Uint8Array(await (await f.handle.getFile()).arrayBuffer()));
    } catch(e) { if (e.name !== 'AbortError') console.warn('expSearch:', e); }
  };

  window.expBrowse = function() {
    const inp = document.createElement('input');
    inp.type = 'file'; inp.multiple = true; inp.accept = '.trf,.trv,.avc,.avr,.csv';
    inp.addEventListener('change', async () => {
      if (!window.pyExploreLoadFile) { alert('Python not ready — try again.'); return; }
      for (const f of inp.files)
        window.pyExploreLoadFile(f.name, new Uint8Array(await f.arrayBuffer()));
    });
    inp.click();
  };

  window.expLists = function() {
    const modal = $('lists-modal'); if (!modal) return;
    const box = modal.querySelector('.lists-content');
    if (box) {
      box.innerHTML = _lists.length
        ? _lists.map(l =>
            `<div class="list-item">
              <div class="list-name">${_esc(l.name)}</div>
              <div class="list-desc">${_esc(l.description||'')}</div>
              <ul class="list-files">${(l.files||[]).map(f=>`<li>${_esc(f)}</li>`).join('')}</ul>
            </div>`
          ).join('')
        : '<p class="muted-txt">No predefined lists found.</p>';
    }
    modal.classList.add('open');
  };
  window.expCloseLists = () => $('lists-modal')?.classList.remove('open');

  window.expShare = function() {
    const vis = _datasets.filter(d => d.visible);
    if (!vis.length) { alert('No visible datasets to export.'); return; }
    const allFreqs = [...new Set(vis.flatMap(d => d.freqs))].sort((a,b)=>a-b);
    const header = ['Frequency_Hz', ...vis.map(d => d.name.replace(/[,\n"]/g,'_'))].join(',');
    const rows = allFreqs.map(f => {
      const vals = vis.map(d => {
        const idx = d.freqs.indexOf(f);
        return idx >= 0 ? d.mags[idx].toFixed(4) : '';
      });
      return [f, ...vals].join(',');
    });
    const csv = [header, ...rows].join('\n');
    const url = URL.createObjectURL(new Blob([csv], {type:'text/csv'}));
    const a = document.createElement('a');
    a.href = url; a.download = 'explore_export_' + new Date().toISOString().slice(0,10) + '.csv';
    a.click(); URL.revokeObjectURL(url);
  };

  window.expColors = function() { $('colors-modal')?.classList.add('open'); };
  window.expCloseColors = () => $('colors-modal')?.classList.remove('open');
  window.expPickPalette = function(name) {
    _palette = PALETTES[name] || PALETTES.default;
    _datasets.forEach((d,i) => d.color = _palette[i % _palette.length]);
    _renderList(); render();
    $('colors-modal')?.classList.remove('open');
  };

  // ── Plot controls ─────────────────────────────────────────────────────
  window.expToggleYLog = function() { _S.yLog = !_S.yLog; _syncAxisBtns(); render(); };
  window.expRescaleY   = function() { _S.yMin = null; _S.yMax = null; render(); };
  window.expSetYDbRange = function(v) { _S.yDbRange = parseFloat(v) || 38; render(); };
  window.expSetXRange  = function() {
    const mn = parseFloat($('x-min-inp')?.value), mx = parseFloat($('x-max-inp')?.value);
    if (isFinite(mn)) _S.xMin = mn; if (isFinite(mx)) _S.xMax = mx;
    render();
  };
  window.expToggleXLog = function() { _S.xLog = !_S.xLog; _syncAxisBtns(); render(); };
  window.expSetSmoothing = function(v) { _S.smoothing = parseFloat(v) || 0; render(); };
  window.expSetNormalize = function(v) { _S.normalize = v === 'normalize'; render(); };
  window.expSetBandPreset = function(v) {
    if (v === 'custom') { expCustomBands(); return; }
    _S.bandPreset = v; render();
  };
  window.expCustomBands = function() {
    const input = prompt(
      'Enter custom band boundaries (Hz), comma-separated.\nExample: 200,500,1000,2000,4000,7000'
    );
    if (!input) return;
    const edges = input.split(',').map(s => parseFloat(s.trim())).filter(isFinite);
    if (edges.length < 2) { alert('Need at least 2 boundary values.'); return; }
    _customBands = [];
    for (let i = 0; i < edges.length - 1; i++)
      _customBands.push({label: `${edges[i]}–${edges[i+1]}`, f_lo: edges[i], f_hi: edges[i+1]});
    _S.bandPreset = 'custom';
    const sel = $('band-sel'); if (sel) { const o = document.createElement('option'); o.value='custom'; o.textContent='Custom'; sel.appendChild(o); sel.value='custom'; }
    render();
  };
  window.expExportBands = function() {
    if (!window._exploreLastBandData?.length) { alert('Select a band preset first.'); return; }
    const rows = ['Band,f_lo_Hz,f_hi_Hz,avg_dB,centroid_Hz'];
    window._exploreLastBandData.forEach(b =>
      rows.push(`${b.label},${b.f_lo},${b.f_hi},${b.avg_db.toFixed(3)},${b.centroid.toFixed(1)}`)
    );
    const url = URL.createObjectURL(new Blob([rows.join('\n')], {type:'text/csv'}));
    const a = document.createElement('a'); a.href=url; a.download='band_data.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  // ── Interpret modal ───────────────────────────────────────────────────
  window.expInterpret = function() {
    const modal = $('interpret-modal'); if (!modal) return;
    modal.classList.add('open');
    const vis = _datasets.filter(d => d.visible);
    const traces = vis.map(d => {
      let mags = _smooth(d.freqs, d.mags, _S.smoothing);
      if (_S.normalize) mags = _norm(mags);
      return {x:d.freqs, y:mags, type:'scatter', mode:'lines', name:d.name, line:{color:d.color, width:1.5}, showlegend:true};
    });
    // String mode tick marks at bottom
    STRING_MODES.forEach(m => traces.push({
      x:[m.freq,m.freq], y:[-35,-28], type:'scatter', mode:'lines+text',
      text:['',m.label], textposition:'bottom center',
      line:{color:'#c00', width:1.5, dash:'dot'},
      showlegend:false, textfont:{color:'#c00', size:11},
    }));
    if (!traces.length) traces.push({x:[],y:[],type:'scatter',mode:'lines',showlegend:false});

    const shapes = INTERPRET_REGIONS.map(r => ({
      type:'rect', xref:'x', yref:'paper', x0:r.f_lo, x1:r.f_hi, y0:0, y1:1,
      fillcolor:r.color, opacity:0.1, line:{width:0},
    }));
    const annotations = INTERPRET_REGIONS.map(r => ({
      x: Math.sqrt(r.f_lo * r.f_hi), xref:'x', y:1.05, yref:'paper',
      text: r.label, showarrow:false, font:{color:r.color, size:11}, xanchor:'center',
    }));
    // Typical range bars near top
    [{lo:264,hi:290},{lo:380,hi:420},{lo:393,hi:470},{lo:473,hi:593}].forEach((r,i) => {
      shapes.push({type:'line', xref:'x', yref:'paper', x0:r.lo, x1:r.hi, y0:0.97-i*0.015, y1:0.97-i*0.015, line:{color:'#888',width:3}});
    });

    Plotly.react('interpret-plot', traces, {
      paper_bgcolor:'white', plot_bgcolor:'white',
      font:{color:'#333', family:'inherit', size:12},
      margin:{l:65, r:16, t:50, b:60},
      showlegend: traces.length > 1,
      legend:{x:1, xanchor:'right', y:1, font:{size:10}},
      xaxis:{title:'Frequency (Hz)', type:'log', range:[Math.log10(200), Math.log10(10000)], gridcolor:'#ddd', zerolinecolor:'#ddd'},
      yaxis:{title:'Intensity (dB)', gridcolor:'#ddd', zerolinecolor:'#ddd'},
      shapes, annotations,
    }, {responsive:true, displayModeBar:false});
  };
  window.expCloseInterpret = () => $('interpret-modal')?.classList.remove('open');

  // ── Sync controls ─────────────────────────────────────────────────────
  function _syncControls() {
    const xMin = $('x-min-inp'), xMax = $('x-max-inp');
    if (xMin) xMin.value = _S.xMin; if (xMax) xMax.value = _S.xMax;
    const yRange = $('y-db-range'); if (yRange) yRange.value = _S.yDbRange;
    const sm = $('smooth-sel'); if (sm) sm.value = String(_S.smoothing);
    const nm = $('norm-sel');   if (nm) nm.value = _S.normalize ? 'normalize' : 'as_measured';
    _syncAxisBtns();
  }
  function _syncAxisBtns() {
    const yl = $('y-log-btn');
    if (yl) { yl.textContent = _S.yLog ? 'Y=log' : 'Y=lin'; yl.classList.toggle('active', _S.yLog); }
    const xl = $('x-log-btn');
    if (xl) { xl.textContent = _S.xLog ? 'X=log' : 'X=lin'; xl.classList.toggle('active', _S.xLog); }
  }

  // ── Hover readout ─────────────────────────────────────────────────────
  function _setupHover() {
    const el = $('explore-plot'); if (!el) return;
    el.on('plotly_hover', data => {
      if (!data.points?.length) return;
      const pt = data.points[0]; if (!isFinite(pt.y)) return;
      const ro = $('hover-readout');
      if (ro) ro.textContent = `Amp = ${pt.y.toFixed(1)} dB,  Freq = ${Number(pt.x).toFixed(0)} Hz`;
    });
    el.on('plotly_unhover', () => { const ro=$('hover-readout'); if(ro) ro.textContent=''; });
  }

  // ── Drag-and-drop onto plot ───────────────────────────────────────────
  function _setupDropZone() {
    const area = $('explore-drop-area'); if (!area) return;
    ['dragenter','dragover'].forEach(ev => area.addEventListener(ev, e => {
      e.preventDefault(); area.classList.add('dragging');
    }));
    ['dragleave','drop'].forEach(ev => area.addEventListener(ev, e => {
      e.preventDefault(); area.classList.remove('dragging');
    }));
    area.addEventListener('drop', async e => {
      if (!window.pyExploreLoadFile) { alert('Python not ready.'); return; }
      for (const f of (e.dataTransfer?.files||[]))
        window.pyExploreLoadFile(f.name, new Uint8Array(await f.arrayBuffer()));
    });
  }

  // ── Python-side callbacks ─────────────────────────────────────────────
  window.obieExploreAddDataset = function(name, freqsJs, magsJs) {
    const n = String(name).split('/').pop().split('\\').pop();
    _saveUndo();
    const id = _nextId++;
    const color = _palette[_datasets.length % _palette.length];
    _datasets.push({id, name:n, color, visible:true, freqs:Array.from(freqsJs), mags:Array.from(magsJs)});
    _renderList(); render();
    const st = $('explore-status');
    if (st) { st.textContent = `✓ ${n}`; setTimeout(()=>st.textContent='', 3000); }
  };

  window.obieExploreError = function(name, msg) {
    const st = $('explore-status');
    if (st) { st.textContent = `Error: ${msg}`; st.style.color='var(--red,#c00)'; setTimeout(()=>{st.textContent=''; st.style.color='';}, 5000); }
    console.error(`[Explore] ${name}: ${msg}`);
  };

  window.obieExploreWavReady = function(info) {
    const el = $('wav-info'); if (el) el.textContent = '✓ WAV: ' + info;
  };
  window.obieExploreWavError = function(msg) {
    const el = $('wav-info'); if (el) el.textContent = 'WAV error: ' + msg;
  };

  window.obieExploreReady = function() {
    $('loading')?.classList.add('gone');
    // Load default WAV
    const url = localStorage.getItem('obieExplore_defaultWavUrl')
      || '../../sample-data/1-Tchaikovsky-short.wav';
    fetch(url)
      .then(r => r.ok ? r.arrayBuffer() : Promise.reject(r.status))
      .then(ab => window.pyExploreSetWav && window.pyExploreSetWav(new Uint8Array(ab), url.split('/').pop()))
      .catch(e => console.warn('Default WAV fetch failed:', e));

    // Restore saved settings
    try {
      const saved = JSON.parse(localStorage.getItem('obieExplore_plotState') || '{}');
      Object.assign(_S, saved);
    } catch(_) {}
    _syncControls();
    render();
    _setupHover();
    _setupDropZone();
    _syncUndoBtn();
    _renderList();
    window.addEventListener('resize', () => Plotly.Plots.resize('explore-plot'));
  };

  // Save plot state on page hide
  window.addEventListener('pagehide', () => {
    try { localStorage.setItem('obieExplore_plotState', JSON.stringify(_S)); } catch(_) {}
  });

  // ── Load templates + lists ────────────────────────────────────────────
  fetch('./templates.json').then(r=>r.json()).then(d=>{
    _templates = d.templates||[];
    const menu = $('new-test-menu'); if (!menu) return;
    menu.innerHTML = _templates.map((t,i)=>
      `<button class="menu-item" onclick="expPickTemplate(${i})">${_esc(t.name)}</button>`
    ).join('');
  }).catch(()=>{});

  fetch('./lists.json').then(r=>r.json()).then(d=>{ _lists = d.lists||[]; }).catch(()=>{});

  // ── Boot ──────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    Plotly.newPlot('explore-plot', [], {
      paper_bgcolor:'transparent', plot_bgcolor:'transparent',
      margin:{l:65, r:16, t:12, b:50}, autosize:true,
      xaxis:{title:'Frequency (Hz)', type:'log', range:[Math.log10(200),Math.log10(7000)]},
      yaxis:{title:'Magnitude (dB)'},
    }, {responsive:true, displayModeBar:true, displaylogo:false, modeBarButtonsToRemove:['sendDataToCloud']});
    _syncUndoBtn();
    _renderList();
    _syncAxisBtns();
  });

})();
