from __future__ import annotations

import struct
from pathlib import Path

import numpy as np


def parse_sync_file(sync_path: str | Path) -> list[tuple[str, str]]:
    pairs = []
    with Path(sync_path).open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line or (i == 0 and not line[0].isdigit()):
                continue
            parts = line.split()
            if len(parts) == 2:
                pairs.append((parts[0], parts[1]))
    return pairs


def load_pcd_ascii(pcd_path: str | Path) -> np.ndarray:
    points = []
    data_start = False
    with Path(pcd_path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line == "DATA ascii":
                data_start = True
                continue
            if data_start and line:
                parts = line.split()
                if len(parts) >= 3:
                    points.append([float(parts[0]), float(parts[1]), float(parts[2])])
    if not points:
        return np.empty((0, 3), dtype=float)
    return np.array(points, dtype=float)


def inflate_points(points: np.ndarray, radius: float = 0.1) -> np.ndarray:
    if points.shape[0] == 0 or radius <= 0:
        return points
    offsets = []
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            for dz in [-1, 0, 1]:
                if dx == 0 and dy == 0 and dz == 0:
                    continue
                norm = np.sqrt(dx**2 + dy**2 + dz**2)
                offsets.append([dx / norm * radius, dy / norm * radius, dz / norm * radius])
    return np.vstack([points] + [points + off for off in np.array(offsets)])


def write_colored_pcd(path: str | Path, points: np.ndarray, r: int, g: int, b: int) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = points.shape[0]
    rgb_int = (r << 16) | (g << 8) | b
    rgb_float = struct.unpack("f", struct.pack("I", rgb_int))[0]
    with path.open("w", encoding="utf-8") as f:
        f.write("# .PCD v0.7 - Point Cloud Data file format\n")
        f.write("VERSION 0.7\n")
        f.write("FIELDS x y z rgb\n")
        f.write("SIZE 4 4 4 4\n")
        f.write("TYPE F F F F\n")
        f.write("COUNT 1 1 1 1\n")
        f.write(f"WIDTH {n}\n")
        f.write("HEIGHT 1\n")
        f.write("VIEWPOINT 0 0 0 1 0 0 0\n")
        f.write(f"POINTS {n}\n")
        f.write("DATA ascii\n")
        for point in points:
            f.write(f"{point[0]:.6f} {point[1]:.6f} {point[2]:.6f} {rgb_float}\n")
