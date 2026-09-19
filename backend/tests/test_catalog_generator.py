import os
import tempfile
import pytest
import pandas as pd
from app.services.catalog_generator import (
    path_for_io,
    is_segy_file,
    is_las_file,
    get_md5_from_file,
    get_md5_from_path,
    get_file_extensions,
    get_file_sizes,
    line_name_generator,
    generate_seismic_catalog,
    generate_well_catalog,
    DEFAULT_LINE_NAME,
)


def test_path_and_extension_utils():
    assert is_segy_file("test.sgy") is True
    assert is_segy_file("survey.SEGY") is True
    assert is_segy_file("report.pdf") is False

    assert is_las_file("well_1.las") is True
    assert is_las_file("well_1.LAS") is True
    assert is_las_file("test.txt") is False

    exts = get_file_extensions(["a.sgy", "b.las", "c.PDF", "d.bin"])
    assert exts == ["SGY", "LAS", "PDF", "BIN"]


def test_md5_and_size_calculation():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "sample.txt")
        with open(test_file, "wb") as f:
            f.write(b"Hello Deliverable Verification")

        # MD5
        md5_val = get_md5_from_file(test_file)
        assert len(md5_val) == 32
        assert md5_val.isupper()

        # Batch MD5
        hashes = get_md5_from_path([test_file])
        assert hashes == [md5_val]

        # File sizes
        sizes = get_file_sizes([test_file])
        assert sizes == [len(b"Hello Deliverable Verification")]


def test_line_name_generator_fallback():
    # Non-segy file should return DEFAULT_LINE_NAME
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_file = os.path.join(tmpdir, "test.txt")
        with open(dummy_file, "w") as f:
            f.write("Some dummy text")

        assert line_name_generator(dummy_file) == DEFAULT_LINE_NAME


def test_generate_seismic_catalog_mock():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a dummy segy file
        dummy_segy = os.path.join(tmpdir, "survey_line_01.sgy")
        with open(dummy_segy, "wb") as f:
            f.write(b"\x00" * 4000)

        params = {
            "BA_LONG_NAME": "Pertamina Hulu Rokan",
            "BA_TYPE": "BADAN USAHA",
            "AREA_ID": "ROKAN",
            "AREA_TYPE": "WILAYAH KERJA",
            "STEP_TYPE": "MIGRATION",
            "ITEM_CATEGORY": "2. PROCESSING",
            "ITEM_SUB_CATEGORY": "2.3. M - MIGRATION (NON PRESERVE)",
            "MEDIA_TYPE": "EKSTERNAL HARDISK",
            "SEIS_POINT_LABEL": "CDP",
            "ROW_QUALITY": "TERVERIFIKASI OLEH SKK MIGAS",
            "CHECKED_BY_BA_ID": "USR001",
            "generate_md5": True,
        }

        res = generate_seismic_catalog(
            catalog_type="B.1.5.2 SEIS_2D_PROCESS_DIGITAL",
            folder_path=tmpdir,
            params=params
        )

        assert res["status"] == "success"
        assert res["total_files"] == 1
        assert os.path.exists(res["output_path"])
        assert "ORIGINAL_FILE_NAME" in res["columns"]
        assert "BA_LONG_NAME" in res["columns"]
        assert res["rows"][0]["BA_LONG_NAME"] == "PERTAMINA HULU ROKAN"
        assert res["rows"][0]["ORIGINAL_FILE_NAME"] == "survey_line_01.sgy"
        assert res["rows"][0]["DECRYPTION_TYPE"] == "MD5"


