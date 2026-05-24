"""
avc_unitTest.py

Read the sample .AvC and .AvR files from SampleData and plot them.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import matplotlib.pyplot as plt
from fileio.avc_fileio import parse_avc, parse_avr

_SAMPLE_DIR = Path(__file__).parent.parent / "SampleData"

avc_path = _SAMPLE_DIR / "Violin 03 H.AvC"
avr_path = _SAMPLE_DIR / "Violin 03 H.AvR"

avc = parse_avc(avc_path.read_bytes())
avr = parse_avr(avr_path.read_bytes())

# ── Print headers ─────────────────────────────────────────────────────────────
print("=== .AvC header ===")
for k, v in avc.items():
    if k not in ("freqs", "H_complex"):
        print(f"  {k:20s} {v}")
print(f"  {'freqs':20s} {avc['freqs'][0]:.2f} – {avc['freqs'][-1]:.2f} Hz  ({len(avc['freqs'])} bins)")
print(f"  {'H_complex':20s} {len(avc['H_complex'])} complex values")

print("\n=== .AvR header ===")
for k, v in avr.items():
    if k not in ("freqs", "data"):
        print(f"  {k:20s} {v}")
print(f"  {'freqs':20s} {avr['freqs'][0]:.2f} – {avr['freqs'][-1]:.2f} Hz  ({len(avr['freqs'])} bins)")

# ── Plot ──────────────────────────────────────────────────────────────────────
BG = "#0d1117"

fig, ax = plt.subplots(figsize=(12, 5))
fig.patch.set_facecolor(BG)
fig.suptitle(avc_path.stem, color="#ffffff", fontsize=12)

H_dB   = 20 * np.log10(np.maximum(np.abs(avc["H_complex"]), np.finfo(float).eps))
avr_dB = 20 * np.log10(np.maximum(avr["data"],              np.finfo(float).eps))

ax.set_facecolor(BG)
ax.plot(avc["freqs"], H_dB,   color="#44dd88", linewidth=0.9, label=".AvC — complex avg FRF")
ax.plot(avr["freqs"], avr_dB, color="#ffaa33", linewidth=0.9, label=".AvR — avg magnitude")
ax.set_ylabel("FRF (dB)", color="#dddddd")
ax.set_xlabel("Frequency (Hz)", color="#aaaaaa")
ax.set_xscale("log")
ax.tick_params(colors="#aaaaaa")
ax.legend(facecolor="#1a1f2b", edgecolor="#444444", labelcolor="#dddddd")
for spine in ax.spines.values():
    spine.set_edgecolor("#333333")

plt.show()
