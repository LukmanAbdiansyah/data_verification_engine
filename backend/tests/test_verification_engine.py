import gc
import os
import tempfile
import pandas as pd
import pytest
from app.verification.errors import VerificationError
from app.verification.inventory import scan_inventory, validate_path
from app.verification.tools import verify_catalog, search_files_by_keywords, verify_keyword_coverage
from app.verification.service import VerificationCoordinator

def test_validate_path_nonexistent():
    with pytest.raises(VerificationError) as exc_info:
        validate_path("non_existent_folder_xyz_123", kind="folder")
    assert exc_info.value.code == "PATH_NOT_FOUND"

def test_scan_inventory_and_search():
    with tempfile.TemporaryDirectory() as tmpdir:
        f1 = os.path.join(tmpdir, "stack_pstm_final.sgy")
        f2 = os.path.join(tmpdir, "gather_cdp_01.sgy")
        f3 = os.path.join(tmpdir, "report_processing.pdf")
        with open(f1, "w") as f: f.write("dummy")
        with open(f2, "w") as f: f.write("dummy")
        with open(f3, "w") as f: f.write("dummy")

        sub = os.path.join(tmpdir, "VELOCITY")
        os.makedirs(sub, exist_ok=True)
        f4 = os.path.join(sub, "velocity_model.txt")
        with open(f4, "w") as f: f.write("dummy")

        inventory = scan_inventory(tmpdir)
        assert len(inventory.files) == 4
        assert "VELOCITY" in inventory.subfolders

        res_any = search_files_by_keywords(
            folder_path=tmpdir,
            keywords=["stack", "velocity"],
            match_mode="any",
            inventory=inventory
        )
        assert res_any["status"] == "complete"
        assert res_any["summary"]["matched_files"] == 2

        res_all = search_files_by_keywords(
            folder_path=tmpdir,
            keywords=["stack", "pstm"],
            match_mode="all",
            inventory=inventory
        )
        assert res_all["summary"]["matched_files"] == 1
        assert res_all["matched_files"][0]["file_name"] == "stack_pstm_final.sgy"

def test_verify_catalog():
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = os.path.join(tmpdir, "data")
        os.makedirs(data_dir, exist_ok=True)
        f1 = os.path.join(data_dir, "file_a.sgy")
        f2 = os.path.join(data_dir, "file_b.txt")
        f3 = os.path.join(data_dir, "extra_file.dat")
        with open(f1, "w") as f: f.write("a")
        with open(f2, "w") as f: f.write("b")
        with open(f3, "w") as f: f.write("c")

        excel_path = os.path.join(tmpdir, "catalog.xlsx")
        df = pd.DataFrame({
            "ID": [1, 2, 3, 4],
            "ORIGINAL_FILE_NAME": ["file_a.sgy", "file_b.txt", "missing_file.sgy", None]
        })
        df.to_excel(excel_path, index=False)

        res = verify_catalog(
            metadata_path=excel_path,
            folder_path=data_dir,
            file_column="ORIGINAL_FILE_NAME"
        )
        gc.collect()
        summary = res["summary"]
        assert summary["matched"] == 2
        assert summary["missing"] == 1
        assert summary["empty"] == 1
        assert summary["extra"] == 1

def test_verify_multi_catalog():
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = os.path.join(tmpdir, "data")
        os.makedirs(data_dir, exist_ok=True)
        f1 = os.path.join(data_dir, "file_a.sgy")
        f2 = os.path.join(data_dir, "file_b.txt")
        f3 = os.path.join(data_dir, "extra_file.dat")
        with open(f1, "w") as f: f.write("a")
        with open(f2, "w") as f: f.write("b")
        with open(f3, "w") as f: f.write("c")

        cat1 = os.path.join(tmpdir, "catalog1.xlsx")
        pd.DataFrame({
            "ORIGINAL_FILE_NAME": ["file_a.sgy"]
        }).to_excel(cat1, index=False)

        cat2 = os.path.join(tmpdir, "catalog2.xlsx")
        pd.DataFrame({
            "ORIGINAL_FILE_NAME": ["file_b.txt", "file_missing.sgy"]
        }).to_excel(cat2, index=False)

        res = verify_catalog(
            metadata_paths=[cat1, cat2],
            folder_path=data_dir,
            file_column="ORIGINAL_FILE_NAME"
        )
        gc.collect()
        summary = res["summary"]
        assert summary["catalog_files_count"] == 2
        assert summary["matched"] == 2
        assert summary["missing"] == 1
        assert summary["extra"] == 1

def test_verify_keyword_coverage():
    with tempfile.TemporaryDirectory() as tmpdir:
        folder_pass = os.path.join(tmpdir, "LINE_01")
        folder_fail = os.path.join(tmpdir, "LINE_02")
        os.makedirs(folder_pass, exist_ok=True)
        os.makedirs(folder_fail, exist_ok=True)

        with open(os.path.join(folder_pass, "line01_stack.sgy"), "w") as f: f.write("data")
        with open(os.path.join(folder_pass, "line01_gather.sgy"), "w") as f: f.write("data")
        with open(os.path.join(folder_fail, "line02_stack.sgy"), "w") as f: f.write("data")

        # In ANY mode, having at least one keyword in the folder yields PASS
        res_any = verify_keyword_coverage(
            folder_path=tmpdir,
            keywords=["stack", "gather"],
            match_mode="any"
        )
        assert res_any["summary"]["pass"] == 2
        assert res_any["summary"]["fail"] == 0

        # In ALL mode, LINE_02 fails because gather is missing
        res_all = verify_keyword_coverage(
            folder_path=tmpdir,
            keywords=["stack", "gather"],
            match_mode="all"
        )
        assert res_all["summary"]["pass"] == 1
        assert res_all["summary"]["fail"] == 1

def test_coordinator_execution():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "test.sgy"), "w") as f: f.write("data")

        coord = VerificationCoordinator()
        result = coord.run(
            session_id="test-session-123",
            tool_name="search_files_by_keywords",
            arguments={"folder_path": tmpdir, "keywords": ["test"]}
        )
        assert result["status"] == "complete"
        assert result["summary"]["matched_files"] == 1
        assert result["session_id"] == "test-session-123"

        cached = coord.get_result("test-session-123")
        assert cached is not None
        assert cached["summary"]["matched_files"] == 1