def test_generate_well_catalog_mock():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a dummy las file
        dummy_las = os.path.join(tmpdir, "well_alpha_1.las")
        with open(dummy_las, "w") as f:
            f.write("~VERSION INFORMATION\nVERS. 2.0:\n~WELL INFORMATION\nWELL. ALPHA-1: WELL NAME\nFLD . FIELD-X: FIELD\nSTRT.M 100.0: START\nSTOP.M 500.0: STOP\n")

        params = {
            "BA_LONG_NAME": "ExxonMobil Cepu",
            "BA_TYPE": "BADAN USAHA",
            "AREA_ID": "CEPU",
            "AREA_TYPE": "WILAYAH KERJA",
            "ROW_QUALITY": "TERVERIFIKASI OLEH SKK MIGAS",
            "CHECKED_BY_BA_ID": "QC01",
            "MEDIA_TYPE": "EKSTERNAL HARDISK",
            "generate_md5": False,
        }

        res = generate_well_catalog(
            catalog_type="D.2.3 WELL_LOG_DIGITAL",
            folder_path=tmpdir,
            params=params
        )

        assert res["status"] == "success"
        assert res["total_files"] == 1
        assert os.path.exists(res["output_path"])
        assert res["rows"][0]["BA_LONG_NAME"] == "EXXONMOBIL CEPU"
        assert res["rows"][0]["ORIGINAL_FILE_NAME"] == "well_alpha_1.las"


def test_progress_callback_emits_file_indicator():
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_segy = os.path.join(tmpdir, "line_test_01.sgy")
        with open(dummy_segy, "wb") as f:
            f.write(b"\x00" * 4000)

        events = []
        def on_progress(data):
            events.append(data)

        params = {
            "BA_LONG_NAME": "Pertamina Hulu Rokan",
            "generate_md5": False,
        }

        res = generate_seismic_catalog(
            catalog_type="B.1.5.2 SEIS_2D_PROCESS_DIGITAL",
            folder_path=tmpdir,
            params=params,
            progress_callback=on_progress
        )

        assert res["status"] == "success"
        assert len(events) > 0

        # Verify that file indicator fields are emitted
        file_events = [e for e in events if isinstance(e, dict) and e.get("current_file")]
        assert len(file_events) > 0
        assert any(e["current_file"] == "line_test_01.sgy" for e in file_events)
        assert any(e.get("total_files") == 1 for e in file_events)
        assert any(e.get("current_index") == 1 for e in file_events)


def test_streaming_catalog_endpoint():
    import json
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_segy = os.path.join(tmpdir, "stream_test_01.sgy")
        with open(dummy_segy, "wb") as f:
            f.write(b"\x00" * 4000)

        payload = {
            "catalog_type": "B.1.5.2 SEIS_2D_PROCESS_DIGITAL",
            "folder_path": tmpdir,
            "params": {"BA_LONG_NAME": "Testing Stream", "generate_md5": False}
        }

        with client.stream("POST", "/api/catalog/generate/seismic-stream", json=payload) as response:
            assert response.status_code == 200
            lines = [line for line in response.iter_lines() if line.strip()]
            events = [json.loads(line) for line in lines]

            assert len(events) > 0
            # Check for progress and completion events
            types = [e.get("type") for e in events]
            assert "progress" in types
            assert "complete" in types
            complete_event = next(e for e in events if e.get("type") == "complete")
            assert complete_event["result"]["status"] == "success"
            assert complete_event["result"]["total_files"] == 1


def test_streaming_well_catalog_endpoint():
    import json
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_las = os.path.join(tmpdir, "stream_well_01.las")
        with open(dummy_las, "w") as f:
            f.write("~VERSION INFORMATION\nVERS. 2.0:\n~WELL INFORMATION\nWELL. TEST-WELL: WELL\nSTRT.M 50.0:\nSTOP.M 200.0:\n")

        payload = {
            "catalog_type": "D.2.3 WELL_LOG_DIGITAL",
            "folder_path": tmpdir,
            "params": {"BA_LONG_NAME": "Testing Well Stream", "generate_md5": False}
        }

        with client.stream("POST", "/api/catalog/generate/well-stream", json=payload) as response:
            assert response.status_code == 200
            lines = [line for line in response.iter_lines() if line.strip()]
            events = [json.loads(line) for line in lines]

            assert len(events) > 0
            types = [e.get("type") for e in events]
            assert "progress" in types
            assert "complete" in types
            complete_event = next(e for e in events if e.get("type") == "complete")
            assert complete_event["result"]["status"] == "success"
            assert complete_event["result"]["total_files"] == 1
            # Verify rows are clean JSON with no NaN
            for r in complete_event["result"]["rows"]:
                for v in r.values():
                    assert v != "NaN"


