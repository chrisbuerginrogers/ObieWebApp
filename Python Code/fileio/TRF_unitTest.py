"""
TRF File Visualization Tool

This script loads a TRF (Transfer Function) file and displays it as an interactive plot.
The plot includes the frequency response data with a header information box showing
metadata from the TRF file.

Usage:
    Update 'file_path' with the path to your TRF file, then run the script.
    The plot will display with header information on the right side.
"""

from trf_fileio import parse_trf
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

# Load a sample TRF file
file_path = 'Betts Strad RHV20 H_001.trf'
with open(file_path, 'rb') as f:
    raw_data = f.read()
data = parse_trf(raw_data)

# Format header information as text
header_text = '\n'.join([f"{key}: {value}" for key, value in data['header'].items()])

xlabel = data['columns'][0] if len(data['columns']) > 0 else 'Frequency'
ylabel = data['columns'][1] if len(data['columns']) > 1 else 'Magnitude'

# Extract frequency and magnitude
freq = data['freq']
mag = data['mag']

# Create the plot with extra space on the right
fig, ax = plt.subplots(figsize=(14, 6))
fig.subplots_adjust(right=0.75)
line, = ax.plot(freq, mag, 'b-', linewidth=0.5)
ax.set(xlabel=xlabel, ylabel=ylabel, title='TRF File Plot: ' + file_path)
ax.grid(True, alpha=0.3)

# Add text to the right of the plot
ax.text(1.02, 0.5, header_text, transform=ax.transAxes, fontsize=9,
        verticalalignment='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
        family='monospace')

plt.tight_layout()
plt.show()

# Print any warnings
if data['warnings']:
    print("Warnings:")
    for warning in data['warnings']:
        print(f"  - {warning}")