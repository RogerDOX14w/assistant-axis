"""Open English WordNet access through the ``wn`` package, pinned in-tree.

The ``wn`` library stores its SQLite database and downloads under
``~/.wn_data`` by default.  This module sets both ``$WN_DATA_DIR`` (read by
``wn`` when it is first imported) and ``wn.config.data_directory`` to
``data/external/wn/`` **at import time, before any lookup or download**, so
nothing is ever read from or written to the home directory.  Import ``wn``
through this module (or after it) in every platform file.

Functions:

* :func:`ensure_oewn` downloads OEWN 2024 into the in-tree directory if the
  lexicon is not there yet (about 100 MB; idempotent).
* :func:`oewn` returns the ``wn.Wordnet`` handle for the configured lexicon
  (interface resolution 3 of the platform plan).
* :func:`sense_info` gives the local polysemy prior used by the filter.
* :func:`adjective_lemmas` lists adjective lemmas for the random-adjective
  validation stratum.
"""
from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from .paths import wn_data_dir

logger = logging.getLogger(__name__)

WN_DATA_DIR = wn_data_dir()
OEWN_LEXICON = "oewn:2024"
ADJ_POS = ("a", "s")  # adjective and adjective satellite

# Pin the data directory before ``wn`` is imported anywhere through us.
os.environ["WN_DATA_DIR"] = str(WN_DATA_DIR)

try:  # pragma: no cover - exercised whenever wn is installed
    import wn as _wn

    _wn.config.data_directory = WN_DATA_DIR
except ImportError:  # pragma: no cover
    _wn = None


@dataclass(frozen=True)
class WordNetInfo:
    """Local sense evidence for a surface form.

    ``n_senses`` counts adjective senses (``a`` + ``s``) when the word has
    any, else senses of every part of speech; ``n_senses_all`` always counts
    every part of speech.  ``pos`` lists the parts of speech found, sorted.
    """
    n_senses: int = 0
    pos: list[str] = field(default_factory=list)
    found: bool = False
    n_senses_all: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def _module(wn_module=None):
    mod = wn_module if wn_module is not None else _wn
    if mod is None:
        raise ImportError("the 'wn' package is not installed (uv sync)")
    return mod


def oewn_installed(wn_module=None) -> bool:
    """True when the OEWN 2024 lexicon is in the in-tree database.

    Never touches the network.  With the real module this also creates
    ``data/external/wn/`` (the database lives there)."""
    mod = _module(wn_module)
    if wn_module is None:
        WN_DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        return bool(mod.lexicons(lexicon=OEWN_LEXICON))
    except Exception:  # noqa: BLE001 - an empty or missing database
        return False


def ensure_oewn(*, wn_module=None, download: bool = True) -> bool:
    """Make OEWN 2024 available in ``data/external/wn/``.

    Returns True if the lexicon is (now) installed.  With ``download=False``
    only reports.  The download goes through ``wn.download`` with the data
    directory already pinned in-tree.
    """
    mod = _module(wn_module)
    if oewn_installed(mod if wn_module is not None else None):
        return True
    if not download:
        return False
    if wn_module is None:
        WN_DATA_DIR.mkdir(parents=True, exist_ok=True)
        assert _wn.config.database_path.parent == WN_DATA_DIR, "wn data directory is not in-tree"
    logger.info("downloading %s into %s", OEWN_LEXICON, WN_DATA_DIR)
    mod.download(OEWN_LEXICON)
    return oewn_installed(mod if wn_module is not None else None)


_HANDLE: dict[int, Any] = {}


def oewn(*, wn_module=None):
    """The ``wn.Wordnet`` handle for OEWN 2024 (cached per module)."""
    mod = _module(wn_module)
    key = id(mod)
    if wn_module is None:
        # wn creates its data directory without parents; on a checkout with no
        # data/external/ that is a bare FileNotFoundError (review_m1.md finding 6)
        WN_DATA_DIR.mkdir(parents=True, exist_ok=True)
        _wn.config.data_directory = WN_DATA_DIR
    if key not in _HANDLE:
        _HANDLE[key] = mod.Wordnet(OEWN_LEXICON)
    return _HANDLE[key]


def _lookup_forms(surface: str) -> list[str]:
    s = " ".join(surface.strip().split())
    forms = [s, s.lower()]
    if "-" in s:
        forms.append(s.lower().replace("-", " "))
    if " " in s:
        forms.append(s.lower().replace(" ", "-"))
    seen, out = set(), []
    for f in forms:
        if f and f not in seen:
            seen.add(f)
            out.append(f)
    return out


def sense_info(surface: str, *, wn_module=None, wordnet=None) -> WordNetInfo:
    """Sense count and parts of speech of ``surface`` in OEWN.

    ``wordnet`` may be any object with a ``synsets(form)`` method (the real
    ``wn.Wordnet`` or a fake); by default the OEWN handle.  The first form
    variant that yields synsets wins (as given, lowercase, hyphen <-> space).
    """
    wnet = wordnet if wordnet is not None else oewn(wn_module=wn_module)
    for form in _lookup_forms(surface):
        syns = list(wnet.synsets(form))
        if not syns:
            continue
        pos = sorted({s.pos for s in syns})
        n_adj = sum(1 for s in syns if s.pos in ADJ_POS)
        return WordNetInfo(n_senses=n_adj if n_adj else len(syns), pos=pos, found=True,
                           n_senses_all=len(syns))
    return WordNetInfo()


def adjective_lemmas(*, wn_module=None, wordnet=None) -> list[str]:
    """Every distinct adjective lemma (``a`` and ``s``) in OEWN, sorted,
    lowercase-deduplicated (the first spelling in sorted order is kept)."""
    wnet = wordnet if wordnet is not None else oewn(wn_module=wn_module)
    seen: dict[str, str] = {}
    for pos in ADJ_POS:
        for w in wnet.words(pos=pos):
            lemma = w.lemma()
            seen.setdefault(lemma.lower(), lemma)
    return sorted(seen.values(), key=str.lower)
