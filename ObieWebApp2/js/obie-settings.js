/**
 * obie-settings.js — Shared ObieAppSettings folder management + cross-tool
 * folder-handle persistence via IndexedDB.
 *
 * Exposes one function used by Acquire, Explore, and Convolve It:
 *
 *   const { settingsHandle, templatesHandle } = await openObieAppSettings(dirHandle);
 *
 * If ObieAppSettings does not yet exist in dirHandle, the folder is created
 * and seeded with the default templates fetched from GitHub.
 */

// ── Shared IndexedDB for cross-tool data-folder persistence ──────────────────
const _OBIE_IDB = (() => {
  let _db = null;
  function _open() {
    if (_db) return Promise.resolve(_db);
    return new Promise((res, rej) => {
      const req = indexedDB.open('ObieWebApp', 1);
      req.onupgradeneeded = e => e.target.result.createObjectStore('kv');
      req.onsuccess  = e => { _db = e.target.result; res(_db); };
      req.onerror    = e => rej(e.target.error);
    });
  }
  return {
    async put(key, val) {
      const db = await _open();
      return new Promise((res, rej) => {
        const tx = db.transaction('kv', 'readwrite');
        tx.objectStore('kv').put(val, key);
        tx.oncomplete = res; tx.onerror = e => rej(e.target.error);
      });
    },
    async get(key) {
      const db = await _open();
      return new Promise((res, rej) => {
        const tx = db.transaction('kv', 'readonly');
        const req = tx.objectStore('kv').get(key);
        req.onsuccess = () => res(req.result ?? null);
        req.onerror   = e => rej(e.target.error);
      });
    },
  };
})();

async function saveDataFolderHandle(handle) {
  try {
    await _OBIE_IDB.put('dataFolderHandle', handle);
    localStorage.setItem('obieDataFolderName', handle.name);
  } catch (e) { console.warn('saveDataFolderHandle:', e); }
}

async function loadDataFolderHandle() {
  try { return await _OBIE_IDB.get('dataFolderHandle'); }
  catch (_) { return null; }
}

const _TEMPLATE_SEEDS = [
  [
    'HV 24 Obie Rig_template.json',
    'https://raw.githubusercontent.com/chrisbuerginrogers/ObieWebApp/main/Python%20Code/ObieApp%20Settings/template/HV%2024%20Obie%20Rig_template.json',
  ],
  [
    'ScratchPad_template.json',
    'https://raw.githubusercontent.com/chrisbuerginrogers/ObieWebApp/main/Python%20Code/ObieApp%20Settings/template/ScratchPad_template.json',
  ],
  [
    'Scratchpad Obie 26_template.json',
    'https://raw.githubusercontent.com/chrisbuerginrogers/ObieWebApp/main/Python%20Code/ObieApp%20Settings/template/Scratchpad%20Obie%2026_template.json',
  ],
];

async function _seedObieAppSettings(templatesHandle) {
  for (const [name, url] of _TEMPLATE_SEEDS) {
    try {
      const r = await fetch(url);
      if (!r.ok) continue;
      const fh = await templatesHandle.getFileHandle(name, { create: true });
      const w  = await fh.createWritable();
      await w.write(await r.text());
      await w.close();
    } catch (e) {
      console.warn('ObieAppSettings seed failed for', name, e);
    }
  }
}

/**
 * Open (or create) ObieAppSettings inside the given data-folder handle.
 * If the folder is newly created, seeds it with default templates from GitHub.
 *
 * @param {FileSystemDirectoryHandle} dirHandle  The user-selected data folder.
 * @returns {{ settingsHandle, templatesHandle }}
 */
async function openObieAppSettings(dirHandle) {
  let settingsHandle;
  let isNew = false;

  // Detect whether ObieAppSettings already exists without creating it first.
  try {
    settingsHandle = await dirHandle.getDirectoryHandle('ObieAppSettings');
  } catch (_) {
    settingsHandle = await dirHandle.getDirectoryHandle('ObieAppSettings', { create: true });
    isNew = true;
  }

  const templatesHandle = await settingsHandle.getDirectoryHandle('Templates', { create: true });

  if (isNew) {
    await _seedObieAppSettings(templatesHandle);
  }

  return { settingsHandle, templatesHandle };
}
