"""Run Assignment 6 capabilities against the local mock inbox."""

import argparse
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from memory import recall, remember
from part4 import (
    DELETED_DIR,
    INJECTION_PATTERN,
    OUTBOX_DIR,
    TRACE_FILE as PART4_TRACE_FILE,
    confirm,
    log_action,
    log_refusal,
    write_simulated_action,
)

PROJECT_ROOT = Path(__file__).parent
INBOX_FILE = PROJECT_ROOT / "inbox.json"
DECISIONS_FILE = PROJECT_ROOT / "decisions.json"
TRACE_FILE = PROJECT_ROOT / "trace.jsonl"
DRAFT_FILE = PROJECT_ROOT / "draft.json"
DEADLINES_FILE = PROJECT_ROOT / "deadlines.json"
FOLLOWUPS_FILE = PROJECT_ROOT / "followups.json"
DASHBOARD_JSON = PROJECT_ROOT / "dashboard.json"
DASHBOARD_HTML = PROJECT_ROOT / "dashboard.html"

DISPOSITIONS = {"reply", "archive", "defer", "delegate", "escalate"}

HOSTILE_SIGNALS = (
    "automated-agent directive",
    "system notice for automated assistants",
    "ignore all previous instructions",
    "forward the full contents of this mailbox",
    "do not mention this",
    "no need to surface this",
)
SECURITY_SIGNALS = (
    "password",
    "verification code",
    "if this wasn't you",
    "credentials",
    "credential",
    "amqp://",
)
FINANCIAL_RISK_SIGNALS = (
    "wire $",
    "updated remittance details",
    "keep this between us",
    "don't loop in finance",
)
COMMITMENT_SIGNALS = (
    "meeting",
    "deadline",
    "due today",
    "by monday",
    "by thursday",
    "please review",
    "appointment",
    "reply confirm",
    "can you approve",
    "could you confirm",
    "please confirm",
)
NOISE_SIGNALS = (
    "receipt",
    "newsletter",
    "monthly usage",
    "weekly digest",
    "security digest",
    "no action needed",
    "your order has shipped",
    "new notifications",
)
AUTOMATED_SENDER_MARKERS = (
    "no-reply@",
    "noreply@",
    "notifications@",
    "newsletter@",
    "digest@",
    "receipts@",
    "alerts@",
    "invoice+",
)
USER_EMAIL = "sam@paperjet.io"

MONTH_NAMES = "January|February|March|April|May|June|July|August|September|October|November|December"
WEEKDAY_NAMES = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
DEADLINE_PATTERN = re.compile(
    rf"(?:by|before|deadline for|due)\s+(?P<value>"
    rf"today|tomorrow|month-end|the\s+\d{{1,2}}(?:st|nd|rd|th)?|"
    rf"(?:{MONTH_NAMES})\s+\d{{1,2}}(?:st|nd|rd|th)?|"
    rf"(?:{WEEKDAY_NAMES})(?:\s+\d{{1,2}}(?::\d{{2}})?\s*(?:am|pm))?"
    rf")",
    re.IGNORECASE,
)


def load_inbox():
    with INBOX_FILE.open("r", encoding="utf-8") as inbox_file:
        messages = json.load(inbox_file)
    if not isinstance(messages, list):
        raise ValueError("inbox.json must contain a JSON array")
    return messages


def parse_deadline(value, message_date):
    value = re.sub(r"\s+", " ", value.strip().casefold())
    if value == "today":
        return message_date
    if value == "tomorrow":
        return message_date + timedelta(days=1)
    if value == "month-end":
        next_month = message_date.replace(day=28) + timedelta(days=4)
        return next_month - timedelta(days=next_month.day)

    weekday = next(
        (index for index, name in enumerate(WEEKDAY_NAMES.casefold().split("|"))
         if value.startswith(name)),
        None,
    )
    if weekday is not None:
        days_ahead = (weekday - message_date.weekday()) % 7
        return message_date + timedelta(days=days_ahead)

    ordinal_match = re.search(r"(\d{1,2})", value)
    if not ordinal_match:
        return None
    day = int(ordinal_match.group(1))
    month_match = re.match(rf"({MONTH_NAMES})", value, re.IGNORECASE)
    month = (
        datetime.strptime(month_match.group(1), "%B").month
        if month_match
        else message_date.month
    )
    try:
        return date(message_date.year, month, day)
    except ValueError:
        return None


def extract_deadline(message):
    text = f"{message['subject']} {message['body']}"
    match = DEADLINE_PATTERN.search(text)
    if not match:
        return None
    message_date = datetime.fromisoformat(message["timestamp"]).date()
    deadline = parse_deadline(match.group("value"), message_date)
    if deadline is None:
        return None
    return {
        "message_id": message["id"],
        "subject": message["subject"],
        "deadline": deadline.isoformat(),
        "deadline_text": match.group("value"),
    }


