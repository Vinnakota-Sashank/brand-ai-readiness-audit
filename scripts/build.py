#!/usr/bin/env python3
"""
build.py - Cross-platform packaging script for Brand AI-Readiness Audit Marketplace.
Creates brand-ai-readiness-audit.zip conforming to Marketplace distribution standards.
"""

import hashlib
import os
import shutil
import sys
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
PACKAGE_DIR = os.path.join(BUILD_DIR, "brand-ai-readiness-audit")
ZIP_NAME = "brand-ai-readiness-audit.zip"
ZIP_PATH = os.path.join(BUILD_DIR, ZIP_NAME)
ROOT_ZIP_PATH = os.path.join(PROJECT_ROOT, ZIP_NAME)
SHA_PATH = os.path.join(BUILD_DIR, f"{ZIP_NAME}.sha256")
ROOT_SHA_PATH = os.path.join(PROJECT_ROOT, f"{ZIP_NAME}.sha256")


def main():
    print("=== Building Marketplace Distribution Package ===")

    # 1. Clean build directory
    if os.path.exists(PACKAGE_DIR):
        shutil.rmtree(PACKAGE_DIR)
    os.makedirs(PACKAGE_DIR, exist_ok=True)

    # 2. Copy src/* into build/brand-ai-readiness-audit/
    print("Copying src to build/brand-ai-readiness-audit...")
    for item in os.listdir(SRC_DIR):
        src_item = os.path.join(SRC_DIR, item)
        dst_item = os.path.join(PACKAGE_DIR, item)
        if os.path.isdir(src_item):
            shutil.copytree(
                src_item,
                dst_item,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
            )
        else:
            shutil.copy2(src_item, dst_item)

    # 3. Clean any stray pycache or .pyc
    for root, dirs, files in os.walk(PACKAGE_DIR, topdown=False):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d))
        for f in files:
            if f.endswith(".pyc") or f == ".DS_Store":
                try:
                    os.remove(os.path.join(root, f))
                except OSError:
                    pass

    # 4. Create ZIP archive with single root folder 'brand-ai-readiness-audit/'
    print(f"Creating archive {ZIP_NAME}...")
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(PACKAGE_DIR):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, BUILD_DIR)
                # Ensure forward slashes in zip internal paths
                zip_path_str = rel_path.replace("\\", "/")
                zf.write(abs_path, zip_path_str)

    # 5. Compute SHA-256 Checksum
    hasher = hashlib.sha256()
    with open(ZIP_PATH, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    digest = hasher.hexdigest()

    sha_content = f"{digest}  {ZIP_NAME}\n"
    with open(SHA_PATH, "w", encoding="utf-8") as f:
        f.write(sha_content)

    # 6. Copy to project root
    shutil.copy2(ZIP_PATH, ROOT_ZIP_PATH)
    shutil.copy2(SHA_PATH, ROOT_SHA_PATH)

    size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
    print(f"Package built successfully: {ZIP_PATH} ({size_mb:.2f} MB)")
    print(f"SHA-256: {digest}")
    print("=== Build Complete ===")


if __name__ == "__main__":
    main()