def test_corrupted_las_files_never_fail_extraction():
    """Verify that empty, corrupt, or binary files renamed to .las never crash well catalog extraction."""
    from app.services.catalog_generator import well_information_extraction

    with tempfile.TemporaryDirectory() as tmpdir:
        # File 1: Normal LAS file
        normal_las = os.path.join(tmpdir, "normal.las")
        with open(normal_las, "w") as f:
            f.write("~VERSION INFORMATION\nVERS. 2.0:\n~WELL INFORMATION\nWELL. NORMAL_WELL: WELL\nFLD . FIELD_A: FIELD\nSTRT.M 10.0: START\nSTOP.M 500.0: STOP\n~CURVE\nDEPT.M:\nGR.GAPI:\n~A\n")

        # File 2: 0-byte empty file
        empty_las = os.path.join(tmpdir, "empty.las")
        with open(empty_las, "wb") as f:
            f.write(b"")

        # File 3: Corrupted binary/garbage file
        garbage_las = os.path.join(tmpdir, "corrupt.las")
        with open(garbage_las, "wb") as f:
            f.write(b"\xFF\xFE\x00\x12\x34\x56\x78\x9A\xBC\xDE\xF0\x00\x00\x00")

        # File 4: Missing curve section and incomplete well header
        partial_las = os.path.join(tmpdir, "partial.las")
        with open(partial_las, "w") as f:
            f.write("~WELL\nWELL. PARTIAL_WELL:\n")

        file_list = [normal_las, empty_las, garbage_las, partial_las]
        header = well_information_extraction(file_list)

        # Ensure all 9 arrays have EXACTLY the same length as file_list
        assert len(header) == 9
        for arr in header:
            assert len(arr) == len(file_list)

        # Verify normal file values
        assert header[0][0] == "NORMAL_WELL"
        assert header[1][0] == "FIELD_A"
        assert header[3][0] == 10.0
        assert header[4][0] == 500.0
        assert "GR" in header[7][0]

        # Verify corrupted files got safe fallback values without raising any exception
        assert header[0][1] == "Unknown"
        assert header[0][2] == "Unknown"
        assert header[0][3] == "PARTIAL_WELL"

        # Now test full catalog generation with all 4 files
        res = generate_well_catalog(
            catalog_type="D.2.3 WELL_LOG_DIGITAL",
            folder_path=tmpdir,
            params={"BA_LONG_NAME": "Test Resilience", "generate_md5": True}
        )
        assert res["status"] == "success"
        assert res["total_files"] == 4
        assert len(res["rows"]) == 4
        assert os.path.exists(res["output_path"])


