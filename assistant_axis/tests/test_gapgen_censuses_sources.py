"""Census generator, source configuration."""
from pathlib import PurePosixPath

from assistant_axis.gapgen.generators.censuses import sources as S


def test_every_source_is_complete():
    for k, s in S.SOURCES.items():
        assert s.key == k and s.url.startswith("https://")
        d = PurePosixPath(s.dest)
        assert not d.is_absolute() and ".." not in d.parts and len(d.parts) == 2
        assert d.parts[0] in (S.OSF_DIR, S.TDA_DIR)
        assert s.licence in ("CC BY 4.0", "CC0 1.0") and s.licence_url.startswith("http")
        assert s.sha256 or s.md5
        if s.provider == "osf":
            assert len(s.sha256) == 64 and len(s.md5) == 32
        if s.filename.endswith(".pdf"):
            assert s.size_bytes <= 100_000


def test_columns_and_defaults():
    assert S.ALLPORT_COLUMN_SOURCES == {"I": "allport_I", "II": "allport_II", "III": "allport_III", "IV": "allport_IV"}
    assert set(S.DEFAULT_FETCH) == {"allport_I", "allport_II", "allport_III", "allport_IV", "allport_merged",
                                    "tda_properties", "tda_codebook"}
    assert S.SOURCES["tda_properties"].alt_url and "format=original" in S.SOURCES["tda_properties"].url


def test_skipped_names_the_big_files():
    assert "Allport and Odbert 1936.pdf" in S.SKIPPED and "TDA_data_scored.tab" in S.SKIPPED


def test_generators_package_docstring_exact():
    from pathlib import Path

    import assistant_axis.gapgen.generators as G
    assert Path(G.__file__).read_bytes() == b'"""Generator workstreams, one subpackage each."""\n'
