---
name: distributed-screen-debug
description: Analyze distributed screen v1.0 incidents from source/sink/caller/dependency logs. Use when the user provides a clear time point, operation, and symptom for DSCREEN, DHFWK, DHARDWARECOMMON, ScreenManager, distributed_input, or window_manager issues, and needs first-fault localization, code-backed root-cause analysis, or v2.0 is mentioned and should still be treated as v1.0.
---

# Distributed Screen Debug

Use a fixed path: classify the incident, pull the matching experience rule, then verify the first abnormal event against code.

## 1. Required input

Ask for missing essentials before concluding:

- time point, ideally to milliseconds
- operation
- symptom

Also collect any available logs from:

- source
- sink
- caller
- DHFWK, window_manager, distributed_input, multimodalinput_input

If only one side is available, continue with lower confidence and say so.

## 2. Always classify first

Before reading deeply, classify the case into one of these paths:

- setup
- data
- stop/recovery
- status callback
- input

Use [references/case-index.md](references/case-index.md) to match the symptom pattern and [references/cross-repo-map.md](references/cross-repo-map.md) to choose the right log boundary.

## 3. Workflow

1. Build a 3 to 10 second window around the user time point.
2. Run the timeline script on the main chain first.
3. Check the matching case rule and anti-patterns before calling a log line the root cause.
4. Separate three chains:
   - 投屏主链
   - DHARDWARECOMMON status callback path
   - distributed_input input path
5. Find the first missing, out-of-order, or failed key event.
6. Verify that event in code: function, state machine, return value, and boundary ownership.
7. Only then explain the cause.

## 4. Subagent rule

If subagents are available, use them as log collectors first.

- One subagent should summarize the main chain.
- A second subagent is optional for caller, callback, or input branches when those logs are large or independent.
- Subagents must only report evidence: timestamps, files, line numbers, missing events, and what is still needed.
- Subagents must not assign blame or jump to code root cause.

## 5. Commands

Use the script and then drill down with `rg` only where the timeline shows a gap.

```bash
python3 scripts/extract_dscreen_timeline.py \
  --focus "01-30 16:46:32.450" \
  --window 6 \
  --summary \
  /path/to/source.log /path/to/sink.log
```

```bash
python3 scripts/extract_dscreen_timeline.py \
  --focus "01-30 16:46:32.450" \
  --window 2 \
  /path/to/source.log /path/to/sink.log
```

```bash
rg -n "HandleEnable|CreateVirtualScreen|MakeMirror|NotifyRemoteSinkSetUp|HandleNotifySetUp|NotifyRemoteSourceSetUpResult|HandleNotifySetUpResult|HandleConnect|OnScreenSessionOpened|OnChannelSessionOpened|StartEncoder|SendFullData|OnStreamReceived|InputScreenData|OnDecodeOutputBufferAvailable|HandleDisconnect|HandleDisable|StateHandleLoop get callback reference failed" <logfile>
```

```bash
rg -n "DHARDWARECOMMON|OnDscreenChange|NotifyDHCommonMessage|StartShare|StopShare|StartPullInput|StopPullInput|stateChange|StateHandleLoop|get callback reference failed" <logfile>
```

```bash
rg -n "StartCaptureMMInput|StopCaptureMMInput|NotifyRemoteSinkSetUp|HandleNotifySetUpResult|AddMonitor|RemoveMonitor|SimulateInputEvent" <logfile>
```

## 6. Rules that matter

- Analyze only v1.0. If `screenVersion:"2.0"` appears, say it is ignored here and continue on the v1.0 control path.
- Prefer the first abnormal event.
- Do not let stop noise, heartbeat noise, or repeated disconnects override the first fault.
- If `SendFullData` and `OnDecodeOutputBufferAvailable` are already stable, the main screen path is usually alive; inspect callback, UI, or input branches next.
- Treat `DHARDWARECOMMON` state codes as state-layer signals, not main-chain evidence.
- If evidence is weak, say unknown.

## 7. Reference material

Read only the needed reference:

- [references/key-events.md](references/key-events.md): normal baseline, stop baseline, and known false positives
- [references/cross-repo-map.md](references/cross-repo-map.md): caller/dependency boundaries and search terms
- [references/case-index.md](references/case-index.md): historical case patterns and code anchors
- [references/anti-patterns.md](references/anti-patterns.md): logs that are easy to misread

## 8. Output order

1. Restate the user symptom
2. Give the key timeline
3. Name the first abnormal break
4. State the layer
5. Explain the code-backed cause
6. Say what evidence is still missing
7. Separate confirmed, likely, and unknown
