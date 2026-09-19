from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from .errors import VerificationError
from .inventory import FileInventory, InventoryFile, scan_inventory, validate_path


def _ensure_inventory(folder_path: str, inventory: FileInventory | None) -> FileInventory:
    resolved = validate_path(folder_path, kind="folder")
    if inventory is not None:
        try:
            inventory_root = Path(inventory.root_path).resolve(strict=True)
        except (OSError, AttributeError) as exc:
            raise VerificationError(
                "INVALID_INVENTORY",
                "Inventory cache tidak valid.",
            ) from exc
        if inventory_root == resolved:
            return inventory
    return scan_inventory(str(resolved))


def _clean_catalog_name(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    name = text.replace("\\", "/").rsplit("/", maxsplit=1)[-1].strip()
    return name or None


def _normalize_sheet_name(value: str | int) -> str | int:
    if isinstance(value, bool):
        raise VerificationError(
            "INVALID_SHEET",
            "sheet_name harus berupa nama atau indeks sheet.",
            field="sheet_name",
        )
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    if not text:
        raise VerificationError(
            "INVALID_SHEET",
            "sheet_name tidak boleh kosong.",
            field="sheet_name",
        )
    return text


def verify_catalog(
    *,
    metadata_path: str | list[str] | None = None,
    metadata_paths: list[str] | str | None = None,
    folder_path: str,
    sheet_name: str | int = 0,
    file_column: str = "ORIGINAL_FILE_NAME",
    case_sensitive: bool = False,
    inventory: FileInventory | None = None,
) -> dict[str, Any]:
    raw_paths: list[str] = []
    if metadata_paths:
        if isinstance(metadata_paths, list):
            raw_paths.extend(str(p) for p in metadata_paths)
        else:
            raw_paths.extend([p.strip() for p in str(metadata_paths).replace('\n', ',').split(',') if p.strip()])
    if metadata_path:
        if isinstance(metadata_path, list):
            raw_paths.extend(str(p) for p in metadata_path)
        else:
            raw_paths.extend([p.strip() for p in str(metadata_path).replace('\n', ',').split(',') if p.strip()])

    seen_paths: set[str] = set()
    paths: list[str] = []
    for p in raw_paths:
        clean_p = str(p).strip()
        if clean_p and clean_p not in seen_paths:
            seen_paths.add(clean_p)
            paths.append(clean_p)

    if not paths:
        raise VerificationError(
            "MISSING_METADATA",
            "Pilih minimal satu file metadata Excel.",
            field="metadata_path",
        )

    column = str(file_column).strip()
    if not column:
        raise VerificationError(
            "COLUMN_NOT_FOUND",
            "Nama kolom file tidak boleh kosong.",
            field="file_column",
        )

    validated_metas = []
    for p in paths:
        meta = validate_path(p, kind="metadata")
        if meta.suffix.casefold() not in {".xlsx", ".xls"}:
            raise VerificationError(
                "INVALID_METADATA",
                f"File metadata '{meta.name}' harus berformat .xlsx atau .xls.",
                field="metadata_path",
            )
        validated_metas.append(meta)

    all_raw_records: list[dict[str, Any]] = []
    all_cleaned_names: list[str] = []
    all_normalized_names: list[str] = []

    for meta in validated_metas:
        catalog_name = meta.name
        try:
            frame = pd.read_excel(
                meta,
                sheet_name=_normalize_sheet_name(sheet_name),
                dtype=object,
            )
        except PermissionError as exc:
            raise VerificationError(
                "PERMISSION_DENIED",
                f"File metadata '{catalog_name}' tidak dapat dibaca. Pastikan file tidak dikunci Excel.",
                field="metadata_path",
            ) from exc
        except (ImportError, ValueError, OSError) as exc:
            raise VerificationError(
                "METADATA_READ_FAILED",
                f"File metadata Excel '{catalog_name}' tidak dapat dibaca.",
                field="metadata_path",
            ) from exc

        if not isinstance(frame, pd.DataFrame):
            raise VerificationError(
                "INVALID_SHEET",
                f"sheet_name pada '{catalog_name}' harus menunjuk tepat satu sheet.",
                field="sheet_name",
            )
        frame.columns = frame.columns.astype(str).str.strip()
        if column not in frame.columns:
            raise VerificationError(
                "COLUMN_NOT_FOUND",
                f"Kolom '{column}' tidak ditemukan pada metadata '{catalog_name}'.",
                field="file_column",
                details={"available_columns": list(frame.columns), "file": catalog_name},
            )

        cleaned_names = [_clean_catalog_name(value) for value in frame[column].tolist()]
        for index, (raw_value, clean_name) in enumerate(
            zip(frame[column].tolist(), cleaned_names),
            start=2,
        ):
            original = None if pd.isna(raw_value) else str(raw_value).strip()
            all_raw_records.append({
                "catalog_file": catalog_name,
                "row_number": index,
                "original_file_name": original,
                "clean_name": clean_name,
            })
            if clean_name is not None:
                all_cleaned_names.append(clean_name)
                all_normalized_names.append(clean_name if case_sensitive else clean_name.casefold())

    metadata_counts = Counter(all_normalized_names)
    file_inventory = _ensure_inventory(folder_path, inventory)
    file_index: dict[str, list[InventoryFile]] = {}
    for item in file_inventory.files:
        key = item.name if case_sensitive else item.name.casefold()
        file_index.setdefault(key, []).append(item)

    catalog_results: list[dict[str, Any]] = []
    missing_files: list[dict[str, Any]] = []
    duplicate_files: list[dict[str, Any]] = []
    empty_metadata: list[dict[str, Any]] = []
    matched_files: list[dict[str, Any]] = []

    for item in all_raw_records:
        clean_name = item["clean_name"]
        if clean_name is None:
            record = {
                "catalog_file": item["catalog_file"],
                "row_number": item["row_number"],
                "original_file_name": item["original_file_name"],
                "file_name": "",
                "status": "EMPTY",
                "file_count": 0,
                "found_paths": [],
                "metadata_duplicate": False,
            }
            empty_metadata.append(record)
            catalog_results.append(record)
            continue

        key = clean_name if case_sensitive else clean_name.casefold()
        matches = sorted(file_index.get(key, []), key=lambda val: val.relative_path.casefold())
        status = "MISSING" if not matches else "DUPLICATE" if len(matches) > 1 else "MATCHED"
        record = {
            "catalog_file": item["catalog_file"],
            "row_number": item["row_number"],
            "original_file_name": item["original_file_name"],
            "file_name": clean_name,
            "status": status,
            "file_count": len(matches),
            "found_paths": [m.relative_path for m in matches],
            "metadata_duplicate": metadata_counts[key] > 1,
        }
        catalog_results.append(record)
        if status == "MISSING":
            missing_files.append(record)
        elif status == "DUPLICATE":
            duplicate_files.append(record)
        else:
            matched_files.append(record)

    catalog_keys = set(all_normalized_names)
    extra_files = [
        {
            "file_name": item.name,
            "relative_path": item.relative_path,
        }
        for key, items in sorted(file_index.items(), key=lambda entry: entry[0])
        if key not in catalog_keys
        for item in sorted(items, key=lambda value: value.relative_path.casefold())
    ]
    duplicate_metadata_names = [
        {
            "file_name": next(
                name
                for name in all_cleaned_names
                if (name if case_sensitive else name.casefold()) == key
            ),
            "row_count": count,
        }
        for key, count in sorted(metadata_counts.items())
        if count > 1
    ]

    summary = {
        "catalog_files_count": len(validated_metas),
        "catalog_rows": len(catalog_results),
        "valid_names": len(all_normalized_names),
        "scanned_files": len(file_inventory.files),
        "matched": len(matched_files),
        "missing": len(missing_files),
        "duplicate": len(duplicate_files),
        "empty": len(empty_metadata),
        "extra": len(extra_files),
        "duplicate_metadata_names": len(duplicate_metadata_names),
    }
    return {
        "status": "complete",
        "kind": "catalog",
        "tool": "verify_catalog",
        "configuration": {
            "metadata_path": str(validated_metas[0]) if len(validated_metas) == 1 else [str(m) for m in validated_metas],
            "metadata_paths": [str(m) for m in validated_metas],
            "folder_path": file_inventory.root_path,
            "sheet_name": _normalize_sheet_name(sheet_name),
            "file_column": column,
            "case_sensitive": bool(case_sensitive),
        },
        "summary": summary,
        "catalog_results": catalog_results,
        "matched_files": matched_files,
        "missing_files": missing_files,
        "duplicate_files": duplicate_files,
        "duplicate_metadata_names": duplicate_metadata_names,
        "empty_metadata": empty_metadata,
        "extra_files": extra_files,
        "warnings": list(file_inventory.warnings),
    }


def _validated_keywords(keywords: list[str] | str, case_sensitive: bool) -> tuple[list[str], list[str]]:
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.replace('\n', ',').split(',') if k.strip()]
    if not isinstance(keywords, list):
        raise VerificationError(
            "INVALID_KEYWORDS",
            "keywords harus berupa daftar.",
            field="keywords",
        )
    originals: list[str] = []
    checks: list[str] = []
    seen: set[str] = set()
    for value in keywords:
        keyword = str(value).strip()
        if not keyword:
            continue
        if len(keyword) > 120:
            raise VerificationError(
                "INVALID_KEYWORDS",
                "Panjang setiap keyword maksimal 120 karakter.",
                field="keywords",
            )
        check = keyword if case_sensitive else keyword.casefold()
        if check in seen:
            continue
        originals.append(keyword)
        checks.append(check)
        seen.add(check)
    if not originals:
        raise VerificationError(
            "INVALID_KEYWORDS",
            "Tambahkan minimal satu keyword.",
            field="keywords",
        )
    if len(originals) > 25:
        raise VerificationError(
            "INVALID_KEYWORDS",
            "Jumlah keyword maksimal 25.",
            field="keywords",
        )
    return originals, checks


