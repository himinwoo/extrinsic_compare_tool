from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

from .cloudcompare import find_cloudcompare
from .pcd import inflate_points, load_pcd_ascii, parse_sync_file, write_colored_pcd
from .transforms import apply_delta, apply_transform, load_matrix, parse_values, save_matrix, variant_name


def add_dataset_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data-dir", required=True, help="Dataset root directory.")
    parser.add_argument("--sync-file", default="radar_Continental_lidar_Hesai.txt")
    parser.add_argument("--radar-dir", default="radar_Continental")
    parser.add_argument("--lidar-dir", default="lidar_Hesai")
    parser.add_argument("--start-idx", type=int, default=0)
    parser.add_argument("--num-frames", type=int, default=10)
    parser.add_argument("--step", type=int, default=50)
    parser.add_argument("--merge", action="store_true", help="Merge selected frames into one radar/lidar pair.")
    parser.add_argument("--filter-z", type=float, default=None)
    parser.add_argument("--inflate-radius", type=float, default=0.1)


def cmd_variants(args: argparse.Namespace) -> int:
    base = load_matrix(args.base)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    created = []

    for roll in parse_values(args.roll):
        for pitch in parse_values(args.pitch):
            for yaw in parse_values(args.yaw):
                for dx in parse_values(args.dx):
                    for dy in parse_values(args.dy):
                        for dz in parse_values(args.dz):
                            mat = apply_delta(base, roll, pitch, yaw, dx, dy, dz, args.delta_frame)
                            name = variant_name(args.prefix, roll, pitch, yaw, dx, dy, dz)
                            path = out_dir / f"{name}.txt"
                            save_matrix(path, mat)
                            created.append(path)

    print(f"generated {len(created)} files in {out_dir}")
    for path in created:
        print(path)
    return 0


def render_dataset(
    data_dir: Path,
    sync_file: str,
    radar_dir_name: str,
    lidar_dir_name: str,
    transform_file: str | None,
    output_dir: Path,
    start_idx: int,
    num_frames: int,
    step: int,
    merge: bool,
    filter_z: float | None,
    inflate_radius: float,
) -> list[Path]:
    sync_path = data_dir / sync_file
    radar_dir = data_dir / radar_dir_name
    lidar_dir = data_dir / lidar_dir_name
    transform = load_matrix(transform_file) if transform_file else None

    pairs = parse_sync_file(sync_path)
    indices = list(range(start_idx, len(pairs), step))[:num_frames]
    print(f"[INFO] sync pairs: {len(pairs)}, selected: {indices}")

    output_dir.mkdir(parents=True, exist_ok=True)
    cc_files = []
    all_radar = []
    all_lidar = []

    for fnum, idx in enumerate(indices):
        radar_stamp, lidar_stamp = pairs[idx]
        radar_pcd = radar_dir / f"{radar_stamp}.pcd"
        lidar_pcd = lidar_dir / f"{lidar_stamp}.pcd"
        if not radar_pcd.exists():
            print(f"[WARN] missing radar: {radar_pcd}")
            continue
        if not lidar_pcd.exists():
            print(f"[WARN] missing lidar: {lidar_pcd}")
            continue

        radar_pts = load_pcd_ascii(radar_pcd)
        raw_count = radar_pts.shape[0]
        if filter_z is not None and radar_pts.shape[0] > 0:
            radar_pts = radar_pts[radar_pts[:, 2] >= filter_z]
        if transform is not None:
            radar_pts = apply_transform(radar_pts, transform)
        radar_pts = inflate_points(radar_pts, inflate_radius)

        lidar_pts = load_pcd_ascii(lidar_pcd)
        lidar_pts = lidar_pts[~np.all(lidar_pts == 0, axis=1)]
        print(f"[{fnum + 1}] radar {raw_count} -> {radar_pts.shape[0]}, lidar {lidar_pts.shape[0]}")

        if merge:
            all_radar.append(radar_pts)
            all_lidar.append(lidar_pts)
        else:
            radar_out = output_dir / f"f{fnum:03d}_radar.pcd"
            lidar_out = output_dir / f"f{fnum:03d}_lidar.pcd"
            write_colored_pcd(radar_out, radar_pts, 255, 50, 50)
            write_colored_pcd(lidar_out, lidar_pts, 50, 255, 50)
            cc_files.extend([radar_out, lidar_out])

    if merge:
        if not all_radar and not all_lidar:
            raise RuntimeError("no valid frame pairs")
        merged_radar = np.vstack(all_radar) if all_radar else np.empty((0, 3))
        merged_lidar = np.vstack(all_lidar) if all_lidar else np.empty((0, 3))
        radar_out = output_dir / "merged_radar.pcd"
        lidar_out = output_dir / "merged_lidar.pcd"
        write_colored_pcd(radar_out, merged_radar, 255, 50, 50)
        write_colored_pcd(lidar_out, merged_lidar, 50, 255, 50)
        cc_files = [radar_out, lidar_out]

    if not cc_files:
        raise RuntimeError("no valid frame pairs")
    return cc_files


