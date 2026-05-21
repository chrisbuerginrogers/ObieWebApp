"""
trigger_capture.py

Continuously reads from AudioStream and fires a capture when Channel 1
exceeds a threshold.  Each capture returns:
  - 0.01 s of pre-trigger data  (both channels)
  - 0.30 s of post-trigger data (both channels)
as a numpy array of shape (n_samples, 2), dtype int16.
"""

#import sys
import time
import collections
import numpy as np

from streamAudio import AudioStream

# ── Parameters ────────────────────────────────────────────────────────────────

THRESHOLD    = 5000          # int16 amplitude on Channel 1; adjust to taste
PRE_SECS     = 0.01
POST_SECS    = 0.30
PRE_SAMPLES  = int(SAMPLE_RATE * PRE_SECS)    # 480
POST_SAMPLES = int(SAMPLE_RATE * POST_SECS)   # 14 400
from config import DEVICE_NAME, AUDIO_FORMAT, SAMPLE_RATE, CHUNK_SIZE, PRE_SECS, POST_SECS, PRE_SAMPLES, POST_SAMPLES


# ── Core capture logic ────────────────────────────────────────────────────────

def wait_for_trigger(stream: AudioStream, threshold: int = THRESHOLD) -> np.ndarray:
    """
    Block until |Channel 1| exceeds `threshold`, then return an array of
    shape (PRE_SAMPLES + POST_SAMPLES, channels), dtype int16.

    The returned array starts PRE_SECS before the first crossing and ends
    POST_SECS after it.
    """
    # Rolling buffer: keeps exactly the last PRE_SAMPLES rows
    pre_buf: collections.deque[np.ndarray] = collections.deque(maxlen=PRE_SAMPLES)

    triggered   = False
    post_pieces = []
    post_needed = POST_SAMPLES
    pre_snapshot: np.ndarray | None = None

    while True:
        chunk = stream.read_chunks()
        if chunk is None:
            time.sleep(0.001)
            continue

        if not triggered:
            ch1  = chunk[:, 0]
            hits = np.where(np.abs(ch1) > threshold)[0]

            if len(hits) == 0:
                for row in chunk:
                    pre_buf.append(row)
                continue

            trig_idx = int(hits[0])

            # Feed samples before the crossing into the rolling buffer
            for row in chunk[:trig_idx]:
                pre_buf.append(row)

            pre_snapshot = np.array(pre_buf)   # ≤ PRE_SAMPLES rows
            triggered    = True
            remainder    = chunk[trig_idx:]    # from trigger onward

        else:
            remainder = chunk

        # Collect post-trigger samples
        if len(remainder) >= post_needed:
            post_pieces.append(remainder[:post_needed])
            break
        else:
            post_pieces.append(remainder)
            post_needed -= len(remainder)

    post_data = np.concatenate(post_pieces, axis=0)

    if pre_snapshot is None or len(pre_snapshot) == 0:
        return post_data

    return np.concatenate([pre_snapshot, post_data], axis=0)


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    print(f"Threshold: |Ch1| > {THRESHOLD}  |  pre={PRE_SECS*1000:.0f} ms  post={POST_SECS*1000:.0f} ms")
    print("Press Ctrl+C to stop.\n")

    with AudioStream(device_index=DEVICE, sample_rate=SAMPLE_RATE, channels=2) as stream:
        event_idx = 0
        while True:
            try:
                print("Waiting for trigger...")
                data = wait_for_trigger(stream)

                event_idx += 1
                duration_ms = len(data) / SAMPLE_RATE * 1000
                ch1_peak    = int(np.max(np.abs(data[:, 0])))
                ch2_peak    = int(np.max(np.abs(data[:, 1])))

                print(
                    f"  [Event {event_idx}]  {len(data)} samples "
                    f"({duration_ms:.1f} ms)  |  Ch1 peak={ch1_peak}  Ch2 peak={ch2_peak}"
                )

                # ── Do something with `data` here ──────────────────────────
                # np.save(f"event_{event_idx:04d}.npy", data)
                # ----------------------------------------------------------

            except KeyboardInterrupt:
                print("\nStopped.")
                break


if __name__ == "__main__":
    main()