def _validated_match_mode(match_mode: str) -> str:
    mode = str(match_mode or "any").strip().casefold()
    if mode not in {"any", "all"}:
        raise VerificationError(
            "INVALID_MATCH_MODE",
            "match_mode harus ANY atau ALL.",
            field="match_mode",
        )
    return mode


def _matches(
    file_name: str,
    originals: list[str],
    checks: list[str],
    *,
    mode: str,
    case_sensitive: bool,
) -> list[str]:
    candidate = file_name if case_sensitive else file_name.casefold()
    matched = [
        original
        for original, check in zip(originals, checks)
        if check in candidate
    ]
    if mode == "all" and len(matched) != len(originals):
        return []
    return matched


def search_files_by_keywords(
    *,
    folder_path: str,
    keywords: list[str] | str,
    match_mode: str = "any",
    recursive: bool = True,
    case_sensitive: bool = False,
    inventory: FileInventory | None = None,
) -> dict[str, Any]:
    mode = _validated_match_mode(match_mode)
    originals, checks = _validated_keywords(keywords, case_sensitive)
    file_inventory = _ensure_inventory(folder_path, inventory)
    candidates = [
        item
        for item in file_inventory.files
        if recursive or "/" not in item.relative_path
    ]
    matched_files: list[dict[str, Any]] = []
    for item in candidates:
        matched = _matches(
            item.name,
            originals,
            checks,
            mode=mode,
            case_sensitive=case_sensitive,
        )
        if matched:
            matched_files.append(
                {
                    "file_name": item.name,
                    "relative_path": item.relative_path,
                    "matched_keywords": matched,
                }
            )

    scanned_folders = {
        str(Path(item.relative_path).parent).replace("\\", "/")
        for item in candidates
    } or {"."}
    return {
        "status": "complete",
        "kind": "search",
        "tool": "search_files_by_keywords",
        "configuration": {
            "folder_path": file_inventory.root_path,
            "keywords": originals,
            "match_mode": mode,
            "recursive": bool(recursive),
            "case_sensitive": bool(case_sensitive),
        },
        "summary": {
            "scanned_files": len(candidates),
            "matched_files": len(matched_files),
            "folders": len(scanned_folders),
        },
        "matched_files": matched_files,
        "matched_keywords": sorted(
            {keyword for item in matched_files for keyword in item["matched_keywords"]},
            key=str.casefold,
        ),
        "warnings": list(file_inventory.warnings),
    }


