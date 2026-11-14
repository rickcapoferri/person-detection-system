# Rover vision — click-to-lock prototype

This first vertical slice detects people from the Mac webcam, assigns temporary
track IDs, and lets the operator lock one person by clicking their bounding box.
Other people remain visible but are not selected automatically.

## Current safety behavior

- The target is never replaced automatically.
- If its track ID disappears, the state changes to `LOST`.
- `error_x` reports horizontal displacement from the image center in `[-1, 1]`.
- `size` reports bounding-box height as a fraction of frame height.
- No motor commands are emitted yet.

## Setup on macOS

Use the installed Python 3.14 in an isolated environment:

```bash
cd person-detection-system
python3 -m venv .venv
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

## Tests

The selection and control-signal geometry can be tested without a camera or AI
dependencies:

```bash
python3 -m unittest discover -s tests -v
```

## Next engineering steps

1. Record target-loss and ID-switch metrics on short test videos.
2. Add a safe reacquisition policy using motion and appearance confidence.
3. Convert `error_x` and `size` into bounded linear/angular velocity commands.
4. Send commands to Arduino with a watchdog and explicit `STOP` state.
