"""The pilot readout (``report.md``) and Roger's spot-check sample (``roger_sample.md``) of a run.

Both are documents for Roger: every file is linked relative to the document, every corpus trait named links to
its file, and terms are defined on first use or linked to the glossary.  Nothing here calls a model.
"""
from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Mapping, Optional, Sequence

from assistant_axis.gapgen.paths import REPO_ROOT

from .sense import BLOCK as SENSE_BLOCK
from .sense import resolved_hint
from .submit import M1_PASS_RATE_ASSUMED as PASS_RATE_ASSUMED
from .submit import M1_PASS_RATE_HIGH as PASS_RATE_HIGH

GLOSSARY = REPO_ROOT / "reports" / "trait_gap_generation" / "glossary.md"
PLAN = REPO_ROOT / "reports" / "trait_gap_generation" / "coding_plan_03_base_model.md"


def _link(target: Path, doc: Path, text: Optional[str] = None) -> str:
    rel = os.path.relpath(Path(target), Path(doc).parent)
    return f"[{text or Path(target).name}]({rel.replace(os.sep, '/')})"


def _pct(x: Optional[float]) -> str:
    return "n/a" if x is None else f"{x:.1%}"


def _num(x) -> str:
    return "n/a" if x is None else str(x)


def _plural(n: Optional[int], one: str, many: Optional[str] = None) -> str:
    return f"{_num(n)} {one if n == 1 else (many or one + 's')}"


#: The `person` family's prompts are `wiki_bio` openings: tokenized and lower-cased, with only the name and
#: sentence starts restored (QUESTIONS 61).  The others are prompts we wrote.
BIO_FAMILY = "person"
CLEAN_FAMILIES = ("list_gloss", "occupation", "ai_assistant")
FAMILY_SOURCE = {"person": "wiki_bio opening (lower-cased)", "list_gloss": "glossary (clean)",
                 "occupation": "professions (clean)", "ai_assistant": "AI assistant (clean)",
                 "list": "trait list (clean)", "contrast": "contrast sentence (clean)"}


def _echo_section(st: Mapping) -> list[str]:
    """What the biography-echo screen cost (Roger, QUESTIONS 54): the two rules counted apart, the words the
    name rule dropped, and the ones no other seed brought in."""
    j = st.get("junk") or {}
    lost = j.get("name_echo_not_elsewhere")
    words = j.get("name_echo_words") or {}
    top = ", ".join(f"`{w}` ({c})" for w, c in list(words.items())[:12])
    lines = ["## The biography-echo screen", "",
             f"Dropped as a **name echo** (a one-word candidate matching a word of the person's name): "
             f"{_plural(j.get('name_echo'), 'emission')} over {_plural(len(words), 'distinct word')}.  Dropped "
             f"as a **biography span** (a multiword label appearing verbatim in the biography): "
             f"{_num(j.get('bio_span_echo'))} (the spans themselves are not listed: they are verbatim CC BY-SA "
             f"prose).", ""]
    if top:
        lines += [f"The words the name rule dropped, most often first: {top}.", ""]
    if lost is None:
        lines += ["No name-echo record in this round's stats (an older `parse`).", ""]
    elif lost:
        lines += [f"**Words lost altogether** — dropped as a name echo and never emitted from another seed "
                  f"({len(lost)}): " + ", ".join(f"`{w}`" for w in lost) + ".  This list *is* the whitelist "
                  "QUESTIONS 54 asks for: these words, and only these, cost the run anything.", ""]
    else:
        lines += ["**No word was lost**: every word the name rule dropped also arrived from another seed, where "
                  "no biography named it.  That closes QUESTIONS 54 with evidence — the rule's cost in this "
                  "round is zero, and no whitelist is needed.", ""]
    return lines


