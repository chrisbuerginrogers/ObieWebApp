def unpack_tsv(text, freq_range=[0,float('inf')]):
    # Split into lines
    lines = text.strip().split("\n")
    headers = lines[0].split("\t")
    cplx = True
    if len(headers) == 2:
        cplx = False

    H = []
    frequencies = []

    filtered_rows = []
    for line in lines[1:]:
        parts = line.split("\t")
        freq = float(parts[0])
        if freq_range[0] <= freq:
            if freq > freq_range[1]:
                break
            frequencies.append(freq)
            if cplx:
                value = complex(float(parts[1]), float(parts[2]))
            else:
                value = float(parts[1])
            H.append(value)

    return (frequencies, H)