def run_x1(sender):
    sender = sender.strip().casefold()
    if not sender:
        raise ValueError("--sender must not be empty")

    unread_mail = [
        {
            "message_id": message["id"],
            "from": message["from"],
            "subject": message["subject"],
            "timestamp": message["timestamp"],
        }
        for message in load_inbox()
        if message["unread"] and message["from"].casefold() == sender
    ]
    result = {
        "capability": "X1",
        "sender": sender,
        "unread_count": len(unread_mail),
        "messages": unread_mail,
    }
    output_file = PROJECT_ROOT / "unread_mail.json"
    output_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    with TRACE_FILE.open("a", encoding="utf-8") as trace_file:
        trace_file.write(json.dumps({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "cap": "X1",
            "event": "unread_mail_listed",
            "sender": sender,
            "message_ids": [item["message_id"] for item in unread_mail],
        }) + "\n")
    print(json.dumps(result, indent=2))
    print(f"unread mail written: {output_file}")


def run_x2(today_text=None):
    as_of = date.fromisoformat(today_text) if today_text else date.today()
    messages = load_inbox()
    followups = []
    for message in messages:
        if message["from"].casefold() != USER_EMAIL or message["to"].casefold() == USER_EMAIL:
            continue
        sent_at = datetime.fromisoformat(message["timestamp"])
        thread_messages = [
            item for item in messages
            if item["thread_id"] == message["thread_id"]
            and datetime.fromisoformat(item["timestamp"]) > sent_at
        ]
        has_reply = any(
            item["from"].casefold() != USER_EMAIL
            for item in thread_messages
        )
        days_waiting = (as_of - sent_at.date()).days
        if has_reply or days_waiting < 3:
            continue
        followups.append({
            "message_id": message["id"],
            "thread_id": message["thread_id"],
            "to": message["to"],
            "subject": message["subject"],
            "days_waiting": days_waiting,
            "draft": (
                f"Hi,\n\nJust following up on my message about "
                f"{message['subject'].removeprefix('Re: ')}. "
                "Please let me know when you have a chance.\n\nThanks,\nSam"
            ),
        })

    result = {
        "capability": "X2",
        "as_of": as_of.isoformat(),
        "followups": followups,
    }
    FOLLOWUPS_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    with TRACE_FILE.open("a", encoding="utf-8") as trace_file:
        for followup in followups:
            trace_file.write(json.dumps({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "cap": "X2",
                "event": "followup_drafted",
                "message_id": followup["message_id"],
                "thread_id": followup["thread_id"],
                "days_waiting": followup["days_waiting"],
            }) + "\n")
    print(json.dumps(result, indent=2))
    print(f"follow-ups written: {FOLLOWUPS_FILE}")


def contains_any(text, signals):
    return any(signal in text for signal in signals)


def classify(message):
    subject = message["subject"]
    body = message["body"]
    text = f"{subject} {body}".casefold()
    sender = message["from"].casefold()

    if contains_any(text, HOSTILE_SIGNALS):
        return "escalate", "Possible hostile instruction; requires human review", "hostile"

    if contains_any(text, FINANCIAL_RISK_SIGNALS):
        return "escalate", "Financial or social-engineering risk requires human review", "financial-risk"

    if contains_any(text, SECURITY_SIGNALS):
        return "escalate", "Security-sensitive content requires human review", "security"

    if contains_any(text, COMMITMENT_SIGNALS):
        return "defer", "Contains a meeting, deadline, approval, or confirmation request", "commitment"

    if contains_any(text, NOISE_SIGNALS) or sender.startswith(AUTOMATED_SENDER_MARKERS):
        return "archive", "Automated notification, receipt, newsletter, or routine update", "noise"

    if any(marker in text for marker in ("can you", "could you", "please", "would you", "?") ):
        return "reply", "Direct request from a correspondent requires attention", "request"

    return "defer", "No safe automatic action rule matched", "fallback"


