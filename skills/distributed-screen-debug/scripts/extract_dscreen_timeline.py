#!/usr/bin/env python3
"""Extract a compact distributed-screen timeline from log files."""

from __future__ import annotations

import argparse
from collections import defaultdict
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

TIME_RE = re.compile(
    r"^(?P<month>\d{2})-(?P<day>\d{2}) "
    r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<millis>\d{3}))?"
)
TAG_RE = re.compile(r"\b(DSCREEN|DHFWK|DHARDWARECOMMON)\b")

STAGE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("caller-make-mirror", re.compile(r"MakeMirror|RemoveVirtualScreenFromGroup")),
    ("dhfwk-online", re.compile(r"SendOnLineEvent|OnLineTask|OnDeviceReady|AddRealTimeOnlineDeviceNetworkId")),
    ("dhfwk-enable", re.compile(r"EnableDistributedScreen1\.0|EnableTask|RegisterHardware")),
    ("state-listener-register", re.compile(r"RegisterDScreenStateListener")),
    ("source-enable", re.compile(r"HandleEnable")),
    ("create-virtual-screen", re.compile(r"CreateVirtualScreen")),
    ("notify-sink-setup", re.compile(r"NotifyRemoteSinkSetUp|start notify remote screen")),
    ("setup-result", re.compile(r"NotifyRemoteSourceSetUpResult|HandleNotifySetUpResult")),
    ("sink-setup", re.compile(r"DScreenNotify|HandleNotifySetUp,|ScreenRegion::SetUp|ScreenRegion::Start")),
    ("sink-trans-ready", re.compile(r"ScreenSinkTrans: SetUp success|ImageSinkProcessor: SetImageSurface|ImageSinkDecoder: StartDecoder|InitHeartBeatProcesser")),
    ("source-connect", re.compile(r"HandleConnect|DScreen SetUp success|SetImageSurface for virtualscreen")),
    ("softbus-open", re.compile(r"OpenSession, peerDevId|CreateSession, peerDevId|OpenSoftbusSession")),
    ("session-open", re.compile(r"OnScreenSessionOpened|OnChannelSessionOpened")),
    (
        "source-encoder",
        re.compile(
            r"ImageSourceProcessor: StartImageProcessor|ImageSourceEncoder: StartEncoder|"
            r"ImageEncoderCallback: OnOutputBufferAvailable|"
            r"ImageSourceEncoder: OnOutputBufferAvailable"
        ),
    ),
    ("heartbeat", re.compile(r"\bHeartBeat\b|heartbeat_timeout|Send heartbeat|ASK_SOURCE_IF_ONLINE|SOURCE_ONLINE_ACK|StopHeartBeatProcesser")),
    ("source-send", re.compile(r"SendFullData|SendDirtyData|FeedChannelData")),
    ("sink-recv", re.compile(r"OnStreamReceived|ProcessDullData|ProcessDirtyData|ProcessImage")),
    (
        "sink-decode",
        re.compile(
            r"ImageSinkDecoder: InputScreenData|ImageSinkDecoder: OnDecodeOutputBufferAvailable|"
            r"ImageSinkDecoder: ProcessData|ImageSinkDecoder: StartInputThread"
        ),
    ),
    ("dhcommon-state", re.compile(r"OnDscreenChange|NOTIFY_STATE_START|NOTIFY_STATE_STOP|NOTIFY_STATE_STOP_BY_USER|STOP_BY_USER")),
    ("source-remove-group", re.compile(r"RemoveFromGroup|RemoveScreenFromGroup")),
    ("source-disconnect", re.compile(r"HandleDisconnect|ScreenSourceTrans: Stop\.|StopEncoder")),
    ("session-close-request", re.compile(r"CloseSession, sessionId")),
    ("session-close", re.compile(r"OnSessionClosed|OnScreenSessionClosed|Close session success")),
    ("release", re.compile(r"ReleaseSession|Release success")),
    ("sink-stop", re.compile(r"ScreenRegion::Stop|StopDecoder")),
    ("disable-offline", re.compile(r"HandleDisable|DestroyVirtualScreen|RemoveVirtualScreen|DisableTask|OffLineTask")),
]
STAGE_ORDER = {stage: index for index, (stage, _) in enumerate(STAGE_PATTERNS)}


@dataclass(order=True)
class Event:
    ts: datetime
    file_name: str
    line_no: int
    tag: str
    stage: str
    line: str


def format_timestamp(ts: datetime) -> str:
    return ts.strftime("%m-%d %H:%M:%S.%f")[:-3]


def parse_timestamp(line: str) -> datetime | None:
    match = TIME_RE.match(line)
    if match is None:
        return None
    millis = int(match.group("millis") or "0")
    return datetime(
        year=2000,
        month=int(match.group("month")),
        day=int(match.group("day")),
        hour=int(match.group("hour")),
        minute=int(match.group("minute")),
        second=int(match.group("second")),
        microsecond=millis * 1000,
    )


