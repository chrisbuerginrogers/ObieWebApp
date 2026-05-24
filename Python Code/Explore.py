# this lets you explore existin data sets

"""
TRF File Visualization Tool

This script loads a TRF (Transfer Function) file and displays it as an interactive plot.
The plot includes the frequency response data with a header information box showing
metadata from the TRF file.

Usage:
    Update 'file_path' with the path to your TRF file, then run the script.
    The plot will display with header information on the right side.
"""

from fileio.trf_fileio import parse_trf
from plotio.plotIt import plot_trf

# Load a sample TRF file
file_path = 'SampleData/Betts Strad RHV20 H_001.trf'
with open(file_path, 'rb') as f:
    raw_data = f.read()
data = parse_trf(raw_data)

plot_trf(data, file_path)
