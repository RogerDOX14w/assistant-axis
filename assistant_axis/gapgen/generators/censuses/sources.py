"""The census files this generator downloads, with their published hashes and licences.

Hashes were copied from the OSF API (``api.osf.io/v2/nodes/k6rwj/files/osfstorage/``,
``extra.hashes``: sha256 and md5) and the Dataverse API
(``dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/5T80PF``,
one md5 per file) on 2026-09-23 and re-checked against both APIs on 2026-10-08 (unchanged).
Dataverse's md5 for an ingested tabular file is the md5 of the *original* upload (the CSV
served by ``?format=original``), checked 2026-10-08; :mod:`download` still tries the ``.tab``
form when the original does not match, and records which one did (``checksum_source``).

Attribution for the OSF files is read from the OSF API at download time
(:func:`download.osf_node_attribution`), never typed here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

OSF_NODE = "k6rwj"
OSF_NODE_URL = f"https://osf.io/{OSF_NODE}/"
OSF_NODE_API = f"https://api.osf.io/v2/nodes/{OSF_NODE}/"
OSF_DOI = "10.17605/OSF.IO/K6RWJ"
OSF_DIR = "allport_odbert_osf_k6rwj"

TDA_DOI = "10.7910/DVN/5T80PF"
TDA_DIR = "tda_dataverse_5T80PF"

CC_BY_4 = ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/")
CC0_1 = ("CC0 1.0", "http://creativecommons.org/publicdomain/zero/1.0")

#: Where the full licence texts are fetched from for the ``LICENSE.txt`` beside each source
#: directory (the OSF API serves the CC BY 4.0 text with the node's licence record).
LICENCE_TEXT_URLS = {
    "CC BY 4.0": "https://api.osf.io/v2/licenses/563c1cf88c5e4a3877f9e96a/",
    "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt",
}

#: Allport-Odbert columns (1936): I personal traits, II temporary states and activities,
#: III social evaluations, IV metaphorical, doubtful and miscellaneous terms.
ALLPORT_COLUMNS = ("I", "II", "III", "IV")


@dataclass(frozen=True)
class Source:
    key: str
    filename: str
    url: str
    dest: str                      # relative to the wordlists directory
    size_bytes: int
    licence: str
    licence_url: str
    citation: str
    alt_url: Optional[str] = None  # Dataverse: the ingested .tab form
    sha256: Optional[str] = None
    md5: Optional[str] = None
    doi: Optional[str] = None
    version: Optional[int] = None
    column: Optional[str] = None   # Allport-Odbert column, None for merged and TDA files
    optional: bool = False
    provider: str = "osf"          # osf | dataverse

    def as_dict(self) -> dict:
        return asdict(self)


_OSF_CITATION = "OSF node k6rwj (title and contributors read from the API at download time)"
_TDA_CITATION = "Dataverse dataset doi:10.7910/DVN/5T80PF, V4 (citation read from the API at download time)"
TDA_CITATION_API = ("https://dataverse.harvard.edu/api/datasets/:persistentId/versions/:latest/citation"
                    "?persistentId=doi:10.7910/DVN/5T80PF")


def _osf(key, filename, file_id, size, sha256, md5, column):
    return Source(key=key, filename=filename, url=f"https://osf.io/download/{file_id}/",
                  dest=f"{OSF_DIR}/{filename}", size_bytes=size, sha256=sha256, md5=md5,
                  licence=CC_BY_4[0], licence_url=CC_BY_4[1], citation=_OSF_CITATION, doi=OSF_DOI,
                  column=column, provider="osf")


def _dataverse(key, filename, file_id, size, md5, *, original: bool, optional: bool):
    base = f"https://dataverse.harvard.edu/api/access/datafile/{file_id}"
    return Source(key=key, filename=filename, url=f"{base}?format=original" if original else base,
                  alt_url=base if original else None, dest=f"{TDA_DIR}/{filename}", size_bytes=size,
                  md5=md5, licence=CC0_1[0], licence_url=CC0_1[1], citation=_TDA_CITATION, doi=TDA_DOI,
                  version=4, optional=optional, provider="dataverse")


SOURCES: dict[str, Source] = {s.key: s for s in (
    _osf("allport_I", "Personal Traits.txt", "fdg4j", 50975,
         "50f931baa3680af2111c1d5d94dc744398d72a16779a5a60a9cf711a948c6ca4", "2eab18841cb35fab5713acc044f72095", "I"),
    _osf("allport_II", "Temporary States.txt", "cg3rz", 49932,
         "8b8c8ae39ecb89749828a8abc9ab5a68de6af67a883ecb1eb6b636b39c24511c", "302812b0dee7be3dfc201544ce105fbc", "II"),
    _osf("allport_III", "Social Evaluations.txt", "6ptxv", 56516,
         "7f66d61d2647f62e4317e722b628f4d532af37cec9bcc9cab77d6e0054027262", "48cf379d22808df496f1a485ea85d562", "III"),
    _osf("allport_IV", "Metaphorical Doubtful.txt", "sjknr", 39732,
         "28c6466bf56ec40ba8a3acebfbf070833c334a8383720b1a9e134ceb3185163e", "1d3e4d6d5ff6787421d86887866437bf", "IV"),
    _osf("allport_merged", "Allport-Traits.txt", "5qwk9", 179338,
         "54c348856bc575462b8d41113a66e58c8ca0340af0759bebf3ed0241545dbcd9", "403e3b6d3ffd92c3c7447106e6edcd14", None),
    # size_bytes is the original CSV's (Dataverse lists the ingested .tab's: 87,240 and 64,753 bytes)
    _dataverse("tda_properties", "TDA_properties.csv", 5255447, 83504, "e858ae14f1d56211690562159c4f0f3d",
               original=True, optional=False),
    _dataverse("tda_codebook", "Data Description.pdf", 5343069, 56187, "011924ea56c5003285cf1be2967c1639",
               original=False, optional=True),
    _dataverse("tda_frequencies", "TDA_frequencies.csv", 5255448, 63832, "5fb68ab2843f0e663b321823eb15098a",
               original=True, optional=True),
)}

#: Fetched by ``download`` with no ``--only``: every non-optional source plus the codebook;
#: ``tda_frequencies`` only when the properties header lacks ``gbooks.freq``.
DEFAULT_FETCH = tuple(k for k, s in SOURCES.items() if not s.optional) + ("tda_codebook",)

#: Files on the two pages deliberately not fetched.
SKIPPED: dict[str, str] = {
    "Allport and Odbert 1936.pdf": "6.2 MB monograph scan on OSF; the four column lists are its transcription",
    "TDA_data_scored.tab": "20 MB of raw ratings; the properties file carries the per-word summaries",
    "item_difficulty.tab": "psychometric item parameters, not needed",
    "masterkey.tab": "scale keys, not needed",
}

#: Allport-Odbert column files by column.
ALLPORT_COLUMN_SOURCES: dict[str, str] = {s.column: k for k, s in SOURCES.items() if s.column}
