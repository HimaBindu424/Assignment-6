"""Run Assignment 6 capabilities against the local mock inbox."""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
INBOX_FILE = PROJECT_ROOT / "inbox.json"
DECISIONS_FILE = PROJECT_ROOT / "decisions.json"
TRACE_FILE = PROJECT_ROOT / "trace.jsonl"
DRAFT_FILE = PROJECT_ROOT / "draft.json"

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


def load_inbox():
    with INBOX_FILE.open("r", encoding="utf-8") as inbox_file:
        messages = json.load(inbox_file)
    if not isinstance(messages, list):
        raise ValueError("inbox.json must contain a JSON array")
    return messages


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cap", required=True, choices=["R1", "R2"])
    parser.add_argument("--msg", help="Message ID required for R2")
    args = parser.parse_args()
    if args.cap == "R1":
        run_r1()
    elif not args.msg:
        parser.error("--msg is required for R2")
    else:
        run_r2(args.msg)


if __name__ == "__main__":
    main()
