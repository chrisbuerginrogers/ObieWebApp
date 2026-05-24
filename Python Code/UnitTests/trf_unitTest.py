"""
trf_unitTest.py

Parse a sample .trf file from SampleData and print the header.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fileio.trf_fileio import parse_trf

file_path = Path(__file__).parent.parent / "SampleData" / "Betts Strad RHV20 H_001.trf"

with open(file_path, "rb") as f:
    raw_data = f.read()

data = parse_trf(raw_data)

header_text = "\n".join([f"{key}: {value}" for key, value in data["header"].items()])
print(header_text)

if data["warnings"]:
    print("Warnings:")
    for warning in data["warnings"]:
        print(f"  - {warning}")
