#!/usr/bin/env python3
"""
NEU-DET Training & Evaluation Pipeline
=======================================
End-to-end pipeline that:
  1. Converts Pascal VOC XML annotations → YOLO txt format
  2. Splits the dataset into train / val / test (70/20/10, stratified, seeded)
  3. Checks for image-hash duplicates and cross-split leakage
  4. Trains YOLO11n (ultralytics) on the train split
  5. Evaluates best.pt on the held-out test split and exports metrics

Usage
-----
    # Step 1 – Prepare dataset (convert + split + integrity checks)
    python train_eval_pipeline.py --prepare \
        --raw-images  ./archive_extracted/NEU-DET/IMAGES \
        --raw-annots  ./archive_extracted/NEU-DET/ANNOTATIONS \
        --output-dir  ./datasets/NEU-DET

    # Step 2 – Train
    python train_eval_pipeline.py --train \
        --data ./dataset_neu.yaml \
        --epochs 100 --batch 16 --imgsz 640

    # Step 3 – Evaluate a checkpoint on the test set
    python train_eval_pipeline.py --evaluate \
        --weights ./runs/detect/train/weights/best.pt \
        --data ./dataset_neu.yaml

Requirements
------------
    pip install ultralytics>=8.4 scikit-learn Pillow

Reproducibility
---------------
    Random seed : 42  (used for dataset splitting)
    Library     : ultralytics 8.4.x, Python 3.11, PyTorch 2.x
    Hardware    : NVIDIA GPU recommended; CPU fallback supported
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEED = 42
SPLIT_RATIOS = (0.70, 0.20, 0.10)  # train / val / test

CLASS_MAP: Dict[str, int] = {
    "crazing": 0,
    "inclusion": 1,
    "patches": 2,
    "pitted_surface": 3,
    "rolled-in_scale": 4,
    "scratches": 5,
}

IMG_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}


# ---------------------------------------------------------------------------
# 1. VOC XML → YOLO TXT conversion
# ---------------------------------------------------------------------------
def voc_xml_to_yolo(xml_path: Path, img_w: int = 200, img_h: int = 200) -> List[str]:
    """Parse a Pascal VOC XML and return YOLO-format label lines."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    size_el = root.find("size")
    if size_el is not None:
        img_w = int(size_el.findtext("width", str(img_w)))
        img_h = int(size_el.findtext("height", str(img_h)))

    lines: List[str] = []
    for obj in root.iter("object"):
        name = obj.findtext("name", "").strip()
        if name not in CLASS_MAP:
            print(f"  [WARN] Unknown class '{name}' in {xml_path.name}, skipping.")
            continue
        cls_id = CLASS_MAP[name]

        bndbox = obj.find("bndbox")
        xmin = float(bndbox.findtext("xmin"))  # type: ignore[union-attr]
        ymin = float(bndbox.findtext("ymin"))  # type: ignore[union-attr]
        xmax = float(bndbox.findtext("xmax"))  # type: ignore[union-attr]
        ymax = float(bndbox.findtext("ymax"))  # type: ignore[union-attr]

        # Convert to YOLO (cx, cy, w, h) normalised
        cx = ((xmin + xmax) / 2.0) / img_w
        cy = ((ymin + ymax) / 2.0) / img_h
        bw = (xmax - xmin) / img_w
        bh = (ymax - ymin) / img_h

        lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
    return lines


# ---------------------------------------------------------------------------
# 2. Dataset splitting (stratified by class prefix)
# ---------------------------------------------------------------------------
def split_dataset(
    images: List[Path],
    ratios: Tuple[float, float, float] = SPLIT_RATIOS,
    seed: int = SEED,
) -> Dict[str, List[Path]]:
    """Stratified split by the class prefix of the filename (e.g. 'crazing_1')."""
    from sklearn.model_selection import train_test_split

    # Extract class label from filename: "crazing_123.jpg" -> "crazing"
    labels = []
    for p in images:
        stem = p.stem  # e.g. "crazing_123"
        # Handle "rolled-in_scale_1" (hyphenated class name)
        for cls_name in sorted(CLASS_MAP.keys(), key=len, reverse=True):
            if stem.startswith(cls_name):
                labels.append(cls_name)
                break
        else:
            labels.append("unknown")

    train_ratio, val_ratio, test_ratio = ratios
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-9

    # First split: train vs (val+test)
    train_imgs, valtest_imgs, train_labels, valtest_labels = train_test_split(
        images, labels, test_size=(val_ratio + test_ratio),
        random_state=seed, stratify=labels,
    )

    # Second split: val vs test
    relative_test = test_ratio / (val_ratio + test_ratio)
    val_imgs, test_imgs = train_test_split(
        valtest_imgs, test_size=relative_test,
        random_state=seed, stratify=valtest_labels,
    )

    return {"train": train_imgs, "val": val_imgs, "test": test_imgs}


