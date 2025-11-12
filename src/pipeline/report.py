import os, json, datetime
from jinja2 import Template

TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>DFIRBox Report</title>
<style>
body{font-family:system-ui,Arial,sans-serif;margin:24px;}
h1{margin:0 0 8px 0;} .meta{color:#555;margin-bottom:16px}
section{margin:16px 0;padding:12px;border:1px solid #ddd;border-radius:8px}
code,pre{background:#f6f8fa;padding:4px;border-radius:4px}
table{border-collapse:collapse;width:100%} th,td{border:1px solid #ddd;padding:6px;text-align:left}
.small{font-size:12px;color:#666}
</style></head><body>
<h1>DFIRBox Report</h1>
<div class="meta">Generated: {{ now }} | Profile: {{ meta.profile }} | Evidence: {{ meta.evidence }}</div>

<section>
<h2>Summary</h2>
<ul>
<li>Total events (JSONL): {{ summary.events }}</li>
<li>Sigma matches: {{ summary.sigma }}</li>
<li>YARA hits: {{ summary.yara }}</li>
</ul>
</section>

<section>
<h2>Provenance</h2>
<pre class="small">{{ provenance | tojson(indent=2) }}</pre>
</section>

<section>
<h2>Sigma Matches (top 20)</h2>
<pre class="small">{{ sigma_preview }}</pre>
</section>

<section>
<h2>YARA Hits (top 50)</h2>
<pre class="small">{{ yara_preview }}</pre>
</section>

<section>
<h2>Artifacts</h2>
<ul>
<li><a href="events.jsonl">events.jsonl</a></li>
<li><a href="sigma_findings.json">sigma_findings.json</a></li>
<li><a href="yara_hits.json">yara_hits.json</a></li>
<li><a href="provenance.json">provenance.json</a></li>
<li><a href="timeline.plaso">timeline.plaso</a></li>
</ul>
</section>

</body></html>
"""

def build(outdir, jsonl_events, sigma_path, yara_path, provenance_path, meta):
    with open(jsonl_events,"r") as f:
        events_count = sum(1 for _ in f)

    sigma = json.load(open(sigma_path,"r"))
    yara = json.load(open(yara_path,"r"))
    prov = json.load(open(provenance_path,"r"))

    tpl = Template(TEMPLATE)
    html = tpl.render(
        now=str(datetime.datetime.utcnow()),
        meta=meta,
        summary={"events": events_count, "sigma": len(sigma), "yara": len(yara)},
        provenance=prov,
        sigma_preview=json.dumps(sigma[:20], indent=2),
        yara_preview=json.dumps(yara[:50], indent=2),
    )

    out_html = os.path.join(outdir, "dfirbox_report.html")
    with open(out_html,"w") as f:
        f.write(html)

    # also emit a machine-readable summary
    with open(os.path.join(outdir, "dfirbox_report.json"), "w") as f:
        json.dump({
            "events": events_count,
            "sigma_matches": len(sigma),
            "yara_hits": len(yara),
            "meta": meta
        }, f, indent=2)

    return out_html
