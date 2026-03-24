# Mini-Ralph Reference — Autonomous Sub-Loop Architecture

This document describes how mini-ralph loops work, how they relate to the main Ralph loop and agents, and how to create new ones.

---

## What Is a Mini-Ralph?

A mini-ralph is a **domain-scoped autonomous loop** that runs the same 8-step protocol as the main Ralph but with its own prompt, task list, requirements, and memory. It owns a specific problem domain (e.g., data quality, animation, testing) and works through a task plan independently.

Mini-ralphs are **not agents**. The distinction matters:

| | Agent | Mini-Ralph |
|---|---|---|
| **Scope** | Single task within one iteration | Full task plan across many iterations |
| **Autonomy** | Called by Ralph to do work, returns result | Runs independently via `ralph.sh --preset` |
| **Memory** | No persistent memory | Own `memories.md` + access to shared memory |
| **Plan** | No plan — executes what it's told | Own `plan.md` with tracked tasks |
| **Lifecycle** | Created and destroyed within one step | Persists across sessions until all tasks pass |
| **Location** | `.claude/agents/*.md` (definition only) | `{name}-ralph/` (full directory with state) |

An agent is a **role definition** (e.g., "you are a Three.js expert"). A mini-ralph is a **running loop** with its own backlog, progress tracking, and institutional memory.

---

## Directory Structure

Every mini-ralph lives in a top-level directory named `{domain}-ralph/`:

```
{domain}-ralph/
├── prompt.md       # The loop's operating instructions (extends main protocol)
├── plan.md         # Task list — JSON-per-line, each with passes: true/false
├── prd.md          # Acceptance criteria — what "done" looks like
├── memories.md     # Loop-specific learnings (patterns, decisions, fixes, context)
├── scripts/        # Transformation scripts written during execution
│   ├── task1_description.cjs
│   ├── task2_description.cjs
│   └── ...
└── backups/        # Pre-modification snapshots of files before destructive ops
    ├── filename_pre_task1.json
    └── ...
```

**Five required files**: `prompt.md`, `plan.md`, `prd.md`, `memories.md`, plus the `scripts/` and `backups/` directories.

---

## How It Connects to the Main Ralph

### 1. Orchestration via ralph.sh

The main `ralph.sh` dispatches to mini-ralphs through the preset system:

```bash
bash ralph.sh --preset {domain}     # Run the mini-ralph loop
bash ralph.sh --status              # Dashboard showing all loop progress
bash ralph.sh --chain {a} {b}       # Run multiple presets sequentially
```

**Registration**: Add a case to `resolve_preset()` in `ralph.sh`:

```bash
resolve_preset() {
  case "$1" in
    default)    echo ".claude/PROMPT.md" ;;
    ingredient) echo "ingredient-ralph/prompt.md" ;;
    {domain})   echo "{domain}-ralph/prompt.md" ;;    # ← add this
    *)          echo "" ;;
  esac
}
```

### 2. Shared Memory

Mini-ralphs have **two memory layers**:

- **Shared** (`.claude/memories.md`): Project-wide learnings. All loops read this. Mini-ralphs write here when a discovery affects the whole project.
- **Local** (`{domain}-ralph/memories.md`): Loop-specific learnings. Only this loop reads/writes here. Patterns, fixes, and decisions that only matter within this domain.

### 3. Main Fix Plan Reference

The main `.claude/fix_plan.md` tracks active mini-loops as line items:

```markdown
## Active Mini-Loops
- [>] {DOMAIN}-RALPH: N tasks (M/N complete) → `{domain}-ralph/plan.md`
```

This gives the main Ralph visibility into sub-loop progress without managing individual tasks.

### 4. Shared Gates

All mini-ralphs use the same validation gates (`bash .claude/scripts/gates.sh`). The build must pass before any commit, regardless of which loop made the change.

### 5. Agent Delegation

Mini-ralphs can delegate to agents just like the main Ralph. The delegation matrix in `.claude/docs/ralph-workflow.md` lists which agent handles which domain. A mini-ralph working on data might delegate a search to the `data-engineer` agent; one working on UI might call `ui-builder`.

---

## The 8-Step Protocol (Mini-Ralph Variation)

Each mini-ralph prompt **extends** the main 8-step protocol with domain-specific rules. The steps are the same, but the details differ:

### Step 1: Orient
Read `{domain}-ralph/plan.md`. Find the first task where `"passes": false`. Also read both memory files (shared + local).

### Step 2: Search
Understand the current state before modifying anything. Use subagents for large files. Never load huge data files into context directly.

### Step 3: Implement
Work on **one task**. Complete it fully — no partial work, no stubs. If the task requires a complex transformation, write a script in `{domain}-ralph/scripts/`. Back up target files to `{domain}-ralph/backups/` before destructive operations.

### Step 4: Verify
Run `bash .claude/scripts/gates.sh`. Also run task-specific verification (e.g., count records, check for remaining anomalies, confirm no regressions).

### Step 5: Record
Add a memory to `{domain}-ralph/memories.md`. Include what was done, how many records were affected, and anything surprising.

