"""Renders a `digest.DailyOverview` as the Daily Overview email.

Pure string building -- the `/daily-overview` skill passes the result to
the Gmail connector's `send_message` (`htmlBody` + plain-text `body`).
Every item links straight to the page where the user acts on it (the
assignment, its feedback, the announcement, the submit page) so the email
replaces opening the course shell. See CLAUDE.md invariant 38.

Inline styles only (Gmail strips <style> blocks), small and readable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from html import escape
from typing import Any

from academic_sync.digest import DailyOverview, DeadlineLine

_H3 = (
    'style="margin:18px 0 6px;font-size:15px;color:#1f2937;'
    'border-bottom:1px solid #e5e7eb;padding-bottom:3px"'
)
_MUTED = 'style="color:#6b7280"'


@dataclass
class EmailMessage:
    subject: str
    html: str
    text: str


def email_subject(course_code: str) -> str:
    return f"Daily Overview {course_code}"


def _a(url: str | None, label: str) -> str:
    safe = escape(label)
    return f'<a href="{escape(url, quote=True)}">{safe}</a>' if url else safe


def _fmt_time(t: time | None) -> str:
    if t is None:
        return ""
    hour = t.hour % 12 or 12
    return f"{hour}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"


def _grade_line(o: DailyOverview) -> tuple[str, str]:
    if o.overall_percent is None:
        value = "not posted"
    else:
        value = f"{o.overall_percent:g}%"
        if o.letter_grade:
            value += f" ({o.letter_grade})"
    trend = ""
    if o.trend_points is not None and o.trend_since is not None:
        if abs(o.trend_points) < 0.05:
            trend = f"no change since {o.trend_since.strftime('%b')} {o.trend_since.day}"
        else:
            sign = "+" if o.trend_points > 0 else "−"
            trend = (f"{sign}{abs(o.trend_points):.1f} since "
                     f"{o.trend_since.strftime('%b')} {o.trend_since.day}")
    html = f'<p style="font-size:18px;margin:4px 0 2px"><b>Current grade: {escape(value)}</b>'
    if trend:
        html += f' <span {_MUTED}>({escape(trend)})</span>'
    html += "</p>"
    text = f"Current grade: {value}" + (f" ({trend})" if trend else "")
    return html, text


def _deadline_html(d: DeadlineLine, *, missed: bool) -> str:
    when = _fmt_time(d.due_time)
    line = f"<b>{_a(d.url, d.title)}</b>"
    if when and not missed:
        line += f" — due {when}"
    if missed:
        if d.submitted is None:
            line += f' <span {_MUTED}>— submission not confirmed</span>'
        elif d.window_open is True:
            line += " — still open, " + _a(d.url, "submit now")
        elif d.window_open is False:
            line += f' <span {_MUTED}>— closed</span>'
    return f"<li>{line}</li>"


def _deadline_text(d: DeadlineLine, *, missed: bool) -> str:
    out = f"- {d.title}"
    if d.due_time and not missed:
        out += f" (due {_fmt_time(d.due_time)})"
    if missed:
        if d.submitted is None:
            out += " — submission not confirmed"
        elif d.window_open is True:
            out += " — still open"
        elif d.window_open is False:
            out += " — closed"
    if d.url:
        out += f" {d.url}"
    return out


def _graded_html(g: dict[str, Any]) -> str:
    title = g.get("title") or "Graded item"
    score = g.get("score_text") or (
        f"{g['score_percent']:g}%" if g.get("score_percent") is not None else "graded"
    )
    if g.get("score_text") and g.get("score_percent") is not None:
        score = f"{g['score_percent']:g}% ({g['score_text']})"
    head = f"<b>{_a(g.get('item_url'), title)} — {escape(str(score))}</b>"
    if g.get("is_update"):
        head += f' <span {_MUTED}>(updated)</span>'
    parts = [head]
    if g.get("comment"):
        parts.append(f'<span style="color:#374151">“{escape(g["comment"])}”</span>')
    if g.get("feedback_url"):
        parts.append(_a(g["feedback_url"], "Open feedback"))
    return '<p style="margin:6px 0">' + "<br>".join(parts) + "</p>"


def _announcement_html(a: dict[str, Any]) -> str:
    head = f"<b>{_a(a.get('url'), a.get('title') or 'Announcement')}</b>"
    if a.get("posted_on"):
        head += f' <span {_MUTED}>({escape(a["posted_on"])})</span>'
    if a.get("is_update"):
        head += f' <span {_MUTED}>(edited)</span>'
    lines = [head] + [f"• {escape(h)}" for h in a.get("highlights") or []]
    return '<p style="margin:6px 0">' + "<br>".join(lines) + "</p>"


def _line_html(entry: dict[str, Any]) -> str:
    return f"<li>{_a(entry.get('url'), entry.get('text') or '')}</li>"


def build_daily_overview_email(o: DailyOverview) -> EmailMessage:
    """Order: grade line -> needs attention -> newly graded -> new
    announcements -> missed yesterday -> due today -> coming up -> calendar
    updates -> needs you -> portal footer. Sections with nothing in them
    are omitted, never padded."""
    html: list[str] = [
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;'
        'line-height:1.45;color:#111827;max-width:640px">',
        f'<h2 style="margin:0 0 2px;font-size:20px">{escape(o.course_code)} — '
        f'{escape(o.course_name)}</h2>',
    ]
    text: list[str] = [f"{o.course_code} — {o.course_name}"]

    grade_html, grade_text = _grade_line(o)
    html.append(grade_html)
    text.append(grade_text)
    if o.advice:
        html.append(f'<p style="margin:2px 0 0"><i>Advice: {escape(o.advice)}</i></p>')
        text.append(f"Advice: {o.advice}")

    if o.login_failed:
        msg = ("D2L needs you to sign in, so this morning's announcements and grades weren't "
               "checked. Deadlines below come from your saved calendar data; sign in once and "
               "tomorrow's email catches up.")
        home = next((url for label, url in o.portal_links if label.lower() in ("home", "course home")),
                    None)
        link = f" {_a(home, 'Open D2L')}" if home else ""
        html.append(f'<p style="background:#fef3c7;padding:8px;border-radius:4px">⚠ {msg}{link}</p>')
        text.append(f"!! {msg}" + (f" {home}" if home else ""))

    def section(title: str, body: list[str], body_text: list[str], as_list: bool = False) -> None:
        if not body:
            return
        html.append(f"<h3 {_H3}>{escape(title)}</h3>")
        html.append("<ul style=\"margin:4px 0;padding-left:20px\">" + "".join(body) + "</ul>"
                    if as_list else "".join(body))
        text.append("")
        text.append(title.upper())
        text.extend(body_text)

    section("Needs attention", [_line_html(e) for e in o.attention],
            [f"- {e.get('text')}" for e in o.attention], as_list=True)
    section(
        "Newly graded", [_graded_html(g) for g in o.graded],
        [
            f"- {g.get('title')}: "
            f"{g.get('score_text') or g.get('score_percent')}"
            + (f' — "{g["comment"]}"' if g.get("comment") else "")
            + (f" {g['feedback_url']}" if g.get("feedback_url") else "")
            for g in o.graded
        ],
    )
    section("New announcements", [_announcement_html(a) for a in o.announcements],
            [f"- {a.get('title')} {a.get('url') or ''}".rstrip() for a in o.announcements])
    section("Missed yesterday", [_deadline_html(d, missed=True) for d in o.missed_yesterday],
            [_deadline_text(d, missed=True) for d in o.missed_yesterday], as_list=True)
    section("Due today", [_deadline_html(d, missed=False) for d in o.due_today],
            [_deadline_text(d, missed=False) for d in o.due_today], as_list=True)
    if o.upcoming:
        up_html = [
            f"<li>{_a(d.url, d.title)} <span {_MUTED}>— "
            f"{d.due_on.strftime('%a')} {d.due_on.strftime('%b')} {d.due_on.day}"
            f"{' ' + _fmt_time(d.due_time) if d.due_time else ''}</span></li>"
            for d in o.upcoming
        ]
        section("Coming up", up_html,
                [f"- {d.title} ({d.due_on.isoformat()}) {d.url or ''}".rstrip() for d in o.upcoming],
                as_list=True)
    section("Calendar updated", [_line_html(e) for e in o.calendar_changes],
            [f"- {e.get('text')}" for e in o.calendar_changes], as_list=True)
    section("Needs you", [_line_html(e) for e in o.needs_you],
            [f"- {e.get('text')} {e.get('url') or ''}".rstrip() for e in o.needs_you], as_list=True)

    if o.portal_links:
        html.append('<p style="margin-top:20px;font-size:12px;color:#6b7280">'
                    + " · ".join(_a(url, label) for label, url in o.portal_links) + "</p>")
    html.append("</div>")
    return EmailMessage(subject=email_subject(o.course_code), html="".join(html),
                        text="\n".join(text))
