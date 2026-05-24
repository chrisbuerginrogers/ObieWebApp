"""
TRF File Unit test
This script serves as a unit test for the TRF file parsing and visualization functionality.
"""

from trf_fileio import parse_trf
from pathlib import Path

# Load a sample TRF file
script_dir = Path(__file__).resolve().parent
file_path = script_dir.parent / 'SampleData' / 'Betts Strad RHV20 H_001.trf'

with open(file_path, 'rb') as f:
    raw_data = f.read()
data = parse_trf(raw_data)

# Format header information as text
header_text = '\n'.join([f"{key}: {value}" for key, value in data['header'].items()])
print(header_text)

# Print any warnings
if data['warnings']:
    print("Warnings:")
    for warning in data['warnings']:
        print(f"  - {warning}")