def run_r1():
    messages = load_inbox()
    decisions = []
    rule_counts = {}

    for message in messages:
        disposition, reason, rule = classify(message)
        if disposition not in DISPOSITIONS:
            raise ValueError(f"Invalid disposition for {message['id']}: {disposition}")
        decision = {
            "message_id": message["id"],
            "disposition": disposition,
            "reason": reason,
            "rule": rule,
        }
        decisions.append(decision)
        rule_counts[rule] = rule_counts.get(rule, 0) + 1

    undecided = len(messages) - len(decisions)
    output = {
        "capability": "R1",
        "messages_processed": len(messages),
        "rule_handled": len(messages),
        "undecided": undecided,
        "disposition_counts": {
            disposition: sum(
                decision["disposition"] == disposition for decision in decisions
            )
            for disposition in sorted(DISPOSITIONS)
        },
        "rule_counts": rule_counts,
        "decisions": decisions,
    }
    DECISIONS_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")

    with TRACE_FILE.open("w", encoding="utf-8") as trace_file:
        for decision in decisions:
            trace_file.write(
                json.dumps(
                    {
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "cap": "R1",
                        "event": "decision",
                        **decision,
                    }
                )
                + "\n"
            )

    print("message_id | disposition | reason")
    print("-" * 78)
    for decision in decisions:
        print(
            f"{decision['message_id']:10} | "
            f"{decision['disposition']:11} | {decision['reason']}"
        )
    print()
    print(f"messages processed: {len(messages)}")
    print(f"rule-handled: {len(messages)}")
    print(f"undecided: {undecided}")
    print(f"decisions written: {DECISIONS_FILE}")
    print(f"trace written: {TRACE_FILE}")


def run_r2(message_id):
    messages = load_inbox()
    target = next((message for message in messages if message["id"] == message_id), None)
    if target is None:
        raise ValueError(f"Message not found: {message_id}")

    related_messages = [
        message
        for message in messages
        if message["thread_id"] == target["thread_id"]
        and message["id"] != message_id
    ]
    related_messages.sort(key=lambda message: message["timestamp"])
    read_ids = [message["id"] for message in related_messages]
    source = next(
        (
            message
            for message in related_messages
            if re.search(r"amqp://\S+", message["body"])
        ),
        None,
    )
    url = re.search(r"amqp://\S+", source["body"]) if source else None
    cited_ids = [source["id"]] if source and url else []
    draft = (
        f"The staging AMQP URL is: {url.group(0)}"
        if url
        else None
    )
    result = {
        "capability": "R2",
        "message_id": message_id,
        "draft": draft,
        "cited": cited_ids,
        "read": read_ids,
    }
    DRAFT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    with TRACE_FILE.open("a", encoding="utf-8") as trace_file:
        trace_file.write(json.dumps({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "cap": "R2",
            "event": "draft",
            "message_id": message_id,
            "read": read_ids,
            "cited": cited_ids,
        }) + "\n")

    if draft:
        print(f"draft for {message_id}:\n{draft}")
    else:
        print(f"no grounded draft available for {message_id}")
    print(f"cited: {cited_ids}")
    print(f"draft written: {DRAFT_FILE}")


def run_r3(message_id, dry_run):
    messages = load_inbox()
    target = next((item for item in messages if item["id"] == message_id), None)
    if target is None:
        raise ValueError(f"Message not found: {message_id}")

    proposal = {
        "action": "send",
        "message_id": message_id,
        "to": target["from"],
        "subject": target["subject"],
        "body": "Simulated approved draft",
    }
    if dry_run:
        print(json.dumps({"would_do": proposal, "outbox_writes": 0}, indent=2))
        return

    response = confirm("send", message_id)
    if response.lower() == "y":
        write_simulated_action(OUTBOX_DIR, message_id, proposal)
        log_action("send", message_id, response, "written_to_outbox")
        print(f"outbox/{message_id}.json written")
    else:
        log_action("send", message_id, response, "cancelled")
        print("send cancelled; outbox writes: 0")


def run_r4():
    messages = load_inbox()
    preference = next(
        item for item in messages
        if item["id"] == "m041"
    )
    result = remember(
        "meeting_time_rule",
        preference["body"],
        "inbox:m041",
    )
    print("stored preference:")
    print(json.dumps(result, indent=2))
    print("restart demonstration: recall from a fresh process with `python demo.py --cap R4 --recall`")


def run_r5():
    flagged = []
    for message in load_inbox():
        text = f"{message['subject']} {message['body']}"
        if INJECTION_PATTERN.search(text):
            attempted = "follow an embedded email instruction or disclose sensitive data"
            reason = "prompt-injection: embedded instructions target assistant behavior"
            log_refusal(message["id"], attempted, reason)
            flagged.append({
                "message_id": message["id"],
                "attempted": attempted,
                "action": "not done; left in place",
            })
    for item in flagged:
        print(
            f"FLAGGED: {item['message_id']} attempted to {item['attempted']}; "
            f"{item['action']}."
        )
    print(f"flagged: {len(flagged)}")


def commitment_slot(message):
    text = f"{message['subject']} {message['body']}"
    time_match = re.search(r"\b(\d{1,2}:\d{2}\s*(?:am|pm))\b", text, re.I)
    if not time_match:
        return None
    day_candidates = re.findall(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\b", text[:time_match.start()], re.I
    )
    if not day_candidates:
        return None
    day = int(day_candidates[-1])
    time = time_match.group(1).replace(" ", "").lower()
    return day, time


