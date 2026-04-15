from __future__ import annotations

import math
from pathlib import Path

import numpy as np


def load_matrix(path: str | Path) -> np.ndarray:
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            vals = [float(v) for v in line.split()]
            if len(vals) == 4:
                rows.append(vals)
    if len(rows) != 4:
        raise ValueError(f"expected 4 matrix rows in {path}, got {len(rows)}")
    return np.array(rows, dtype=float)


def save_matrix(path: str | Path, mat: np.ndarray) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in mat:
            f.write(" ".join(f"{v:.12f}" for v in row) + "\n")


def rotation_matrix(roll_deg: float = 0.0, pitch_deg: float = 0.0, yaw_deg: float = 0.0) -> np.ndarray:
    roll = math.radians(roll_deg)
    pitch = math.radians(pitch_deg)
    yaw = math.radians(yaw_deg)

    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)

    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]], dtype=float)
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]], dtype=float)
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]], dtype=float)
    return rz @ ry @ rx


def parse_values(values: list[str]) -> list[float]:
    parsed = []
    for value in values:
        parsed.extend(float(v) for v in value.split(",") if v.strip())
    return parsed


def variant_name(prefix: str, roll: float, pitch: float, yaw: float, dx: float, dy: float, dz: float) -> str:
    parts = [prefix]
    if roll:
        parts.append(f"roll_{roll:+.2f}deg")
    if pitch:
        parts.append(f"pitch_{pitch:+.2f}deg")
    if yaw:
        parts.append(f"yaw_{yaw:+.2f}deg")
    if dx:
        parts.append(f"dx_{dx:+.2f}m")
    if dy:
        parts.append(f"dy_{dy:+.2f}m")
    if dz:
        parts.append(f"dz_{dz:+.2f}m")
    if len(parts) == 1:
        parts.append("base")
    return "__".join(parts).replace("+", "p").replace("-", "m")


def apply_delta(
    base: np.ndarray,
    roll: float,
    pitch: float,
    yaw: float,
    dx: float,
    dy: float,
    dz: float,
    delta_frame: str,
) -> np.ndarray:
    mat = base.copy()
    delta_r = rotation_matrix(roll, pitch, yaw)
    base_r = base[:3, :3]
    if delta_frame == "lidar":
        mat[:3, :3] = delta_r @ base_r
    elif delta_frame == "radar":
        mat[:3, :3] = base_r @ delta_r
    else:
        raise ValueError(f"unsupported delta frame: {delta_frame}")
    mat[:3, 3] = base[:3, 3] + np.array([dx, dy, dz], dtype=float)
    return mat


def apply_transform(points: np.ndarray, transform: np.ndarray) -> np.ndarray:
    if points.shape[0] == 0:
        return points
    return (transform[:3, :3] @ points.T).T + transform[:3, 3]