def cmd_view(args: argparse.Namespace) -> int:
    cc_files = render_dataset(
        data_dir=Path(args.data_dir),
        sync_file=args.sync_file,
        radar_dir_name=args.radar_dir,
        lidar_dir_name=args.lidar_dir,
        transform_file=args.transform_file,
        output_dir=Path(args.output_dir),
        start_idx=args.start_idx,
        num_frames=args.num_frames,
        step=args.step,
        merge=args.merge,
        filter_z=args.filter_z,
        inflate_radius=args.inflate_radius,
    )
    print(f"[INFO] wrote {len(cc_files)} PCD files under {args.output_dir}")

    if args.no_launch:
        return 0

    cc_cmd, cc_desc = find_cloudcompare()
    if cc_cmd is None:
        print("[ERROR] CloudCompare not found. Try: sudo snap install cloudcompare")
        return 1
    print(f"[INFO] launching {cc_desc}")
    subprocess.Popen(cc_cmd + [str(path) for path in cc_files])
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    transforms = sorted(Path(args.transforms_dir).glob("*.txt"))
    if not transforms:
        print(f"[ERROR] no transform .txt files in {args.transforms_dir}")
        return 1

    root = Path(args.output_dir)
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / "manifest.tsv"
    with manifest.open("w", encoding="utf-8") as f:
        f.write("name\ttransform\toutput_dir\n")
        for transform_path in transforms:
            out_dir = root / transform_path.stem
            print(f"\n[COMPARE] {transform_path.name}")
            render_dataset(
                data_dir=Path(args.data_dir),
                sync_file=args.sync_file,
                radar_dir_name=args.radar_dir,
                lidar_dir_name=args.lidar_dir,
                transform_file=str(transform_path),
                output_dir=out_dir,
                start_idx=args.start_idx,
                num_frames=args.num_frames,
                step=args.step,
                merge=args.merge,
                filter_z=args.filter_z,
                inflate_radius=args.inflate_radius,
            )
            f.write(f"{transform_path.stem}\t{transform_path}\t{out_dir}\n")

    print(f"\n[INFO] compare outputs: {root}")
    print(f"[INFO] manifest: {manifest}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare radar-lidar extrinsic candidates.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    variants = subparsers.add_parser("variants", help="Generate 4x4 transform variants.")
    variants.add_argument("--base", required=True)
    variants.add_argument("--out-dir", required=True)
    variants.add_argument("--yaw", nargs="*", default=["-2,-1.5,-1,-0.5,0.5,1,1.5,2"])
    variants.add_argument("--pitch", nargs="*", default=["0"])
    variants.add_argument("--roll", nargs="*", default=["0"])
    variants.add_argument("--dx", nargs="*", default=["0"])
    variants.add_argument("--dy", nargs="*", default=["0"])
    variants.add_argument("--dz", nargs="*", default=["0"])
    variants.add_argument("--prefix", default="radar_to_lidar")
    variants.add_argument("--delta-frame", choices=("lidar", "radar"), default="lidar")
    variants.set_defaults(func=cmd_variants)

    view = subparsers.add_parser("view", help="Create colored PCDs for one transform.")
    add_dataset_args(view)
    view.add_argument("--transform-file", default=None)
    view.add_argument("--output-dir", required=True)
    view.add_argument("--no-launch", action="store_true")
    view.set_defaults(func=cmd_view)

    compare = subparsers.add_parser("compare", help="Create comparable outputs for all transforms in a directory.")
    add_dataset_args(compare)
    compare.add_argument("--transforms-dir", required=True)
    compare.add_argument("--output-dir", required=True)
    compare.set_defaults(func=cmd_compare)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
