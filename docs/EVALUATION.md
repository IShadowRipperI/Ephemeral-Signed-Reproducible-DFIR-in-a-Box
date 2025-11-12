# Evaluation Plan

Metrics:
- Reproducibility: identical `dfirbox_report.json` on repeated runs with same image and inputs.
- Coverage: number of Sigma matches on seeded EVTX or JSONL samples.
- Runtime: wall clock from start to end. Output size.

Datasets:
- Use public Windows event log samples and benign file trees for YARA smoke tests.
