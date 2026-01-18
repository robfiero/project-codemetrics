#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set


DEFAULT_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules",
    "target", "build", "dist", "out",
    ".idea", ".vscode",
    ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache",
    ".gradle", ".mvn",
    "coverage", ".coverage",
}

PROFILE_EXTS = {
    "java": {".java", ".kt", ".groovy", ".gradle", ".xml", ".properties", ".yml", ".yaml", ".md", ".txt"},
    "python": {".py", ".pyi", ".toml", ".ini", ".cfg", ".yml", ".yaml", ".md", ".txt"},
    "js": {".js", ".jsx", ".ts", ".tsx", ".json", ".css", ".scss", ".html", ".md", ".txt", ".yml", ".yaml"},
    "all": set(),
}

C_LIKE_EXTS = {".java", ".kt", ".groovy", ".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".c", ".cc", ".cpp", ".h", ".hpp"}
HASH_COMMENT_EXTS = {".py", ".pyi", ".sh", ".zsh", ".bash", ".yaml", ".yml", ".toml", ".ini", ".cfg"}

_TEST_DIR_HINTS = {"test", "tests", "__tests__", "spec", "specs", "testing"}
_JS_TEST_EXTS = {".js", ".jsx", ".ts", ".tsx"}
_PY_TEST_EXTS = {".py", ".pyi"}
_JAVA_TEST_EXTS = {".java", ".kt", ".groovy"}

_JS_TEST_NAME_RE = re.compile(r".*(\.test|\.spec)\.(js|jsx|ts|tsx)$", re.IGNORECASE)
_PY_TEST_NAME_RE = re.compile(r"^(test_.*|.*_test)\.(py|pyi)$", re.IGNORECASE)
_JAVA_TEST_NAME_RE = re.compile(r".*(Test|Tests|IT|ITCase)\.(java|kt|groovy)$", re.IGNORECASE)


def is_test_file(path: Path, profile: str) -> bool:
    ext = path.suffix.lower()
    name = path.name
    parts = [p.lower() for p in path.parts]

    if any(seg in _TEST_DIR_HINTS for seg in parts):
        return True

    if profile in {"js", "all"} and ext in _JS_TEST_EXTS and _JS_TEST_NAME_RE.match(name):
        return True

    if profile in {"python", "all"} and ext in _PY_TEST_EXTS and _PY_TEST_NAME_RE.match(name):
        return True

    if profile in {"java", "all"} and ext in _JAVA_TEST_EXTS and _JAVA_TEST_NAME_RE.match(name):
        return True

    if re.search(r"(?:^|/)(?:src/)?(?:test|tests)/", str(path).replace("\\", "/"), re.IGNORECASE):
        return True

    return False


# --- Self exclusion (Option 1, fixed) --------------------------------------

def get_self_files() -> Set[Path]:
    """
    Exclude the tool files:
      - this python file (__file__)
      - wrapper path provided via env var (PROJMETRICS_EXCLUDE_SELF)
    """
    files: Set[Path] = set()

    # This python script
    try:
        files.add(Path(__file__).resolve())
    except Exception:
        pass

    # Wrapper path (reliably provided by wrapper)
    wrapper = os.environ.get("PROJMETRICS_EXCLUDE_SELF", "").strip()
    if wrapper:
        try:
            files.add(Path(wrapper).resolve())
        except Exception:
            pass

    return files


@dataclass
class LineCounts:
    total: int = 0
    blank: int = 0
    comment: int = 0
    code: int = 0

    def add(self, other: "LineCounts") -> None:
        self.total += other.total
        self.blank += other.blank
        self.comment += other.comment
        self.code += other.code


@dataclass
class FileMetrics:
    path: Path
    size_bytes: int
    lines_total: int


@dataclass
class Totals:
    files: int = 0
    bytes: int = 0
    lines: LineCounts = field(default_factory=LineCounts)
    by_ext_files: Dict[str, int] = field(default_factory=dict)
    by_ext_lines: Dict[str, LineCounts] = field(default_factory=dict)


@dataclass
class TestTotals:
    test_files: int = 0
    non_test_files: int = 0
    test_lines: LineCounts = field(default_factory=LineCounts)
    non_test_lines: LineCounts = field(default_factory=LineCounts)


def human_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    x = float(n)
    for u in units:
        if x < 1024.0 or u == units[-1]:
            return f"{x:.1f} {u}" if u != "B" else f"{int(x)} {u}"
        x /= 1024.0
    return f"{n} B"


def detect_text_file(path: Path, sniff_bytes: int = 8192) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(sniff_bytes)
        return b"\x00" not in chunk
    except Exception:
        return False


def count_lines_with_heuristics(path: Path) -> Optional[LineCounts]:
    if not detect_text_file(path):
        return None

    ext = path.suffix.lower()
    counts = LineCounts()

    in_block_comment = False
    in_py_triple = False
    py_triple_delim = None

    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                counts.total += 1
                stripped = raw.rstrip("\n").strip()

                if stripped == "":
                    counts.blank += 1
                    continue

                if ext in {".py", ".pyi"}:
                    if not in_py_triple:
                        if stripped in {"'''", '"""'}:
                            in_py_triple = True
                            py_triple_delim = stripped
                            counts.comment += 1
                            continue
                    else:
                        counts.comment += 1
                        if py_triple_delim and stripped.endswith(py_triple_delim):
                            in_py_triple = False
                            py_triple_delim = None
                        continue

                if ext in C_LIKE_EXTS:
                    if in_block_comment:
                        counts.comment += 1
                        if "*/" in stripped:
                            in_block_comment = False
                        continue
                    if stripped.startswith("//"):
                        counts.comment += 1
                        continue
                    if stripped.startswith("/*"):
                        counts.comment += 1
                        if "*/" not in stripped:
                            in_block_comment = True
                        continue
                    counts.code += 1
                    continue

                if ext in HASH_COMMENT_EXTS:
                    if stripped.startswith("#"):
                        counts.comment += 1
                    else:
                        counts.code += 1
                    continue

                counts.code += 1

        return counts
    except Exception:
        return None


def should_skip_dir(dir_name: str, include_hidden: bool, default_excludes: bool, extra_excludes: Set[str]) -> bool:
    if not include_hidden and dir_name.startswith("."):
        return True
    if dir_name in extra_excludes:
        return True
    if default_excludes and dir_name in DEFAULT_EXCLUDE_DIRS:
        return True
    return False


def iter_files(root: Path, include_hidden: bool, default_excludes: bool, extra_excludes: Set[str]) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        for d in list(dirnames):
            if should_skip_dir(d, include_hidden, default_excludes, extra_excludes):
                dirnames.remove(d)
        for fn in filenames:
            if not include_hidden and fn.startswith("."):
                continue
            yield Path(dirpath) / fn


def ext_key(path: Path) -> str:
    e = path.suffix.lower()
    return e if e else "(no_ext)"


def pick_profile(args: argparse.Namespace) -> str:
    if args.java:
        return "java"
    if args.python:
        return "python"
    if args.js:
        return "js"
    return "all"


def pick_profile_exts(profile: str) -> Set[str]:
    return PROFILE_EXTS.get(profile, set())


def pct(numer: int, denom: int) -> str:
    if denom <= 0:
        return "0.0%"
    return f"{(numer * 100.0 / denom):.1f}%"


def main() -> int:
    ap = argparse.ArgumentParser(description="Project metrics: files, bytes, LOC (with basic comment heuristics).")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--java", action="store_true")
    g.add_argument("--python", action="store_true")
    g.add_argument("--js", action="store_true")
    g.add_argument("--all", action="store_true")

    ap.add_argument("--root", default=".")
    ap.add_argument("--include-hidden", action="store_true")
    ap.add_argument("--no-default-excludes", action="store_true")
    ap.add_argument("--exclude-dir", action="append", default=[])
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--only-profile-exts", action="store_true")
    ap.add_argument("--test-ratio", action="store_true")

    args = ap.parse_args()

    profile = pick_profile(args)
    profile_exts = pick_profile_exts(profile)

    root = Path(args.root).resolve()
    include_hidden = bool(args.include_hidden)
    default_excludes = not bool(args.no_default_excludes)
    extra_excludes = set(args.exclude_dir or [])
    top_n = max(0, int(args.top))

    restrict_to_profile = bool(args.only_profile_exts) and len(profile_exts) > 0

    self_files = get_self_files()

    totals = Totals()
    test_totals = TestTotals()
    unreadable_text_files = 0

    largest: List[FileMetrics] = []
    longest: List[FileMetrics] = []

    for p in iter_files(root, include_hidden, default_excludes, extra_excludes):
        try:
            if p.resolve() in self_files:
                continue
        except Exception:
            pass

        try:
            st = p.stat()
        except Exception:
            continue

        e = ext_key(p)
        if restrict_to_profile and e not in profile_exts:
            continue

        totals.files += 1
        totals.bytes += int(st.st_size)
        totals.by_ext_files[e] = totals.by_ext_files.get(e, 0) + 1

        lc = count_lines_with_heuristics(p)
        if lc is None:
            unreadable_text_files += 1
            continue

        totals.lines.add(lc)
        totals.by_ext_lines.setdefault(e, LineCounts()).add(lc)

        largest.append(FileMetrics(path=p, size_bytes=int(st.st_size), lines_total=lc.total))
        longest.append(FileMetrics(path=p, size_bytes=int(st.st_size), lines_total=lc.total))

        if args.test_ratio:
            rel = p
            try:
                rel = p.relative_to(root)
            except Exception:
                pass
            if is_test_file(rel, profile):
                test_totals.test_files += 1
                test_totals.test_lines.add(lc)
            else:
                test_totals.non_test_files += 1
                test_totals.non_test_lines.add(lc)

    largest.sort(key=lambda x: x.size_bytes, reverse=True)
    longest.sort(key=lambda x: x.lines_total, reverse=True)

    print(f"\nRoot: {root}")
    print(f"Profile: {profile}")
    print(f"Files counted: {totals.files}")
    print(f"Total size: {human_bytes(totals.bytes)}")
    print(f"Text files skipped (binary/unreadable): {unreadable_text_files}")
    print(f"Tool files excluded: {len(self_files)}")

    print("\nLine counts (heuristic):")
    print(f"  Total:   {totals.lines.total}")
    print(f"  Code:    {totals.lines.code}")
    print(f"  Comment: {totals.lines.comment}")
    print(f"  Blank:   {totals.lines.blank}")

    if args.test_ratio:
        print("\nTest ratio (heuristic):")
        total_text_files = test_totals.test_files + test_totals.non_test_files
        total_loc = test_totals.test_lines.total + test_totals.non_test_lines.total

        print(f"  Test files:     {test_totals.test_files} ({pct(test_totals.test_files, total_text_files)})")
        print(f"  Non-test files: {test_totals.non_test_files} ({pct(test_totals.non_test_files, total_text_files)})")
        print(f"  Test LOC:       {test_totals.test_lines.total} ({pct(test_totals.test_lines.total, total_loc)})")
        print(f"  Non-test LOC:   {test_totals.non_test_lines.total} ({pct(test_totals.non_test_lines.total, total_loc)})")

        total_code = test_totals.test_lines.code + test_totals.non_test_lines.code
        print(f"  Test code LOC:  {test_totals.test_lines.code} ({pct(test_totals.test_lines.code, total_code)})")
        print(f"  Non-test code:  {test_totals.non_test_lines.code} ({pct(test_totals.non_test_lines.code, total_code)})")

    print("\nBy extension:")
    exts_to_print = sorted(totals.by_ext_files.keys(), key=lambda k: totals.by_ext_files.get(k, 0), reverse=True)
    if len(profile_exts) > 0 and not restrict_to_profile:
        exts_to_print.sort(key=lambda k: (k not in profile_exts, -totals.by_ext_files.get(k, 0), k))

    for e in exts_to_print:
        fcount = totals.by_ext_files.get(e, 0)
        lc = totals.by_ext_lines.get(e)
        if lc:
            print(f"  {e:10} files={fcount:6}  lines={lc.total:9}  code={lc.code:9}  cmt={lc.comment:9}  blank={lc.blank:9}")
        else:
            print(f"  {e:10} files={fcount:6}  lines=   (binary/unreadable)")

    if top_n > 0:
        print(f"\nTop {top_n} largest files:")
        for fm in largest[:top_n]:
            rel = fm.path
            try:
                rel = fm.path.relative_to(root)
            except Exception:
                pass
            print(f"  {human_bytes(fm.size_bytes):>9}  {rel}")

        print(f"\nTop {top_n} longest files (by total lines):")
        for fm in longest[:top_n]:
            rel = fm.path
            try:
                rel = fm.path.relative_to(root)
            except Exception:
                pass
            print(f"  {fm.lines_total:>9} lines  {rel}")

    print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

