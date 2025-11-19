## Title: Ephemeral, Signed, Reproducible DFIR-in-a-Box

## Thesis
One command spins up a constrained container, runs a selected triage profile, and outputs a timeline, detections, and a signed provenance bundle that proves which tools and rules produced each result.

## Problem statement
IR toolchains are hard to reproduce. Version drift changes results, which weakens confidence and slows handoffs. A portable, hermetic triage pipeline with verifiable provenance improves speed and trust during response.

## Prior work to cite in the paper
- Plaso/log2timeline for timeline generation.  
- Timesketch for interactive review and its official Docker install path.  
- YARA for file and memory pattern matching.  
- Sigma rules and pySigma for log detections and backend conversion pipelines.  
- Volatility3 for memory forensics.  
- MemProcFS for memory image analysis and EVTX extraction.  
- Hayabusa for EVTX triage and timeline generation.  
- Velociraptor as an IR platform and artifact concept, used here as related work not embedded.  
- ForensicArtifacts repository and format to define collection targets.  
- SLSA provenance and in-toto attestations for build and run transparency. Syft and Grype for SBOMs.  

## What is new
- **Reproducible triage**: All tooling pinned and containerized. Outputs record exact tool versions, rule SHAs, and config.
- **Signed provenance**: Each run emits an SBOM and an in-toto or SLSA provenance attestation that binds evidence hash to toolchain and parameters.
- **Profile-driven pipeline**: YAML profiles select artifacts, parsers, and detectors per case type. Profiles reference ForensicArtifacts for cross-OS path logic.
- **Memory + EVTX triage**: Optional MemProcFS extraction from memory images feeding Hayabusa EVTX timelines into the same report.

## System design

### Inputs
- Read-only evidence mount: directory, disk image, or memory image.
- Case profile: `profiles/{windows-triage.yml, linux-triage.yml, macos-triage.yml}`

### Modules
- **Collect**: Artifact selectors from ForensicArtifacts. Optional image mount via libguestfs or aff4.
- **Timeline**: Plaso `log2timeline` → `.plaso` → `psort` JSONL.
- **Detections**: Sigma via `sigma-cli` with appropriate pipelines, plus YARA across file sets.
- **Memory**: Volatility3 if a memory image is present.
- **MemProcFS + Hayabusa**: If a memory image is present, MemProcFS extracts EVTX; Hayabusa runs `json-timeline` over those logs and writes to a dedicated `hayabusa_out/` folder.
- **Report**: Merge JSON artifacts into a single JSON index and a static HTML summary.
- **Provenance**: Syft SBOM of the running container and a run-level attestation that includes tool versions, rule pack SHAs, profile name, and evidence SHA256.

### Security and portability
- Read-only binds for evidence. No `--privileged`. Non-root user inside the container.
- Deterministic apt and pip pinning. Rebuilds produce the same SBOM.
- Output directory is a write-only bind mount.

---

## Build

```bash
# build (amd64 image so tools work consistently)
docker buildx build --platform linux/amd64 -t dfirbox:test .
```

## How to use 
### Note If you are using a memoery image make a evidence file and store mem image in there.  
```Bash
./run_dfirbox.sh
```

## How to test
```Bash
docker buildx build --platform linux/amd64 -t dfirbox:test .
echo "cmd.exe /c whoami" > evidence/demo.txt
./run_dfirbox.sh
ls -lh out
wc -l out/events.jsonl
jq '.events, .sigma_matches, .yara_hits' out/dfirbox_report.json
```

## file arch
```bash
dfirbox/
├── Dockerfile
├── requirements.txt
├── entrypoint.sh
├── README.md
├── LICENSE
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   ├── cli.py
│   └── pipeline/
│       ├── __init__.py
│       ├── timeline.py
│       ├── detections.py
│       ├── report.py
│       └── provenance.py
├── profiles/
│   ├── windows-triage.yml
│   ├── linux-triage.yml
│   └── macos-triage.yml
├── rules/
│   ├── yara/
│   │   ├── example_malware.yar
│   │   └── README.md
│   └── sigma/
│       ├── example_rule.yml
│       └── README.md
├── docs/
│   ├── DESIGN.md
│   └── EVALUATION.md
└── tests/
    └── test_smoke.sh
```