import os
import re
import hashlib
import logging
from typing import List, Dict, Any, Optional, Callable, Tuple
import pandas as pd

logger = logging.getLogger(__name__)

SEGY_EXTENSIONS = {".sgy", ".segy"}
DEFAULT_LINE_NAME = "Tidak Ada"
DEFAULT_HEADER_VALUE = ""


def path_for_io(file_path: str) -> str:
    """Normalize file path for Windows long path compatibility."""
    path = os.path.abspath(os.path.normpath(str(file_path)))
    if os.name != "nt" or path.startswith("\\\\?\\"):
        return path
    if path.startswith("\\\\"):
        return "\\\\?\\UNC\\" + path.lstrip("\\")
    return "\\\\?\\" + path


def is_segy_file(file_path: str) -> bool:
    """Check if file has a SEG-Y extension."""
    _, ext = os.path.splitext(str(file_path))
    return ext.lower() in SEGY_EXTENSIONS


def is_las_file(file_path: str) -> bool:
    """Check if file has a LAS extension."""
    _, ext = os.path.splitext(str(file_path))
    return ext.lower() in {".las"}


def get_md5_from_file(file_path: str, chunk_callback: Optional[Callable[[int, int], None]] = None) -> str:
    """Calculate MD5 hash of a file with optional progress chunk callback."""
    try:
        io_path = path_for_io(file_path)
        total_size = os.path.getsize(io_path)
        bytes_read = 0
        md5_hash = hashlib.md5()
        with open(io_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                md5_hash.update(chunk)
                bytes_read += len(chunk)
                if chunk_callback:
                    chunk_callback(bytes_read, total_size)
        return md5_hash.hexdigest().upper()
    except FileNotFoundError:
        return "File tidak ditemukan."
    except Exception as e:
        logger.warning(f"Error calculating MD5 for {file_path}: {e}")
        return f"Terjadi kesalahan: {e}"


def get_md5_from_path(
    list_path: List[str],
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    chunk_callback: Optional[Callable[[int, int, str, int, int], None]] = None
) -> List[str]:
    """Calculate MD5 hashes for a list of file paths."""
    file_md5 = []
    total = len(list_path)
    for index, file in enumerate(list_path, start=1):
        def _chunk_cb(bytes_read, total_size, file_index=index, file_path=file):
            if chunk_callback:
                chunk_callback(file_index, total, file_path, bytes_read, total_size)

        file_md5.append(get_md5_from_file(file, chunk_callback=_chunk_cb))
        if progress_callback:
            progress_callback(index, total, file)
    return file_md5


def list_files_with_paths_and_folders(folder_path: str) -> Tuple[List[str], List[str], List[str]]:
    """Recursively list all files with their full paths, filenames, and parent directories."""
    files_with_paths = []
    file_names = []
    folder_paths = []

    def _walk_error(err):
        logger.warning(f"Error accessing directory during scan: {err}")

    for root, dirs, files in os.walk(path_for_io(folder_path), onerror=_walk_error):
        # Exclude hidden, system and recycle bin directories
        dirs[:] = [
            d for d in dirs
            if not d.startswith('$') and d.lower() not in ('system volume information', '$recycle.bin', '.git', '.svn', '__pycache__')
        ]
        for file in files:
            if file.startswith('~$') or file.startswith('.'):
                continue
            full_path = os.path.join(root, file)
            files_with_paths.append(full_path)
            file_names.append(file)
            folder_paths.append(root)

    return files_with_paths, file_names, folder_paths



def get_file_extensions(file_paths: List[str]) -> List[str]:
    """Get uppercase extensions without dot."""
    extensions = []
    for file_path in file_paths:
        _, ext = os.path.splitext(file_path)
        extensions.append(ext[1:].upper() if ext.startswith('.') else ext.upper())
    return extensions


def get_file_sizes(file_paths: List[str], progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[Any]:
    """Get sizes of files in bytes."""
    sizes = []
    total = len(file_paths)
    for index, file_path in enumerate(file_paths, start=1):
        try:
            sizes.append(os.path.getsize(path_for_io(file_path)))
        except FileNotFoundError:
            sizes.append("File not found")
        except Exception as e:
            sizes.append(f"Error: {e}")

        if progress_callback:
            progress_callback(index, total, file_path)
    return sizes


def line_name_generator(file_path: str) -> str:
    """Extract seismic line name from textual header using regex patterns."""
    if not is_segy_file(file_path) or not os.path.isfile(path_for_io(file_path)):
        return DEFAULT_LINE_NAME

    text = ""
    # Try fast read of first 3200 bytes first
    try:
        from .segy_parser import decode_textual_header, detect_encoding
        with open(path_for_io(file_path), "rb") as f:
            header_bytes = f.read(3200)
        enc = detect_encoding(header_bytes)
        lines = decode_textual_header(header_bytes, enc)
        text = "\n".join(lines)
    except Exception:
        try:
            from segysak.segy import get_segy_texthead
            text = get_segy_texthead(path_for_io(file_path))
        except Exception:
            return DEFAULT_LINE_NAME

    opsi_1 = [line for line in text.split('\n') if re.search(r'\bLINE\b', line, re.IGNORECASE)]
    opsi_2 = [line for line in text.split('\n') if re.search(r'\bName\b', line, re.IGNORECASE)]
    opsi_3 = [line for line in text.split('\n') if re.search(r'LINENAME\(S\):\s*(\S+)', line, re.IGNORECASE)]
    opsi_4 = re.search(r"C03LINE\s+:\s+([^\n]+)", text, re.IGNORECASE)
    opsi_5 = re.search(r"LINE NAME\s*:\s*(.+)", text, re.IGNORECASE)
    opsi_6 = re.search(r"LINE NUMBER\s*:\s*(.+)", text, re.IGNORECASE)
    opsi_7 = re.search(r'LINENAME:\s*(\S+)', text, re.IGNORECASE)

    if len(opsi_1) > 0 and len(opsi_2) == 0 and len(opsi_3) == 0 and (opsi_5 is None) and (opsi_6 is None) and (opsi_7 is None):
        row = opsi_1[0]
        match = re.search(r'LINE\s*:\s*(\S+)', row, re.IGNORECASE)
        match1 = re.search(r'LINE\s+(\S+)', row, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        elif match1:
            return match1.group(1).strip()
        else:
            return DEFAULT_LINE_NAME

    elif len(opsi_2) > 0:
        row = opsi_2[0]
        match = re.search(r'Name:\s*(\S+)', row, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    elif len(opsi_3) > 0:
        row = opsi_3[0]
        match = re.search(r'LINENAME\(S\):\s*(\S+)', row, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    elif opsi_4:
        return opsi_4.group(1).strip()

    elif opsi_5:
        return opsi_5.group(1).strip()

    elif opsi_6:
        return opsi_6.group(1).strip()

    elif opsi_7:
        return opsi_7.group(1).strip()

    return DEFAULT_LINE_NAME


def line_name(list_path: List[str], progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[str]:
    """Extract line names for a list of file paths."""
    lines_ = []
    total = len(list_path)
    for index, i in enumerate(list_path, start=1):
        lines_.append(line_name_generator(i))
        if progress_callback:
            progress_callback(index, total, i)
    return lines_


def extract_seismic_polarity(file_path: str, default_polarity: str = "") -> str:
    """
    Extract seismic polarity (NORMAL or REVERSE) from SEG-Y textual header.
    Returns strictly 'NORMAL', 'REVERSE', or default/empty string.
    """
    def_clean = str(default_polarity or "").strip().upper()
    if def_clean.startswith("AUTO"):
        def_clean = ""
    if def_clean not in ("NORMAL", "REVERSE"):
        def_clean = ""

    if not is_segy_file(file_path) or not os.path.isfile(path_for_io(file_path)):
        return def_clean

    try:
        norm_path = path_for_io(file_path)
        with open(norm_path, 'rb') as f:
            header_bytes = f.read(3200)
        if len(header_bytes) < 3200:
            return def_clean

        from .segy_parser import detect_encoding, decode_textual_header
        enc = detect_encoding(header_bytes)
        lines = decode_textual_header(header_bytes, enc)

        for line in lines:
            upper = line.upper()
            if 'POLAR' in upper:
                # 1. Explicit statement: e.g. POLARITY : NORMAL, POLARITY: REVERSE
                m = re.search(r'\bPOLARITY\b\s*[:=IS\s]+\s*(NORMAL|REVERSE|REVERSED)\b', upper)
                if m:
                    return 'REVERSE' if 'REV' in m.group(1) else 'NORMAL'
                m2 = re.search(r'\b(NORMAL|REVERSE|REVERSED)\s+POLARITY\b', upper)
                if m2:
                    return 'REVERSE' if 'REV' in m2.group(1) else 'NORMAL'
                # 2. SEG geophysical impedance convention:
                # Increasing impedance represented by peak/positive -> NORMAL
                # Increasing impedance represented by trough/negative -> REVERSE
                if re.search(r'(?:INCREAS\w*\s+IMPEDANCE|ACOUSTIC\s+IMPEDANCE).*?(?:PEAK|POSITIV)', upper):
                    return 'NORMAL'
                elif re.search(r'(?:INCREAS\w*\s+IMPEDANCE|ACOUSTIC\s+IMPEDANCE).*?(?:TROUGH|NEGATIV)', upper):
                    return 'REVERSE'
                elif 'EUROPEAN' in upper:
                    return 'REVERSE'
                elif 'AMERICAN' in upper or 'SEG' in upper:
                    return 'NORMAL'
                elif 'NORMAL' in upper:
                    return 'NORMAL'
                elif 'REVERS' in upper:
                    return 'REVERSE'

        # Also search entire concatenated textual header
        full_text = " ".join(lines).upper()
        if 'POLARITY' in full_text:
            m_full = re.search(r'\bPOLARITY\b\s*[:=IS\s]+\s*(NORMAL|REVERSE|REVERSED)\b', full_text)
            if m_full:
                return 'REVERSE' if 'REV' in m_full.group(1) else 'NORMAL'
            m_full2 = re.search(r'\b(NORMAL|REVERSE|REVERSED)\s+POLARITY\b', full_text)
            if m_full2:
                return 'REVERSE' if 'REV' in m_full2.group(1) else 'NORMAL'

    except Exception as e:
        logger.debug(f"Polarity extraction failed for {file_path}: {e}")

    return def_clean


def extract_polarity_batch(
    list_path: List[str],
    default_polarity: str = "",
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> List[str]:
    """Extract polarities for a list of file paths. Values are strictly 'NORMAL' or 'REVERSE' (or empty string)."""
    polarities = []
    total = len(list_path)
    for idx, f in enumerate(list_path, start=1):
        pol = extract_seismic_polarity(f, default_polarity=default_polarity)
        polarities.append(pol)
        if progress_callback:
            progress_callback(idx, total, f)
    return polarities


import struct


def fast_segy_header_scan(file_path: str) -> Optional[Dict[str, Any]]:
    """Ultra-fast binary header and trace header extraction without loading full trace sample arrays."""
    try:
        norm_path = path_for_io(file_path)
        with open(norm_path, 'rb') as f:
            f.seek(3200)
            bin_hdr = f.read(400)
            if len(bin_hdr) < 26:
                return None

            sample_interval = struct.unpack('>h', bin_hdr[16:18])[0]
            samples_per_trace = struct.unpack('>h', bin_hdr[20:22])[0]
            format_code = struct.unpack('>h', bin_hdr[24:26])[0]

            endian = '>'
            if sample_interval <= 0 or samples_per_trace <= 0:
                sample_interval = struct.unpack('<h', bin_hdr[16:18])[0]
                samples_per_trace = struct.unpack('<h', bin_hdr[20:22])[0]
                format_code = struct.unpack('<h', bin_hdr[24:26])[0]
                endian = '<'

            if sample_interval <= 0 or samples_per_trace <= 0:
                return None

            bytes_per_sample = 4
            if format_code == 3:
                bytes_per_sample = 2
            elif format_code == 8:
                bytes_per_sample = 1

            trace_size = 240 + samples_per_trace * bytes_per_sample
            file_size = os.path.getsize(norm_path)
            if file_size < 3600 + trace_size:
                return None

            num_traces = max(1, (file_size - 3600) // trace_size)

            def _parse_th_fields(th_bytes):
                esp = struct.unpack(f'{endian}i', th_bytes[16:20])[0]
                sp197 = struct.unpack(f'{endian}i', th_bytes[196:200])[0]
                scalar = struct.unpack(f'{endian}h', th_bytes[200:202])[0]
                if scalar > 0:
                    sp197 = int(sp197 * scalar)
                elif scalar < 0:
                    sp197 = int(sp197 / abs(scalar))
                ffid = struct.unpack(f'{endian}i', th_bytes[8:12])[0]
                cdp = struct.unpack(f'{endian}i', th_bytes[20:24])[0]
                inl = struct.unpack(f'{endian}i', th_bytes[188:192])[0]
                xl = struct.unpack(f'{endian}i', th_bytes[192:196])[0]
                return esp, sp197, ffid, cdp, inl, xl

            # Read first trace header
            f.seek(3600)
            th_first = f.read(240)
            if len(th_first) < 240:
                return None

            esp1, sp197_1, ffid1, cdp1, inl1, xl1 = _parse_th_fields(th_first)
            esp_list = [esp1]
            sp197_list = [sp197_1]
            ffid_list = [ffid1]
            cdp_vals = [cdp1]
            inl_vals = [inl1]
            xl_vals = [xl1]

            # Read last trace header
            if num_traces > 1:
                f.seek(3600 + (num_traces - 1) * trace_size)
                th_last = f.read(240)
                if len(th_last) >= 240:
                    esp_l, sp197_l, ffid_l, cdp_l, inl_l, xl_l = _parse_th_fields(th_last)
                    esp_list.append(esp_l)
                    sp197_list.append(sp197_l)
                    ffid_list.append(ffid_l)
                    cdp_vals.append(cdp_l)
                    inl_vals.append(inl_l)
                    xl_vals.append(xl_l)

            # Sample up to 10 points between start and end
            if num_traces > 10:
                step = num_traces // 10
                for idx in range(step, num_traces - 1, step):
                    f.seek(3600 + idx * trace_size)
                    th = f.read(240)
                    if len(th) >= 240:
                        esp_m, sp197_m, ffid_m, cdp_m, inl_m, xl_m = _parse_th_fields(th)
                        esp_list.append(esp_m)
                        sp197_list.append(sp197_m)
                        ffid_list.append(ffid_m)
                        cdp_vals.append(cdp_m)
                        inl_vals.append(inl_m)
                        xl_vals.append(xl_m)

            # Intelligently resolve SP: Priority: EnergySourcePoint -> ShotPoint (bytes 197-200) -> FieldRecord (bytes 9-12)
            if any(v != 0 for v in esp_list):
                sp_vals = [v for v in esp_list if v != 0]
            elif any(v != 0 for v in sp197_list):
                sp_vals = [v for v in sp197_list if v != 0]
            elif any(v != 0 for v in ffid_list):
                sp_vals = [v for v in ffid_list if v != 0]
            else:
                sp_vals = esp_list

            si_ms = sample_interval / 1000.0
            rl_s = (si_ms * (samples_per_trace - 1)) / 1000.0
            u_si = 'ms' if si_ms % 2 == 0 else 'm'
            u_rl = 's' if si_ms % 2 == 0 else 'km'

            return {
                'sp_min': min(sp_vals) if sp_vals else 0,
                'sp_max': max(sp_vals) if sp_vals else 0,
                'cdp_min': min(cdp_vals) if cdp_vals else 0,
                'cdp_max': max(cdp_vals) if cdp_vals else 0,
                'inline_min': min(inl_vals) if inl_vals else 0,
                'inline_max': max(inl_vals) if inl_vals else 0,
                'crossline_min': min(xl_vals) if xl_vals else 0,
                'crossline_max': max(xl_vals) if xl_vals else 0,
                'sample_interval': si_ms,
                'record_length': rl_s,
                'satuan_si': u_si,
                'satuan_rec_length': u_rl,
            }
    except Exception as e:
        logger.debug(f"fast_segy_header_scan failed for {file_path}: {e}")
        return None


def generate_sp_sample_interval(list_path: List[str], progress_callback: Optional[Callable[[int, int, str], None]] = None):
    """Extract Shot Point (EnergySourcePoint, ShotPoint byte 197-200, or FieldRecord), sample interval, and record length."""
    sp_min, sp_max, sample_interval, record_length, satuan_si, satuan_rec_length = [], [], [], [], [], []
    total = len(list_path)
    for idx, i in enumerate(list_path, start=1):
        if not is_segy_file(i):
            sp_min.append(DEFAULT_HEADER_VALUE)
            sp_max.append(DEFAULT_HEADER_VALUE)
            sample_interval.append(DEFAULT_HEADER_VALUE)
            record_length.append(DEFAULT_HEADER_VALUE)
            satuan_si.append(DEFAULT_HEADER_VALUE)
            satuan_rec_length.append(DEFAULT_HEADER_VALUE)
        else:
            fast_res = fast_segy_header_scan(i)
            if fast_res is not None:
                sp_min.append(fast_res['sp_min'])
                sp_max.append(fast_res['sp_max'])
                sample_interval.append(fast_res['sample_interval'])
                record_length.append(fast_res['record_length'])
                satuan_si.append(fast_res['satuan_si'])
                satuan_rec_length.append(fast_res['satuan_rec_length'])
            else:
                try:
                    from segysak.segy import segy_header_scrape
                    trace_header = segy_header_scrape(path_for_io(i))
                    sp_series = None
                    for col in ['EnergySourcePoint', 'ShotPoint', 'FieldRecord']:
                        if col in trace_header:
                            s = trace_header[col].dropna()
                            if any(s != 0):
                                sp_series = s[s != 0]
                                break
                            elif sp_series is None:
                                sp_series = s

                    if sp_series is not None and len(sp_series) > 0:
                        sp_min.append(int(min(sp_series)))
                        sp_max.append(int(max(sp_series)))
                    else:
                        sp_min.append(DEFAULT_HEADER_VALUE)
                        sp_max.append(DEFAULT_HEADER_VALUE)

                    sample_interval.append(max(trace_header['TRACE_SAMPLE_INTERVAL']) / 1000)
                    record_length.append(min(trace_header['TRACE_SAMPLE_INTERVAL']) / 1000 * (min(trace_header['TRACE_SAMPLE_COUNT']) - 1) / 1000)
                    if (max(trace_header['TRACE_SAMPLE_INTERVAL']) / 1000) % 2 == 0:
                        satuan_si.append('ms')
                        satuan_rec_length.append('s')
                    else:
                        satuan_si.append('m')
                        satuan_rec_length.append('km')
                except Exception as e:
                    logger.warning(f"Error scraping SP header for {i}: {e}")
                    sp_min.append(DEFAULT_HEADER_VALUE)
                    sp_max.append(DEFAULT_HEADER_VALUE)
                    sample_interval.append(DEFAULT_HEADER_VALUE)
                    record_length.append(DEFAULT_HEADER_VALUE)
                    satuan_si.append(DEFAULT_HEADER_VALUE)
                    satuan_rec_length.append(DEFAULT_HEADER_VALUE)


        if progress_callback:
            progress_callback(idx, total, i)

    return sp_min, sp_max, sample_interval, record_length, satuan_si, satuan_rec_length


def generate_cdp_sample_interval(list_path: List[str], progress_callback: Optional[Callable[[int, int, str], None]] = None):
    """Extract CDP min/max, sample interval, and record length."""
    cdp_min, cdp_max, sample_interval, record_length, satuan_si, satuan_rec_length = [], [], [], [], [], []
    total = len(list_path)
    for idx, i in enumerate(list_path, start=1):
        if not is_segy_file(i):
            cdp_min.append(DEFAULT_HEADER_VALUE)
            cdp_max.append(DEFAULT_HEADER_VALUE)
            sample_interval.append(DEFAULT_HEADER_VALUE)
            record_length.append(DEFAULT_HEADER_VALUE)
            satuan_si.append(DEFAULT_HEADER_VALUE)
            satuan_rec_length.append(DEFAULT_HEADER_VALUE)
        else:
            fast_res = fast_segy_header_scan(i)
            if fast_res is not None:
                cdp_min.append(fast_res['cdp_min'])
                cdp_max.append(fast_res['cdp_max'])
                sample_interval.append(fast_res['sample_interval'])
                record_length.append(fast_res['record_length'])
                satuan_si.append(fast_res['satuan_si'])
                satuan_rec_length.append(fast_res['satuan_rec_length'])
            else:
                try:
                    from segysak.segy import segy_header_scrape
                    trace_header = segy_header_scrape(path_for_io(i))
                    cdp_min.append(min(trace_header['CDP']))
                    cdp_max.append(max(trace_header['CDP']))
                    sample_interval.append(max(trace_header['TRACE_SAMPLE_INTERVAL']) / 1000)
                    record_length.append(min(trace_header['TRACE_SAMPLE_INTERVAL']) / 1000 * (min(trace_header['TRACE_SAMPLE_COUNT']) - 1) / 1000)
                    if (max(trace_header['TRACE_SAMPLE_INTERVAL']) / 1000) % 2 == 0:
                        satuan_si.append('ms')
                        satuan_rec_length.append('s')
                    else:
                        satuan_si.append('m')
                        satuan_rec_length.append('km')
                except Exception as e:
                    logger.warning(f"Error scraping CDP header for {i}: {e}")
                    cdp_min.append(DEFAULT_HEADER_VALUE)
                    cdp_max.append(DEFAULT_HEADER_VALUE)
                    sample_interval.append(DEFAULT_HEADER_VALUE)
                    record_length.append(DEFAULT_HEADER_VALUE)
                    satuan_si.append(DEFAULT_HEADER_VALUE)
                    satuan_rec_length.append(DEFAULT_HEADER_VALUE)

        if progress_callback:
            progress_callback(idx, total, i)

    return cdp_min, cdp_max, sample_interval, record_length, satuan_si, satuan_rec_length


def generate_sp_sample_interval_3d(list_path: List[str], progress_callback: Optional[Callable[[int, int, str], None]] = None):
    """Extract 3D SP, sample interval, and Inline/Crossline ranges."""
    sp_min, sp_max, sample_interval, record_length = [], [], [], []
    satuan_si, satuan_rec_length = [], []
    inline_min, inline_max, crossline_min, crossline_max = [], [], [], []

    total = len(list_path)
    for idx, i in enumerate(list_path, start=1):
        if not is_segy_file(i):
            for lst in [sp_min, sp_max, sample_interval, record_length, satuan_si, satuan_rec_length, inline_min, inline_max, crossline_min, crossline_max]:
                lst.append(DEFAULT_HEADER_VALUE)
        else:
            fast_res = fast_segy_header_scan(i)
            if fast_res is not None:
                sp_min.append(fast_res['sp_min'])
                sp_max.append(fast_res['sp_max'])
                sample_interval.append(fast_res['sample_interval'])
                record_length.append(fast_res['record_length'])
                satuan_si.append(fast_res['satuan_si'])
                satuan_rec_length.append(fast_res['satuan_rec_length'])
                inline_min.append(fast_res['inline_min'])
                inline_max.append(fast_res['inline_max'])
                crossline_min.append(fast_res['crossline_min'])
                crossline_max.append(fast_res['crossline_max'])
            else:
                try:
                    from segysak.segy import segy_header_scrape
                    trace_header = segy_header_scrape(path_for_io(i))
                    sp_series = None
                    for col in ['EnergySourcePoint', 'ShotPoint', 'FieldRecord']:
                        if col in trace_header:
                            s = trace_header[col].dropna()
                            if any(s != 0):
                                sp_series = s[s != 0]
                                break
                            elif sp_series is None:
                                sp_series = s

                    if sp_series is not None and len(sp_series) > 0:
                        sp_min.append(int(min(sp_series)))
                        sp_max.append(int(max(sp_series)))
                    else:
                        sp_min.append(DEFAULT_HEADER_VALUE)
                        sp_max.append(DEFAULT_HEADER_VALUE)

                    sample_interval.append(max(trace_header['TRACE_SAMPLE_INTERVAL']) / 1000)
                    record_length.append(min(trace_header['TRACE_SAMPLE_INTERVAL']) / 1000 * (min(trace_header['TRACE_SAMPLE_COUNT']) - 1) / 1000)
                    if (max(trace_header['TRACE_SAMPLE_INTERVAL']) / 1000) % 2 == 0:
                        satuan_si.append('ms')
                        satuan_rec_length.append('s')
                    else:
                        satuan_si.append('m')
                        satuan_rec_length.append('km')
                    inline_min.append(min(trace_header.get('INLINE_3D', [DEFAULT_HEADER_VALUE])))
                    inline_max.append(max(trace_header.get('INLINE_3D', [DEFAULT_HEADER_VALUE])))
                    crossline_min.append(min(trace_header.get('CROSSLINE_3D', [DEFAULT_HEADER_VALUE])))
                    crossline_max.append(max(trace_header.get('CROSSLINE_3D', [DEFAULT_HEADER_VALUE])))
                except Exception as e:
                    logger.warning(f"Error scraping 3D SP header for {i}: {e}")
                    for lst in [sp_min, sp_max, sample_interval, record_length, satuan_si, satuan_rec_length, inline_min, inline_max, crossline_min, crossline_max]:
                        lst.append(DEFAULT_HEADER_VALUE)


        if progress_callback:
            progress_callback(idx, total, i)

    return sp_min, sp_max, sample_interval, record_length, satuan_si, satuan_rec_length, inline_min, inline_max, crossline_min, crossline_max


def generate_cdp_sample_interval_3d(list_path: List[str], progress_callback: Optional[Callable[[int, int, str], None]] = None):
    """Extract 3D CDP, sample interval, and Inline/Crossline ranges."""
    cdp_min, cdp_max, sample_interval, record_length = [], [], [], []
    satuan_si, satuan_rec_length = [], []
    inline_min, inline_max, crossline_min, crossline_max = [], [], [], []

    total = len(list_path)
    for idx, i in enumerate(list_path, start=1):
        if not is_segy_file(i):
            for lst in [cdp_min, cdp_max, sample_interval, record_length, satuan_si, satuan_rec_length, inline_min, inline_max, crossline_min, crossline_max]:
                lst.append(DEFAULT_HEADER_VALUE)
        else:
            fast_res = fast_segy_header_scan(i)
            if fast_res is not None:
                cdp_min.append(fast_res['cdp_min'])
                cdp_max.append(fast_res['cdp_max'])
                sample_interval.append(fast_res['sample_interval'])
                record_length.append(fast_res['record_length'])
                satuan_si.append(fast_res['satuan_si'])
                satuan_rec_length.append(fast_res['satuan_rec_length'])
                inline_min.append(fast_res['inline_min'])
                inline_max.append(fast_res['inline_max'])
                crossline_min.append(fast_res['crossline_min'])
                crossline_max.append(fast_res['crossline_max'])
            else:
                try:
                    from segysak.segy import segy_header_scrape
                    trace_header = segy_header_scrape(path_for_io(i))
                    cdp_min.append(min(trace_header['CDP']))
                    cdp_max.append(max(trace_header['CDP']))
                    sample_interval.append(max(trace_header['TRACE_SAMPLE_INTERVAL']) / 1000)
                    record_length.append(min(trace_header['TRACE_SAMPLE_INTERVAL']) / 1000 * (min(trace_header['TRACE_SAMPLE_COUNT']) - 1) / 1000)
                    if (max(trace_header['TRACE_SAMPLE_INTERVAL']) / 1000) % 2 == 0:
                        satuan_si.append('ms')
                        satuan_rec_length.append('s')
                    else:
                        satuan_si.append('m')
                        satuan_rec_length.append('km')
                    inline_min.append(min(trace_header.get('INLINE_3D', [DEFAULT_HEADER_VALUE])))
                    inline_max.append(max(trace_header.get('INLINE_3D', [DEFAULT_HEADER_VALUE])))
                    crossline_min.append(min(trace_header.get('CROSSLINE_3D', [DEFAULT_HEADER_VALUE])))
                    crossline_max.append(max(trace_header.get('CROSSLINE_3D', [DEFAULT_HEADER_VALUE])))
                except Exception as e:
                    logger.warning(f"Error scraping 3D CDP header for {i}: {e}")
                    for lst in [cdp_min, cdp_max, sample_interval, record_length, satuan_si, satuan_rec_length, inline_min, inline_max, crossline_min, crossline_max]:
                        lst.append(DEFAULT_HEADER_VALUE)

        if progress_callback:
            progress_callback(idx, total, i)

    return cdp_min, cdp_max, sample_interval, record_length, satuan_si, satuan_rec_length, inline_min, inline_max, crossline_min, crossline_max


def save_dataframe_to_excel_safe(df: pd.DataFrame, folder_path: str, filename: str) -> str:
    """Save dataframe to Excel file, using fallback timestamp filename if file is locked."""
    base_name, ext = os.path.splitext(filename)
    target_path = os.path.join(folder_path, filename)
    io_path = path_for_io(target_path)
    try:
        df.to_excel(io_path, index=False)
        return target_path
    except PermissionError:
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        alt_filename = f"{base_name}_{ts}{ext}"
        alt_path = os.path.join(folder_path, alt_filename)
        logger.warning(f"File {target_path} sedang dibuka/terkunci, menyimpan ke {alt_path}")
        df.to_excel(path_for_io(alt_path), index=False)
        return alt_path
    except Exception as e:
        logger.error(f"Gagal menyimpan file Excel ke {target_path}: {e}")
        import tempfile, datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        tmp_path = os.path.join(tempfile.gettempdir(), f"{base_name}_{ts}{ext}")
        df.to_excel(path_for_io(tmp_path), index=False)
        return tmp_path


def sanitize_records_for_json(df: pd.DataFrame, max_rows: int = 500) -> List[Dict[str, Any]]:
    """Convert dataframe rows to strictly valid JSON objects with no NaN/Inf."""
    import math
    import datetime
    import numpy as np
    target_df = df.iloc[:max_rows] if len(df) > max_rows else df
    safe_df = target_df.fillna("")
    records = safe_df.to_dict(orient="records")
    clean_records = []
    for r in records:
        clean_row = {}
        for k, v in r.items():
            if v is None or pd.isna(v):
                clean_row[k] = ""
            elif isinstance(v, (np.floating, float)):
                if math.isnan(v) or math.isinf(v):
                    clean_row[k] = ""
                else:
                    clean_row[k] = float(v)
            elif isinstance(v, (np.integer, int)):
                clean_row[k] = int(v)
            elif isinstance(v, (np.bool_, bool)):
                clean_row[k] = bool(v)
            elif isinstance(v, (datetime.date, datetime.datetime, pd.Timestamp)):
                clean_row[k] = str(v)
            else:
                clean_row[k] = str(v).strip()
        clean_records.append(clean_row)
    return clean_records


def well_information_extraction(list_path: List[str], progress_callback: Optional[Callable[[int, int, str], None]] = None):
    """Extract Well metadata from LAS files using lasio fast header read with regex and welly fallback."""
    well_name = []
    field_name = []
    date = []
    top_depth = []
    base_depth = []
    log_comp = []
    log_title = []
    ouom = []
    run_number = []

    total = len(list_path)
    for index, i in enumerate(list_path, start=1):
        io_p = path_for_io(i)

        # Default safe fallback values for this file
        w_val = "Unknown"
        f_val = "Unknown"
        d_val = ""
        t_val: Any = ""
        b_val: Any = ""
        c_val = "Unknown"
        u_val = "m"
        r_val = ""
        curves_str = "Unknown"

        extracted = False

        # 1. Primary Reader: lasio fast header read (ignore_data avoids parsing millions of curve samples)
        try:
            import lasio
            las = lasio.read(
                io_p,
                ignore_data=True,
                ignore_header_errors=True,
                encoding_errors='replace'
            )

            def _get_las_val(mnems: List[str], default: str = "") -> str:
                for m in mnems:
                    try:
                        item = las.well.get(m)
                        if item is not None and item.value is not None:
                            v = str(item.value).strip()
                            if v and v.lower() not in ("none", "nan", "null", "-999.25", "-9999", "-9999.0"):
                                return v
                    except Exception:
                        continue
                return default

            extracted_w = _get_las_val(['WELL', 'WELLNAME', 'WELL_NAME', 'WELL NAME'])
            if extracted_w:
                w_val = extracted_w.upper()

            extracted_f = _get_las_val(['FLD', 'FIELD', 'FIELD_NAME', 'FIELD NAME'])
            if extracted_f:
                f_val = extracted_f.upper()

            extracted_d = _get_las_val(['DATE', 'TRIP_DATE', 'DATE1', 'DATE2'])
            if extracted_d:
                d_val = extracted_d

            def _get_item(mnems: List[str]):
                for m in mnems:
                    try:
                        item = las.well.get(m)
                        if item is not None:
                            return item
                    except Exception:
                        continue
                return None

            # STRT / TOP DEPTH
            try:
                strt_item = _get_item(['STRT', 'START', 'STRT_DEPTH'])
                if strt_item is not None and strt_item.value is not None and pd.notna(strt_item.value):
                    try:
                        t_val = float(strt_item.value)
                    except (ValueError, TypeError):
                        t_val = str(strt_item.value).strip()
                    if getattr(strt_item, 'unit', None):
                        unit_str = str(strt_item.unit).strip().lower()
                        if unit_str in ('f', 'ft', 'feet'):
                            u_val = 'ft'
                        elif unit_str in ('m', 'meter', 'meters'):
                            u_val = 'm'
                        elif unit_str:
                            u_val = unit_str
            except Exception:
                pass

            # STOP / BASE DEPTH
            try:
                stop_item = _get_item(['STOP', 'BASE', 'STOP_DEPTH'])
                if stop_item is not None and stop_item.value is not None and pd.notna(stop_item.value):
                    try:
                        b_val = float(stop_item.value)
                    except (ValueError, TypeError):
                        b_val = str(stop_item.value).strip()
            except Exception:
                pass


            extracted_r = _get_las_val(['RUN', 'RUN_NUMBER', 'RUN NUMBER'])
            if extracted_r:
                r_val = extracted_r

            extracted_c = _get_las_val(['SVCO', 'SRVC', 'COMP', 'COMPANY', 'SERVICE'])
            if extracted_c:
                c_val = extracted_c.upper()

            try:
                curves = [str(c.mnemonic).strip() for c in getattr(las, 'curves', []) if getattr(c, 'mnemonic', None)]
                if curves:
                    curves_str = "-".join(curves)
            except Exception:
                pass

            extracted = True
        except Exception as e:
            logger.debug(f"lasio fast read failed for {i}: {e}")

        # 2. Secondary fallback: Fast line-by-line ASCII header scanner with latin-1
        if not extracted or w_val == "Unknown":
            try:
                with open(io_p, 'r', encoding='latin-1', errors='replace') as lf:
                    lines = [lf.readline() for _ in range(600)]

                in_well_sec = False
                in_curve_sec = False
                found_curves = []

                for line in lines:
                    line_s = line.strip()
                    if not line_s:
                        continue
                    if line_s.startswith('~'):
                        sec_char = line_s[1:2].upper()
                        in_well_sec = (sec_char == 'W')
                        in_curve_sec = (sec_char == 'C')
                        if sec_char in ('A', 'O', 'P'):
                            break
                        continue

                    if in_well_sec and '.' in line_s and ':' in line_s:
                        parts = line_s.split(':', 1)
                        left = parts[0]
                        dot_idx = left.find('.')
                        mnem = left[:dot_idx].strip().upper()
                        val_and_unit = left[dot_idx+1:].strip()
                        tokens = val_and_unit.split()
                        val_part = tokens[-1] if tokens else ""
                        if len(tokens) > 1:
                            val_part = " ".join(tokens[1:])

                        if mnem in ('WELL', 'WELLNAME', 'WELL_NAME') and w_val == "Unknown":
                            if val_part:
                                w_val = val_part.strip().upper()
                        elif mnem in ('FLD', 'FIELD', 'FIELD_NAME') and f_val == "Unknown":
                            if val_part:
                                f_val = val_part.strip().upper()
                        elif mnem in ('DATE', 'TRIP_DATE') and not d_val:
                            if val_part:
                                d_val = val_part.strip()
                        elif mnem in ('STRT', 'START') and t_val == "":
                            try:
                                t_val = float(val_part)
                            except Exception:
                                t_val = val_part
                            if tokens and tokens[0].lower() in ('f', 'ft', 'feet'):
                                u_val = 'ft'
                        elif mnem in ('STOP', 'BASE') and b_val == "":
                            try:
                                b_val = float(val_part)
                            except Exception:
                                b_val = val_part
                        elif mnem in ('RUN', 'RUN_NUMBER') and not r_val:
                            if val_part:
                                r_val = val_part.strip()
                        elif mnem in ('COMP', 'COMPANY', 'SVCO', 'SRVC') and c_val == "Unknown":
                            if val_part:
                                c_val = val_part.strip().upper()

                    elif in_curve_sec and '.' in line_s:
                        dot_idx = line_s.find('.')
                        c_mnem = line_s[:dot_idx].strip()
                        if c_mnem and not c_mnem.startswith('#'):
                            found_curves.append(c_mnem)

                if found_curves and curves_str == "Unknown":
                    curves_str = "-".join(found_curves)
            except Exception as e_text:
                logger.debug(f"text header scan failed for {i}: {e_text}")

        # 3. Tertiary fallback: welly if still unextracted
        if not extracted and w_val == "Unknown":
            try:
                from welly import Well
                well = Well.from_las(io_p)
                header = well.header
                try:
                    val = header[header['mnemonic'] == 'WELL']['value'].values[0]
                    if pd.notna(val) and str(val).strip():
                        w_val = str(val).strip().upper()
                except Exception:
                    pass
                try:
                    val = header[header['mnemonic'] == 'FLD']['value'].values[0]
                    if pd.notna(val) and str(val).strip():
                        f_val = str(val).strip().upper()
                except Exception:
                    pass
                try:
                    val = header[header['mnemonic'] == 'DATE']['value'].values[0]
                    if pd.notna(val) and str(val).strip():
                        d_val = str(val).strip()
                except Exception:
                    pass
                try:
                    val = header[header['mnemonic'] == 'STRT']['value'].values[0]
                    if pd.notna(val):
                        t_val = float(val)
                except Exception:
                    pass
                try:
                    val = header[header['mnemonic'] == 'STOP']['value'].values[0]
                    if pd.notna(val):
                        b_val = float(val)
                except Exception:
                    pass
                try:
                    val = header[header['mnemonic'] == 'RUN']['value'].values[0]
                    if pd.notna(val) and str(val).strip():
                        r_val = str(val).strip()
                except Exception:
                    pass
                try:
                    val = header[header['mnemonic'] == 'SVCO']['value'].values[0]
                    if pd.notna(val) and str(val).strip():
                        c_val = str(val).strip().upper()
                except Exception:
                    pass
                try:
                    val = header[header['mnemonic'] == 'STRT']['unit'].values[0]
                    if pd.notna(val) and str(val).strip():
                        u_val = str(val).strip().lower()
                except Exception:
                    pass
                try:
                    curves_str = "-".join(list(well.data.keys()))
                except Exception:
                    pass
            except Exception as e_welly:
                logger.debug(f"welly read failed for {i}: {e_welly}")

        # EXACTLY ONE APPEND PER FILE TO PREVENT MISMATCHED LENGTH ERRORS
        well_name.append(w_val)
        field_name.append(f_val)
        date.append(d_val)
        top_depth.append(t_val)
        base_depth.append(b_val)
        log_comp.append(c_val)
        ouom.append(u_val)
        log_title.append(curves_str)
        run_number.append(r_val)

        if progress_callback:
            progress_callback(index, total, i)

    return well_name, field_name, date, top_depth, base_depth, log_comp, ouom, log_title, run_number



def generate_seismic_catalog(
    catalog_type: str,
    folder_path: str,
    params: Dict[str, Any],
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Generate seismic catalog for standard PPDM 3.9 catalogs:
    - B.1.5.1 SEIS_2D_FIELD_DIGITAL
    - B.1.5.2 SEIS_2D_PROCESS_DIGITAL
    - B.2.3.1 SEIS_3D_FIELD_DIGITAL
    - B.2.3.2 SEIS_3D_PROCESS_DIGITAL
    - B.1.6.1 SEIS_2D_NAVI_DIGITAL
    - B.2.4.1 SEIS_3D_NAVI_DIGITAL
    """
    def _notify(percent: int, msg: str, file_name: str = "", current_index: int = 0, total_files: int = 0, stage: str = ""):
        if progress_callback:
            try:
                progress_callback({
                    "percent": percent,
                    "message": msg,
                    "current_file": file_name,
                    "current_index": current_index,
                    "total_files": total_files,
                    "stage": stage,
                })
            except TypeError:
                progress_callback(percent, msg)

    _notify(2, "Memindai folder file seismik...", stage="scan")
    full_name_path = list_files_with_paths_and_folders(folder_path)
    all_paths = full_name_path[0]
    all_names = full_name_path[1]
    all_dirs = full_name_path[2]

    # Exclude generated Excel catalogs, temp files, and hidden files
    indices = [
        i for i, f in enumerate(all_names)
        if not f.startswith("~$") and not f.startswith(".") and not f.lower().endswith((".xlsx", ".xls", ".tmp"))
    ]
    list_of_path = [all_paths[i] for i in indices]
    file_names = [all_names[i] for i in indices]
    path_of_file = [all_dirs[i] for i in indices]

    if not file_names:
        return {
            "status": "warning",
            "message": "Tidak ada file seismik ditemukan dalam folder yang dipilih.",
            "total_files": 0,
            "catalog_type": catalog_type,
            "output_path": None,
            "rows": []
        }


    ba_long_name = str(params.get("BA_LONG_NAME", "")).upper()
    ba_type = params.get("BA_TYPE", "BADAN USAHA")
    area_id = params.get("AREA_ID", "")
    area_type = params.get("AREA_TYPE", "WILAYAH KERJA")
    step_type = params.get("STEP_TYPE", "RAW FIELD")
    item_category = params.get("ITEM_CATEGORY", "1. ACQUISITION")
    item_sub_category = params.get("ITEM_SUB_CATEGORY", "1.1. F - FIELD DATA")
    media_type = params.get("MEDIA_TYPE", "EKSTERNAL HARDISK")
    seis_point_label = params.get("SEIS_POINT_LABEL", "CDP")
    row_quality = params.get("ROW_QUALITY", "TERVERIFIKASI OLEH SKK MIGAS")
    checked_by_ba_id = params.get("CHECKED_BY_BA_ID", "")
    dimension = params.get("DIMENSION", "2D")
    generate_md5 = bool(params.get("generate_md5", False))

    n = len(file_names)
    df = pd.DataFrame()

    is_navi = catalog_type in ["B.1.6.1 SEIS_2D_NAVI_DIGITAL", "B.2.4.1 SEIS_3D_NAVI_DIGITAL"]

    def _line_progress(idx, total, fpath):
        fname = os.path.basename(fpath)
        if is_navi:
            pct = 5 + int((idx / max(total, 1)) * (45 if generate_md5 else 80))
        else:
            pct = 5 + int((idx / max(total, 1)) * (25 if generate_md5 else 40))
        _notify(pct, f"Ekstraksi Line Name ({idx}/{total}): {fname}", file_name=fname, current_index=idx, total_files=total, stage="line_name")

    lines = line_name(list_of_path, progress_callback=_line_progress)

    _notify(50 if (is_navi and generate_md5) else (85 if is_navi else (30 if generate_md5 else 45)), "Mengambil format dan ekstensi file...", stage="ext")
    exts = get_file_extensions(list_of_path)

    def _header_progress(idx, total, fpath):
        fname = os.path.basename(fpath)
        if generate_md5:
            pct = 30 + int((idx / max(total, 1)) * 30)
        else:
            pct = 45 + int((idx / max(total, 1)) * 45)
        _notify(pct, f"Ekstraksi Header {seis_point_label} ({idx}/{total}): {fname}", file_name=fname, current_index=idx, total_files=total, stage="header")

    # Header extraction depending on catalog type
    header_data = None
    if catalog_type in ["B.1.5.1 SEIS_2D_FIELD_DIGITAL", "B.1.5.2 SEIS_2D_PROCESS_DIGITAL"]:
        if seis_point_label == 'CDP':
            header_data = generate_cdp_sample_interval(list_of_path, progress_callback=_header_progress)
        else:
            header_data = generate_sp_sample_interval(list_of_path, progress_callback=_header_progress)
    elif catalog_type in ["B.2.3.1 SEIS_3D_FIELD_DIGITAL", "B.2.3.2 SEIS_3D_PROCESS_DIGITAL"]:
        if seis_point_label == 'CDP':
            header_data = generate_cdp_sample_interval_3d(list_of_path, progress_callback=_header_progress)
        else:
            header_data = generate_sp_sample_interval_3d(list_of_path, progress_callback=_header_progress)

    # MD5 calculation
    decrypt_keys = ["" for _ in range(n)]
    decryption_types = ["" for _ in range(n)]
    if generate_md5:
        def _md5_progress(idx, total, fpath):
            fname = os.path.basename(fpath)
            if is_navi:
                pct = 50 + int((idx / max(total, 1)) * 38)
            else:
                pct = 60 + int((idx / max(total, 1)) * 30)
            _notify(pct, f"Generate MD5 ({idx}/{total}): {fname}", file_name=fname, current_index=idx, total_files=total, stage="md5")

        decrypt_keys = get_md5_from_path(list_of_path, progress_callback=_md5_progress)
        decryption_types = ["MD5" for _ in range(n)]

    def _size_progress(idx, total, fpath):
        fname = os.path.basename(fpath)
        pct = 90 + int((idx / max(total, 1)) * 3)
        _notify(pct, f"Membaca ukuran berkas ({idx}/{total}): {fname}", file_name=fname, current_index=idx, total_files=total, stage="sizes")

    sizes = get_file_sizes(list_of_path, progress_callback=_size_progress)
    size_uoms = ["byte" for _ in range(n)]

    # Polarity extraction for processing catalogs
    has_polarity = catalog_type in ["B.1.5.2 SEIS_2D_PROCESS_DIGITAL", "B.2.3.2 SEIS_3D_PROCESS_DIGITAL"]
    polarities = ["" for _ in range(n)]
    if has_polarity:
        def _pol_progress(idx, total, fpath):
            fname = os.path.basename(fpath)
            pct = 90 + int((idx / max(total, 1)) * 3)
            _notify(pct, f"Ekstraksi Polarity ({idx}/{total}): {fname}", file_name=fname, current_index=idx, total_files=total, stage="polarity")

        user_pol = params.get("POLARITY", "")
        polarities = extract_polarity_batch(list_of_path, default_polarity=user_pol, progress_callback=_pol_progress)

    _notify(93, "Menyusun skema kolom katalog PPDM 3.9...", stage="schema")

    # Build schema
    if catalog_type == "B.1.5.2 SEIS_2D_PROCESS_DIGITAL":
        df = pd.DataFrame({
            'BA_LONG_NAME': [ba_long_name] * n,
            'BA_TYPE': [ba_type] * n,
            'AREA_ID': [area_id] * n,
            'AREA_TYPE': [area_type] * n,
            'ACQTN_SURVEY_NAME': [""] * n,
            'PROCESSING_COMPANY': [""] * n,
            'START_DATE': [""] * n,
            'RCRD_REC_LENGTH': header_data[3] if header_data else [""] * n,
            'RCRD_REC_LENGTH_OUOM': header_data[5] if header_data else [""] * n,
            'RCRD_SAMPLE_RATE': header_data[2] if header_data else [""] * n,
            'RCRD_SAMPLE_RATE_OUOM': header_data[4] if header_data else [""] * n,
            'LINE_NAME': lines,
            'DIGITAL_FORMAT': exts,
            'STEP_TYPE': [step_type] * n,
            'ITEM_CATEGORY': [item_category] * n,
            'ITEM_SUB_CATEGORY': [item_sub_category] * n,
            'MEDIA_TYPE': [media_type] * n,
            'FIRST_SEIS_POINT_ID': header_data[0] if header_data else [""] * n,
            'LAST_SEIS_POINT_ID': header_data[1] if header_data else [""] * n,
            'SEIS_POINT_LABEL': [seis_point_label] * n,
            'POLARITY': polarities,
            'BA_LONG_NAME_1': [""] * n,
            'BA_TYPE_1': [""] * n,
            'DATA_STORE_NAME': path_of_file,
            'ORIGINAL_FILE_NAME': file_names,
            'DECRYPT_KEY': decrypt_keys,
            'DECRYPTION_TYPE': decryption_types,
            'SW_APPLICATION_ID': [""] * n,
            'APPLICATION_VERSION': [""] * n,
            'DIGITAL_SIZE': sizes,
            'DIGITAL_SIZE_UOM': size_uoms,
            'REMARK': [""] * n,
            'SOURCE': [""] * n,
            'ROW_QUALITY': [row_quality] * n,
            'CHECKED_BY_BA_ID': [checked_by_ba_id] * n,
        })
    elif catalog_type == "B.1.5.1 SEIS_2D_FIELD_DIGITAL":
        df = pd.DataFrame({
            'BA_LONG_NAME': [ba_long_name] * n,
            'BA_TYPE': [ba_type] * n,
            'AREA_ID': [area_id] * n,
            'AREA_TYPE': [area_type] * n,
            'ACQTN_SURVEY_NAME': [""] * n,
            'SHOT_BY': [""] * n,
            'START_DATE': [""] * n,
            'RCRD_REC_LENGTH': header_data[3] if header_data else [""] * n,
            'RCRD_REC_LENGTH_OUOM': header_data[5] if header_data else [""] * n,
            'RCRD_SAMPLE_RATE': header_data[2] if header_data else [""] * n,
            'RCRD_SAMPLE_RATE_OUOM': header_data[4] if header_data else [""] * n,
            'LINE_NAME': lines,
            'DIGITAL_FORMAT': exts,
            'STEP_TYPE': [step_type] * n,
            'ITEM_CATEGORY': [item_category] * n,
            'ITEM_SUB_CATEGORY': [item_sub_category] * n,
            'CREATE_DATE': [""] * n,
            'FIRST_SEIS_POINT_ID': header_data[0] if header_data else [""] * n,
            'LAST_SEIS_POINT_ID': header_data[1] if header_data else [""] * n,
            'SEIS_POINT_LABEL': [seis_point_label] * n,
            'FIELD_FILE_NUMBER': [""] * n,
            'TAPE_NUMBER': [""] * n,
            'BA_LONG_NAME_1': [""] * n,
            'BA_TYPE_1': [""] * n,
            'DATA_STORE_NAME': path_of_file,
            'ORIGINAL_FILE_NAME': file_names,
            'DECRYPT_KEY': decrypt_keys,
            'DECRYPTION_TYPE': decryption_types,
            'DIGITAL_SIZE': sizes,
            'DIGITAL_SIZE_UOM': size_uoms,
            'REMARK': [""] * n,
            'SOURCE': [""] * n,
            'ROW_QUALITY': [row_quality] * n,
            'CHECKED_BY_BA_ID': [checked_by_ba_id] * n,
        })
    elif catalog_type == "B.2.3.2 SEIS_3D_PROCESS_DIGITAL":
        df = pd.DataFrame({
            'BA_LONG_NAME': [ba_long_name] * n,
            'BA_TYPE': [ba_type] * n,
            'AREA_ID': [area_id] * n,
            'AREA_TYPE': [area_type] * n,
            'ACQTN_SURVEY_NAME': [""] * n,
            'DIMENSION': [dimension] * n,
            'SHOT_BY': [""] * n,
            'LINE_NAME': lines,
            'PROCESSING_COMPANY': [""] * n,
            'START_DATE': [""] * n,
            'STEP_TYPE': [step_type] * n,
            'ITEM_CATEGORY': [item_category] * n,
            'ITEM_SUB_CATEGORY': [item_sub_category] * n,
            'RCRD_REC_LENGTH': header_data[3] if header_data else [""] * n,
            'RCRD_REC_LENGTH_OUOM': header_data[5] if header_data else [""] * n,
            'RCRD_SAMPLE_RATE': header_data[2] if header_data else [""] * n,
            'RCRD_SAMPLE_RATE_OUOM': header_data[4] if header_data else [""] * n,
            'FIRST_SEIS_POINT_ID': header_data[0] if header_data else [""] * n,
            'LAST_SEIS_POINT_ID': header_data[1] if header_data else [""] * n,
            'SEIS_POINT_LABEL': [seis_point_label] * n,
            'FIRST_NLINE_NO': header_data[6] if header_data else [""] * n,
            'LAST_NLINE_NO': header_data[7] if header_data else [""] * n,
            'FIRST_XLINE_NO': header_data[8] if header_data else [""] * n,
            'LAST_XLINE_NO': header_data[9] if header_data else [""] * n,
            'DIGITAL_FORMAT': exts,
            'MEDIA_TYPE': [media_type] * n,
            'POLARITY': polarities,
            'BA_LONG_NAME_1': [""] * n,
            'BA_TYPE_1': [""] * n,
            'DATA_STORE_NAME': path_of_file,
            'ORIGINAL_FILE_NAME': file_names,
            'DECRYPT_KEY': decrypt_keys,
            'DECRYPTION_TYPE': decryption_types,
            'SW_APPLICATION_ID': [""] * n,
            'APPLICATION_VERSION': [""] * n,
            'DIGITAL_SIZE': sizes,
            'DIGITAL_SIZE_UOM': size_uoms,
            'REMARK': [""] * n,
            'SOURCE': [""] * n,
            'ROW_QUALITY': [row_quality] * n,
            'CHECKED_BY_BA_ID': [checked_by_ba_id] * n,
        })
    elif catalog_type == "B.2.3.1 SEIS_3D_FIELD_DIGITAL":
        df = pd.DataFrame({
            'BA_LONG_NAME': [ba_long_name] * n,
            'BA_TYPE': [ba_type] * n,
            'AREA_ID': [area_id] * n,
            'AREA_TYPE': [area_type] * n,
            'ACQTN_SURVEY_NAME': [""] * n,
            'DIMENSION': [dimension] * n,
            'LINE_NAME': lines,
            'SHOT_BY': [""] * n,
            'START_DATE': [""] * n,
            'STEP_TYPE': [step_type] * n,
            'ITEM_CATEGORY': [item_category] * n,
            'ITEM_SUB_CATEGORY': [item_sub_category] * n,
            'RCRD_REC_LENGTH': header_data[3] if header_data else [""] * n,
            'RCRD_REC_LENGTH_OUOM': header_data[5] if header_data else [""] * n,
            'RCRD_SAMPLE_RATE': header_data[2] if header_data else [""] * n,
            'RCRD_SAMPLE_RATE_OUOM': header_data[4] if header_data else [""] * n,
            'CREATE_DATE': [""] * n,
            'FIRST_SEIS_POINT_ID': header_data[0] if header_data else [""] * n,
            'LAST_SEIS_POINT_ID': header_data[1] if header_data else [""] * n,
            'SEIS_POINT_LABEL': [seis_point_label] * n,
            'DIGITAL_FORMAT': exts,
            'TAPE_NUMBER': [""] * n,
            'FIELD_FILE_NUMBER': [""] * n,
            'BA_LONG_NAME_1': [""] * n,
            'BA_TYPE_1': [""] * n,
            'DATA_STORE_NAME': path_of_file,
            'ORIGINAL_FILE_NAME': file_names,
            'DECRYPT_KEY': decrypt_keys,
            'DECRYPTION_TYPE': decryption_types,
            'DIGITAL_SIZE': sizes,
            'DIGITAL_SIZE_UOM': size_uoms,
            'REMARK': [""] * n,
            'SOURCE': [""] * n,
            'ROW_QUALITY': [row_quality] * n,
            'CHECKED_BY_BA_ID': [checked_by_ba_id] * n,
        })
    elif catalog_type == "B.1.6.1 SEIS_2D_NAVI_DIGITAL":
        df = pd.DataFrame({
            'BA_LONG_NAME': [ba_long_name] * n,
            'BA_TYPE': [ba_type] * n,
            'AREA_ID': [area_id] * n,
            'AREA_TYPE': [area_type] * n,
            'ACQTN_SURVEY_NAME': [""] * n,
            'SEIS_DIMENSION': [dimension] * n,
            'PROCESS_DATE': [""] * n,
            'SHOT_BY': [""] * n,
            'LINE_NAME': lines,
            'DIGITAL_FORMAT': exts,
            'MEDIA_TYPE': [media_type] * n,
            'ORIGINAL_FILE_NAME': file_names,
            'DECRYPT_KEY': decrypt_keys,
            'DECRYPTION_TYPE': decryption_types,
            'DIGITAL_SIZE': sizes,
            'DIGITAL_SIZE_UOM': size_uoms,
            'BA_LONG_NAME_1': [""] * n,
            'BA_TYPE_1': [""] * n,
            'DATA_STORE_NAME': path_of_file,
            'REMARK': [""] * n,
            'SOURCE': [""] * n,
            'ROW_QUALITY': [row_quality] * n,
            'CHECKED_BY_BA_ID': [checked_by_ba_id] * n,
        })
    elif catalog_type == "B.2.4.1 SEIS_3D_NAVI_DIGITAL":
        df = pd.DataFrame({
            'BA_LONG_NAME': [ba_long_name] * n,
            'BA_TYPE': [ba_type] * n,
            'AREA_ID': [area_id] * n,
            'AREA_TYPE': [area_type] * n,
            'ACQTN_SURVEY_NAME': [""] * n,
            'SEIS_DIMENSION': [dimension] * n,
            'SHOT_BY': [""] * n,
            'PROCESS_DATE': [""] * n,
            'DIGITAL_FORMAT': exts,
            'DATA_STORE_NAME': path_of_file,
            'ORIGINAL_FILE_NAME': file_names,
            'DECRYPT_KEY': decrypt_keys,
            'DECRYPTION_TYPE': decryption_types,
            'DIGITAL_SIZE': sizes,
            'DIGITAL_SIZE_UOM': size_uoms,
            'BA_LONG_NAME_1': [""] * n,
            'BA_TYPE_1': [""] * n,
            'REMARK': [""] * n,
            'SOURCE': [""] * n,
            'ROW_QUALITY': [row_quality] * n,
            'CHECKED_BY_BA_ID': [checked_by_ba_id] * n,
        })
    else:
        # Fallback default dataframe
        df = pd.DataFrame({
            'ORIGINAL_FILE_NAME': file_names,
            'DATA_STORE_NAME': path_of_file,
            'DIGITAL_FORMAT': exts,
            'DIGITAL_SIZE': sizes,
            'DIGITAL_SIZE_UOM': size_uoms,
            'DECRYPT_KEY': decrypt_keys,
            'DECRYPTION_TYPE': decryption_types,
        })

    _notify(95, "Menyimpan file Excel katalog...")
    excel_filename = f"{catalog_type}.xlsx"
    output_excel_path = save_dataframe_to_excel_safe(df, folder_path, excel_filename)

    _notify(100, "Catalog seismik berhasil dibuat!")

    return {
        "status": "success",
        "message": "Catalog seismik berhasil dibuat!",
        "catalog_type": catalog_type,
        "total_files": n,
        "output_path": output_excel_path,
        "columns": list(df.columns),
        "rows": sanitize_records_for_json(df),
    }


def generate_well_catalog(
    catalog_type: str,
    folder_path: str,
    params: Dict[str, Any],
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Generate Well catalog for standard PPDM 3.9 catalogs:
    - D.2.3 WELL_LOG_DIGITAL (filter .las)
    - D.3.2 WELL_REPORT_DIGITAL (reports, pdf/docx/etc.)
    """
    def _notify(percent: int, msg: str, file_name: str = "", current_index: int = 0, total_files: int = 0, stage: str = ""):
        if progress_callback:
            try:
                progress_callback({
                    "percent": percent,
                    "message": msg,
                    "current_file": file_name,
                    "current_index": current_index,
                    "total_files": total_files,
                    "stage": stage,
                })
            except TypeError:
                progress_callback(percent, msg)

    _notify(2, "Memindai folder file well...", stage="scan")
    full_name_path = list_files_with_paths_and_folders(folder_path)
    all_paths = full_name_path[0]
    all_names = full_name_path[1]
    all_dirs = full_name_path[2]

    # Filter files based on catalog type
    if catalog_type == "D.2.3 WELL_LOG_DIGITAL":
        indices = [i for i, f in enumerate(all_names) if is_las_file(f)]
    else:
        # For well report, include all non-temporary files
        indices = [i for i, f in enumerate(all_names) if not f.startswith("~$") and not f.startswith(".")]

    list_of_path = [all_paths[i] for i in indices]
    file_names = [all_names[i] for i in indices]
    path_of_file = [all_dirs[i] for i in indices]

    if not file_names:
        filter_msg = "file LAS (.las)" if catalog_type == "D.2.3 WELL_LOG_DIGITAL" else "file laporan"
        return {
            "status": "warning",
            "message": f"Tidak ada {filter_msg} ditemukan dalam folder yang dipilih.",
            "total_files": 0,
            "catalog_type": catalog_type,
            "output_path": None,
            "rows": []
        }

    ba_long_name = str(params.get("BA_LONG_NAME", "")).upper()
    ba_type = params.get("BA_TYPE", "BADAN USAHA")
    area_id = params.get("AREA_ID", "")
    area_type = params.get("AREA_TYPE", "WILAYAH KERJA")
    row_quality = params.get("ROW_QUALITY", "TERVERIFIKASI OLEH SKK MIGAS")
    checked_by_ba_id = params.get("CHECKED_BY_BA_ID", "")
    media_type = params.get("MEDIA_TYPE", "EKSTERNAL HARDISK")
    generate_md5 = bool(params.get("generate_md5", False))

    n = len(file_names)
    df = pd.DataFrame()

    is_log = catalog_type == "D.2.3 WELL_LOG_DIGITAL"

    _notify(10, f"Mengambil ekstensi untuk {n} file...", stage="ext")
    exts = get_file_extensions(list_of_path)

    # MD5 calculation
    decrypt_keys = ["" for _ in range(n)]
    decryption_types = ["" for _ in range(n)]
    if generate_md5:
        def _md5_progress(idx, total, fpath):
            fname = os.path.basename(fpath)
            if is_log:
                pct = 10 + int((idx / max(total, 1)) * 35)
            else:
                pct = 10 + int((idx / max(total, 1)) * 60)
            _notify(pct, f"Generate MD5 ({idx}/{total}): {fname}", file_name=fname, current_index=idx, total_files=total, stage="md5")

        decrypt_keys = get_md5_from_path(list_of_path, progress_callback=_md5_progress)
        decryption_types = ["MD5" for _ in range(n)]

    def _size_progress(idx, total, fpath):
        fname = os.path.basename(fpath)
        if is_log:
            pct = (45 if generate_md5 else 10) + int((idx / max(total, 1)) * (10 if generate_md5 else 20))
        else:
            pct = (70 if generate_md5 else 10) + int((idx / max(total, 1)) * (22 if generate_md5 else 82))
        _notify(pct, f"Membaca ukuran berkas ({idx}/{total}): {fname}", file_name=fname, current_index=idx, total_files=total, stage="sizes")

    sizes = get_file_sizes(list_of_path, progress_callback=_size_progress)
    size_uoms = ["byte" for _ in range(n)]

    if is_log:
        def _las_progress(idx, total, fpath):
            fname = os.path.basename(fpath)
            pct = (55 if generate_md5 else 30) + int((idx / max(total, 1)) * (38 if generate_md5 else 63))
            _notify(pct, f"Membaca Header LAS ({idx}/{total}): {fname}", file_name=fname, current_index=idx, total_files=total, stage="las_header")

        header = well_information_extraction(list_of_path, progress_callback=_las_progress)

        _notify(93, "Menyusun skema kolom D.2.3 WELL_LOG_DIGITAL...", stage="schema")
        df = pd.DataFrame({
            'BA_LONG_NAME': [ba_long_name] * n,
            'BA_TYPE': [ba_type] * n,
            'AREA_ID': [area_id] * n,
            'AREA_TYPE': [area_type] * n,
            'FIELD_NAME': header[1],
            'WELL_NAME': header[0],
            'UWI': [""] * n,
            'LOGGING_COMPANY': header[5],
            'MEDIA_TYPE': [media_type] * n,
            'WELL_LOG_CLASS_ID': [""] * n,
            'LOG_TITLE': header[7],
            'DIGITAL_FORMAT': exts,
            'REPORT_LOG_RUN': header[8],
            'TRIP_DATE': header[2],
            'TOP_DEPTH': header[3],
            'TOP_DEPTH_OUOM': header[6],
            'BASE_DEPTH': header[4],
            'BASE_DEPTH_OUOM': header[6],
            'ORIGINAL_FILE_NAME': file_names,
            'DECRYPT_KEY': decrypt_keys,
            'DECRYPTION_TYPE': decryption_types,
            'DIGITAL_SIZE': sizes,
            'DIGITAL_SIZE_UOM': size_uoms,
            'BA_LONG_NAME_1': [""] * n,
            'BA_TYPE_1': [""] * n,
            'DATA_STORE_NAME': path_of_file,
            'REMARK': [""] * n,
            'SOURCE': [""] * n,
            'ROW_QUALITY': [row_quality] * n,
            'CHECKED_BY_BA_ID': [checked_by_ba_id] * n,
        })
    else:  # D.3.2 WELL_REPORT_DIGITAL
        _notify(92, "Menyusun skema kolom D.3.2 WELL_REPORT_DIGITAL...")
        df = pd.DataFrame({
            'BA_LONG_NAME': [ba_long_name] * n,
            'BA_TYPE': [ba_type] * n,
            'AREA_ID': [area_id] * n,
            'AREA_TYPE': [area_type] * n,
            'FIELD_NAME': [""] * n,
            'WELL_NAME': [""] * n,
            'UWI': [""] * n,
            'REPORT_TYPE': [""] * n,
            'START_DATE': [""] * n,
            'COMPLETION_DATE': [""] * n,
            'MEDIA_TYPE': [media_type] * n,
            'ORIGINAL_FILE_NAME': file_names,
            'DIGITAL_FORMAT': exts,
            'DECRYPT_KEY': decrypt_keys,
            'DECRYPTION_TYPE': decryption_types,
            'DIGITAL_SIZE': sizes,
            'DIGITAL_SIZE_UOM': size_uoms,
            'BA_LONG_NAME_1': [""] * n,
            'BA_TYPE_1': [""] * n,
            'DATA_STORE_NAME': path_of_file,
            'REMARK': [""] * n,
            'SOURCE': [""] * n,
            'ROW_QUALITY': [row_quality] * n,
            'CHECKED_BY_BA_ID': [checked_by_ba_id] * n,
        })

    _notify(95, "Menyimpan file Excel katalog...")
    excel_filename = f"{catalog_type}.xlsx"
    output_excel_path = save_dataframe_to_excel_safe(df, folder_path, excel_filename)

    _notify(100, "Catalog well berhasil dibuat!")

    return {
        "status": "success",
        "message": "Catalog well berhasil dibuat!",
        "catalog_type": catalog_type,
        "total_files": n,
        "output_path": output_excel_path,
        "columns": list(df.columns),
        "rows": sanitize_records_for_json(df),
    }
