from __future__ import annotations

import csv
import json
import shutil
from collections import Counter
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1] / "extracted_assets"


def detect_audio_extension(data: bytes) -> str:
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return "m4a/mp4"
    if data.startswith(b"RIFF"):
        return "wav"
    if data.startswith(b"OggS"):
        return "ogg"
    if data.startswith(b"ID3"):
        return "mp3"
    if data.startswith(b"fLaC"):
        return "flac"
    return "unknown"


def main() -> int:
    json_root = ROOT / "data" / "json"
    json_root.mkdir(parents=True, exist_ok=True)

    json_copied = 0
    for source in sorted((ROOT / "text").glob("*")):
        if source.suffix.lower() not in {".txt", ".bytes"}:
            continue
        try:
            json.loads(source.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        target = json_root / f"{source.stem}.json"
        shutil.copy2(source, target)
        json_copied += 1

    image_results = []
    for image_path in sorted((ROOT / "images").rglob("*.png")):
        try:
            with Image.open(image_path) as image:
                image.verify()
            with Image.open(image_path) as image:
                width, height = image.size
            image_results.append(
                {
                    "path": str(image_path.relative_to(ROOT)),
                    "valid": True,
                    "width": width,
                    "height": height,
                }
            )
        except Exception as exc:
            image_results.append(
                {
                    "path": str(image_path.relative_to(ROOT)),
                    "valid": False,
                    "error": repr(exc),
                }
            )

    audio_results = []
    for audio_path in sorted((ROOT / "audio").glob("*")):
        data = audio_path.read_bytes()[:64]
        fmt = detect_audio_extension(data)
        audio_results.append(
            {
                "path": str(audio_path.relative_to(ROOT)),
                "bytes": audio_path.stat().st_size,
                "format": fmt,
                "valid": fmt != "unknown",
            }
        )

    font_results = []
    for font_path in sorted((ROOT / "fonts").glob("*")):
        data = font_path.read_bytes()[:16]
        valid = data.startswith(
            (b"\x00\x01\x00\x00", b"OTTO", b"ttcf", b"true", b"typ1")
        )
        font_results.append(
            {
                "path": str(font_path.relative_to(ROOT)),
                "bytes": font_path.stat().st_size,
                "valid": valid,
            }
        )

    mesh_results = []
    for mesh_path in sorted((ROOT / "meshes").glob("*.obj")):
        data = mesh_path.read_bytes()[:256]
        mesh_results.append(
            {
                "path": str(mesh_path.relative_to(ROOT)),
                "bytes": mesh_path.stat().st_size,
                "valid": b"\nv " in data or data.startswith(b"v ") or b"\r\nv " in data,
            }
        )

    statuses: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    with (ROOT / "manifest.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            statuses[row["status"]] += 1
            if row["error"]:
                errors[row["error"].split(" | ")[0]] += 1

    zero_files = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*")
        if path.is_file() and path.stat().st_size == 0
    ]
    all_files = [path for path in ROOT.rglob("*") if path.is_file()]
    validation = {
        "root": str(ROOT),
        "json_configs_created": json_copied,
        "file_count": len(all_files),
        "total_bytes": sum(path.stat().st_size for path in all_files),
        "zero_byte_files": zero_files,
        "manifest_statuses": dict(statuses),
        "manifest_error_kinds": dict(errors.most_common(20)),
        "images": {
            "count": len(image_results),
            "valid": sum(item["valid"] for item in image_results),
            "invalid": [item for item in image_results if not item["valid"]],
        },
        "audio": {
            "count": len(audio_results),
            "valid": sum(item["valid"] for item in audio_results),
            "items": audio_results,
        },
        "fonts": {
            "count": len(font_results),
            "valid": sum(item["valid"] for item in font_results),
            "items": font_results,
        },
        "meshes": {
            "count": len(mesh_results),
            "valid": sum(item["valid"] for item in mesh_results),
            "items": mesh_results,
        },
    }
    (ROOT / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
