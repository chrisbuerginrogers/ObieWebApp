"""
Explore.py — load a TRF file and visualise it with band analysis.
"""

from fileio.obieapp_config import ROOT, load
from fileio.trf_fileio import parse_trf
from processing.bands import compute_bands, print_bands
from plotio.plotIt import plot_trf_bands

cfg       = load()
file_path = ROOT / cfg['data']['base_dir'] / 'Betts Strad RHV20 H_001.trf'
with open(file_path, 'rb') as f:
    data = parse_trf(f.read())

bands = compute_bands(data['freq'], data['mag'], cfg.get('bands', []))
print_bands(bands)
plot_trf_bands(data, bands, file_path.name)
