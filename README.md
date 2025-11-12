## Title: Ephemeral, Signed, Reproducible DFIR-in-a-Box
## Thesis: 
One command spins up a constrained container, runs a selected triage profile, and outputs a timeline, detections, and a signed provenance bundle that proves which tools and rules produced each result.

## Problem statement
IR toolchains are hard to reproduce. Version drift changes results, which weakens confidence and slows handoffs. A portable, hermetic triage pipeline with verifiable provenance improves speed and trust during response.

## Prior work to cite in the paper
- Plaso/log2timeline for timeline generation. 
- Timesketch for interactive review and its official Docker install path. 
- YARA for file and memory pattern matching. 
- Sigma rules and pySigma for log detections and backend conversion pipelines. 
- Volatility3 for memory forensics. 
- Velociraptor as an IR platform and artifact concept, used here as related work not embedded. 
- ForensicArtifacts repository and format to define collection targets. 
- SLSA provenance and in-toto attestations for build and run transparency. Syft and Grype for SBOMs. 

## What is new
- reproducible triage: All tooling pinned and containerized. Outputs record exact tool versions, rule SHAs, and config.
- signed provenance: Each run emits an SBOM and an in-toto or SLSA provenance attestation that binds evidence hash to toolchain and parameters.
- Profile-driven pipeline: YAML profiles select artifacts, parsers, and detectors per case type. Profiles reference ForensicArtifacts for cross-OS path logic.

## System design
### Inputs
- Read-only evidence mount: directory, disk image, or memory image.
- Case profile: profiles/{windows-triage.yml, linux-triage.yml, macos-triage.yml}

### Modules
- Collect: Artifact selectors from ForensicArtifacts. Optional image mount via libguestfs or aff4.
- Timeline: Plaso log2timeline → .plaso → psort JSONL.
- Detections: Sigma via sigma-cli with appropriate pipelines, plus YARA across file sets.
- Memory: Volatility3 if a memory image is present.
- Report: Merge JSON artifacts into a single JSON index and a static HTML summary.
- Provenance: Syft SBOM of the running container and a run-level attestation that includes tool versions, rule pack SHAs, profile name, and evidence SHA256.

### Security and portability
- Read-only binds for evidence. No --privileged. Non-root user inside the container.
- Deterministic apt and pip pinning. Rebuilds produce the same SBOM.
- Output directory is write-only bind mount.

## Build

```bash
# build
docker build -t dfirbox:0.1 .

# quick demo with included rules
mkdir -p evidence out
echo "cmd.exe /c whoami" > evidence/demo.txt

docker run --rm \
  --user 1000:1000 \
  -v "$PWD/evidence":/evidence:ro \
  -v "$PWD/out":/out \
  dfirbox:0.1 dfirbox run -e /evidence -o /out -p /app/profiles/windows-triage.yml

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

## How to test
```bash
docker buildx build --platform linux/amd64 -t dfirbox:0.1 .

mkdir -p evidence out
echo "cmd.exe /c whoami" > evidence/demo.txt

docker run --rm --platform linux/amd64 \
  -v "$PWD/evidence":/evidence:ro -v "$PWD/out":/out \
  dfirbox:0.1 dfirbox run -e /evidence -o /out -p /app/profiles/windows-triage.yml

ls -lh out
wc -l out/events.jsonl
jq '.events, .sigma_matches, .yara_hits' out/dfirbox_report.json
```