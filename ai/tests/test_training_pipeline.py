from collections import Counter
from pathlib import Path

import pytest

from ai.train_eval_pipeline import (
    CLASS_MAP,
    build_parser,
    check_duplicates_and_leakage,
    deduplicate_images,
    ensure_empty_output_dir,
    file_hash,
    macro_f1,
    split_dataset,
    voc_xml_to_yolo,
)


def _class_counts(paths: list[Path]) -> Counter[str]:
    return Counter(
        next(name for name in CLASS_MAP if path.stem.startswith(name))
        for path in paths
    )


def test_split_is_stratified_deterministic_and_input_order_independent() -> None:
    images = [
        Path(f"{class_name}_{index}.jpg")
        for class_name in CLASS_MAP
        for index in range(1, 301)
    ]

    first = split_dataset(images)
    second = split_dataset(list(reversed(images)))

    assert first == second
    assert {name: len(paths) for name, paths in first.items()} == {
        "train": 1260,
        "val": 360,
        "test": 180,
    }
    for name, paths in first.items():
        expected = {"train": 210, "val": 60, "test": 30}[name]
        assert _class_counts(paths) == Counter(
            {class_name: expected for class_name in CLASS_MAP}
        )


def test_split_rejects_unknown_filename_class() -> None:
    with pytest.raises(ValueError, match="class prefix"):
        split_dataset([Path("mystery_1.jpg")])


def test_any_exact_duplicate_fails_integrity_check(tmp_path: Path) -> None:
    first = tmp_path / "crazing_1.jpg"
    second = tmp_path / "crazing_2.jpg"
    first.write_bytes(b"same-image")
    second.write_bytes(b"same-image")

    messages, integrity_failed = check_duplicates_and_leakage(
        {"train": [first, second], "val": [], "test": []}
    )

    assert integrity_failed is True
    assert any("[DUP]" in message for message in messages)


def test_exact_duplicates_are_removed_deterministically_before_split(
    tmp_path: Path,
) -> None:
    first = tmp_path / "patches_101.jpg"
    second = tmp_path / "patches_105.jpg"
    unique = tmp_path / "patches_106.jpg"
    first.write_bytes(b"duplicate")
    second.write_bytes(b"duplicate")
    unique.write_bytes(b"unique")

    retained, excluded = deduplicate_images([second, unique, first])

    assert retained == [first, unique]
    assert excluded == [
        {
            "excluded": second.name,
            "kept": first.name,
            "sha256": file_hash(first),
        }
    ]


def test_prepare_requires_an_empty_output_directory(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    ensure_empty_output_dir(empty)

    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "stale.txt").write_text("old split", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        ensure_empty_output_dir(occupied)


def test_macro_f1_averages_per_class_scores() -> None:
    assert macro_f1([1.0, 0.5], [0.5, 0.5]) == pytest.approx(7 / 12)
    assert macro_f1([], []) == 0.0
    with pytest.raises(ValueError):
        macro_f1([1.0], [1.0, 0.5])


def test_cli_help_is_ascii_safe_for_windows_consoles() -> None:
    build_parser().format_help().encode("ascii")


def test_voc_conversion_removes_exact_duplicate_boxes(tmp_path: Path) -> None:
    annotation = tmp_path / "crazing_1.xml"
    annotation.write_text(
        """<annotation>
        <size><width>200</width><height>200</height></size>
        <object><name>crazing</name><bndbox>
        <xmin>10</xmin><ymin>20</ymin><xmax>110</xmax><ymax>120</ymax>
        </bndbox></object>
        <object><name>crazing</name><bndbox>
        <xmin>10</xmin><ymin>20</ymin><xmax>110</xmax><ymax>120</ymax>
        </bndbox></object>
        </annotation>""",
        encoding="ascii",
    )

    assert voc_xml_to_yolo(annotation) == ["0 0.300000 0.350000 0.500000 0.500000"]
