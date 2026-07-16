---
title: Artifact sandbox blocks navigator.clipboard — visible textarea is the reliable path
severity: low
tags: [artifact, html, clipboard, ui]
source: hand-authored
created: 2026-07-16
project: comfyui-toolchain
---

## Symptom

A "Copy scores" button in a published artifact (claude.ai/code) did
nothing for the user: `navigator.clipboard.writeText` rejects inside the
artifact iframe (permissions policy), and the promise-rejection path
showed no feedback. The user reported "copy button doesn't work" and the
data round-trip stalled.

## Root cause

The artifact runtime sandboxes the page; clipboard-write is not granted.
Any interactive artifact whose purpose is handing data BACK to the chat
cannot rely on the async clipboard API.

## Mitigation

1. Primary path: render the payload into a visible, readonly `<textarea>`,
   `.focus()` + `.select()` it, and tell the user to Ctrl+C — works in
   every sandbox.
2. Clipboard write stays as best-effort enhancement, with BOTH the resolve
   and reject branches setting user-visible status text (a silent reject
   is what made this failure confusing).
3. Cheaper still, when the data is small: skip the button and ask the user
   to answer in chat — the 2026-07-16 bake-off verdicts ultimately arrived
   as plain text.

## Notes (optional)

Applies to any capability the sandbox may deny (downloads, popups):
feature-detect AND handle rejection visibly; never let the only feedback
channel be a promise that dies silently.
