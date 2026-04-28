/* ─────────────────────────────────────────────────────────────────────
 * plotly-helpers.js
 * Theme + layout factory for Plotly. Stateless — state lives in
 * plot-controls.js.
 * ───────────────────────────────────────────────────────────────────── */

window.OBIE_PLOT_THEME = {
  bg:    '#fbf3e3',     // plot area
  paper: '#f3e7d3',     // outer frame
  grid:  '#d4c2a0',
  text:  '#3a2e1d',
  line:  '#ff6f00',     // orange data line
};

window.obieBuildPlotLayout = function (s) {
  const T = window.OBIE_PLOT_THEME;
  function rangeFor(min, max, log) {
    if (min == null || max == null) return undefined;
    return log
      ? [Math.log10(Math.max(1e-12, min)), Math.log10(Math.max(1e-12, max))]
      : [min, max];
  }
  return {
    paper_bgcolor: T.paper,
    plot_bgcolor:  T.bg,
    font:          { color: T.text, family: 'inherit', size: 12 },
    margin:        { l: 70, r: 24, t: 26, b: 56 },
    showlegend:    false,
    autosize:      true,
    xaxis: {
      title:        s.xLabel || 'X',
      type:         s.xLog ? 'log' : 'linear',
      gridcolor:    T.grid,
      zerolinecolor:T.grid,
      linecolor:    T.grid,
      autorange:    !(s.xMin != null && s.xMax != null),
      range:        rangeFor(s.xMin, s.xMax, s.xLog),
    },
    yaxis: {
      title:        s.yLabel || 'Y',
      type:         s.yLog ? 'log' : 'linear',
      gridcolor:    T.grid,
      zerolinecolor:T.grid,
      linecolor:    T.grid,
      autorange:    !(s.yMin != null && s.yMax != null),
      range:        rangeFor(s.yMin, s.yMax, s.yLog),
    },
  };
};

window.OBIE_PLOT_CONFIG = {
  responsive: true,
  displaylogo: false,
  modeBarButtonsToRemove: ['sendDataToCloud'],
};
