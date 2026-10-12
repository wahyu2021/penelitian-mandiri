"""Parser dump SQL MySQL untuk e-Arsip (SIMANIS).

Hanya membaca tabel yang diizinkan (ALLOWED_TABLES). Tabel lain, termasuk
`apptb_user`, `apptb_log`, dan `apptb_arsip1`, tidak pernah dibaca.
"""
import hashlib
import re
from typing import Dict, List, Optional, Tuple

ALLOWED_TABLES = frozenset({"apptb_arsip", "apptb_opd", "apptb_klasifikasi"})

_INSERT_HEADER = re.compile(
    r"INSERT\s+INTO\s+`(?P<table>[A-Za-z0-9_]+)`\s*\((?P<columns>[^)]*)\)\s*VALUES",
    re.IGNORECASE,
)
_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "0": "\0", "Z": "\x1a"}

Row = Dict[str, Optional[str]]


def sha256_of_file(path: str, chunk_size: int = 65536) -> str:
    """Hitung SHA-256 berkas untuk pencatatan keterulangan.

    Args:
        path: Lokasi berkas.
        chunk_size: Ukuran blok baca dalam byte.

    Returns:
        Digest heksadesimal.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_quoted(text: str, pos: int) -> Tuple[str, int]:
    """Baca string berkutip tunggal; `pos` menunjuk karakter setelah kutip pembuka."""
    buffer: List[str] = []
    length = len(text)
    while pos < length:
        char = text[pos]
        if char == "\\" and pos + 1 < length:
            nxt = text[pos + 1]
            buffer.append(_ESCAPES.get(nxt, nxt))
            pos += 2
        elif char == "'":
            if pos + 1 < length and text[pos + 1] == "'":
                buffer.append("'")
                pos += 2
            else:
                return "".join(buffer), pos + 1
        else:
            buffer.append(char)
            pos += 1
    raise ValueError("String SQL tidak ditutup")


def _skip_statement(text: str, pos: int) -> int:
    """Lewati teks SQL hingga tanda titik koma (;) di luar kutip tunggal."""
    length = len(text)
    while pos < length:
        char = text[pos]
        if char == ";":
            return pos + 1
        if char == "'":
            _, pos = _read_quoted(text, pos + 1)
        else:
            pos += 1
    return pos


def _parse_tuples(text: str, pos: int) -> Tuple[List[List[Optional[str]]], int]:
    """Parse deret tuple `(..),(..)` sampai `;` di luar kutip.

    Returns:
        Daftar baris dan posisi setelah titik koma penutup.
    """
    rows: List[List[Optional[str]]] = []
    length = len(text)
    while pos < length:
        char = text[pos]
        if char == ";":
            return rows, pos + 1
        if char != "(":
            pos += 1
            continue
        pos += 1
        row: List[Optional[str]] = []
        while pos < length:
            while pos < length and text[pos] in " \t\r\n":
                pos += 1
            if pos >= length:
                raise ValueError("Dump SQL terpotong di dalam baris data")
            if text[pos] == "'":
                value, pos = _read_quoted(text, pos + 1)
                row.append(value)
            else:
                start = pos
                while pos < length and text[pos] not in ",)":
                    pos += 1
                token = text[start:pos].strip()
                row.append(None if token.upper() == "NULL" else token)
            while pos < length and text[pos] in " \t\r\n":
                pos += 1
            if pos >= length:
                raise ValueError("Dump SQL terpotong di dalam baris data")
            if text[pos] == ",":
                pos += 1
                continue
            if text[pos] == ")":
                pos += 1
                break
            raise ValueError(f"Karakter tak terduga di posisi {pos}")
        rows.append(row)
    return rows, pos


def parse_sql_text(text: str) -> Dict[str, List[Row]]:
    """Ekstrak baris INSERT dari tabel yang diizinkan.

    Args:
        text: Isi dump SQL.

    Returns:
        Kamus nama tabel -> daftar baris (dict kolom -> nilai).

    Raises:
        ValueError: jumlah kolom pada baris tidak sama dengan header.
    """
    tables: Dict[str, List[Row]] = {name: [] for name in ALLOWED_TABLES}
    pos = 0
    while True:
        match = _INSERT_HEADER.search(text, pos)
        if match is None:
            break
        table = match.group("table")
        if table not in ALLOWED_TABLES:
            # Lewati seluruh statement tanpa mem-parse isinya.
            pos = _skip_statement(text, match.end())
            continue
        columns = [c.strip("` \r\n") for c in match.group("columns").split(",")]
        raw_rows, pos = _parse_tuples(text, match.end())
        for raw in raw_rows:
            if len(raw) != len(columns):
                raise ValueError(
                    f"Tabel {table}: {len(raw)} nilai untuk {len(columns)} kolom"
                )
            tables[table].append(dict(zip(columns, raw)))
    return tables


def parse_sql_dump(path: str, encoding: str = "latin-1") -> Dict[str, object]:
    """Baca berkas dump dan kembalikan data tabel yang diizinkan beserta hash.

    Args:
        path: Lokasi berkas .sql.
        encoding: Encoding berkas (dump MySQL lama memakai latin1).

    Returns:
        Kamus berisi `sha256`, `arsip`, `opd`, `klasifikasi`.
    """
    with open(path, "r", encoding=encoding, newline="") as handle:
        text = handle.read().replace("\r\n", "\n")
    tables = parse_sql_text(text)
    return {
        "sha256": sha256_of_file(path),
        "arsip": tables["apptb_arsip"],
        "opd": tables["apptb_opd"],
        "klasifikasi": tables["apptb_klasifikasi"],
    }