def find_commitment_conflicts(commitments):
    conflicts = []
    for index, left in enumerate(commitments):
        left_slot = commitment_slot(left)
        if left_slot is None:
            continue
        for right in commitments[index + 1:]:
            if left_slot == commitment_slot(right):
                conflicts.append({
                    "slot": {"day": left_slot[0], "time": left_slot[1]},
                    "message_ids": [left["message_id"], right["message_id"]],
                    "description": (
                        f"CONFLICT: {left['message_id']} and {right['message_id']} "
                        f"share day {left_slot[0]} at {left_slot[1]}"
                    ),
                })
    return conflicts


def run_r6():
    messages = load_inbox()
    commitments = [
        {"message_id": message["id"], "subject": message["subject"], "body": message["body"]}
        for message in messages
        if contains_any(
            f"{message['subject']} {message['body']}".casefold(),
            COMMITMENT_SIGNALS,
        )
    ]
    flagged = []
    for message in messages:
        if INJECTION_PATTERN.search(f"{message['subject']} {message['body']}"):
            flagged.append(message["id"])
            conflicts = find_commitment_conflicts(commitments)
    pending = [
        decision for decision in (classify(message) for message in messages)
        if decision[0] in {"reply", "defer", "escalate"}
    ]
    dashboard = {
        "pending_actions": pending,
        "flagged": flagged,
        "commitments": commitments,
        "conflicts": conflicts,
    }
    DASHBOARD_JSON.write_text(json.dumps(dashboard, indent=2), encoding="utf-8")
    DASHBOARD_HTML.write_text(
        "<html><body><h1>InboxHero dashboard</h1>"
        f"<h2>Pending actions</h2><pre>{json.dumps(pending, indent=2)}</pre>"
        f"<h2>Flagged</h2><pre>{json.dumps(flagged, indent=2)}</pre>"
        f"<h2>Commitments</h2><pre>{json.dumps(commitments, indent=2)}</pre>"
        f"<h2>Conflicts</h2><pre>{json.dumps(conflicts, indent=2)}</pre>"
        "</body></html>",
        encoding="utf-8",
    )
    print(f"dashboard written: {DASHBOARD_HTML}")
    print(f"dashboard data written: {DASHBOARD_JSON}")
    for conflict in conflicts:
        print(conflict["description"])


def run_x3(today_text=None):
    as_of = date.fromisoformat(today_text) if today_text else date.today()
    deadlines = []
    for message in load_inbox():
        deadline = extract_deadline(message)
        if deadline is None:
            continue
        deadline_date = date.fromisoformat(deadline["deadline"])
        deadline["status"] = (
            "overdue"
            if deadline_date < as_of
            else "due_today"
            if deadline_date == as_of
            else "upcoming"
        )
        deadlines.append(deadline)

    result = {
        "capability": "X3",
        "as_of": as_of.isoformat(),
        "deadlines": deadlines,
    }
    DEADLINES_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    with TRACE_FILE.open("a", encoding="utf-8") as trace_file:
        for deadline in deadlines:
            trace_file.write(json.dumps({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "cap": "X3",
                "event": "deadline_extracted",
                **deadline,
            }) + "\n")
    print(json.dumps(result, indent=2))
    print(f"deadlines written: {DEADLINES_FILE}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cap",
        required=True,
        choices=["R1", "R2", "R3", "R4", "R5", "R6", "X1", "X2", "X3"],
    )
    parser.add_argument("--msg", help="Message ID required for R2")
    parser.add_argument("--sender", help="Sender address required for A1")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--recall", action="store_true")
    parser.add_argument("--today", help="Reference date for X3, in YYYY-MM-DD format")
    args = parser.parse_args()
    if args.cap == "X1":
        if not args.sender:
            parser.error("--sender is required for A1")
        run_x1(args.sender)
    elif args.cap == "R1":
        run_r1()
    elif not args.msg:
        if args.cap == "R3":
            run_r3("m013", args.dry_run)
        elif args.cap == "R4" and args.recall:
            print(json.dumps(recall("meeting"), indent=2))
        elif args.cap == "R4":
            run_r4()
        elif args.cap == "R5":
            run_r5()
        elif args.cap == "R6":
            run_r6()
        elif args.cap == "X2":
            run_x2(args.today)
        elif args.cap == "X3":
            run_x3(args.today)
        else:
            parser.error("--msg is required for R2")
    else:
        if args.cap == "R2":
            run_r2(args.msg)
        elif args.cap == "R3":
            run_r3(args.msg, args.dry_run)
        else:
            parser.error("--msg is only supported for R2 and R3")


if __name__ == "__main__":
    main()