def verify_keyword_coverage(
    *,
    folder_path: str,
    keywords: list[str] | str,
    match_mode: str = "any",
    search_scope: str = "recursive_per_folder",
    case_sensitive: bool = False,
    inventory: FileInventory | None = None,
) -> dict[str, Any]:
    mode = _validated_match_mode(match_mode)
    originals, checks = _validated_keywords(keywords, case_sensitive)
    scope = str(search_scope or "recursive_per_folder").strip().casefold()
    if scope not in {"direct_files", "recursive_per_folder"}:
        raise VerificationError(
            "INVALID_SEARCH_SCOPE",
            "search_scope harus direct_files atau recursive_per_folder.",
            field="search_scope",
        )
    file_inventory = _ensure_inventory(folder_path, inventory)
    child_folders = [
        folder
        for folder in file_inventory.subfolders
        if "/" not in folder
    ]
    folder_results: list[dict[str, Any]] = []
    total_considered = 0

    for child in sorted(child_folders, key=str.casefold):
        prefix = f"{child}/"
        candidates: list[InventoryFile] = []
        for item in file_inventory.files:
            if not item.relative_path.startswith(prefix):
                continue
            remainder = item.relative_path[len(prefix):]
            if scope == "direct_files" and "/" in remainder:
                continue
            candidates.append(item)
        total_considered += len(candidates)

        matched_files: list[dict[str, Any]] = []
        covered_keys: set[str] = set()
        for item in candidates:
            candidate_name = item.name if case_sensitive else item.name.casefold()
            matches = [
                original
                for original, check in zip(originals, checks)
                if check in candidate_name
            ]
            if not matches:
                continue
            matched_files.append(
                {
                    "file_name": item.name,
                    "relative_path": item.relative_path,
                    "matched_keywords": matches,
                }
            )
            covered_keys.update(
                original if case_sensitive else original.casefold()
                for original in matches
            )

        expected_keys = {
            original if case_sensitive else original.casefold()
            for original in originals
        }
        passed = bool(covered_keys) if mode == "any" else expected_keys.issubset(covered_keys)
        covered_originals = [
            original
            for original in originals
            if (original if case_sensitive else original.casefold()) in covered_keys
        ]
        missing = [
            original
            for original in originals
            if (original if case_sensitive else original.casefold()) not in covered_keys
        ]
        folder_results.append(
            {
                "folder_name": child,
                "relative_path": child,
                "status": "PASS" if passed else "FAIL",
                "passed": passed,
                "scanned_files": len(candidates),
                "matched_file_count": len(matched_files),
                "matched_keywords": covered_originals,
                "missing_keywords": [] if mode == "any" and passed else missing,
                "matched_files": matched_files,
            }
        )

    pass_count = sum(1 for item in folder_results if item["passed"])
    warnings = list(file_inventory.warnings)
    if not child_folders:
        warnings.append(
            {
                "code": "NO_SUBFOLDERS",
                "message": "Tidak ada subfolder langsung pada folder yang dipilih.",
            }
        )
    return {
        "status": "complete",
        "kind": "coverage",
        "tool": "verify_keyword_coverage",
        "configuration": {
            "folder_path": file_inventory.root_path,
            "keywords": originals,
            "match_mode": mode,
            "search_scope": scope,
            "case_sensitive": bool(case_sensitive),
        },
        "summary": {
            "folders": len(folder_results),
            "pass": pass_count,
            "fail": len(folder_results) - pass_count,
            "scanned_files": total_considered,
        },
        "folder_results": folder_results,
        "warnings": warnings,
    }
