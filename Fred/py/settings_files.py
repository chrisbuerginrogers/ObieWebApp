def unpack_settings(text):
    settings = {}
    lines = text.strip().splitlines()
    key = None
    buffer = []

    for line in lines:
        if key:  # we are in a multiline block
            if line.strip().endswith("/>"):  # block ends
                # join and clean
                value = []
                try:
                    for piece in buffer:
                        # x and y range go [increment, maximum, miminum, minor increment, start]
                        # for each [hammer spectrum, hammer data, mic data, frf average]
                        value.append([float(x) for x in piece.split()])
                except ValueError:
                    value = " ".join(buffer)
                
                settings[key] = value
                key, buffer = None, []
            else:
                buffer.append(line)
            continue

        if "=" not in line:
            continue

        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()

        if v.startswith("<") and not v.endswith("/>"):
            # start of multiline block
            key = k
            buffer = [v[1:]]
            continue

        # normal one-line entry
        value = v[1:-2] if v.startswith("<") and v.endswith("/>") else v
        # try convert to float, bool, or leave as string
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
        else:
            try:
                value = float(value)
            except ValueError:
                pass

        settings[k] = value

    return settings