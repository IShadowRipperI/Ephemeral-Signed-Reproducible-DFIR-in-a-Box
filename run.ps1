param([string]$Profile='/app/profiles/windows-triage.yml')
$IMAGE = $env:IMAGE; if (-not $IMAGE) { $IMAGE = 'ghcr.io/<youruser>/dfirbox:0.1' }
New-Item -ItemType Directory -Force -Path evidence,out | Out-Null
docker run --rm $env:PLATFORM ? "--platform $env:PLATFORM" : "" `
  -v "${PWD}\evidence:/evidence:ro" -v "${PWD}\out:/out" `
  $IMAGE dfirbox run -e /evidence -o /out -p $Profile
