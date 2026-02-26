import struct

### note end_freq appears to be defined as res*fLength,
### but that means end_freq is not included

def unpack_av(contents):
    header_fmt = (
        '<'     # little-endian
        'B'     # Data type (u8)
        '4d'    # Hz_Resolution, Start_Freq, Stop_Freq, Scale_Factor
        'I'     # Number of averages (u32)
        'B'     # Averaging type (u8)
        '11f'   # fComplex, fLength, a[2], fConditionCheck, Precision,
                # MtxVecVersion, SizeOf_TSample, Tag, MtxVecFileCount, a[9], a[10]
        '4s'    # caption (char[4])
    )

    
    header_size = struct.calcsize(header_fmt)
    header = struct.unpack(header_fmt, contents[:header_size])

    # Unpack named fields
    data_type = header[0]
    hz_resolution, start_freq, stop_freq, scale_factor = header[1:5]
    num_avgs = header[5]
    averaging_type = header[6]
    fComplex, fLength = header[7], header[8]
    a2 = header[9]
    fConditionCheck = header[10]
    Precision = header[11]
    MtxVecVersion = header[12]
    SizeOf_TSample = header[13]
    Tag = header[14]
    MtxVecFileCount = header[15]
    a9, a10 = header[16:18]
    caption = header[18].decode('ascii')#.rstrip('\x00')


    # --- Data section ---
    data_bytes = contents[header_size:]
    num_doubles = len(data_bytes) // 8
    is_complex = int(fComplex) == 1

    if is_complex:
        # Complex values are stored as alternating real/imag doubles
        raw = struct.unpack(f'<{num_doubles}d', data_bytes)
        data_array = [complex(raw[i], raw[i+1]) for i in range(0, num_doubles, 2)]
    else:
        data_array = struct.unpack(f'<{num_doubles}d', data_bytes)

    # --- Return structured dict ---
    return {
        'Data_Type': data_type,              # Accel, Mobility, Mic, Unknown
        'Hz_Resolution': hz_resolution,
        'Start_Freq': start_freq,
        'Stop_Freq': stop_freq,
        'Scale_Factor': scale_factor,
        'Num_Averages': num_avgs,
        'Averaging_Type': averaging_type,    # RMS, Mean, Complex, Geometric, None
        'fComplex': bool(is_complex),
        'fLength': fLength,
        'a2': a2,
        'fConditionCheck': fConditionCheck,
        'Precision': Precision,
        'MtxVecVersion': MtxVecVersion,
        'SizeOf_TSample': SizeOf_TSample,
        'Tag': Tag,
        'MtxVecFileCount': MtxVecFileCount,
        'a9': a9,
        'a10': a10,
        'caption': caption,
        'data': data_array
    }


def pack_av(data_dict):
    # Define defaults for all fields
    defaults = {
        'Data_Type': 3, # unknown
        'Hz_Resolution': None, # REQUIRED
        'Start_Freq': None,    # REQUIRED
        'Stop_Freq': None,     # REQUIRED
        'Scale_Factor': 1,
        'Num_Averages': 1,
        'Averaging_Type': 2,  # complex
        'fComplex': None,     # REQUIRED
        'fLength': None,
        'a2': 0.0,
        'fConditionCheck': 0.0,
        'Precision': 0.0,
        'MtxVecVersion': 0.0,
        'SizeOf_TSample': 0.0,
        'Tag': 0.0,
        'MtxVecFileCount': 0.0,
        'a9': 0.0,
        'a10': 0.0,
        'caption': '\x00\x00\x00\x00',
        'data': None          # REQUIRED
    }

    # Merge user data into defaults
    merged = defaults.copy()
    merged.update(data_dict)

    # Check required fields
    for field in ['fComplex', 'Hz_Resolution', 'Start_Freq', 'Stop_Freq', 'data']:
        if merged[field] is None:
            raise ValueError(f"Missing required field: {field}")
        
    # Derive expected length from frequency range and resolution
    start = merged['Start_Freq']
    end = merged['Stop_Freq']
    res = merged['Hz_Resolution']
    expected_length = int((end - start) / res) # feels like this should have +1

    if merged['fLength'] is None:
        merged['fLength'] = expected_length
    else:
        if int(merged['fLength']) != expected_length:
            raise ValueError(
                f"fLength mismatch: got {merged['fLength']}, expected {expected_length} "
                f"from freq range ({start}–{end}) and resolution {res}"
            )
        
    # Pack the data section
    is_complex = int(merged['fComplex']) == 1
    
    raw_data = merged['data'][:expected_length]
    if is_complex:
        formatted_data = []
        for c in raw_data:
            formatted_data.extend([c.real, c.imag])
        data_length = expected_length * 2
    else:
        if not all(isinstance(x, (float, int)) for x in raw_data):
            raise ValueError("Expected real-valued data for non-complex format.")
        formatted_data = raw_data
        data_length = expected_length

    data_bytes = struct.pack(f'<{data_length}d', *formatted_data)

    caption = merged['caption'].encode('ascii').ljust(4, b'\x00')[:4]

    # Header format and tuple
    header_fmt = '<B4dIB11f4s'
    header_tuple = (
        merged['Data_Type'],
        merged['Hz_Resolution'], merged['Start_Freq'], merged['Stop_Freq'],
        merged['Scale_Factor'], merged['Num_Averages'], merged['Averaging_Type'],
        float(merged['fComplex']), float(merged['fLength']),
        merged['a2'],
        merged['fConditionCheck'],
        merged['Precision'],
        merged['MtxVecVersion'],
        merged['SizeOf_TSample'],
        merged['Tag'],
        merged['MtxVecFileCount'],
        merged['a9'], merged['a10'],
        caption
    )

    header_bytes = struct.pack(header_fmt, *header_tuple)
    return header_bytes + data_bytes