def test_direct_catalog_endpoints():
    """Verify standard direct REST endpoints POST /api/catalog/generate/well and /seismic."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_las = os.path.join(tmpdir, "direct_well.las")
        with open(dummy_las, "w") as f:
            f.write("~VERSION\nVERS. 2.0:\n~WELL\nWELL. DIRECT-SUMUR:\nSTRT.M 100:\nSTOP.M 300:\n")

        res = client.post(
            "/api/catalog/generate/well",
            json={
                "catalog_type": "D.2.3 WELL_LOG_DIGITAL",
                "folder_path": tmpdir,
                "params": {"BA_LONG_NAME": "Direct KKKS", "generate_md5": False}
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["total_files"] == 1
        assert data["rows"][0]["WELL_NAME"] == "DIRECT-SUMUR"
        assert data["rows"][0]["BA_LONG_NAME"] == "DIRECT KKKS"


def test_seismic_catalog_sp_and_cdp_extraction():
    """Verify that SEIS_POINT_LABEL='SP' extracts First and Last Seis Point from EnergySourcePoint, ShotPoint (197-200), or FieldRecord."""
    import segyio
    import numpy as np

    with tempfile.TemporaryDirectory() as tmpdir:
        spec = segyio.spec()
        spec.samples = [0, 1, 2, 3]
        spec.tracecount = 3
        spec.format = 5

        # Case 1: SP in EnergySourcePoint (bytes 17-20)
        f1 = os.path.join(tmpdir, "line_esp.sgy")
        with segyio.create(f1, spec) as s:
            s.header[0] = {segyio.TraceField.EnergySourcePoint: 100, segyio.TraceField.CDP: 1001}
            s.header[1] = {segyio.TraceField.EnergySourcePoint: 150, segyio.TraceField.CDP: 1050}
            s.header[2] = {segyio.TraceField.EnergySourcePoint: 200, segyio.TraceField.CDP: 1100}
            for i in range(3):
                s.trace[i] = np.zeros(4, dtype=np.float32)

        # Case 2: SP in ShotPoint (bytes 197-200)
        f2 = os.path.join(tmpdir, "line_sp197.sgy")
        with segyio.create(f2, spec) as s:
            s.header[0] = {segyio.TraceField.EnergySourcePoint: 0, segyio.TraceField.ShotPoint: 500, segyio.TraceField.CDP: 2001}
            s.header[1] = {segyio.TraceField.EnergySourcePoint: 0, segyio.TraceField.ShotPoint: 550, segyio.TraceField.CDP: 2050}
            s.header[2] = {segyio.TraceField.EnergySourcePoint: 0, segyio.TraceField.ShotPoint: 600, segyio.TraceField.CDP: 2100}
            for i in range(3):
                s.trace[i] = np.zeros(4, dtype=np.float32)

        # Generate catalog with SP
        res_sp = generate_seismic_catalog(
            catalog_type="B.1.5.2 SEIS_2D_PROCESS_DIGITAL",
            folder_path=tmpdir,
            params={"SEIS_POINT_LABEL": "SP"}
        )
        assert res_sp["status"] == "success"
        rows_by_name = {r["ORIGINAL_FILE_NAME"]: r for r in res_sp["rows"]}
        assert rows_by_name["line_esp.sgy"]["SEIS_POINT_LABEL"] == "SP"
        assert rows_by_name["line_esp.sgy"]["FIRST_SEIS_POINT_ID"] == 100
        assert rows_by_name["line_esp.sgy"]["LAST_SEIS_POINT_ID"] == 200

        assert rows_by_name["line_sp197.sgy"]["SEIS_POINT_LABEL"] == "SP"
        assert rows_by_name["line_sp197.sgy"]["FIRST_SEIS_POINT_ID"] == 500
        assert rows_by_name["line_sp197.sgy"]["LAST_SEIS_POINT_ID"] == 600

        # Generate catalog with CDP
        res_cdp = generate_seismic_catalog(
            catalog_type="B.1.5.2 SEIS_2D_PROCESS_DIGITAL",
            folder_path=tmpdir,
            params={"SEIS_POINT_LABEL": "CDP"}
        )
        assert res_cdp["status"] == "success"
        cdp_by_name = {r["ORIGINAL_FILE_NAME"]: r for r in res_cdp["rows"]}
        assert cdp_by_name["line_esp.sgy"]["SEIS_POINT_LABEL"] == "CDP"
        assert cdp_by_name["line_esp.sgy"]["FIRST_SEIS_POINT_ID"] == 1001
        assert cdp_by_name["line_esp.sgy"]["LAST_SEIS_POINT_ID"] == 1100

        assert cdp_by_name["line_sp197.sgy"]["SEIS_POINT_LABEL"] == "CDP"
        assert cdp_by_name["line_sp197.sgy"]["FIRST_SEIS_POINT_ID"] == 2001
        assert cdp_by_name["line_sp197.sgy"]["LAST_SEIS_POINT_ID"] == 2100


def test_extract_seismic_polarity_normal_and_reverse():
    """Verify that extract_seismic_polarity extracts NORMAL, REVERSE, or handles defaults strictly."""
    import segyio
    import numpy as np
    from app.services.catalog_generator import (
        extract_seismic_polarity,
        extract_polarity_batch,
        generate_seismic_catalog,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        spec = segyio.spec()
        spec.samples = [0, 2, 4, 6]
        spec.format = 1
        spec.tracecount = 1

        # File 1: Explicit NORMAL polarity
        f_norm = os.path.join(tmpdir, "line_normal.sgy")
        with segyio.create(f_norm, spec) as s:
            lines = [f"C{i:02d} " + " " * 76 for i in range(1, 41)]
            lines[5] = "C06 POLARITY : NORMAL" + " " * 59
            s.text[0] = "".join(l[:80].ljust(80) for l in lines).encode("ascii")
            s.trace[0] = np.zeros(4, dtype=np.float32)

        # File 2: SEG convention (INCREASING IMPEDANCE -> PEAK/POSITIVE)
        f_seg = os.path.join(tmpdir, "line_seg_normal.sgy")
        with segyio.create(f_seg, spec) as s:
            lines = [f"C{i:02d} " + " " * 76 for i in range(1, 41)]
            lines[5] = "C06 POLARITY : INCREASING IMPEDANCE IS REPRESENTED BY PEAK/POSITIVE VALUE"
            s.text[0] = "".join(l[:80].ljust(80) for l in lines).encode("ascii")
            s.trace[0] = np.zeros(4, dtype=np.float32)

        # File 3: Explicit REVERSE polarity
        f_rev = os.path.join(tmpdir, "line_reverse.sgy")
        with segyio.create(f_rev, spec) as s:
            lines = [f"C{i:02d} " + " " * 76 for i in range(1, 41)]
            lines[5] = "C06 POLARITY : REVERSE" + " " * 58
            s.text[0] = "".join(l[:80].ljust(80) for l in lines).encode("ascii")
            s.trace[0] = np.zeros(4, dtype=np.float32)

        # File 4: No polarity declared
        f_none = os.path.join(tmpdir, "line_none.sgy")
        with segyio.create(f_none, spec) as s:
            lines = [f"C{i:02d} " + " " * 76 for i in range(1, 41)]
            s.text[0] = "".join(l[:80].ljust(80) for l in lines).encode("ascii")
            s.trace[0] = np.zeros(4, dtype=np.float32)

        assert extract_seismic_polarity(f_norm) == "NORMAL"
        assert extract_seismic_polarity(f_seg) == "NORMAL"
        assert extract_seismic_polarity(f_rev) == "REVERSE"
        assert extract_seismic_polarity(f_none) == ""
        assert extract_seismic_polarity(f_none, default_polarity="NORMAL") == "NORMAL"
        assert extract_seismic_polarity(f_none, default_polarity="REVERSE") == "REVERSE"
        assert extract_seismic_polarity(f_none, default_polarity="AUTO") == ""

        # Batch test
        batch = extract_polarity_batch([f_norm, f_seg, f_rev, f_none])
        assert batch == ["NORMAL", "NORMAL", "REVERSE", ""]

        # Catalog generation test
        res = generate_seismic_catalog(
            catalog_type="B.1.5.2 SEIS_2D_PROCESS_DIGITAL",
            folder_path=tmpdir,
            params={"generate_md5": False}
        )
        assert res["status"] == "success"
        rows = {r["ORIGINAL_FILE_NAME"]: r["POLARITY"] for r in res["rows"]}
        assert rows["line_normal.sgy"] == "NORMAL"
        assert rows["line_seg_normal.sgy"] == "NORMAL"
        assert rows["line_reverse.sgy"] == "REVERSE"
        assert rows["line_none.sgy"] == ""







