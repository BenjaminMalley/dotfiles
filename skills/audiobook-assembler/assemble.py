#!/usr/bin/env python3
"""Assemble one audiobook: an ordered set of audio files -> one .m4b.

Encodes to AAC 128 kbps with one chapter marker per input file (named
from the file's title tag, else its filename stem) and writes title /
author / album / narrator / date metadata. With --remux a single input
that is already an .m4b is stream-copied instead of re-encoded.

Runs inside the audiobook-assembler container image (ffmpeg + ffprobe on
PATH); uses only the Python standard library.

Self-checks the output with ffprobe: codec, duration vs. the sum of the
inputs, chapter count, and required tags. Exits nonzero on any failure.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

TIMEOUT = 6 * 3600  # generous; long books encode single-threaded


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)


def probe(path: Path, entries: str = "format=duration:format_tags:stream=codec_name") -> dict:
    p = run(["ffprobe", "-v", "error", "-show_entries", entries,
             "-of", "json", str(path)])
    if p.returncode != 0:
        raise SystemExit(f"ffprobe failed on {path}: {p.stderr.strip()}")
    return json.loads(p.stdout)


def chapter_count(path: Path) -> int:
    return len(probe(path, "chapters").get("chapters", []))


def track_number(tags: dict) -> int | None:
    raw = tags.get("track")
    if not raw:
        return None
    m = re.match(r"\d+", raw)
    return int(m.group()) if m else None


def natural_key(path: Path):
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", path.name)]


def concat_escape(path: Path) -> str:
    # ffmpeg concat demuxer: single-quote the name, escape inner quotes.
    return str(path).replace("'", "'\\''")


def ffmetadata_escape(value: str) -> str:
    return re.sub(r"([=;#\\])", r"\\\1", value)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("-o", "--output", required=True, type=Path)
    ap.add_argument("--title", required=True)
    ap.add_argument("--author", required=True)
    ap.add_argument("--narrator")
    ap.add_argument("--date")
    ap.add_argument("--remux", action="store_true",
                    help="stream-copy a single .m4b input instead of "
                         "re-encoding (chapters preserved from source)")
    args = ap.parse_args()
    # The container entrypoint is python3 (no shell), so expand any
    # glob patterns (e.g. /in/*) ourselves.
    files = [Path(p) for a in args.files
             for p in (sorted(glob.glob(str(a))) or [str(a)])]
    if args.remux and len(files) != 1:
        raise SystemExit("--remux takes exactly one input file")

    # Order inputs: track tag first, then natural filename sort.
    infos = []
    for f in files:
        meta = probe(f)
        tags = {k.lower(): v for k, v in meta["format"].get("tags", {}).items()}
        infos.append({
            "path": f,
            "duration": float(meta["format"]["duration"]),
            "track": track_number(tags),
            "chapter": tags.get("title") or f.stem,
        })
    infos.sort(key=lambda i: (i["track"] is None,
                              i["track"] if i["track"] is not None else 0,
                              natural_key(i["path"])))
    total = math.fsum(i["duration"] for i in infos)
    expected_chapters = (chapter_count(infos[0]["path"]) if args.remux
                         else len(infos))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="asm-", dir=args.output.parent))
    part = args.output.with_suffix(args.output.suffix + ".part")
    try:
        cmd = ["ffmpeg", "-nostdin", "-v", "error"]
        if args.remux:
            cmd += ["-i", str(infos[0]["path"]), "-map", "0:a",
                    "-map_chapters", "0", "-c:a", "copy"]
        else:
            concat = work / "concat.txt"
            concat.write_text(
                "".join(f"file '{concat_escape(i['path'])}'\n" for i in infos))
            chapters = [";FFMETADATA1"]
            start = 0.0
            for i in infos:
                end = start + i["duration"]
                chapters += ["[CHAPTER]", "TIMEBASE=1/1000",
                             f"START={int(start * 1000)}",
                             f"END={int(end * 1000)}",
                             f"title={ffmetadata_escape(i['chapter'])}"]
                start = end
            meta_file = work / "chapters.txt"
            meta_file.write_text("\n".join(chapters) + "\n")
            cmd += ["-f", "concat", "-safe", "0", "-i", str(concat),
                    "-i", str(meta_file), "-map", "0:a", "-map_chapters", "1",
                    "-vn", "-c:a", "aac", "-b:a", "128k"]
        cmd += ["-metadata", f"title={args.title}",
                "-metadata", f"artist={args.author}",
                "-metadata", f"album={args.title}",
                "-metadata", "genre=Audiobook"]
        if args.narrator:
            cmd += ["-metadata", f"comment=Narrated by {args.narrator}"]
        if args.date:
            cmd += ["-metadata", f"date={args.date}"]
        cmd += ["-f", "mp4", str(part)]
        p = run(cmd)
        if p.returncode != 0:
            raise SystemExit(f"ffmpeg failed: {p.stderr.strip()}")

        # Self-check the product before publishing it.
        out = probe(part)
        problems = []
        if not args.remux and not any(s.get("codec_name") == "aac"
                                      for s in out.get("streams", [])):
            problems.append("no AAC stream in output")
        got = float(out["format"]["duration"])
        if abs(got - total) > 2:
            problems.append(f"duration {got:.1f}s != expected {total:.1f}s")
        tags = {k.lower(): v
                for k, v in out["format"].get("tags", {}).items()}
        if tags.get("title") != args.title or tags.get("artist") != args.author:
            problems.append("title/artist tags missing or wrong")
        n_chapters = chapter_count(part)
        if n_chapters != expected_chapters:
            problems.append(
                f"{n_chapters} chapters != {expected_chapters} expected")
        if problems:
            part.unlink(missing_ok=True)
            raise SystemExit("output failed self-check: " + "; ".join(problems))

        part.rename(args.output)
        print(f"OK {args.output} ({got / 3600:.2f}h, "
              f"{n_chapters} chapter(s){', remux' if args.remux else ''})")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
