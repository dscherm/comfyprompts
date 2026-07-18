---
title: A downloader's self-reported "CC0" is not evidence — re-fetch each source page
severity: high
tags: [licensing, cc0, sourcing, provenance, subagent, verification]
source: hand-authored
created: 2026-07-17
project: comfyui-toolchain
---

## Symptom

A sourcing subagent downloaded 42 images for a shippable-asset LoRA (TX5) and
wrote a provenance JSON marking every source `"license": "CC0"` with
`"license_verbatim": "CC0"` and an empty rejected list. Taken at face value, the
dataset looked 100% clean.

The `license_verbatim` was just the string `"CC0"` — not text actually quoted
from any page — and zero rejections from a broad web hunt is itself suspicious.

## Root cause

License claims that feed **shippable** assets are load-bearing, but a self-report
(from a subagent, a downloader script, or a search-result snippet) is an assertion,
not verification. OpenGameArt in particular hosts mixed licenses per author and
per file; some authors (e.g. Cethiel, Jattenalle) publish CC-BY / OGA-BY work that
looks CC0 at a glance. A terse "CC0" echoed into a JSON proves nothing about what
the page's License box says.

## Mitigation

1. **Independently re-fetch each unique source page** and read its License box
   before trusting any downloaded file. WebFetch each `source_page`, extract the
   exact licence string(s) + author.
2. **Reject anything not explicitly CC0 / Public Domain (CC0 1.0).** CC-BY, CC-BY-SA,
   OGA-BY, GPL, or "CC0 + attribution requested" do not qualify. (In the TX5 boost
   pass this caught a CC-BY/OGA-BY water texture that a name-only glance had
   accepted.)
3. **Treat an empty rejected list as a red flag**, not a green light — a genuine
   CC0-only hunt across a mixed-licence host rejects candidates.
4. Store the *actual* licence string you read (not a re-typed "CC0") plus the URL
   in the manifest, and note that each page was independently verified with a date.
   Related: [[verify-asset-pack-pixels-before-dataset]].
