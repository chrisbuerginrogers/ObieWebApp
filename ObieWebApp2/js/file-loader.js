/* ─────────────────────────────────────────────────────────────────────
 * file-loader.js
 * Dropzone + file-picker wiring. Reads the chosen file as text and
 * passes it to a Python callback (set up by main.py / py/).
 * ───────────────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  /* ── Public init ─────────────────────────────────────────────────── */
  // Call with:
  //   obieInitFileLoader({
  //     dropZoneId:  'dropzone',
  //     pickerBtnId: 'file-pick-btn',
  //     fileInputId: 'file-input',
  //     onText: (filename, sizeBytes, text) => { ... },   // required
  //   });
  window.obieInitFileLoader = function (cfg) {
    if (!cfg || typeof cfg.onText !== 'function') {
      console.error('obieInitFileLoader: onText callback required');
      return;
    }

    const drop  = document.getElementById(cfg.dropZoneId);
    const pick  = document.getElementById(cfg.pickerBtnId);
    const input = document.getElementById(cfg.fileInputId);

    function readFile(file) {
      if (!file) return;
      const reader = new FileReader();
      reader.onload  = (e) => cfg.onText(file.name, file.size, e.target.result);
      reader.onerror = ()  => cfg.onText(file.name, file.size, null);
      // Try UTF-8; fallback handled in parser
      reader.readAsText(file);
    }

    /* ── File picker ─────────────────────────────────────────────── */
    if (pick && input) {
      pick.addEventListener('click', () => input.click());
      input.addEventListener('change', () => {
        if (input.files && input.files[0]) readFile(input.files[0]);
      });
    }

    /* ── Drag & drop on the dropzone ─────────────────────────────── */
    if (drop) {
      drop.addEventListener('click', () => input && input.click());

      ['dragenter', 'dragover'].forEach(ev =>
        drop.addEventListener(ev, e => {
          e.preventDefault();
          drop.classList.add('dragging');
        })
      );
      ['dragleave', 'drop'].forEach(ev =>
        drop.addEventListener(ev, e => {
          e.preventDefault();
          drop.classList.remove('dragging');
        })
      );
      drop.addEventListener('drop', e => {
        const files = e.dataTransfer && e.dataTransfer.files;
        if (files && files[0]) readFile(files[0]);
      });
    }
  };

  /* ── Helper: format byte count for display ──────────────────────── */
  window.obieFormatSize = function (n) {
    if (n < 1024)        return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
    return (n / 1024 / 1024).toFixed(2) + ' MB';
  };
})();
