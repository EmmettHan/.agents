---
name: memory-leak-analysis
description: >-
  Analyze process memory leak from PSS monitoring data (mem.txt), memory trend
  charts (png), and hilog archives (gz/zip). Use when the user provides memory
  monitoring files, mentions PSS/Rss/Vss growth, suspects a process is leaking
  memory, shares a memory trend chart, or asks to determine whether a process
  has a memory leak on an OpenHarmony/HarmonyOS device. Also use when the user
  mentions hidumper memory snapshots, distributedfiledaemon, file_access_service,
  or any SA service showing upward memory trend. Always trigger even if the user
  only shares a screenshot of a memory graph and asks "is this a leak?".
---

# Memory Leak Analysis

Determine whether a process has a memory leak based on hard evidence: PSS time
series, hilog activity correlation, and process lifecycle data. Never conclude
from a single chart — always extract raw numbers and cross-reference with logs.

## Required input

Collect before starting analysis:

- **mem.txt**: periodic `hidumper --mem` snapshots containing per-process PSS/Vss/Rss/Uss
- **Memory trend chart** (png): visual overview, but treat as a hint, not proof
- **hilog archive** (zip/tgz with .gz log files): activity logs for correlation

If the user only provides a chart, ask for mem.txt and hilog. A chart alone cannot
prove or disprove a leak — it can only tell you where to look.

## Analysis workflow

Follow these steps in order. Each step produces a concrete artifact (data table,
timeline, correlation matrix) that feeds the next. Do not skip steps or jump to
conclusions.

### Step 1: Extract PSS time series

From mem.txt, extract all `<process_name>(pid=<PID>): <PSS> kB` summary lines for
the target process. Associate each data point with its timestamp by finding the
nearest preceding timestamp line (`YYYY-MM-DD HH:MM:SS`).

Output a table with columns: `#, timestamp, PSS_kB, delta_kB`.

Key things to check:
- **Multiple PIDs** for the same process name → the process was restarted. Analyze
  each PID lifecycle separately. Note the baseline PSS when each new PID appears —
  if it resets to the same starting value, the leak is per-process and restarts
  do release memory.
- **SwapPss**: if nonzero, the process has memory swapped out. Effective memory
  usage is higher than reported PSS.
- **Uss vs Pss**: if Uss ≈ Pss, growth is in private anonymous pages (native heap),
  not shared libraries.

### Step 2: Classify the growth pattern

Look at the delta column and identify phases:

```
Pattern A: "Request-driven leak"
  - Periods of steady growth (delta > 0 consistently)
  - Alternating with flat periods (delta ≈ 0)
  - Memory does NOT return to baseline during flat periods
  → Leak tied to specific operations. Need to identify what runs during growth.

Pattern B: "Continuous leak"
  - Every sample is higher than the previous (or nearly so)
  - No flat periods, no recovery
  - Growth even during low-activity hours (e.g., 02:00-05:00)
  → Leak in always-running code path (timer, heartbeat, background task)

Pattern C: "Cache / working set"
  - Growth followed by stable plateau
  - Plateau holds indefinitely (days) at a fixed level
  - If operations resume, memory does NOT grow further
  → Not a leak. Normal memory behavior.

Pattern D: "Stepped growth"
  - Growth in discrete jumps, stable between jumps
  - Each jump correlates with a specific event
  → May or may not be a leak. Check if steps are bounded.
```

A flat period after growth is NOT proof of "no leak" — it may just mean the
triggering operation stopped. The critical test: **does the same operation cause
further growth when resumed?** If two separate growth phases both correlate with
the same operation, and memory never returns between them, that's a leak.

### Step 3: Correlate with hilog activity

This is the step that separates real analysis from guessing. The hilog archive
contains domain-separated .gz files (app, pubservice, distribute, communication,
kmsg, etc.).

For the growth periods identified in Step 2:

1. **Find which hilog domain contains the target process's logs.** Search by PID
   across domains. Native SA services often log in `pubservice` or `distribute`,
   not `app`.

2. **Count activity per time window.** For each .gz file overlapping a growth/flat
   period, count lines matching the target PID or its known IPC callers.

3. **Build a correlation table:**
   ```
   Time range | Activity count | PSS delta | Phase
   ```
   If activity and PSS delta rise and fall together → request-driven.
   If PSS rises even when activity is zero → continuous leak or background path.

4. **Identify the operation type.** Extract unique log message types
   (strip timestamps/numbers, group by message template, sort by frequency).
   The top messages during growth periods reveal what the process is doing.

### Step 4: Cross-validate with process restarts

If the process has multiple PID lifecycles:

- Compare baseline PSS across PIDs — should be similar (~same binary)
- Compare growth rates under similar activity levels
- Check if the growth pattern reproduces across PIDs

Reproduction across independent PID lifecycles under similar conditions is strong
evidence of a leak. A single lifecycle that grows and then stabilizes is ambiguous.

### Step 5: Check for OOM / kill events

Search kmsg logs for:
- `oom` / `lowmem` / `mem_cgroup` events mentioning the PID
- `SAMGR: Scheduler proc:<name> kill` entries

Frequent process restarts (many different PIDs for the same process) suggest it's
being killed for resource consumption and restarted.

## Forming the conclusion

The conclusion must state:

1. **Leak or not** — and which pattern (A/B/C/D)
2. **Evidence summary** — the specific data points that support the conclusion:
   - PSS range (start → end → final)
   - Number of samples and time span
   - Correlation data (activity vs. growth)
   - Cross-PID validation if available
3. **Triggering operation** (if request-driven) — what the process was doing during
   growth, based on hilog
4. **Estimated leak rate** — kB/hour, or kB/request if request-driven

### What constitutes proof

| Claim | Required evidence |
|-------|-------------------|
| "It's a leak" | Growth that never reverses + correlation with operation OR continuous unbounded growth |
| "It's NOT a leak" | Stable plateau for extended period (days) with zero growth under continued operation |
| "Request-driven leak" | Growth starts/stops in sync with identified operation + memory doesn't return after operation stops |
| "Continuous leak" | Monotonic growth across all hours including idle periods |

### What is NOT sufficient

- A single upward chart — could be cache warmup
- "It stopped growing" — the triggering operation may have stopped
- Growth during a single lifecycle — could be one-time initialization
- High PSS — absolute value doesn't indicate a leak, only the trend does

## Output format

Produce a markdown report with:

1. Process name, PID(s), device, time range
2. PSS time series table (or summary if >50 points)
3. Growth pattern classification
4. Hilog correlation table
5. Conclusion with evidence citations
6. Estimated leak rate

Save the report alongside the input data for future reference.
