#!/usr/bin/env python3
"""
File Integrity Checker (CLI)

Usage:
  python file_integrity_checker.py init <path> --baseline baseline.json
  python file_integrity_checker.py check baseline.json
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

CHUNK_SIZE = 1024 * 1024  # 1 MB


def compute_hash(path: Path, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    with path.open("rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def scan_directory(base_dir: Path, recursive=True, algo="sha256"):
    base_dir = base_dir.resolve()
    result = {}

    files = base_dir.rglob("*") if recursive else base_dir.glob("*")

    for p in files:
        if p.is_file():
            try:
                stat = p.stat()
                result[str(p.relative_to(base_dir))] = {
                    "hash": compute_hash(p, algo),
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                }
            except Exception as e:
                result[str(p.relative_to(base_dir))] = {"error": str(e)}

    return result


def save_baseline(data, path: Path):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_baseline(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def compare(old, new):
    old_keys = set(old)
    new_keys = set(new)

    added = new_keys - old_keys
    deleted = old_keys - new_keys
    modified = []

    for k in old_keys & new_keys:
        if old[k].get("hash") != new[k].get("hash"):
            modified.append(k)

    return added, deleted, modified


def cmd_init(args):
    base = Path(args.target)
    data = {
        "_meta": {
            "base_dir": str(base),
            "created_at": time.time(),
            "algo": args.algo,
        },
        "files": scan_directory(base, args.recursive, args.algo),
    }
    save_baseline(data, Path(args.baseline))
    print(f"[+] Baseline created: {args.baseline}")


def cmd_check(args):
    baseline = load_baseline(Path(args.baseline))
    base_dir = Path(baseline["_meta"]["base_dir"])
    algo = baseline["_meta"]["algo"]

    new_scan = scan_directory(base_dir, True, algo)
    added, deleted, modified = compare(baseline["files"], new_scan)

    if not (added or deleted or modified):
        print("[+] No changes detected")
        sys.exit(0)

    if added:
        print("[+] Added files:", *added, sep="\n  ")
    if deleted:
        print("[-] Deleted files:", *deleted, sep="\n  ")
    if modified:
        print("[!] Modified files:", *modified, sep="\n  ")

    sys.exit(2)


def main():
    parser = argparse.ArgumentParser(description="File Integrity Checker")
    sub = parser.add_subparsers(required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("target")
    p_init.add_argument("--baseline", default="baseline.json")
    p_init.add_argument("--algo", default="sha256")
    p_init.add_argument("--recursive", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_check = sub.add_parser("check")
    p_check.add_argument("baseline")
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
