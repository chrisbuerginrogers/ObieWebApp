# Audio
DEVICE_NAME = "Onyx Producer 2-2"  # Substring to match in device name (case-sensitive)
AUDIO_FORMAT     = '24'     # '16', '32', '8', '24', or 'float'
DISPLAY_SECONDS  = 0.03     # scrolling window width (seconds)
MIN_MAX_DECAY    = 0.995    # peak hold decay per frame
SAMPLE_RATE      = 48000
CHUNK_SIZE       = 1024

THRESHOLD    = 5000          # int16 amplitude on Channel 1; adjust to taste
PRE_SECS     = 0.01
POST_SECS    = 0.30