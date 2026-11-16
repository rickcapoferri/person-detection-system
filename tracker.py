"""Click-to-lock person tracker for the rover vision prototype."""

from __future__ import annotations

import argparse
import math
import os
import platform
import time
from pathlib import Path

os.environ.setdefault(
    "YOLO_CONFIG_DIR", str(Path(__file__).resolve().parent / ".ultralytics")
)

import cv2
import torch
from ultralytics import YOLO # type: ignore

from targeting import Detection, TargetState, select_detection, target_signals


WINDOW_NAME = "Rover person tracker"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--model", default="yolo26n.pt")
    parser.add_argument("--tracker", default="bytetrack.yaml")
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--device", default="auto", help="auto, mps, cpu, ...")
    parser.add_argument(
        "--lost-timeout", type=float, default=2.0, metavar="SECONDS",
        help="expire the lock after this many seconds without a sighting (default: 2)",
    )
    args = parser.parse_args()
    if not math.isfinite(args.lost_timeout) or args.lost_timeout <= 0:
        parser.error("--lost-timeout must be a finite positive number")
    return args


def resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def open_camera(index: int) -> cv2.VideoCapture:
    if platform.system() == "Darwin":
        capture = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
    else:
        capture = cv2.VideoCapture(index)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return capture


def extract_people(result: object) -> list[Detection]:
    boxes = result.boxes
    if boxes is None or boxes.id is None:
        return []

    coordinates = boxes.xyxy.cpu().tolist()
    confidences = boxes.conf.cpu().tolist()
    track_ids = boxes.id.int().cpu().tolist()
    return [
        Detection(track_id, confidence, *coordinates)
        for track_id, confidence, coordinates in zip(
            track_ids, confidences, coordinates, strict=True
        )
    ]


def draw_box(
    frame: object,
    detection: Detection,
    color: tuple[int, int, int],
    thickness: int,
    prefix: str = "ID",
) -> None:
    x1, y1, x2, y2 = map(
        int, (detection.x1, detection.y1, detection.x2, detection.y2)
    )
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    label = f"{prefix} {detection.track_id}  {detection.confidence:.2f}"
    cv2.putText(
        frame,
        label,
        (x1, max(24, y1 - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        color,
        2,
        cv2.LINE_AA,
    )


def main() -> None:
    args = parse_args()
    device = resolve_device(args.device)
    model = YOLO(args.model)
    capture = open_camera(args.camera)
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open camera {args.camera}")

    state = TargetState(lost_timeout=args.lost_timeout)
    smoothed_fps = 0.0
    previous_time = time.perf_counter()

    def on_mouse(event: int, x: int, y: int, _flags: int, _data: object) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            state.pending_click = (x, y)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError("Camera stopped returning frames")

            result = model.track(
                frame,
                persist=True,
                classes=[0],
                tracker=args.tracker,
                conf=args.confidence,
                device=device,
                verbose=False,
            )[0]
            detections = extract_people(result)
            now = time.monotonic()

            if state.pending_click is not None:
                selected = select_detection(detections, *state.pending_click)
                state.pending_click = None
                if selected is not None:
                    state.lock(selected.track_id, now)

            target = state.update(detections, now)

            for detection in detections:
                if detection.track_id != state.target_id:
                    draw_box(frame, detection, (180, 180, 180), 1)

            if state.target_id is None:
                status = "SELECT: click on a person"
                status_color = (0, 215, 255)
            elif target is None:
                status = (
                    f"LOST: target {state.target_id} missing "
                    f"({state.missing_frames} frames)"
                )
                status_color = (0, 0, 255)
            else:
                draw_box(frame, target, (0, 255, 0), 3, prefix="TARGET")
                error_x, height_ratio = target_signals(
                    target, frame.shape[1], frame.shape[0]
                )
                status = (
                    f"TRACKING ID {state.target_id} | "
                    f"error_x={error_x:+.2f} | size={height_ratio:.2f}"
                )
                status_color = (0, 255, 0)

            current_time = time.perf_counter()
            instantaneous_fps = 1.0 / max(current_time - previous_time, 1e-6)
            previous_time = current_time
            smoothed_fps = (
                instantaneous_fps
                if smoothed_fps == 0
                else 0.9 * smoothed_fps + 0.1 * instantaneous_fps
            )

            cv2.rectangle(frame, (0, 0), (frame.shape[1], 44), (20, 20, 20), -1)
            cv2.putText(
                frame,
                f"{status} | {smoothed_fps:.1f} FPS",
                (12, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.68,
                status_color,
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                frame,
                "click: lock/replace | r: reset | q: quit",
                (12, frame.shape[0] - 14),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.58,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("r"):
                state.clear()
    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
