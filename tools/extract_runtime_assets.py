from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import UnityPy


SAFE_NAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def safe_name(value: Any, fallback: str = "unnamed", limit: int = 120) -> str:
    text = str(value or "").strip()
    text = SAFE_NAME_RE.sub("_", text).strip(" .")
    if not text:
        text = fallback
    return text[:limit].rstrip(" .")


def snapshot_bytes(value: bytes) -> str:
    digest = hashlib.sha256(value).hexdigest()[:16]
    return f"<{len(value)} bytes sha256={digest}>"


def clean_tree(value: Any, depth: int = 0) -> Any:
    if depth > 40:
        return "<max-depth>"
    if isinstance(value, bytes):
        return snapshot_bytes(value)
    if isinstance(value, dict):
        return {str(k): clean_tree(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_tree(v, depth + 1) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, str) and len(value) > 20000:
            return value[:20000] + f"... <{len(value) - 20000} chars omitted>"
        return value
    return repr(value)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(clean_tree(value), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def source_label(path: Path) -> str:
    return safe_name(path.stem)


def unique_output(base: Path, stem: str, suffix: str, used: set[Path]) -> Path:
    candidate = base / f"{stem}{suffix}"
    counter = 2
    while candidate in used or candidate.exists():
        candidate = base / f"{stem}_{counter}{suffix}"
        counter += 1
    used.add(candidate)
    return candidate


def font_extension(data: bytes) -> str:
    if data.startswith(b"OTTO") or data.startswith(b"ttcf"):
        return ".otf"
    if data.startswith((b"\x00\x01\x00\x00", b"true")):
        return ".ttf"
    return ".bin"


def extract_one_bundle(
    source: Path,
    output_root: Path,
    manifest_rows: list[dict[str, Any]],
    used: set[Path],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    label = source_label(source)

    try:
        env = UnityPy.load(str(source))
    except Exception as exc:
        manifest_rows.append(
            {
                "source": str(source),
                "type": "BUNDLE",
                "name": source.name,
                "path_id": "",
                "status": "load_error",
                "outputs": "",
                "error": repr(exc),
            }
        )
        return counts

    for obj in env.objects:
        type_name = obj.type.name
        path_id = str(obj.path_id)
        counts[type_name] += 1
        outputs: list[Path] = []
        errors: list[str] = []
        name = ""

        try:
            name = str(obj.peek_name() or "")
        except Exception:
            pass

        try:
            asset = obj.read()
            name = str(getattr(asset, "m_Name", "") or name)
        except Exception as exc:
            asset = None
            errors.append(f"read: {exc}")

        stem = safe_name(name, f"{type_name}_{path_id}")
        base_stem = f"{safe_name(label, 'source', 60)}_{stem}_{path_id}"

        try:
            if asset is not None and type_name == "Texture2D":
                image = asset.image
                target = unique_output(output_root / "images" / "textures", base_stem, ".png", used)
                target.parent.mkdir(parents=True, exist_ok=True)
                image.save(target)
                outputs.append(target)
            elif asset is not None and type_name == "Sprite":
                image = asset.image
                target = unique_output(output_root / "images" / "sprites", base_stem, ".png", used)
                target.parent.mkdir(parents=True, exist_ok=True)
                image.save(target)
                outputs.append(target)
            elif asset is not None and type_name == "AudioClip":
                samples = getattr(asset, "samples", {}) or {}
                for sample_name, sample_data in samples.items():
                    sample_path = Path(str(sample_name))
                    suffix = sample_path.suffix or ".audio"
                    sample_stem = safe_name(sample_path.stem or stem)
                    target = unique_output(
                        output_root / "audio",
                        f"{safe_name(label, 'source', 60)}_{sample_stem}_{path_id}",
                        suffix,
                        used,
                    )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(bytes(sample_data))
                    outputs.append(target)
            elif asset is not None and type_name == "Font":
                data = bytes(getattr(asset, "m_FontData", b"") or b"")
                if data:
                    target = unique_output(
                        output_root / "fonts",
                        base_stem,
                        font_extension(data),
                        used,
                    )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    outputs.append(target)
            elif asset is not None and type_name == "Mesh":
                mesh_obj = asset.export()
                if isinstance(mesh_obj, bytes):
                    mesh_obj = mesh_obj.decode("utf-8", errors="replace")
                target = unique_output(output_root / "meshes", base_stem, ".obj", used)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(mesh_obj), encoding="utf-8")
                outputs.append(target)
            elif asset is not None and type_name in {"TextAsset", "MonoScript"}:
                data = getattr(asset, "m_Script", b"") or b""
                if isinstance(data, str):
                    suffix = ".cs" if type_name == "MonoScript" else ".txt"
                    raw = data.encode("utf-8")
                else:
                    raw = bytes(data)
                    suffix = ".cs" if type_name == "MonoScript" else ".txt"
                    try:
                        decoded = raw.decode("utf-8")
                        raw = decoded.encode("utf-8")
                    except UnicodeDecodeError:
                        suffix = ".bytes"
                if raw:
                    target = unique_output(output_root / "text", base_stem, suffix, used)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
                    outputs.append(target)

            try:
                tree = obj.read_typetree()
                tree_target = unique_output(
                    output_root / "metadata" / safe_name(type_name),
                    base_stem,
                    ".json",
                    used,
                )
                write_json(tree_target, tree)
                outputs.append(tree_target)
            except Exception as exc:
                errors.append(f"typetree: {exc}")

            try:
                raw_data = bytes(obj.get_raw_data())
                if raw_data:
                    raw_target = unique_output(
                        output_root / "raw" / safe_name(type_name),
                        base_stem,
                        ".bin",
                        used,
                    )
                    raw_target.parent.mkdir(parents=True, exist_ok=True)
                    raw_target.write_bytes(raw_data)
                    outputs.append(raw_target)
            except Exception as exc:
                errors.append(f"raw: {exc}")
        except Exception as exc:
            errors.append(f"export: {exc}")

        manifest_rows.append(
            {
                "source": str(source),
                "type": type_name,
                "name": name,
                "path_id": path_id,
                "status": "ok" if outputs else "metadata_only",
                "outputs": ";".join(str(p.relative_to(output_root)) for p in outputs),
                "error": " | ".join(errors),
            }
        )

    return counts


def read_wxapkg_header(path: Path) -> dict[str, Any]:
    data = path.read_bytes()[:32]
    result: dict[str, Any] = {
        "magic_hex": data[:8].hex(),
        "magic_ascii": "".join(chr(b) if 32 <= b < 127 else "." for b in data[:8]),
        "size": path.stat().st_size,
    }
    if len(data) >= 16:
        result["uint32_le_8_12"] = list(struct.unpack("<II", data[8:16]))
        result["uint32_be_8_12"] = list(struct.unpack(">II", data[8:16]))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Unity runtime cache assets.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    input_root = args.input.resolve()
    output_root = args.output.resolve()
    if not input_root.exists():
        print(f"Input does not exist: {input_root}", file=sys.stderr)
        return 2

    sources = sorted(
        path
        for path in input_root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".ab", ".bin", ".unity3d"}
    )
    if not sources:
        print(f"No Unity asset containers found under: {input_root}", file=sys.stderr)
        return 3

    output_root.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, Any]] = []
    used: set[Path] = set()
    type_counts: Counter[str] = Counter()
    source_status: list[dict[str, Any]] = []

    for index, source in enumerate(sources, start=1):
        print(f"[{index}/{len(sources)}] {source.relative_to(input_root)}")
        try:
            counts = extract_one_bundle(source, output_root, manifest_rows, used)
            source_status.append(
                {
                    "source": str(source),
                    "objects": sum(counts.values()),
                    "types": dict(sorted(counts.items())),
                }
            )
            type_counts.update(counts)
        except Exception as exc:
            source_status.append({"source": str(source), "error": repr(exc)})
            print(f"  error: {exc}", file=sys.stderr)

    manifest_path = output_root / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source", "type", "name", "path_id", "status", "outputs", "error"],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    package_headers = []
    for package in sorted(input_root.rglob("*.wxapkg")):
        package_headers.append({"path": str(package), **read_wxapkg_header(package)})

    output_files = [path for path in output_root.rglob("*") if path.is_file()]
    summary = {
        "input_root": str(input_root),
        "output_root": str(output_root),
        "sources": len(sources),
        "object_count": sum(type_counts.values()),
        "object_types": dict(sorted(type_counts.items())),
        "output_file_count": len(output_files),
        "output_bytes": sum(path.stat().st_size for path in output_files),
        "source_status": source_status,
        "wxapkg_headers": package_headers,
    }
    write_json(output_root / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
