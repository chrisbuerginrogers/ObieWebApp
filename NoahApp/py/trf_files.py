import struct

### note end_freq appears to be defined as res*fLength,
### but that means end_freq is not included

def unpack_trf(contents):
    header_fmt = (
        '<'       # all little-endian
        'I'       # index
        '4d'      # Xr, Yr, Xactual, YActual
        '2s'      # 2-char string
        '3d'      # Hz_Resolution, Start_Freq, End_Freq
        '11f'     # fComplex, fLength, a[2], fConditionCheck, Precision, MtxVecVersion, SizeOf_TSample, Tag, MtxVecFileCount, a[9], a[10]
        '4s'      # caption
    )
    
    header_size = struct.calcsize(header_fmt)
    header = struct.unpack(header_fmt, contents[:header_size])

    # Unpack named fields
    index = header[0]
    Xr, Yr, Xactual, YActual = header[1:5]
    char_str = header[5].decode('ascii')
    Hz_Resolution, Start_Freq, End_Freq = header[6:9]
    fComplex, fLength = header[9], header[10]
    a2 = header[11]
    fConditionCheck = header[12]
    Precision = header[13]
    MtxVecVersion = header[14]
    SizeOf_TSample = header[15]
    Tag = header[16]
    MtxVecFileCount = header[17]
    a9, a10 = header[18:20]
    caption = header[20].decode('ascii')#.rstrip('\x00')
    
    
    data_bytes = contents[110:]
    num_doubles = len(data_bytes) // 8
    
    is_complex = int(fComplex) == 1
    
    if is_complex:
        # Complex values are stored as alternating real/imag doubles
        raw = struct.unpack(f'<{num_doubles}d', data_bytes)
        complex_data = [complex(raw[i], raw[i+1]) for i in range(0, num_doubles, 2)]
        data_array = complex_data
    else:
        data_array = struct.unpack(f'<{num_doubles}d', data_bytes)

    return {
        'index': index,
        'Xr': Xr,
        'Yr': Yr,
        'Xactual': Xactual,
        'YActual': YActual,
        'char_str': char_str,
        'Hz_Resolution': Hz_Resolution,
        'Start_Freq': Start_Freq,
        'End_Freq': End_Freq,
        'fComplex': is_complex,
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

def pack_trf(data_dict):
    # Define defaults for all fields
    defaults = {
        'index': 0,
        'Xr': 0.0,
        'Yr': 0.0,
        'Xactual': 0.0,
        'YActual': 0.0,
        'char_str': '\x00\x00',
        'Hz_Resolution': None,  # REQUIRED
        'Start_Freq': None,     # REQUIRED
        'End_Freq': None,       # REQUIRED
        'fComplex': None,       # REQUIRED
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
        'data': None            # REQUIRED
    }

    # Merge user data into defaults
    merged = defaults.copy()
    merged.update(data_dict)

    # Check required fields
    for field in ['fComplex', 'Hz_Resolution', 'Start_Freq', 'End_Freq', 'data']:
        if merged[field] is None:
            raise ValueError(f"Missing required field: {field}")

    # Prepare fixed-size strings
    char_str = merged['char_str'].encode('ascii').ljust(2, b'\x00')[:2]
    caption = merged['caption'].encode('ascii').ljust(4, b'\x00')[:4]
        
    # Derive expected length from frequency range and resolution
    start = merged['Start_Freq']
    end = merged['End_Freq']
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

    # Header format and tuple
    header_fmt = '<I4d2s3d11f4s'
    header_tuple = (
        merged['index'],
        merged['Xr'], merged['Yr'], merged['Xactual'], merged['YActual'],
        char_str,
        merged['Hz_Resolution'], merged['Start_Freq'], merged['End_Freq'],
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