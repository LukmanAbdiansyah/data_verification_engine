import pytest
import os
import tempfile
import struct
from app.services.segy_parser import EBCDIC_TO_ASCII_TABLE

@pytest.fixture
def test_dir():
    with tempfile.TemporaryDirectory() as td:
        yield td

@pytest.fixture
def valid_ascii_segy(test_dir):
    path = os.path.join(test_dir, 'valid_ascii.sgy')
    header = b'C01 PRE-STACK TIME MIGRATION'
    header = header.ljust(3200, b' ')
    binary = struct.pack('>iiihhh', 1, 1, 1, 1, 1, 2000)
    binary = binary.ljust(400, b'\x00')
    with open(path, 'wb') as f:
        f.write(header)
        f.write(binary)
    return path

@pytest.fixture
def valid_ebcdic_segy(test_dir):
    path = os.path.join(test_dir, 'valid_ebcdic.sgy')
    ascii_to_ebcdic = {v: k for k, v in EBCDIC_TO_ASCII_TABLE.items()}
    text = 'C01 PRE-STACK TIME MIGRATION'.ljust(3200, ' ')
    header = bytes(ascii_to_ebcdic.get(ord(c), 0x40) for c in text)
    binary = struct.pack('>iiihhh', 1, 1, 1, 1, 1, 2000)
    binary = binary.ljust(400, b'\x00')
    with open(path, 'wb') as f:
        f.write(header)
        f.write(binary)
    return path

@pytest.fixture
def empty_header_segy(test_dir):
    path = os.path.join(test_dir, 'empty_header.sgy')
    header = b' ' * 3200
    binary = struct.pack('>iiihhh', 1, 1, 1, 1, 1, 2000)
    binary = binary.ljust(400, b'\x00')
    with open(path, 'wb') as f:
        f.write(header)
        f.write(binary)
    return path

@pytest.fixture
def corrupted_segy(test_dir):
    path = os.path.join(test_dir, 'corrupted.sgy')
    with open(path, 'wb') as f:
        f.write(b'Just a short file')
    return path
