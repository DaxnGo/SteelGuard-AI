#!/usr/bin/env python3
"""Reproducible NEU-DET preparation, YOLO11n training, and evaluation.

Run from the repository root:

    python -m ai.train_eval_pipeline prepare --raw-images PATH --raw-annots PATH
    python -m ai.train_eval_pipeline train
    python -m ai.train_eval_pipeline evaluate --weights PATH

The dataset and generated ``runs`` directory stay outside Git. Safe audit and
evaluation summaries can be written to ``ai/evaluation`` for review.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import random
import shutil
import xml.etree.ElementTree as ET


SEED = 42
SPLIT_RATIOS = (0.70, 0.20, 0.10)
EXPECTED_IMAGES_PER_CLASS = 300
OFFICIAL_DATASET_URL = (
    "https://faculty.neu.edu.cn/songkc/en/zdylm/263270/list/index.htm"
)

CLASS_MAP: dict[str, int] = {
    "crazing": 0,
    "inclusion": 1,
    "patches": 2,
    "pitted_surface": 3,
    "rolled-in_scale": 4,
    "scratches": 5,
}
IMG_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}


def file_hash(path: Path, algo: str = "sha256") -> str:
    digest = hashlib.new(algo)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def class_name_for_image(path: Path) -> str:
    """Return the exact NEU-DET class encoded in an image filename."""

    for class_name in sorted(CLASS_MAP, key=len, reverse=True):
        if path.stem.startswith(f"{class_name}_"):
            return class_name
    raise ValueError(f"Image has no supported NEU-DET class prefix: {path.name}")


def voc_xml_to_yolo(xml_path: Path) -> list[str]:
    """Convert one validated Pascal VOC annotation to YOLO label rows."""

    root = ET.parse(xml_path).getroot()
    size = root.find("size")
    if size is None:
        raise ValueError(f"Annotation has no image size: {xml_path.name}")
    try:
        image_width = int(size.findtext("width", ""))
        image_height = int(size.findtext("height", ""))
    except ValueError as exc:
        raise ValueError(f"Annotation has an invalid image size: {xml_path.name}") from exc
    if image_width <= 0 or image_height <= 0:
        raise ValueError(f"Annotation has an invalid image size: {xml_path.name}")

    rows: list[str] = []
    for obj in root.iter("object"):
        class_name = obj.findtext("name", "").strip()
        if class_name not in CLASS_MAP:
            raise ValueError(
                f"Unsupported annotation class {class_name!r}: {xml_path.name}"
            )
        box = obj.find("bndbox")
        if box is None:
            raise ValueError(f"Annotation object has no box: {xml_path.name}")
        try:
            xmin = float(box.findtext("xmin", ""))
            ymin = float(box.findtext("ymin", ""))
            xmax = float(box.findtext("xmax", ""))
            ymax = float(box.findtext("ymax", ""))
        except ValueError as exc:
            raise ValueError(f"Annotation has an invalid box: {xml_path.name}") from exc
        if not (
            0 <= xmin < xmax <= image_width
            and 0 <= ymin < ymax <= image_height
        ):
            raise ValueError(f"Annotation box is outside the image: {xml_path.name}")

        center_x = ((xmin + xmax) / 2.0) / image_width
        center_y = ((ymin + ymax) / 2.0) / image_height
        box_width = (xmax - xmin) / image_width
        box_height = (ymax - ymin) / image_height
        row = (
            f"{CLASS_MAP[class_name]} {center_x:.6f} {center_y:.6f} "
            f"{box_width:.6f} {box_height:.6f}"
        )
        if row not in rows:
            rows.append(row)

    if not rows:
        raise ValueError(f"Annotation has no defect objects: {xml_path.name}")
    return rows


def split_dataset(
    images: list[Path],
    ratios: tuple[float, float, float] = SPLIT_RATIOS,
    seed: int = SEED,
) -> dict[str, list[Path]]:
    """Create an input-order-independent stratified train/val/test split."""

    if len(ratios) != 3 or any(ratio <= 0 for ratio in ratios):
        raise ValueError("Split ratios must contain three positive values.")
    if abs(sum(ratios) - 1.0) > 1e-9:
        raise ValueError("Split ratios must sum to 1.0.")

    grouped: dict[str, list[Path]] = {name: [] for name in CLASS_MAP}
    for image in sorted(images):
        grouped[class_name_for_image(image)].append(image)

    train_ratio, val_ratio, _test_ratio = ratios
    result = {"train": [], "val": [], "test": []}
    rng = random.Random(seed)
    for class_name in CLASS_MAP:
        class_images = grouped[class_name]
        rng.shuffle(class_images)
        train_end = round(len(class_images) * train_ratio)
        val_end = round(len(class_images) * (train_ratio + val_ratio))
        result["train"].extend(class_images[:train_end])
        result["val"].extend(class_images[train_end:val_end])
        result["test"].extend(class_images[val_end:])

    return {name: sorted(paths) for name, paths in result.items()}


def deduplicate_images(
    images: list[Path],
) -> tuple[list[Path], list[dict[str, str]]]:
    """Keep the first filename for each exact image hash and audit exclusions."""

    retained: list[Path] = []
    excluded: list[dict[str, str]] = []
    seen: dict[str, Path] = {}
    for image in sorted(images):
        digest = file_hash(image)
        previous = seen.get(digest)
        if previous is None:
            seen[digest] = image
            retained.append(image)
            continue
        if class_name_for_image(previous) != class_name_for_image(image):
            raise ValueError(
                f"Identical images have conflicting classes: {previous.name}, {image.name}"
            )
        excluded.append(
            {"excluded": image.name, "kept": previous.name, "sha256": digest}
        )
    return retained, excluded


def check_duplicates_and_leakage(
    splits: dict[str, list[Path]],
) -> tuple[list[str], bool]:
    """Report exact duplicates; cross-split duplicates are labelled leakage."""

    messages: list[str] = []
    seen: dict[str, tuple[str, Path]] = {}
    for split_name in ("train", "val", "test"):
        for path in splits.get(split_name, []):
            digest = file_hash(path)
            previous = seen.get(digest)
            if previous is None:
                seen[digest] = (split_name, path)
                continue
            previous_split, previous_path = previous
            label = "LEAK" if previous_split != split_name else "DUP"
            messages.append(
                f"[{label}] {previous_split}/{previous_path.name} == "
                f"{split_name}/{path.name}"
            )
    return messages, bool(messages)


def ensure_empty_output_dir(output_dir: Path) -> None:
    """Refuse stale output instead of silently mixing incompatible splits."""

    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError(f"Output path is not a directory: {output_dir}")
    if output_dir.exists() and next(output_dir.iterdir(), None) is not None:
        raise ValueError(
            f"Output directory must be empty to prevent stale split files: {output_dir}"
        )


def macro_f1(precision: list[float], recall: list[float]) -> float:
    """Return the arithmetic mean of per-class F1 scores."""

    if len(precision) != len(recall):
        raise ValueError("Precision and recall must have the same length.")
    if not precision:
        return 0.0
    per_class = [
        2 * p_value * r_value / (p_value + r_value)
        if p_value + r_value > 0
        else 0.0
        for p_value, r_value in zip(precision, recall)
    ]
    return sum(per_class) / len(per_class)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cmd_prepare(args: argparse.Namespace) -> None:
    raw_images = Path(args.raw_images).resolve()
    raw_annots = Path(args.raw_annots).resolve()
    output_dir = Path(args.output_dir).resolve()
    ensure_empty_output_dir(output_dir)
    if not raw_images.is_dir() or not raw_annots.is_dir():
        raise ValueError("Raw image and annotation directories must both exist.")

    images = sorted(
        path
        for path in raw_images.iterdir()
        if path.is_file() and path.suffix.lower() in IMG_EXTENSIONS
    )
    class_counts = Counter(class_name_for_image(path) for path in images)
    expected_counts = Counter(
        {name: EXPECTED_IMAGES_PER_CLASS for name in CLASS_MAP}
    )
    if class_counts != expected_counts:
        raise ValueError(
            f"Expected 300 images for each NEU-DET class, found {dict(class_counts)}."
        )

    archive_sha256 = None
    if args.source_archive:
        source_archive = Path(args.source_archive).resolve()
        if not source_archive.is_file():
            raise ValueError(f"Source archive not found: {source_archive}")
        archive_sha256 = file_hash(source_archive)

    annotations: dict[str, list[str]] = {}
    duplicate_annotation_boxes_removed = 0
    duplicate_annotation_boxes: list[dict[str, int | str]] = []
    for image in images:
        xml_path = raw_annots / f"{image.stem}.xml"
        if not xml_path.is_file():
            raise ValueError(f"Missing annotation: {xml_path.name}")
        label_rows = voc_xml_to_yolo(xml_path)
        source_box_count = sum(
            1 for _object in ET.parse(xml_path).getroot().iter("object")
        )
        removed_boxes = source_box_count - len(label_rows)
        duplicate_annotation_boxes_removed += removed_boxes
        if removed_boxes:
            duplicate_annotation_boxes.append(
                {"annotation": xml_path.name, "removed": removed_boxes}
            )
        annotations[image.stem] = label_rows

    usable_images, excluded_duplicates = deduplicate_images(images)
    usable_class_counts = Counter(
        class_name_for_image(path) for path in usable_images
    )
    splits = split_dataset(usable_images)
    integrity_messages, integrity_failed = check_duplicates_and_leakage(splits)
    if integrity_failed:
        raise ValueError("Dataset integrity check failed:\n" + "\n".join(integrity_messages))

    manifest_rows: list[str] = []
    split_counts: dict[str, dict[str, int]] = {}
    for split_name, split_images in splits.items():
        image_dir = output_dir / "images" / split_name
        label_dir = output_dir / "labels" / split_name
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        split_counts[split_name] = dict(
            Counter(class_name_for_image(path) for path in split_images)
        )
        for source_image in split_images:
            shutil.copy2(source_image, image_dir / source_image.name)
            (label_dir / f"{source_image.stem}.txt").write_text(
                "\n".join(annotations[source_image.stem]) + "\n",
                encoding="ascii",
            )
            manifest_rows.append(
                f"{split_name}\t{source_image.name}\t{file_hash(source_image)}"
            )

    manifest_path = output_dir / "split_manifest.tsv"
    manifest_path.write_text(
        "split\tfilename\tsha256\n" + "\n".join(sorted(manifest_rows)) + "\n",
        encoding="ascii",
    )

    audit = {
        "dataset": "NEU-DET",
        "official_source": OFFICIAL_DATASET_URL,
        "license_status": "Not specified by the official source; permission required for production use.",
        "source_archive_sha256": archive_sha256,
        "images_total_source": len(images),
        "images_total_used": len(usable_images),
        "source_images_per_class": dict(class_counts),
        "used_images_per_class": dict(usable_class_counts),
        "split_ratios": {"train": 0.70, "val": 0.20, "test": 0.10},
        "split_seed": SEED,
        "split_counts": split_counts,
        "excluded_exact_duplicates": excluded_duplicates,
        "duplicate_check": (
            "Passed after deterministic exact-duplicate exclusion; "
            "no SHA-256 duplicates remain within or across splits."
        ),
        "duplicate_annotation_boxes_removed": duplicate_annotation_boxes_removed,
        "duplicate_annotation_boxes": duplicate_annotation_boxes,
        "manifest_sha256": file_hash(manifest_path),
    }
    audit_path = Path(args.audit_report or output_dir / "dataset_audit.json")
    _write_json(audit_path, audit)
    print(json.dumps(audit, indent=2, sort_keys=True))
    print(f"[OK] Dataset written to {output_dir}")


def cmd_train(args: argparse.Namespace) -> None:
    from ultralytics import YOLO

    model = YOLO(args.model)
    model.train(
        data=args.data,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        workers=args.workers,
        seed=SEED,
        deterministic=True,
        patience=args.patience,
        save=True,
        save_period=10,
        project=str(Path(args.project).resolve()),
        name=args.name,
        exist_ok=False,
        optimizer="auto",
        cache=False,
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
    print(f"[OK] Training outputs are under {Path(args.project).resolve() / args.name}")


def _ordered_model_names(model) -> list[str]:
    names = model.names
    return [names[index] for index in range(len(names))]


def cmd_evaluate(args: argparse.Namespace) -> None:
    import torch
    import ultralytics
    from ultralytics import YOLO

    weights_path = Path(args.weights).resolve()
    model = YOLO(str(weights_path))
    expected_names = list(CLASS_MAP)
    if _ordered_model_names(model) != expected_names:
        raise ValueError("Checkpoint class order does not match NEU-DET.")

    metrics = model.val(
        data=args.data,
        split="test",
        batch=args.batch,
        imgsz=args.imgsz,
        conf=args.confidence,
        device=args.device,
        workers=args.workers,
        plots=True,
        save_json=False,
        project=str(Path(args.project).resolve()),
        name=args.name,
        exist_ok=False,
    )

    precision = [float(value) for value in metrics.box.p]
    recall = [float(value) for value in metrics.box.r]
    f1_values = [float(value) for value in metrics.box.f1]
    ap50 = [float(value) for value in metrics.box.ap50]
    ap = [float(value) for value in metrics.box.ap]
    class_ids = [int(value) for value in metrics.box.ap_class_index]
    per_class = {
        expected_names[class_id]: {
            "precision": precision[index],
            "recall": recall[index],
            "f1": f1_values[index],
            "map50": ap50[index],
            "map50_95": ap[index],
        }
        for index, class_id in enumerate(class_ids)
    }

    checkpoint_args = getattr(model, "ckpt", {}).get("train_args", {})
    selected_training_args = {
        key: checkpoint_args.get(key)
        for key in (
            "model",
            "data",
            "epochs",
            "patience",
            "batch",
            "imgsz",
            "device",
            "workers",
            "seed",
            "deterministic",
            "optimizer",
        )
    }
    hardware = (
        torch.cuda.get_device_name(0)
        if torch.cuda.is_available()
        else platform.processor() or "CPU"
    )
    summary = {
        "checkpoint": str(weights_path),
        "checkpoint_sha256": file_hash(weights_path),
        "checkpoint_labels": expected_names,
        "checkpoint_training_args": selected_training_args,
        "dataset_yaml": str(Path(args.data).resolve()),
        "evaluation_split": "test",
        "evaluation_imgsz": args.imgsz,
        "evaluation_confidence": args.confidence,
        "overall": {
            "precision": float(metrics.box.mp),
            "recall": float(metrics.box.mr),
            "f1_macro": macro_f1(precision, recall),
            "map50": float(metrics.box.map50),
            "map50_95": float(metrics.box.map),
        },
        "per_class": per_class,
        "speed_ms_per_image": {
            key: float(value) for key, value in metrics.speed.items()
        },
        "runtime": {
            "hardware": hardware,
            "python": platform.python_version(),
            "pytorch": torch.__version__,
            "ultralytics": ultralytics.__version__,
        },
        "artifacts_directory": str(metrics.save_dir),
    }
    _write_json(Path(args.report), summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"[OK] Evaluation summary written to {args.report}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare, train, and evaluate YOLO11n on NEU-DET."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser(
        "prepare", help="Convert VOC to YOLO, split, and audit the dataset."
    )
    prepare.add_argument("--raw-images", required=True)
    prepare.add_argument("--raw-annots", required=True)
    prepare.add_argument("--output-dir", default="datasets/NEU-DET")
    prepare.add_argument("--source-archive")
    prepare.add_argument("--audit-report")
    prepare.set_defaults(handler=cmd_prepare)

    train = commands.add_parser("train", help="Train a fresh YOLO11n checkpoint.")
    train.add_argument("--model", default="yolo11n.pt")
    train.add_argument("--data", default="ai/dataset_neu.yaml")
    train.add_argument("--epochs", type=int, default=100)
    train.add_argument("--patience", type=int, default=20)
    train.add_argument("--batch", type=int, default=16)
    train.add_argument("--imgsz", type=int, default=640)
    train.add_argument("--device")
    train.add_argument("--workers", type=int, default=4)
    train.add_argument("--project", default="runs/detect")
    train.add_argument("--name", default="neu-det-yolo11n")
    train.set_defaults(handler=cmd_train)

    evaluate = commands.add_parser("evaluate", help="Evaluate on the held-out test split.")
    evaluate.add_argument("--weights", required=True)
    evaluate.add_argument("--data", default="ai/dataset_neu.yaml")
    evaluate.add_argument("--batch", type=int, default=16)
    evaluate.add_argument("--imgsz", type=int, default=640)
    evaluate.add_argument("--confidence", type=float, default=0.001)
    evaluate.add_argument("--device")
    evaluate.add_argument("--workers", type=int, default=4)
    evaluate.add_argument("--project", default="runs/detect")
    evaluate.add_argument("--name", default="neu-det-eval")
    evaluate.add_argument(
        "--report", default="ai/evaluation/evaluation_summary.json"
    )
    evaluate.set_defaults(handler=cmd_evaluate)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
