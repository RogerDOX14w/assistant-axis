# Questions for Roger (trait-gap generation)

Format: `N. [workstream] question. Assumption proceeded under: ... Status: open | answered: ...`

1. [14] Should the holding lists (physical, roles) be written into TRAITS_TO_ADD / ROLES_TO_ADD by the tool? Assumption proceeded under: no; `gap_registry.py holding` prints a markdown block for Roger to paste, and never writes those files. Status: open (pre-registered, coding_plan_platform.md §12; M1 proceeds under the assumption)
2. [14] Which model gives the second opinion: plan 14's "Sonnet 5" or the repo's current default? Assumption proceeded under: `claude-sonnet-4-6` (the repo's current default). Status: open (pre-registered, §12; M1 proceeds under the assumption)
3. [14] Should the rubric return a `region` per candidate, with the corpus validation run supplying `corpus_regions.json` from labels alone (rather than a separate description-based labelling pass)? Assumption proceeded under: yes, the rubric returns `region` and the validation run over the existing labels yields `corpus_regions.json`. Status: open (pre-registered, §12; M1 proceeds under the assumption)
4. [15] In text-embedding space `K_95` may be far above 40. Assumption proceeded under: the config records `K_95` as decided with the K = 10/20/40 sensitivities beside it; if task (c) collapses at `K_95`, that goes to Roger with the numbers. Status: open (pre-registered, §12; for M2)
5. [10] When is the 200-item hand-labelled candidate set built? Assumption proceeded under: it waits for the first generator run. Status: open (pre-registered, §12; for M3)