# ---------------------------------------------------------------------------
# 3. Duplicate / leakage checks
# ---------------------------------------------------------------------------
def file_hash(path: Path, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    h.update(path.read_bytes())
    return h.hexdigest()


def check_duplicates_and_leakage(
    splits: Dict[str, List[Path]],
) -> Tuple[List[str], bool]:
    """Return list of warning messages. If leakage found, second element is True."""
    messages: List[str] = []
    leakage_found = False

    # Compute hashes per split
    split_hashes: Dict[str, Dict[str, Path]] = {}
    for split_name, paths in splits.items():
        hashes: Dict[str, Path] = {}
        for p in paths:
            h = file_hash(p)
            if h in hashes:
                messages.append(
                    f"  [DUP] {split_name}: {p.name} == {hashes[h].name}"
                )
            hashes[h] = p
        split_hashes[split_name] = hashes

    # Cross-split leakage
    split_names = list(split_hashes.keys())
    for i, s1 in enumerate(split_names):
        for s2 in split_names[i + 1 :]:
            overlap = set(split_hashes[s1].keys()) & set(split_hashes[s2].keys())
            if overlap:
                leakage_found = True
                for h in overlap:
                    messages.append(
                        f"  [LEAK] {s1}/{split_hashes[s1][h].name} "
                        f"== {s2}/{split_hashes[s2][h].name}"
                    )

    return messages, leakage_found


# ---------------------------------------------------------------------------
# Prepare command
# ---------------------------------------------------------------------------
def cmd_prepare(args: argparse.Namespace) -> None:
    raw_images = Path(args.raw_images)
    raw_annots = Path(args.raw_annots)
    output_dir = Path(args.output_dir)

    print(f"[1/5] Scanning images in {raw_images} ...")
    all_images = sorted(
        p for p in raw_images.iterdir()
        if p.suffix.lower() in IMG_EXTENSIONS
    )
    print(f"       Found {len(all_images)} images.")

    # --- Convert annotations ---
    print("[2/5] Converting VOC XML → YOLO TXT ...")
    annot_map: Dict[str, List[str]] = {}
    missing_annots: List[str] = []
    for img_path in all_images:
        xml_path = raw_annots / (img_path.stem + ".xml")
        if not xml_path.exists():
            missing_annots.append(img_path.name)
            annot_map[img_path.stem] = []
            continue
        annot_map[img_path.stem] = voc_xml_to_yolo(xml_path)

    if missing_annots:
        print(f"  [WARN] {len(missing_annots)} images have no annotation XML.")

    total_boxes = sum(len(v) for v in annot_map.values())
    print(f"       Converted {total_boxes} bounding boxes across {len(annot_map)} images.")

    # --- Split ---
    print(f"[3/5] Splitting dataset (ratios={SPLIT_RATIOS}, seed={SEED}) ...")
    splits = split_dataset(all_images)
    for name, paths in splits.items():
        cls_counts = Counter()
        for p in paths:
            for cls_name in sorted(CLASS_MAP.keys(), key=len, reverse=True):
                if p.stem.startswith(cls_name):
                    cls_counts[cls_name] += 1
                    break
        print(f"  {name:5s}: {len(paths):4d} images  {dict(cls_counts)}")

    # --- Duplicate / leakage check ---
    print("[4/5] Checking for duplicates and cross-split leakage ...")
    warnings, has_leakage = check_duplicates_and_leakage(splits)
    if warnings:
        for w in warnings:
            print(w)
    if has_leakage:
        print("  *** LEAKAGE DETECTED — aborting. Fix duplicates first. ***")
        sys.exit(1)
    else:
        print("  ✓ No duplicates or leakage found.")

    # --- Write to disk ---
    print(f"[5/5] Writing YOLO dataset tree to {output_dir} ...")
    manifest_lines: List[str] = []

    for split_name, paths in splits.items():
        img_dir = output_dir / "images" / split_name
        lbl_dir = output_dir / "labels" / split_name
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        for src_img in paths:
            dst_img = img_dir / src_img.name
            shutil.copy2(src_img, dst_img)

            label_lines = annot_map.get(src_img.stem, [])
            dst_lbl = lbl_dir / (src_img.stem + ".txt")
            dst_lbl.write_text("\n".join(label_lines) + ("\n" if label_lines else ""))

            manifest_lines.append(f"{split_name}\t{src_img.name}\t{file_hash(src_img)}")

    # Write manifest
    manifest_path = output_dir / "split_manifest.tsv"
    manifest_path.write_text(
        "split\tfilename\tsha256\n" + "\n".join(sorted(manifest_lines)) + "\n"
    )
    print(f"  Manifest written to {manifest_path}")
    print("  Done ✓")


# ---------------------------------------------------------------------------
# Train command
# ---------------------------------------------------------------------------
def cmd_train(args: argparse.Namespace) -> None:
    from ultralytics import YOLO

    print("=" * 60)
    print("  NEU-DET YOLO11n Training")
    print("=" * 60)

    model = YOLO("yolo11n.pt")  # pretrained YOLO11n (nano)

    results = model.train(
        data=args.data,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        seed=SEED,
        patience=20,           # early stopping patience
        save=True,
        save_period=10,
        project="runs/detect",
        name="neu-det-yolo11n",
        exist_ok=True,
        # Augmentation (standard YOLO defaults)
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=0.0,
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        flipud=0.0,
        mosaic=1.0,
        mixup=0.0,
        copy_paste=0.0,
    )

    print("\n[INFO] Training complete.")
    print(f"[INFO] Best weights: runs/detect/neu-det-yolo11n/weights/best.pt")


# ---------------------------------------------------------------------------
# Evaluate command
# ---------------------------------------------------------------------------
def cmd_evaluate(args: argparse.Namespace) -> None:
    from ultralytics import YOLO

    print("=" * 60)
    print("  NEU-DET Evaluation on Test Set")
    print("=" * 60)

    model = YOLO(args.weights)

    metrics = model.val(
        data=args.data,
        split="test",
        batch=args.batch,
        imgsz=args.imgsz,
        save_json=True,
        project="runs/detect",
        name="neu-det-eval",
        exist_ok=True,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("  EVALUATION RESULTS")
    print("=" * 60)

    # Overall metrics
    print(f"\n  mAP@0.5      : {metrics.box.map50:.4f}")
    print(f"  mAP@0.5:0.95 : {metrics.box.map:.4f}")

    # Per-class
    class_names = list(CLASS_MAP.keys())
    print(f"\n  {'Class':<20s} {'P':>8s} {'R':>8s} {'mAP50':>8s} {'mAP50-95':>8s}")
    print("  " + "-" * 54)

    ap50_per_class = metrics.box.ap50
    ap_per_class = metrics.box.ap
    p_per_class = metrics.box.p
    r_per_class = metrics.box.r

    for i, cls_name in enumerate(class_names):
        if i < len(ap50_per_class):
            print(
                f"  {cls_name:<20s} "
                f"{p_per_class[i]:>8.4f} "
                f"{r_per_class[i]:>8.4f} "
                f"{ap50_per_class[i]:>8.4f} "
                f"{ap_per_class[i]:>8.4f}"
            )

    print("  " + "-" * 54)
    mp = metrics.box.mp
    mr = metrics.box.mr
    print(f"  {'ALL (mean)':<20s} {mp:>8.4f} {mr:>8.4f} {metrics.box.map50:>8.4f} {metrics.box.map:>8.4f}")

    # F1
    f1 = 2 * mp * mr / (mp + mr) if (mp + mr) > 0 else 0.0
    print(f"\n  F1 (macro avg): {f1:.4f}")

    print(f"\n  Confusion matrix and result images saved to: runs/detect/neu-det-eval/")
    print("  Done ✓")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="NEU-DET YOLO11n Training & Evaluation Pipeline"
    )
    subparsers = parser.add_subparsers(dest="command")

    # -- prepare --
    p_prep = subparsers.add_parser("prepare", help="Convert VOC→YOLO, split, check integrity")
    p_prep.add_argument("--raw-images", required=True, help="Path to raw NEU-DET IMAGES folder")
    p_prep.add_argument("--raw-annots", required=True, help="Path to raw NEU-DET ANNOTATIONS folder")
    p_prep.add_argument("--output-dir", default="./datasets/NEU-DET", help="Output YOLO dataset dir")

    # -- train --
    p_train = subparsers.add_parser("train", help="Train YOLO11n on NEU-DET")
    p_train.add_argument("--data", default="./dataset_neu.yaml", help="Dataset YAML")
    p_train.add_argument("--epochs", type=int, default=100)
    p_train.add_argument("--batch", type=int, default=16)
    p_train.add_argument("--imgsz", type=int, default=640)

    # -- evaluate --
    p_eval = subparsers.add_parser("evaluate", help="Evaluate checkpoint on test set")
    p_eval.add_argument("--weights", required=True, help="Path to best.pt")
    p_eval.add_argument("--data", default="./dataset_neu.yaml", help="Dataset YAML")
    p_eval.add_argument("--batch", type=int, default=16)
    p_eval.add_argument("--imgsz", type=int, default=640)

    args = parser.parse_args()

    if args.command == "prepare":
        cmd_prepare(args)
    elif args.command == "train":
        cmd_train(args)
    elif args.command == "evaluate":
        cmd_evaluate(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
