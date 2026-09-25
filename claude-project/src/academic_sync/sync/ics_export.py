"""RFC 5545 (.ics) export of already-built Calendar payloads.

Lets a course (typically a synthetic one -- CLAUDE.md invariant 35) be
shared as a file anyone can import into Google Calendar, instead of being
written straight to one person's calendar. Takes the exact payload dicts
`build_event_payload` produces (the single source of truth for titles,
descriptions, and dates) and only re-encodes them -- no second formatting
path.

Guarantees:
- `UID` is the item's fingerprint, so re-importing a re-exported file
  updates events instead of duplicating them;
- never emits ATTENDEE, ORGANIZER, or conference data (CLAUDE.md invariant 4);
- deterministic output for identical input (stable ordering, DTSTAMP pinned
  to a caller-given instant), so re-exports diff cleanly;
- timed events are converted to UTC (`...Z`), so no VTIMEZONE is needed.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from dateutil.zoneinfo import get_zonefile_instance

_FOLD_OCTETS = 75


@dataclass(frozen=True)
class IcsEvent:
    uid: str
    payload: dict[str, Any]


def _escape_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """Fold a content line at 75 octets (RFC 5545 §3.1), never splitting a
    UTF-8 multi-byte character."""
    out: list[str] = []
    current = ""
    current_len = 0
    limit = _FOLD_OCTETS
    for ch in line:
        ch_len = len(ch.encode("utf-8"))
        if current_len + ch_len > limit:
            out.append(current)
            current = " " + ch
            current_len = 1 + ch_len
            limit = _FOLD_OCTETS
        else:
            current += ch
            current_len += ch_len
    out.append(current)
    return "\r\n".join(out)


def html_to_text(description: str) -> str:
    """Plain-text rendering of this project's description HTML (`<b>`,
    `<br>`, `<a href>`, `<i>`, `<small>`) for the ICS DESCRIPTION property.
    Links become `Label (URL)` so nothing clickable is lost."""
    text = re.sub(r'<a href="([^"]+)">([^<]*)</a>', r"\2 (\1)", description)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def _date_value(iso_date: str) -> str:
    return iso_date.replace("-", "")


def _utc_value(date_time: str, tz_name: str) -> str:
    tz = get_zonefile_instance().get(tz_name)
    if tz is None:
        raise ValueError(f"Unknown time zone: {tz_name}")
    local = datetime.fromisoformat(date_time).replace(tzinfo=tz)
    return local.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _time_lines(prop: str, when: dict[str, Any]) -> str:
    if "date" in when:
        return f"{prop};VALUE=DATE:{_date_value(when['date'])}"
    return f"{prop}:{_utc_value(when['dateTime'], when['timeZone'])}"


def _sort_key(event: IcsEvent) -> tuple[str, str]:
    start = event.payload["start"]
    return (start.get("date") or start.get("dateTime", ""), event.uid)


def build_ics(calendar_name: str, events: list[IcsEvent], *, dtstamp: datetime) -> str:
    """One VCALENDAR with one VEVENT per payload. `dtstamp` should be a
    stable instant (e.g. the course start) so identical input always yields
    byte-identical output."""
    stamp = dtstamp.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//study-prompt-system//academic-sync//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape_text(calendar_name)}",
    ]
    for event in sorted(events, key=_sort_key):
        payload = event.payload
        description_html = payload.get("description", "")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{event.uid}",
            f"DTSTAMP:{stamp}",
            _time_lines("DTSTART", payload["start"]),
            _time_lines("DTEND", payload["end"]),
            f"SUMMARY:{_escape_text(payload['summary'])}",
            f"DESCRIPTION:{_escape_text(html_to_text(description_html))}",
            f"X-ALT-DESC;FMTTYPE=text/html:{_escape_text(description_html)}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
        if payload.get("location"):
            lines.insert(len(lines) - 2, f"LOCATION:{_escape_text(payload['location'])}")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
