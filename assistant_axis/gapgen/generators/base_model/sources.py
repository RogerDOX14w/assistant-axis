"""What the base-model generator downloads, with sizes, hashes and licences (plan section 5a).

Roger approved the first three downloads on 2026-10-10 (plan section 5a): the model, ``wiki_bio`` and the
O*NET occupation titles.  The optional instruct model (``Qwen/Qwen3-8B``, the collapse control of plan 03
section 6) is **not** approved and has no entry here: it needs a fresh ask.

Checked against the providers on 2026-10-10:

* ``wiki_bio`` now redirects to ``michaelauli/wiki_bio`` on the Hugging Face Hub, which holds a loading
  script and one archive, ``data/wikipedia-biography-dataset.zip`` (333,998,704 bytes; the LFS sha256 below
  from the Hub's ``paths-info`` API), and **no parquet** (the dataset viewer refuses script datasets).  The
  plan assumed parquet shards; the archive is fetched with ``hf_hub_download`` at a pinned revision and read
  with :mod:`zipfile`, so the ``datasets`` package is still not needed and the loading script never runs.
  Licence CC BY-SA 3.0 (the dataset card's ``license`` field).
* O*NET 31.0 (``onetcenter.org/database.html``): the occupation titles file is ``occupation_data.csv``,
  268,030 bytes.  The licence is **CC BY 4.0** with a required attribution (``onetcenter.org/license_db.html``),
  not public domain as plan 03 had it.
* ``Qwen/Qwen3-8B-Base``: Apache-2.0 (model card), not gated, revision ``49e3418f``, 16,393,044,987 bytes in
  all (five safetensors shards).  Fetched by ``setup_external.py --hf-model`` with the allow patterns below.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class Source:
    key: str
    dest: str                       # relative to data/external/
    size_bytes: int
    licence: str
    licence_url: str
    citation: str
    attribution: str
    url: Optional[str] = None       # a plain HTTPS file
    repo_id: Optional[str] = None   # a Hugging Face dataset repository
    filename: Optional[str] = None  # the file inside it
    revision: Optional[str] = None  # pinned commit
    sha256: Optional[str] = None    # published sha256 (the Hub's LFS oid); None when the provider publishes none
    version: Optional[str] = None
    note: Optional[str] = None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ModelSource:
    model_id: str
    revision: str
    size_bytes: int
    licence: str
    licence_url: str
    todo: str


WIKIBIO_REVISION = "3a00c01f03c79c4799a4b884bd9508a1eea47b6a"

SOURCES: dict[str, Source] = {s.key: s for s in (
    Source(
        key="wikibio", dest="wikibio/data/wikipedia-biography-dataset.zip", size_bytes=333_998_704,
        licence="CC BY-SA 3.0", licence_url="https://creativecommons.org/licenses/by-sa/3.0/",
        citation=("Lebret, Grangier & Auli (2016), Neural Text Generation from Structured Data with Application to "
                  "the Biography Domain, EMNLP; arXiv:1603.07771"),
        attribution="WikiBio (Lebret, Grangier & Auli 2016), from English Wikipedia biographies, CC BY-SA 3.0",
        repo_id="michaelauli/wiki_bio", filename="data/wikipedia-biography-dataset.zip",
        revision=WIKIBIO_REVISION,
        sha256="0de0fef4cc6c9182138939134b81b6ac33ffbc989b6d23a2d9ef1e50c49b8032", version="1.0",
        note="seeds are prompts only, never redistributed (Roger, plan 03 section 9.1)"),
    Source(
        key="onet", dest="onet/occupation_data.csv", size_bytes=268_030,
        licence="CC BY 4.0", licence_url="https://creativecommons.org/licenses/by/4.0/",
        citation="O*NET 31.0 Database, U.S. Department of Labor, Employment and Training Administration",
        attribution=("This work uses information from the O*NET 31.0 Database by the U.S. Department of Labor, "
                     "Employment and Training Administration (USDOL/ETA). Used under the CC BY 4.0 license. "
                     "O*NET(R) is a trademark of USDOL/ETA."),
        url="https://www.onetcenter.org/dl_files/database/db_31_0_csv/occupation_data.csv", version="31.0",
        note="licence verified 2026-10-10 at https://www.onetcenter.org/license_db.html (plan 03 said public domain)"),
)}

#: Fetched by ``fetch`` with no ``--only``.
DEFAULT_FETCH = ("wikibio", "onet")

#: The licence pages read at fetch time to confirm the licence (the text must name it).
LICENCE_CHECK = {
    "wikibio": ("https://huggingface.co/api/datasets/michaelauli/wiki_bio", "cc-by-sa-3.0"),
    "onet": ("https://www.onetcenter.org/license_db.html", "CC BY 4.0"),
}

MODEL = ModelSource(
    model_id="Qwen/Qwen3-8B-Base", revision="49e3418fbbbca6ecbdf9608b4d22e5a407081db4", size_bytes=16_393_044_987,
    licence="Apache-2.0", licence_url="https://huggingface.co/Qwen/Qwen3-8B-Base",
    todo=("TODO once the workstream is done: ask Roger whether to delete the weights (his rule, 2026-10-10: "
          "anything over 2 GB gets this note)"))

#: What ``setup_external.py --hf-model`` fetches for the generator's model (merged with the M2 embedders'
#: ``gapgen.embed.HF_ALLOW_PATTERNS``, which stays theirs alone).
HF_MODEL_ALLOW_PATTERNS: dict[str, list[str]] = {
    MODEL.model_id: ["config.json", "generation_config.json", "model.safetensors.index.json", "*.safetensors",
                     "tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt", "README.md"],
}

#: Considered and not fetched, on purpose.
SKIPPED: dict[str, str] = {
    "PersonaHub": "200k personas generated by GPT-4 / Llama (CC BY-NC-SA): already mode-collapsed, the opposite "
                  "of a seed source for a diversity generator",
    "SUBTLEX-US": "wordfreq's Zipf (gapgen.freq) covers word frequency; the platform's floor supersedes plan 03's "
                  "SUBTLEX threshold",
    "Condon et al. TDA (Dataverse)": "not re-downloaded: seed list A is the TDA rows of the tracked census table "
                                     "(the censuses generator's frozen interface)",
    "Qwen/Qwen3-8B (instruct)": "the optional collapse control: not approved, needs a fresh ask (plan section 5a)",
}
