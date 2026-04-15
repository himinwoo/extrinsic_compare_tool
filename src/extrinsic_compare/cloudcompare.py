from __future__ import annotations

import shutil
import subprocess


def find_cloudcompare() -> tuple[list[str] | None, str | None]:
    for name in ["/snap/bin/cloudcompare", "cloudcompare", "CloudCompare", "ccViewer"]:
        path = shutil.which(name)
        if path:
            return [path], path

    try:
        result = subprocess.run(
            ["snap", "list", "cloudcompare"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            cmd = "cloudcompare.CloudCompare"
            return ["snap", "run", cmd], f"snap run {cmd}"
    except Exception:
        pass

    return None, None
