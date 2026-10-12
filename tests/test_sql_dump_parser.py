import pytest

from core.sql_dump_parser import parse_sql_text, sha256_of_file

SAMPLE = """
INSERT INTO `apptb_opd` (`id_opd`, `nama_opd`) VALUES
(15, 'Sekretaris Daerah'),
(18, 'Dinas Pendidikan ');

INSERT INTO `apptb_user` (`id_user`, `password`) VALUES
(1, 'rahasia');

INSERT INTO `apptb_arsip1` (`id_arsip`, `ringkasan`) VALUES
(1, 'tabel uji');

INSERT INTO `apptb_arsip` (`id_arsip`, `ringkasan`, `dokumen`) VALUES
(1, 'Bayar; termin ke I\\nNo. SPM:1/LS/5', NULL),
(2, 'Toko ''Maju'', koma, (kurung)', '');
"""


def test_only_allowed_tables_are_read():
    tables = parse_sql_text(SAMPLE)
    assert set(tables) == {"apptb_arsip", "apptb_opd", "apptb_klasifikasi"}
    assert len(tables["apptb_opd"]) == 2
    assert len(tables["apptb_arsip"]) == 2


def test_user_and_test_table_content_never_returned():
    tables = parse_sql_text(SAMPLE)
    flat = str(tables)
    assert "rahasia" not in flat
    assert "tabel uji" not in flat


def test_semicolon_inside_string_does_not_end_statement():
    row = parse_sql_text(SAMPLE)["apptb_arsip"][0]
    assert row["ringkasan"] == "Bayar; termin ke I\nNo. SPM:1/LS/5"


def test_null_and_escaped_quotes():
    rows = parse_sql_text(SAMPLE)["apptb_arsip"]
    assert rows[0]["dokumen"] is None
    assert rows[1]["ringkasan"] == "Toko 'Maju', koma, (kurung)"
    assert rows[1]["dokumen"] == ""


def test_column_count_mismatch_raises():
    broken = "INSERT INTO `apptb_opd` (`id_opd`, `nama_opd`) VALUES\n(1);"
    with pytest.raises(ValueError):
        parse_sql_text(broken)


def test_sha256_is_stable(tmp_path):
    path = tmp_path / "a.sql"
    path.write_bytes(b"abc")
    assert sha256_of_file(str(path)) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_truncated_sql_raises_value_error():
    truncated1 = "INSERT INTO `apptb_opd` (`id_opd`, `nama_opd`) VALUES (1, 'Sekret"
    with pytest.raises(ValueError):
        parse_sql_text(truncated1)

    truncated2 = "INSERT INTO `apptb_opd` (`id_opd`, `nama_opd`) VALUES (1, 'Sekret' "
    with pytest.raises(ValueError):
        parse_sql_text(truncated2)


def test_skip_non_allowed_tables_ignores_internal_syntax():
    sample = (
        "INSERT INTO `apptb_user` (`id_user`, `data`) VALUES (1, 'teks ; dengan titik koma');\n"
        "INSERT INTO `apptb_opd` (`id_opd`, `nama_opd`) VALUES (10, 'Dinas Tata Kota');\n"
    )
    tables = parse_sql_text(sample)
    assert len(tables["apptb_opd"]) == 1
    assert tables["apptb_opd"][0]["nama_opd"] == "Dinas Tata Kota"