def parse_focus(raw: str, default_date: datetime) -> datetime | None:
    formats = [
        ("%m-%d %H:%M:%S.%f", True),
        ("%m-%d %H:%M:%S", True),
        ("%H:%M:%S.%f", False),
        ("%H:%M:%S", False),
    ]
    for fmt, has_date in formats:
        try:
            parsed = datetime.strptime(raw, fmt)
        except ValueError:
            continue
        if has_date:
            return parsed.replace(year=2000)
        return default_date.replace(
            hour=parsed.hour,
            minute=parsed.minute,
            second=parsed.second,
            microsecond=parsed.microsecond,
        )
    return None


def classify_stage(line: str) -> str | None:
    for stage, pattern in STAGE_PATTERNS:
        if pattern.search(line):
            return stage
    return None


def iter_events(paths: Iterable[Path], include_unclassified: bool) -> list[Event]:
    events: list[Event] = []
    for path in paths:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_no, raw_line in enumerate(handle, start=1):
                line = raw_line.rstrip("\n")
                ts = parse_timestamp(line)
                if ts is None:
                    continue
                stage = classify_stage(line)
                tag_match = TAG_RE.search(line)
                tag = tag_match.group(1) if tag_match else "-"
                if stage is None and not include_unclassified:
                    continue
                if stage is None and tag == "-":
                    continue
                events.append(
                    Event(
                        ts=ts,
                        file_name=path.name,
                        line_no=line_no,
                        tag=tag,
                        stage=stage or "unclassified",
                        line=line,
                    )
                )
    events.sort()
    return events


def summarize_events(events: Iterable[Event], gap_seconds: float) -> list[str]:
    grouped: dict[tuple[str, str], list[Event]] = defaultdict(list)
    for event in events:
        grouped[(event.file_name, event.stage)].append(event)

    burst_groups: list[list[Event]] = []
    gap = timedelta(seconds=gap_seconds)
    for bucket in grouped.values():
        bucket.sort()
        current_group: list[Event] = []
        for event in bucket:
            if not current_group:
                current_group = [event]
                continue
            if event.ts - current_group[-1].ts <= gap:
                current_group.append(event)
                continue
            burst_groups.append(current_group)
            current_group = [event]
        if current_group:
            burst_groups.append(current_group)

    burst_groups.sort(
        key=lambda items: (
            items[0].ts,
            STAGE_ORDER.get(items[0].stage, len(STAGE_ORDER)),
            items[0].file_name,
            items[0].line_no,
        )
    )

    lines: list[str] = []
    for group in burst_groups:
        first = group[0]
        last = group[-1]
        extra = ""
        if len(group) > 1:
            extra = f" [count={len(group)}, last={format_timestamp(last.ts)} #{last.line_no}]"
        lines.append(
            f"{format_timestamp(first.ts)} | {first.file_name:<16} | {first.tag:<15} | "
            f"{first.stage:<22} | {len(group):>5} | {first.line_no:>5} | {first.line}{extra}"
        )
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs="+", help="Log files to scan")
    parser.add_argument("--focus", help="Focus time, e.g. 01-30 16:46:32.450 or 16:46:32")
    parser.add_argument("--window", type=float, default=5.0, help="Seconds around --focus")
    parser.add_argument(
        "--include-unclassified",
        action="store_true",
        help="Include tag-matched lines that were not mapped to a stage",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Collapse repeated events into stage bursts for quick comparison",
    )
    parser.add_argument(
        "--summary-gap",
        type=float,
        default=1.0,
        help="Split summary bursts when the same stage on the same file is separated by more than this many seconds",
    )
    args = parser.parse_args()

    paths = [Path(item) for item in args.logs]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        for item in missing:
            print(f"[ERROR] file not found: {item}", file=sys.stderr)
        return 1

    events = iter_events(paths, args.include_unclassified)
    if not events:
        print("No matching events found.")
        return 0

    if args.focus:
        focus = parse_focus(args.focus, events[0].ts)
        if focus is None:
            print(f"[ERROR] invalid focus time: {args.focus}", file=sys.stderr)
            return 1
        delta = timedelta(seconds=args.window)
        start = focus - delta
        end = focus + delta
        events = [event for event in events if start <= event.ts <= end]

    if not events:
        print("No events matched the requested window.")
        return 0

    if args.summary:
        for line in summarize_events(events, args.summary_gap):
            print(line)
        return 0

    for event in events:
        print(
            f"{format_timestamp(event.ts)} | {event.file_name:<16} | {event.tag:<15} | "
            f"{event.stage:<22} | {event.line_no:>5} | {event.line}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
