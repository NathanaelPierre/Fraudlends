#!/usr/bin/env python3
"""
Dump every text file under backend/ and frontend/ into one file.

Usage:
    python dump_all.py                    # writes fraudlens_dump.txt
    python dump_all.py -o out.txt         # custom output
    python dump_all.py --roots backend frontend web app
"""

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

# Directories to skip entirely
SKIP_DIRS = {
    ".git", ".hg", ".svn",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".venv", "venv", "env",
    ".idea", ".vscode", "dist", "build", ".next", ".nuxt", ".svelte-kit",
    ".tox", ".coverage", ".cache", ".parcel-cache",
    "coverage", ".turbo", "out",
    # ML model dirs — new since the AI layer
    "models", "weights", "checkpoints", "lora", "adapters",
    "hf_cache", "huggingface",
}

# File extensions we want (text files)
KEEP_EXTS = {
    ".py", ".pyi", ".txt", ".md", ".rst",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".html", ".css", ".scss", ".sass", ".less",
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte",
    ".sql", ".sh", ".bash", ".ps1",
    ".svg", ".env.example",
}

# Extensions that are always skipped, even if KEEP_EXTS contains them
SKIP_EXTS = {
    ".bin", ".safetensors", ".gguf", ".pt", ".pth", ".ckpt",
    ".onnx", ".h5", ".pkl", ".joblib", ".npz", ".npy",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".woff", ".woff2",
    ".ttf", ".otf", ".mp3", ".mp4", ".wav", ".pdf", ".zip", ".tar", ".gz",
}

# Specific filenames worth keeping
KEEP_NAMES = {
    "Dockerfile", "Makefile", "Procfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", ".gitignore", ".dockerignore",
    "requirements.txt", "pytest.ini", "setup.py", "pyproject.toml",
    "package.json", "tsconfig.json", "vite.config.ts", "vite.config.js",
    "next.config.js", "next.config.mjs", "tailwind.config.js", "tailwind.config.ts",
    ".eslintrc", ".eslintrc.json", ".prettierrc", ".editorconfig",
}

# Filenames to never dump (secrets)
SKIP_FILES = {
    ".env", ".env.local", ".env.production", ".env.development",
    ".env.staging", ".env.dev", ".env.ai",
    "secrets.json", "secrets.yaml", "secrets.yml",
    "credentials.json", "service-account.json",
}

# Secret-shaped line scan — flags lines that look like hardcoded secrets
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|pwd)\s*[:=]\s*[\"'][^\"']{16,}[\"']"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"xai-[a-zA-Z0-9]{20,}"),
    re.compile(r"hf_[a-zA-Z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
]

MAX_FILE_SIZE = 512 * 1024  # 512 KB


def is_text_file(path: Path) -> bool:
    if path.name in SKIP_FILES:
        return False
    if path.suffix.lower() in SKIP_EXTS:
        return False
    if path.name in KEEP_NAMES:
        return True
    return path.suffix.lower() in KEEP_EXTS


def looks_binary(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(8192)
        return b"\x00" in chunk
    except OSError:
        return True


def walk_root(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".")
        ]
        for name in sorted(filenames):
            p = Path(dirpath) / name
            if not is_text_file(p):
                continue
            if looks_binary(p):
                continue
            try:
                if p.stat().st_size > MAX_FILE_SIZE:
                    continue
            except OSError:
                continue
            yield p


def scan_for_secrets(rel_path: str, content: str, out) -> None:
    """Write warnings about secret-shaped lines to the manifest, without values."""
    for lineno, line in enumerate(content.splitlines(), 1):
        for pat in SECRET_PATTERNS:
            if pat.search(line):
                out.write(f"#   !! {rel_path}:{lineno} — possible secret, value redacted\n")
                break


def collect_files(roots):
    collected = []
    for root_arg in roots:
        root = Path(root_arg).resolve()
        if not root.exists():
            print(f"WARNING: root '{root}' does not exist, skipping", file=sys.stderr)
            continue
        if not root.is_dir():
            print(f"WARNING: root '{root}' is not a directory, skipping", file=sys.stderr)
            continue
        for p in walk_root(root):
            collected.append((root, p))
    return collected


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--roots", nargs="+",
        default=["backend", "frontend"],
        help="Root directories to dump (default: backend frontend)",
    )
    ap.add_argument("-o", "--output", default="fraudlens_dump.txt",
                    help="Output file (default: fraudlens_dump.txt)")
    args = ap.parse_args()

    collected = collect_files(args.roots)
    if not collected:
        print("ERROR: no files collected from any root", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output).resolve()
    files_written = 0
    total_bytes = 0
    secret_warnings = 0

    # First pass: load all content into memory (so we can write manifest first)
    loaded = []
    for root, p in collected:
        rel = f"{root.name}/{p.relative_to(root)}".replace("\\", "/")
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            loaded.append((rel, f"### [read error: {e}]"))
            continue
        loaded.append((rel, content))

    with out_path.open("w", encoding="utf-8", errors="replace") as out:
        out.write(f"# FraudLens dump\n")
        out.write(f"# Roots: {', '.join(args.roots)}\n")
        out.write(f"# Generated by dump_all.py\n")
        out.write("=" * 78 + "\n\n")

        # ── Manifest ────────────────────────────────────────────────────
        out.write("# FILE MANIFEST\n")
        for rel, content in loaded:
            lines = content.count("\n") + 1
            kb = len(content.encode("utf-8")) / 1024
            out.write(f"#   {rel:<70} {lines:>5} lines  {kb:>8.1f} KB\n")
        out.write(f"# Total: {len(loaded)} files\n")

        # ── Secret scan warnings ────────────────────────────────────────
        out.write("#\n# SECRET SCAN (values redacted):\n")
        for rel, content in loaded:
            for lineno, line in enumerate(content.splitlines(), 1):
                for pat in SECRET_PATTERNS:
                    if pat.search(line):
                        out.write(f"#   !! {rel}:{lineno} — possible secret\n")
                        secret_warnings += 1
                        break
        if secret_warnings == 0:
            out.write("#   (clean)\n")
        out.write("=" * 78 + "\n\n")

        # ── File contents ───────────────────────────────────────────────
        for rel, content in loaded:
            out.write("\n" + "=" * 78 + "\n")
            out.write(f"### FILE: {rel}\n")
            out.write("=" * 78 + "\n")
            out.write(content)
            if not content.endswith("\n"):
                out.write("\n")

            files_written += 1
            total_bytes += len(content.encode("utf-8"))

    size_kb = out_path.stat().st_size / 1024
    print(f"Wrote {files_written} files -> {out_path}")
    print(f"Total: {size_kb:.1f} KB")
    if secret_warnings:
        print(f"WARNING: {secret_warnings} possible secret(s) flagged — check manifest!")


if __name__ == "__main__":
    main()