### Step 6: Mark Complete
In `plan.md`, change the completed task's `"passes": false` to `"passes": true`.

### Step 7: Commit
```bash
git add <specific-files>
git commit -m "{DOMAIN}-N: description"
```
Commit prefix matches the domain name in uppercase. One task per commit.

### Step 8: Signal
- Tasks remain → end iteration (loop restarts)
- All tasks pass → emit `<promise>COMPLETE</promise>`
- Stuck → emit `<promise>BLOCKED: reason</promise>`

---

## Plan Format

Mini-ralphs use **JSON-per-line** (not the markdown checklist format of the main fix_plan):

```json
{"task": 1, "category": "critical", "description": "Short description of what to do", "steps": ["Step 1", "Step 2", "Step 3"], "passes": false}
{"task": 2, "category": "high", "description": "Another task", "steps": ["Step 1", "Step 2"], "passes": false}
```

**Fields**:
- `task`: Integer ID (1-indexed, sequential)
- `category`: Priority bucket — `critical`, `high`, `medium`, `low`
- `description`: What to do (one sentence)
- `steps`: Array of concrete action items
- `passes`: `false` = pending, `true` = completed

**Why JSON-per-line?** It's machine-parseable (ralph.sh counts completions via `grep -c '"passes": true'`), easy to edit, and each line is a self-contained task.

**Ordering**: Tasks are processed top-to-bottom within priority. Critical tasks first, low tasks last.

---

## Prompt Structure

A mini-ralph `prompt.md` has four sections:

### 1. Identity & Scope
```markdown
# {Domain} Ralph — {Purpose}

You are {Domain} Ralph, a specialized agent for {what you do}.
You follow the master 8-step protocol from `.claude/PROMPT.md`.
This prompt adds {domain}-specific rules.

## Your Domain
You own the quality of these files:
- path/to/file1
- path/to/file2
```

### 2. The 8 Steps (domain-specific overrides)
Each step from the protocol, with domain-specific details. What files to read, what to verify, what scripts to write, what constitutes "done."

### 3. Domain Rules
Data formats, naming conventions, culinary knowledge tables, shader conventions — whatever this domain needs. This is where the specialized knowledge lives.

### 4. Safety & Linking
```markdown
## Safety
- Always back up before overwriting
- If a transformation removes >N records, STOP and ask
- Never modify files outside your domain

## Linking to Main Ralph
- This loop's plan is at `{domain}-ralph/plan.md`
- Shared memories go to `.claude/memories.md`
- Loop-specific memories go to `{domain}-ralph/memories.md`
- The main Ralph orchestrator invokes via: `bash ralph.sh --preset {domain}`
```

---

## PRD Structure

The `prd.md` defines acceptance criteria — the "definition of done" for the entire mini-ralph:

```markdown
# {Domain} — Requirements

## Overview
Why this mini-ralph exists. What problem it solves.

## Current State (Pre-Work)
Metrics, counts, known issues — the "before" snapshot.

## Target State
What the data/code should look like when all tasks pass.

## Acceptance Criteria
Numbered list of verifiable conditions:
1. Every X has Y
2. Zero instances of Z
3. All W pass validation
...
```

The PRD is **not a task list** — it's the measuring stick that tasks are evaluated against.

---

## Creating a New Mini-Ralph

### Checklist

1. **Define the domain**: What files does it own? What problem does it solve? What does "done" look like?

2. **Create the directory**:
   ```bash
   mkdir -p {domain}-ralph/scripts {domain}-ralph/backups
   ```

3. **Write prd.md** first: Define acceptance criteria before writing tasks. This prevents scope creep.

4. **Write plan.md**: Break the PRD into discrete tasks. Order by priority (critical → low). Each task should be completable in one iteration.

5. **Write prompt.md**: Start from the 8-step protocol template. Add domain-specific rules, data formats, safety constraints.

6. **Create memories.md**: Initialize with a context entry documenting the initial audit/analysis that motivated this mini-ralph.

7. **Register in ralph.sh**: Add the preset to `resolve_preset()`.

8. **Reference in fix_plan.md**: Add a line under "Active Mini-Loops" so the main Ralph tracks it.

9. **Update ralph-workflow.md**: Add the mini-ralph to the delegation matrix.

### Task Sizing

Each task should be **one iteration of work** — something that can be searched, implemented, verified, and committed in a single pass. If a task needs multiple scripts or touches many files, it's probably too big. Split it.

Good task size:
- "Remove all entries where field X is null" (one script, one verification)
- "Fill missing values for field Y using lookup table Z" (one script, one verification)

Too big:
- "Clean up the entire dataset" (vague, multi-step, no clear completion)

### Naming Conventions

| Thing | Convention | Example |
|---|---|---|
| Directory | `{domain}-ralph/` | `ingredient-ralph/` |
| Preset name | `{domain}` | `ingredient` |
| Commit prefix | `{DOMAIN}-N:` | `INGREDIENT-1:` |
| Script files | `task{N}_{description}.cjs` | `task1_purge_anomalies.cjs` |
| Backup files | `{filename}_pre_task{N}.json` | `pairings_pre_task1.json` |

