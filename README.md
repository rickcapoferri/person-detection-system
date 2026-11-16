# Rover vision — click-to-lock prototype

This first vertical slice detects people from the Mac webcam, assigns temporary
track IDs, and lets the operator lock one person by clicking their bounding box.
Other people remain visible but are not selected automatically.

## Current safety behavior

- The target is never replaced automatically.
- If its track ID disappears, the state changes to `LOST`.
- The lock expires after 2 seconds without a sighting; selecting a target again
  requires a click. The timeout uses elapsed time, not frame count.
- `error_x` reports horizontal displacement from the image center in `[-1, 1]`.
- `size` reports bounding-box height as a fraction of frame height.
- No motor commands are emitted yet.

Tracking follows the selected ByteTrack ID; it does not independently recognize
the person's identity. If that same ID returns before the timeout, tracking
resumes. At or after the timeout, even the same ID requires a new click. If the person
returns with a different ID, click their bounding box to select them again.
ID switches can also cause a track ID to follow the wrong person; this prototype
does not detect or correct those identity errors.

## Setup on macOS

Use the installed Python 3.14 in an isolated environment:

```bash
cd person-detection-system
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The first run downloads the pretrained model weights. macOS may ask for camera
permission for the terminal application.

## Run

```bash
source .venv/bin/activate
python tracker.py
```

Controls:

- click a person to acquire or replace the target;
- press `r` to clear the lock;
- press `q` to quit.

If Metal acceleration causes an error, force CPU execution:

```bash
python tracker.py --device cpu
```

To change the loss timeout (finite positive seconds):

```bash
python tracker.py --lost-timeout 3
```

The deadline is measured from the last sighting using a monotonic clock and
checked on each processed frame. A processing gap that reaches the timeout
also clears the lock.

## Tests

The selection and control-signal geometry can be tested without a camera or AI
dependencies:

```bash
python3.14 -m unittest discover -s tests -v
```

The unit tests cover click selection, bounding-box geometry, brief target loss,
timeout expiry, late returns, explicit reselection, manual reset, replacement,
and timeout validation. Loss timing is tested without sleeping or using a camera.
They do not measure real-world detection or tracking accuracy, appearance-based
reacquisition, or ID switches.

## Next engineering steps

1. Record target-loss and ID-switch metrics on short test videos.
2. Add a safe reacquisition policy using motion and appearance confidence.
3. Convert `error_x` and `size` into bounded linear/angular velocity commands.
4. Send commands to Arduino with a watchdog and explicit `STOP` state.
