/* ─────────────────────────────────────────────────────────────────────
 * plot-controls.js
 * Owns plot state. Wires log/lin toggles + range inputs.
 * Exposes:
 *   obieInitPlotControls(divId, opts)
 *   obieShowData(x, y, xLabel, yLabel)        ← Python calls this
 *   obieClearPlot()                           ← Python calls this on reset
 * ───────────────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  const state = {
    plotDiv: 'plot',
    xLabel:  'Frequency [Hz]',
    yLabel:  'Magnitude',
    xLog:    true,         // default LOG per spec
    yLog:    true,
    xMin: null, xMax: null,
    yMin: null, yMax: null,
  };

  let lastX = [], lastY = [];      // cached for relayout-with-data calls

  function $(id) { return document.getElementById(id); }

  /* ── Render ─────────────────────────────────────────────────────── */
  function render() {
    const layout = window.obieBuildPlotLayout(state);
    const trace  = [{
      x: lastX, y: lastY,
      type: 'scatter', mode: 'lines',
      line: { color: window.OBIE_PLOT_THEME.line, width: 1.6 },
      name: 'data',
    }];
    Plotly.react(state.plotDiv, trace, layout, window.OBIE_PLOT_CONFIG);
  }

  /* ── Toggle wiring ──────────────────────────────────────────────── */
  function setToggle(groupId, axis, val) {
    const grp = $(groupId);
    if (grp) {
      grp.querySelectorAll('button').forEach(b => {
        b.classList.toggle('active', b.dataset.scale === val);
      });
    }
    if (axis === 'x') state.xLog = (val === 'log');
    else              state.yLog = (val === 'log');
    render();
  }
  function wireToggle(groupId, axis) {
    const grp = $(groupId);
    if (!grp) return;
    grp.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => setToggle(groupId, axis, btn.dataset.scale));
    });
  }

  /* ── Range inputs ───────────────────────────────────────────────── */
  function readNum(id) {
    const el = $(id); if (!el) return null;
    const s = el.value.trim();
    if (s === '') return null;
    const v = parseFloat(s);
    return isFinite(v) ? v : null;
  }
  function wireRange(inputId, key) {
    const el = $(inputId); if (!el) return;
    el.addEventListener('change', () => { state[key] = readNum(inputId); render(); });
  }

  function wireAutoscale(btnId) {
    const b = $(btnId); if (!b) return;
    b.addEventListener('click', () => {
      state.xMin = state.xMax = state.yMin = state.yMax = null;
      ['x-min','x-max','y-min','y-max'].forEach(id => { const e=$(id); if(e) e.value=''; });
      render();
    });
  }

  /* ── Public API ─────────────────────────────────────────────────── */
  window.obieInitPlotControls = function (divId, opts) {
    state.plotDiv = divId;
    Object.assign(state, opts || {});
    setToggle('x-scale-toggle', 'x', state.xLog ? 'log' : 'linear');
    setToggle('y-scale-toggle', 'y', state.yLog ? 'log' : 'linear');
    wireToggle('x-scale-toggle', 'x');
    wireToggle('y-scale-toggle', 'y');
    wireRange('x-min', 'xMin'); wireRange('x-max', 'xMax');
    wireRange('y-min', 'yMin'); wireRange('y-max', 'yMax');
    wireAutoscale('autoscale-btn');
    // Initial empty plot
    Plotly.newPlot(state.plotDiv, [{ x: [], y: [], type: 'scatter', mode: 'lines',
      line:{ color: window.OBIE_PLOT_THEME.line, width: 1.6 } }],
      window.obieBuildPlotLayout(state), window.OBIE_PLOT_CONFIG);
  };

  // Called from Python after parsing: hand over arrays + axis labels.
  window.obieShowData = function (x, y, xLabel, yLabel) {
    lastX = Array.from(x || []);
    lastY = Array.from(y || []);
    if (xLabel) state.xLabel = xLabel;
    if (yLabel) state.yLabel = yLabel;
    render();
  };

  window.obieClearPlot = function () {
    lastX = []; lastY = []; render();
  };
})();