---

## Lifecycle

```
┌─────────────────────────────────────────────────────┐
│  1. Audit / Analysis (manual or agent-assisted)     │
│     → Discover problems, quantify scope             │
├─────────────────────────────────────────────────────┤
│  2. Create Mini-Ralph                               │
│     → prd.md, plan.md, prompt.md, memories.md       │
│     → Register in ralph.sh, fix_plan.md             │
├─────────────────────────────────────────────────────┤
│  3. Run Loop                                        │
│     bash ralph.sh --preset {domain}                 │
│     → Iterates: pick task → execute → verify →      │
│       commit → mark complete → repeat               │
├─────────────────────────────────────────────────────┤
│  4. Completion                                      │
│     → All tasks pass → emits COMPLETE signal        │
│     → Update fix_plan.md: [>] → [x]                │
│     → Loop exits                                    │
├─────────────────────────────────────────────────────┤
│  5. Archive                                         │
│     → Scripts remain (replayable if pipeline reruns)│
│     → Memories persist for future reference         │
│     → Backups can be pruned after verification      │
└─────────────────────────────────────────────────────┘
```

After completion, the mini-ralph directory stays in the repo. Its scripts are replayable, its memories inform future work, and its plan serves as an audit trail.

---

## Relationship Diagram

```
ralph.sh (orchestrator)
│
├── --preset default ──→ .claude/PROMPT.md (main Ralph)
│   │                         │
│   │                         ├── Delegates to agents:
│   │                         │   ├── data-engineer
│   │                         │   ├── scene-architect
│   │                         │   ├── ui-builder
│   │                         │   └── tour-guide
│   │                         │
│   │                         ├── Reads/writes: .claude/fix_plan.md
│   │                         ├── Reads/writes: .claude/memories.md (shared)
│   │                         └── Validates via: .claude/scripts/gates.sh
│   │
├── --preset ingredient ──→ ingredient-ralph/prompt.md
│   │                         │
│   │                         ├── Can also delegate to agents
│   │                         ├── Reads/writes: ingredient-ralph/plan.md (own)
│   │                         ├── Reads/writes: ingredient-ralph/memories.md (own)
│   │                         ├── Reads/writes: .claude/memories.md (shared)
│   │                         └── Validates via: .claude/scripts/gates.sh (shared)
│   │
├── --preset {future} ──→ {future}-ralph/prompt.md
│   │                         └── (same pattern)
│   │
├── --status ──→ Reads ALL plan.md files, shows dashboard
└── --chain ──→ Runs presets sequentially
```

**Key insight**: The main Ralph and all mini-ralphs share the same validation gates, the same shared memory, and the same orchestrator. They differ in prompt (domain rules), plan (task list), and local memory (domain learnings). This gives each loop autonomy within its domain while maintaining project-wide consistency.

---

## Variants Across Projects

The mini-ralph pattern adapts to each project's conventions. These are the known variations:

### Directory Placement

| Pattern | Example | When to use |
|---|---|---|
| `{domain}-ralph/` at project root | `ingredient-ralph/`, `road-ralph/` | Most projects — simple, discoverable |
| `ralph/{track}/` subdirectory | `ralph/berserkr/`, `ralph/config-engine/` | When multiple independent tracks share infrastructure |
| `pipelines/{name}-ralph/` | `pipelines/fusion-ralph/` | Pipeline-oriented projects (staged transforms) |

### Plan Format

| Format | Example | When to use |
|---|---|---|
| **JSON-per-line** | `{"task": 1, "passes": false}` | Machine-parseable, `grep -c` for status counts |
| **Markdown checklist** | `- [ ] TASK-1: description` | Human-readable, works with main fix_plan.md |

Both work. Pick whichever your project already uses. The key is that `ralph.sh --status` can count completions — JSON uses `grep -c '"passes": true'`, markdown uses `grep -c '\[x\]'`.

### Completion Signals

| Signal | Used by |
|---|---|
| `<promise>COMPLETE</promise>` | Most projects |
| `<promise>ALL TASKS COMPLETE</promise>` | Main ralph (backward compat) |
| `RALPH_COMPLETE` | berserkr-godot |
| `SIGNAL: COMPLETE` | DissonantDreams |

Match your project's existing convention. The signal is just a grep target in ralph.sh — any unique string works.

### Orchestrator Location

| Pattern | Location |
|---|---|
| Single ralph.sh at root | `./ralph.sh --preset {name}` |
| Per-track ralph.sh | `ralph/{track}/ralph.sh` |
| No ralph.sh (prompt-only) | `while :; do cat prompt.md \| claude; done` |

### Memory System

| Pattern | Shared memory | Local memory |
|---|---|---|
| `.claude/memories.md` + `{domain}-ralph/memories.md` | Project-wide learnings | Domain-specific learnings |
| `.ralph/memories.md` + `{domain}-ralph/memory.md` | Global persistent | Loop-specific |
| `memories.md` at root + `activity.md` | Single memory file | Activity log as memory |

The principle is always the same: **shared memory for cross-domain learnings, local memory for domain-specific patterns**. File names and locations vary by project.
