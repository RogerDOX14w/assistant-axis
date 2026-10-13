"""What the alignment sweep reads: each source's URL, licence, version pin, weight and how it may be used.

Licences (coding_plan_08_alignment_sweep.md § 5; checked 2026-10-10):

* the OpenAI Model Spec: github.com/openai/model_spec, **CC0 1.0 Universal** (the repository's LICENSE); fetched
  at the commit of the 2026-08-18 release, so the version pin is the commit;
* Anthropic's constitution: anthropic.com/constitution, **CC0 1.0** ("We're releasing Claude's constitution in full
  under a Creative Commons CC0 1.0 Deed", on the page); the preface (everything before "Overview") and the
  acknowledgements are not part of the constitution and are dropped; no version is printed, so the pin is the
  capture date and the sha256 of what was fetched;
* the two usage policies: proprietary; ``read_only`` (quotes of 25 words or fewer);
* the failure-mode papers of plan 08 § 2, from their arXiv pages' licence links read 2026-10-10: CC BY 4.0 for the
  sandbagging, ELEPHANT and agentic-misalignment papers; the arXiv non-exclusive distribution licence for the
  sabotage-evaluations, alignment-faking, in-context-scheming and emergent-misalignment papers, so those are
  ``read_only``;
* variant B: the Krakovna specification-gaming list (**no licence stated**; ``read_only``, ``optional`` and never
  stored: :data:`Source.store` is false) and the MACHIAVELLI repository (**MIT, Copyright (c) 2022 Alex Pan**;
  ``optional``).

Weights (plan 08 step 7): the constitution and the Model Spec 2, taxonomies and policies 1, glossaries 0.5.

:data:`DEFAULT_FETCH` is what ``alignment_sweep.py fetch`` downloads without ``--only``: the two sources whose
fetch Roger approved with the plan (2026-10-10) and the only two the pilot reads.  The rest are fetched with
``--only KEY`` when the full extraction (Roger's decision after the pilot) needs them.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

KINDS = ("spec", "constitution", "policy", "taxonomy", "glossary", "incidents", "schema")
#: How a fetched text is read: a markdown file (headings), an HTML page (its headings, through
#: :func:`.chunk.html_to_markdown`), a published Google sheet read through its TSV export (rows, from the header
#: line on), or a markdown or tab-separated table (rows).
FORMATS = ("markdown", "html", "sheet_tsv", "table")
#: Quotes from a ``read_only`` source are cut at this many words (Roger's rule for unlicensed text).
READ_ONLY_QUOTE_WORDS = 25

MODEL_SPEC_COMMIT = "7f1cf79fcb656c07f77c8d95b6fbc78dc7fac5b6"
_MS_RAW = f"https://raw.githubusercontent.com/openai/model_spec/{MODEL_SPEC_COMMIT}"
CHECKED = "2026-10-10"


@dataclass(frozen=True)
class Source:
    key: str                       # also the prefix of chunk ids and source_refs
    name: str
    url: str                       # what is fetched
    kind: str
    fmt: str
    license: Optional[str]         # None: no licence (read_only)
    license_url: Optional[str]
    license_line: str              # the licence statement, verbatim from the source (or what was found)
    license_verified_at: str       # the date the licence status was read (YYYY-MM-DD)
    read_only: bool                # no usable licence: quotes of 25 words or fewer
    weight: float                  # plan 08 step 7: 2, 1 or 0.5
    variant: str                   # "A" or "B"
    short: str                     # item-id prefix (``ms041-1a``)
    optional: bool = False
    store: bool = True             # False: read transiently, never written to disk (Krakovna)
    page_url: Optional[str] = None
    version_label: Optional[str] = None   # in chunk ids; None: the capture date, set at fetch time
    version_pin: Optional[str] = None     # None: set at fetch time (capture date and sha256)
    commit: Optional[str] = None
    license_file_url: Optional[str] = None
    drop_before: Optional[str] = None     # heading title: everything before it is dropped (a preface)
    drop_sections: tuple = ()             # heading titles whose sections are dropped
    table_header: Optional[str] = None    # a table's header line has this first cell; lines above it are dropped
    filename: Optional[str] = None
    citation: Optional[str] = None
    notes: Optional[str] = None
    tags: tuple = field(default_factory=tuple)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["drop_sections"] = list(self.drop_sections)
        d["tags"] = list(self.tags)
        return d

    @property
    def dest_name(self) -> str:
        """File name under ``data/external/alignment_sweep/``."""
        if self.filename:
            return self.filename
        ext = {"markdown": "md", "html": "html", "sheet_tsv": "tsv", "table": "tsv"}[self.fmt]
        return f"{self.key}.{ext}"


def _arxiv(key, short, arxiv_id, version, name, *, cc_by: bool, citation: str, variant: str = "A") -> Source:
    lic = "CC BY 4.0" if cc_by else None
    lic_url = ("http://creativecommons.org/licenses/by/4.0/" if cc_by
               else "http://arxiv.org/licenses/nonexclusive-distrib/1.0/")
    line = ("arXiv licence link: http://creativecommons.org/licenses/by/4.0/" if cc_by else
            "arXiv licence link: http://arxiv.org/licenses/nonexclusive-distrib/1.0/ (arXiv's non-exclusive "
            "licence to distribute; no reuse licence, so read-only)")
    return Source(key=key, name=name, url=f"https://arxiv.org/html/{arxiv_id}v{version}", kind="taxonomy",
                  fmt="html", license=lic, license_url=lic_url, license_line=line, license_verified_at=CHECKED,
                  read_only=not cc_by, weight=1, variant=variant, short=short,
                  page_url=f"https://arxiv.org/abs/{arxiv_id}v{version}", version_label=f"{arxiv_id}v{version}",
                  version_pin=f"arXiv:{arxiv_id}v{version}", citation=citation)


SOURCES: dict[str, Source] = {s.key: s for s in (
    Source(key="model_spec", name="OpenAI Model Spec", url=f"{_MS_RAW}/model_spec.md", kind="spec", fmt="markdown",
           license="CC0 1.0 Universal", license_url="https://github.com/openai/model_spec/blob/main/LICENSE",
           license_line="Creative Commons Legal Code / CC0 1.0 Universal", license_verified_at=CHECKED,
           read_only=False, weight=2, variant="A", short="ms", page_url="https://github.com/openai/model_spec",
           version_label="2026-08-18", version_pin=f"{MODEL_SPEC_COMMIT[:7]} (commit {MODEL_SPEC_COMMIT}, "
                                                   f"\"Release 2026-08-18\")",
           commit=MODEL_SPEC_COMMIT, license_file_url=f"{_MS_RAW}/LICENSE",
           citation="OpenAI, Model Spec, release of 2026-08-18"),
    Source(key="constitution", name="Anthropic, Claude's constitution", url="https://www.anthropic.com/constitution",
           kind="constitution", fmt="html", license="CC0 1.0",
           license_url="https://creativecommons.org/publicdomain/zero/1.0/",
           license_line=("We’re releasing Claude’s constitution in full under a Creative Commons CC0 1.0 "
                         "Deed, meaning it can be freely used by anyone for any purpose without asking for "
                         "permission."),
           license_verified_at=CHECKED, read_only=False, weight=2, variant="A", short="con",
           page_url="https://www.anthropic.com/constitution", drop_before="Overview",
           drop_sections=("Acknowledgements",),
           citation="Anthropic, Claude's constitution (January 2026); page captured at fetch time",
           notes="the page prints no version: the pin is the capture date and the sha256 of the fetched page"),
    Source(key="anthropic_aup", name="Anthropic Usage Policy", url="https://www.anthropic.com/legal/aup",
           kind="policy", fmt="html", license=None, license_url=None,
           license_line="proprietary (no reuse licence on the page)", license_verified_at=CHECKED, read_only=True,
           weight=1, variant="A", short="aup", page_url="https://www.anthropic.com/legal/aup",
           notes="harm categories, not dispositions: used for the over-refusal / over-compliance scope only"),
    Source(key="openai_usage", name="OpenAI Usage Policies", url="https://openai.com/policies/usage-policies/",
           kind="policy", fmt="html", license=None, license_url=None,
           license_line="proprietary (no reuse licence on the page)", license_verified_at=CHECKED, read_only=True,
           weight=1, variant="A", short="oup", page_url="https://openai.com/policies/usage-policies/",
           notes="harm categories, not dispositions: used for the over-refusal / over-compliance scope only"),
    _arxiv("sabotage_evals", "sab", "2410.21514", 1, "Sabotage Evaluations for Frontier Models", cc_by=False,
           citation="Benton et al. (2024), arXiv:2410.21514"),
    _arxiv("alignment_faking", "af", "2412.14093", 2, "Alignment faking in large language models", cc_by=False,
           citation="Greenblatt et al. (2024), arXiv:2412.14093"),
    _arxiv("in_context_scheming", "sch", "2412.04984", 2, "Frontier Models are Capable of In-context Scheming",
           cc_by=False, citation="Meinke et al. (2024), arXiv:2412.04984"),
    _arxiv("sandbagging", "sb", "2406.07358", 4, "AI Sandbagging: Language Models can Strategically Underperform "
           "on Evaluations", cc_by=True, citation="van der Weij et al. (2024), arXiv:2406.07358"),
    _arxiv("emergent_misalignment", "em", "2502.17424", 7, "Emergent Misalignment: Narrow finetuning can produce "
           "broadly misaligned LLMs", cc_by=False, citation="Betley et al. (2025), arXiv:2502.17424"),
    _arxiv("elephant", "el", "2505.13995", 2, "ELEPHANT: Measuring and understanding social sycophancy in LLMs",
           cc_by=True, citation="Cheng et al. (2025), arXiv:2505.13995"),
    _arxiv("agentic_misalignment", "am", "2510.05179", 2, "Agentic Misalignment: How LLMs Could Be Insider Threats",
           cc_by=True, citation="Lynch et al. (2025), arXiv:2510.05179"),
    Source(key="aisafety_glossary", name="AISafety.info (Stampy) concept names", url="https://aisafety.info/",
           kind="glossary", fmt="html", license=None, license_url=None,
           license_line="mixed licences (plan 08 § 2); names only, for the dedup pass", license_verified_at=CHECKED,
           read_only=True, weight=0.5, variant="A", short="gl", optional=True,
           notes="names only, never extracted from; the page to read is chosen before the full extraction"),
    Source(key="krakovna", name="Krakovna et al., specification gaming examples in AI (master list)",
           url="https://vkrakovna.wordpress.com/2018/04/02/specification-gaming-examples-in-ai/", kind="incidents",
           fmt="sheet_tsv", license=None, license_url=None,
           license_line="no licence stated on the landing page (checked 2026-10-10)", license_verified_at=CHECKED,
           read_only=True, weight=1, variant="B", short="kra", optional=True, store=False, table_header="Title",
           notes="the published sheet linked from the landing page is read transiently by extract --variant B, "
                 "through its TSV export (<sheet>/pub?output=tsv; the pubhtml page, read 2026-10-13, is drawn by "
                 "script and holds no table); a banner line sits above the header; never written to the "
                 "repository; quotes of 25 words or fewer"),
    Source(key="machiavelli", name="MACHIAVELLI benchmark annotation schema",
           url="https://raw.githubusercontent.com/aypan17/machiavelli/main/README.md", kind="schema",
           fmt="markdown", license="MIT", license_url="https://github.com/aypan17/machiavelli/blob/main/LICENSE",
           license_line="MIT License / Copyright (c) 2022 Alex Pan", license_verified_at=CHECKED, read_only=False,
           weight=1, variant="B", short="mac", optional=True, page_url="https://github.com/aypan17/machiavelli",
           notes="the annotation categories (deception, manipulation, betrayal, coercion; power); the exact file "
                 "and commit are pinned when variant B runs"),
)}

#: Downloaded by ``fetch`` without ``--only`` (Roger's approval with the plan, 2026-10-10; the pilot's sources).
DEFAULT_FETCH: tuple[str, ...] = ("model_spec", "constitution")
#: Variant B reads the two incident sources only (plan 08 § 8; coding plan § 1).
VARIANT_B_SOURCES: tuple[str, ...] = ("krakovna", "agentic_misalignment")

#: Sources of plan 08 § 2 deliberately not in the table.
SKIPPED: dict[str, str] = {
    "metr_task_reports": "plan 08 names METR task reports without a document; none chosen",
    "ai_incident_database": "variant B's heaviest source; out of scope (coding plan § 2)",
    "elephant_beyond_taxonomy": "ELEPHANT is read for its taxonomy text only (coding plan § 2)",
}


def quote_limit(key: str) -> Optional[int]:
    """The longest quote, in words, the sweep keeps from source ``key``: 25 for a ``read_only`` source, else no
    limit (a full sentence)."""
    return READ_ONLY_QUOTE_WORDS if SOURCES[key].read_only else None


__all__ = ["Source", "SOURCES", "DEFAULT_FETCH", "VARIANT_B_SOURCES", "SKIPPED", "KINDS", "FORMATS",
           "READ_ONLY_QUOTE_WORDS", "MODEL_SPEC_COMMIT", "quote_limit"]