def _sense_section(st: Mapping, ev: Mapping) -> list[str]:
    """The gloss sense settled before M1 (Roger, QUESTIONS 56)."""
    s = (ev.get("args") or {}).get("gloss_sense") or st.get("gloss_sense") or {}
    if not s:
        return []
    return ["## The gloss sense (settled before M1)", "",
            f"{_num(s.get('n_two_sided'))} rows carried two glosses (OEWN's person-descriptive sense and the "
            f"model's own); the cosine screen called {_num(s.get('n_divergent'))} of "
            f"{_num(s.get('n_screened'))} divergent (rate {_pct(s.get('divergence_rate'))}), and one cheap call "
            f"settled each: {_num(s.get('n_chose_sample'))} took the sample's reading, "
            f"{_num(s.get('n_chose_dictionary'))} the dictionary's"
            + (f", {s['n_illegible_sample']} of them because the sample's reading was called illegible"
               if s.get("n_illegible_sample") else "")
            + f".  Still unresolved: {_num(s.get('n_unresolved'))} (submission refuses while any remain).  "
              f"The criterion is fidelity first, subject to legibility, and never novelty.", ""]


def _family_section(ev: Mapping) -> list[str]:
    """Yield, malformed rate and M1 pass rate per prompt family (Roger, QUESTIONS 61): a within-run control
    for whether the `wiki_bio` family's pre-tokenised casing hurts."""
    lines = ["## By family: the `wiki_bio` prompts against the clean ones", "",
             f"The `{BIO_FAMILY}` family's prompts are biography openings as `wiki_bio` stores them (tokenized "
             f"and lower-cased, with only the name and sentence starts restored), so its numbers beside the "
             f"clean-prompt families (" + ", ".join(f"`{f}`" for f in CLEAN_FAMILIES) + ") are a within-run "
             "control for whether that casing hurts: the model continues the prompt, so degraded orthography "
             "invites degraded continuation.  The `ai_assistant` row is also the in-or-out call of plan 03 "
             "section 9.2.  The submitted, M1 and M3 columns count the **submitted rows**, which passed the count "
             "floor; the next section reads the same families over the eligible table before it.", "",
             "| family | prompts | samples | uniques/1k | eligible/1k | malformed | ineligible | submitted | "
             "M1 trait rate | alignment scores | M3 decisions | M3 new rate |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for f, v in (ev.get("by_family") or {}).items():
        s = v.get("stats") or {}
        name = f"**{f}**" if f in (BIO_FAMILY, "ai_assistant") else f
        lines.append(f"| {name} | {FAMILY_SOURCE.get(f, '?')} | {_num(s.get('n_samples'))} | "
                     f"{_num(s.get('uniques_per_1k'))} | {_num(s.get('eligible_per_1k'))} | "
                     f"{_pct(s.get('malformed_rate'))} | {_pct(s.get('ineligible_share'))} | "
                     f"{v['n_submitted']} | {_pct(v['m1'].get('pass_rate'))} | {v['m1'].get('alignment_scores')} | "
                     f"{v['m3'].get('decision')} | {_pct(v['m3'].get('new_rate'))} |")
    lines += ["", "If those numbers say casing matters, the first iteration move is free and deterministic: OEWN "
                  "lists proper adjectives capitalised, so a lookup against the WordNet lemmas already on disk "
                  "restores nationalities, languages and eponyms with no truecasing model and no API spend.  "
                  "Not built yet, by decision (QUESTIONS 61).", ""]
    return lines


def floor_text(fl: Optional[Mapping]) -> str:
    """The count floor with the sample size it was applied at and the one it was chosen at (gate audit 3)."""
    if not fl:
        return "not recorded"
    n, at = fl.get("n_samples"), fl.get("chosen_at_n_samples")
    s = (f"count >= {fl['min_count']} at {n:,} samples ({fl.get('per_1k_samples')} per 1,000 samples)" if n
         else f"count >= {fl['min_count']} (the table's sample size not recorded)")
    s += f"; chosen at {at:,} samples" if at else "; the sample size it was chosen at was not recorded"
    if n and at and n != at:
        s += f" (**a table of another size**: {round(1000.0 * fl['min_count'] / at, 3)} per 1,000 there)"
    return s + (f"; {fl['source']}" if fl.get("source") else "")


def _before_floor_section(ev: Mapping) -> list[str]:
    """Per family over the eligible table before the count floor (gate audit 3, proposal 7): the submitted rows
    alone are what survived the floor, so their family split says more about the floor than the family."""
    b = ev.get("before_floor") or {}
    if not b.get("by_family"):
        return []
    lines = ["## By family, before the count floor (the eligible table)", "",
             f"All {b['n_eligible']} eligible rows, {b['n_at_floor']} of them at or above the floor of "
             f"{b['min_count']}.  The M1 and M3 rates are read from every verdict the registry holds for these "
             "keys, whichever run judged them, so each rests on the **judged** column, not on every row: rows no "
             "run has judged are counted, never guessed.  **Only here** is the rows no other family emitted, "
             "which is what the family adds (the `ai_assistant` in-or-out call, plan 03 section 9.2).", "",
             "| family | eligible | at floor | nouns | M1-judged | M1 trait rate | M3-decided | M3 new rate | "
             "only here: eligible / at floor / M1-judged | only here: M1 trait rate | only here: M3 new rate |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for f, v in b["by_family"].items():
        o = v.get("only_here") or {}
        name = f"**{f}**" if f in (BIO_FAMILY, "ai_assistant") else f
        lines.append(f"| {name} | {v['n_eligible']} | {v['n_at_floor']} | {v['n_nouns']} | {v['n_m1']} | "
                     f"{_pct(v['m1_pass_rate'])} | {v['n_m3']} | {_pct(v['m3_new_rate'])} | "
                     f"{o.get('n_eligible')} / {o.get('n_at_floor')} / {o.get('n_m1')} | {_pct(o.get('m1_pass_rate'))} | "
                     f"{_pct(o.get('m3_new_rate'))} |")
    lines += ["", f"**Noun share of M1 survivors before the floor**: {_pct(b.get('noun_share_m1_survivors'))} of "
                  f"{b.get('n_m1_survivors')} eligible rows M1 called a trait (any run); {b.get('n_nouns_m1_judged')} "
                  f"of the {b.get('n_nouns')} eligible nouns have an M1 verdict.  This, not the share among the "
                  "submitted rows, is the number that gates the noun-normalization follow-up (plan 03 task 11).", ""]
    return lines


def render_report(ev: Mapping, *, doc_path: Path, run_dir: Path, table_path: Path, stats_path: Optional[Path],
                  filter_dir: Path, novelty_dir: Path) -> str:
    d = Path(doc_path)
    L = lambda p, t=None: _link(p, d, t)  # noqa: E731
    g = lambda anchor, text: _link(GLOSSARY, d, text).replace(")", f"#{anchor})")  # noqa: E731
    st = ev.get("stats") or {}
    a = ev.get("args") or {}
    lines = [f"# Base-model generator: run `{ev['run_id']}` readout", "",
             f"Plan: {L(PLAN)}.  Terms: {L(GLOSSARY, 'glossary')}.  Round {a.get('round')}, prompts version "
             f"{a.get('prompts_version')}, temperature {a.get('temperature')}, model `{a.get('model')}`.  Table "
             f"{L(table_path)}" + (f"; stats {L(stats_path)}" if stats_path else "") + ".", "",
             "**M1** is the platform's trait-hood filter, **M3** its novelty check.  The "
             + g("rarefaction-curve", "rarefaction curve") + " counts distinct words against samples drawn; "
             + g("chao1", "Chao1") + " estimates the vocabulary reachable; the "
             + g("collapse-index", "collapse index") + " is the share of emissions taken by the top 50 words "
             "(target under 15%).", "", "## Yield", "",
             "| measure | value |", "|---|---|",
             f"| samples | {st.get('n_samples')} |", f"| raw items | {st.get('n_raw_items')} |",
             f"| distinct stems (uniques) | {st.get('n_unique')} ({st.get('uniques_per_1k_samples')} per 1k samples) |",
             f"| eligible | {st.get('n_eligible')} |",
             f"| count floor | {floor_text(ev.get('floor'))} |",
             f"| submitted | {ev.get('n_candidates')} |",
             f"| collapse index (top 50) | {_pct(st.get('collapse_top50_share'))} |",
             f"| Chao1 (all / eligible) | {st.get('chao1')} / {st.get('chao1_eligible')} |",
             f"| rarefaction | {st.get('rarefaction')} |",
             f"| noun share: uniques / eligible / M1 survivors (submitted; eligible table before the floor) | "
             f"{_pct(st.get('noun_share_unique'))} / {_pct(st.get('noun_share_eligible'))} / "
             f"{_pct(ev.get('noun_share_m1_survivors'))}; "
             f"{_pct((ev.get('before_floor') or {}).get('noun_share_m1_survivors'))} |",
             f"| recovery by string (corpus stems found) | {(st.get('recovery_strings') or {}).get('found')} of "
             f"{(st.get('recovery_strings') or {}).get('n_corpus')} ({_pct((st.get('recovery_strings') or {}).get('recall'))}) |",
             ""]
    lines += _echo_section(st)
    lines += _sense_section(st, ev)
    m1, m3 = ev.get("m1") or {}, ev.get("m3") or {}
    lines += ["## M1 and M3", "",
              f"M1 filtered {m1.get('n_filtered', 0)} of {m1.get('n_rows', 0)} rows: verdicts {m1.get('verdict')}; "
              f"**measured pass rate {_pct(m1.get('pass_rate'))}** (the estimate assumed "
              f"{PASS_RATE_ASSUMED:.0%}, with {PASS_RATE_HIGH:.0%} printed as its high case); alignment scores "
              f"{m1.get('alignment_scores')}.",
              f"M3 scored {m3.get('n_scored', 0)}: {m3.get('decision')}; pair completions {m3.get('pair_completions')}; "
              f"relation-call opposites {m3.get('relation_opposites')}.", ""]
    lines += _family_section(ev)
    lines += _before_floor_section(ev)
    c = ev.get("cost") or {}
    sense_usd = (ev.get("sense_usage") or {}).get("total_usd") or 0.0
    lines += ["", "## Cost", "",
              f"Total ${c.get('total_usd', 0):.4f} from the usage records "
              + ", ".join(L(Path(p)) for p in c.get("files") or []) + f"; per candidate "
              f"${(ev.get('cost_per_candidate') or 0):.4f}; useful (M3 new or pair completion) {ev.get('useful')}, "
              f"{ev.get('useful_per_dollar')} per dollar.  The sampling itself is $0 (a local model, its tokens "
              f"recorded at a zero rate); the generator's own paid calls are the gloss-sense ones, "
              f"${sense_usd:.4f} here.", "",
              "## Files", "",
              f"- {L(run_dir / 'candidates.jsonl')}, {L(run_dir / 'run.json')}, {L(run_dir / 'usage.json')}, "
              f"{L(run_dir / 'submit_report.json')}",
              f"- M1 batch {L(filter_dir, filter_dir.name)}, M3 batch {L(novelty_dir, novelty_dir.name)}",
              f"- {L(d.with_name('roger_sample.md'))}: 100 rows for the spot check", ""]
    return "\n".join(lines)


def render_sample(rows: Sequence[Mapping], *, doc_path: Path, n: int = 100, seed: int = 0) -> str:
    """100 random rows (M1 survivors when M1 has run, else eligible table rows) for the junk and polysemy check."""
    pool = list(rows)
    r = random.Random(seed)
    pick = sorted(r.sample(pool, min(n, len(pool))), key=lambda x: x.get("rank") or 0)
    lines = [f"# Spot check: {_plural(len(pick), 'random row')}", "",
             "Mark each row: **J** junk (not a word for what someone is like), **P** polysemous (the gloss is a "
             "different sense from the one you would expect), or leave blank.  Plan 03 section 6.", "",
             "The **sense** column is the gloss-sense decision of QUESTIONS 56 where a row carried two glosses: "
             "`sample` or `dictionary`, with the cosine that sent it to a call; a blank means the two glosses "
             "agreed or there was only one.  **hint sent to M1** is the resolved one.", "",
             "| # | word | form | count | families | hint sent to M1 | sampled gloss | sense | J/P |",
             "|---|---|---|---|---|---|---|---|---|"]
    for i, x in enumerate(pick, 1):
        b = x.get(SENSE_BLOCK) or {}
        sense = ""
        if b.get("divergent"):
            sense = f"{b.get('chosen') or 'unresolved'} (cos {b.get('cosine')})"
        lines.append(f"| {i} | {x.get('surface')} | {x.get('form')} | {x.get('count')} | "
                     f"{', '.join(sorted(x.get('families') or {}))} | {resolved_hint(x) or ''} | "
                     f"{x.get('sample_gloss') or ''} | {sense} |  |")
    return "\n".join(lines) + "\n"
