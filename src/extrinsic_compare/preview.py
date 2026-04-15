from __future__ import annotations

import struct
import zlib
from pathlib import Path

import numpy as np


AXES = {
    "xy": (0, 1),
    "xz": (0, 2),
    "yz": (1, 2),
}


def _write_png(path: str | Path, image: np.ndarray) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    height, width, channels = image.shape
    if channels != 3:
        raise ValueError("PNG image must be RGB")

    raw_rows = [b"\x00" + image[row].astype(np.uint8).tobytes() for row in range(height)]
    raw = b"".join(raw_rows)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, level=6))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def write_preview_png(
    path: str | Path,
    radar_points: np.ndarray,
    lidar_points: np.ndarray,
    *,
    view: str = "xy",
    size: int = 1200,
    point_size: int = 2,
) -> None:
    if view not in AXES:
        raise ValueError(f"unsupported preview view: {view}")
    if size < 128:
        raise ValueError("preview image size must be at least 128")
    if point_size < 1:
        raise ValueError("preview point size must be at least 1")

    axis_a, axis_b = AXES[view]
    clouds = [
        (lidar_points, np.array([50, 220, 80], dtype=np.float32)),
        (radar_points, np.array([255, 60, 60], dtype=np.float32)),
    ]
    valid_clouds = []
    for points, color in clouds:
        if points.size == 0:
            continue
        projected = points[:, [axis_a, axis_b]]
        projected = projected[np.all(np.isfinite(projected), axis=1)]
        if projected.size:
            valid_clouds.append((projected, color))

    image = np.full((size, size, 3), 18, dtype=np.uint8)
    if not valid_clouds:
        _write_png(path, image)
        return

    combined = np.vstack([points for points, _ in valid_clouds])
    mins = combined.min(axis=0)
    maxs = combined.max(axis=0)
    span = maxs - mins
    span[span == 0] = 1.0
    padding = span.max() * 0.05
    mins -= padding
    maxs += padding
    span = maxs - mins

    margin = max(16, size // 40)
    drawable = size - margin * 2
    scale = drawable / span.max()
    used = span * scale
    offset = np.array(
        [
            margin + (drawable - used[0]) / 2,
            margin + (drawable - used[1]) / 2,
        ]
    )

    grid_color = np.array([42, 42, 42], dtype=np.uint8)
    for frac in np.linspace(0.0, 1.0, 5):
        pos = int(round(margin + drawable * frac))
        image[margin : size - margin, pos : pos + 1] = grid_color
        image[pos : pos + 1, margin : size - margin] = grid_color

    radius = max(0, point_size // 2)
    for projected, color in valid_clouds:
        px = ((projected[:, 0] - mins[0]) * scale + offset[0]).round().astype(int)
        py = (size - 1 - ((projected[:, 1] - mins[1]) * scale + offset[1])).round().astype(int)
        keep = (px >= 0) & (px < size) & (py >= 0) & (py < size)
        for x, y in zip(px[keep], py[keep]):
            x0 = max(0, x - radius)
            x1 = min(size, x + radius + 1)
            y0 = max(0, y - radius)
            y1 = min(size, y + radius + 1)
            current = image[y0:y1, x0:x1].astype(np.float32)
            image[y0:y1, x0:x1] = np.clip(current * 0.35 + color * 0.65, 0, 255).astype(np.uint8)

    _write_png(path, image)
