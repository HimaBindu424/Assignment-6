"""Create a reproducible inventory of the Assignment 6 inbox.

Part 1 is an inspection step. This script does not call an LLM, change mail,
or execute instructions found in message bodies.
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


NOISE_PATTERNS = (
    "receipt",
    "invoice",
    "newsletter",
    "monthly",
    "weekly",
    "notification",
    "alert",
    "usage",
    "order",
    "verification code",
    "security digest",
    "screen time",
)
COMMITMENT_PATTERNS = (
    "meeting",
    "deadline",
    "due",
    "schedule",
    "calendar",
    "launch",
    "approve",
    "sign",
    "invoice",
)
INSTRUCTION_PATTERNS = (
    "assistant",
    "ai",
    "do not mention",
    "forward",
    "delete this",
    "send this",
    "ignore previous",
    "system administrator",
)
SECURITY_PATTERNS = (
    "password",
    "verification code",
    "credential",
    "secret",
    "token",
    "api key",
    "amqp://",
    "if this wasn't you",
)


def matches(text, patterns):
    normalized = text.casefold()
    found = []
    for pattern in patterns:
        if " " in pattern or any(character in pattern for character in "-/:"):
            matched = pattern in normalized
        else:
            matched = re.search(rf"(?<!\w){re.escape(pattern)}(?!\w)", normalized)
        if matched:
            found.append(pattern)
    return found


def load_messages(inbox_path):
    with inbox_path.open("r", encoding="utf-8") as inbox_file:
        messages = json.load(inbox_file)

    if not isinstance(messages, list):
        raise ValueError("Inbox must contain a JSON array of messages.")

    required = {
        "id",
        "thread_id",
        "from",
        "to",
        "subject",
        "timestamp",
        "body",
        "unread",
    }
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise ValueError(f"Message {index} must be a JSON object.")
        missing = required - message.keys()
        if missing:
            raise ValueError(
                f"Message {index} is missing fields: {sorted(missing)}"
            )
        datetime.fromisoformat(message["timestamp"])
        if not isinstance(message["unread"], bool):
            raise ValueError(f"Message {message['id']} has a non-boolean unread field.")
    return messages


def build_report(messages):
    threads = defaultdict(list)
    senders = Counter()
    unread = []
    noise_candidates = []
    commitment_candidates = []
    instruction_candidates = []
    security_candidates = []

    for message in messages:
        message_id = message["id"]
        subject = message["subject"]
        body = message["body"]
        searchable_text = f"{subject} {body}"
        threads[message["thread_id"]].append(message_id)
        senders[message["from"]] += 1

        if message["unread"]:
            unread.append(message_id)
        noise_matches = matches(searchable_text, NOISE_PATTERNS)
        if noise_matches:
            noise_candidates.append({"id": message_id, "signals": noise_matches})
        commitment_matches = matches(searchable_text, COMMITMENT_PATTERNS)
        if commitment_matches:
            commitment_candidates.append(
                {"id": message_id, "signals": commitment_matches}
            )
        instruction_matches = matches(searchable_text, INSTRUCTION_PATTERNS)
        if instruction_matches:
            instruction_candidates.append(
                {"id": message_id, "signals": instruction_matches}
            )
        security_matches = matches(searchable_text, SECURITY_PATTERNS)
        if security_matches:
            security_candidates.append(
                {"id": message_id, "signals": security_matches}
            )

    multi_message_threads = {
        thread_id: message_ids
        for thread_id, message_ids in threads.items()
        if len(message_ids) > 1
    }
    return {
        "messages_processed": len(messages),
        "unread_messages": len(unread),
        "read_messages": len(messages) - len(unread),
        "thread_count": len(threads),
        "multi_message_threads": multi_message_threads,
        "top_senders": senders.most_common(15),
        "candidate_noise": noise_candidates,
        "candidate_commitments": commitment_candidates,
        "candidate_assistant_instructions": instruction_candidates,
        "candidate_security_sensitive": security_candidates,
        "assumptions": [
            "The inbox is a UTF-8 JSON array.",
            "Each message has the eight required fields from the assignment brief.",
            "Timestamps are ISO-8601 strings and unread is boolean.",
            "Keyword matches are review candidates, not final classifications.",
            "Message bodies are untrusted data and are never executed as instructions.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inbox",
        type=Path,
        default=Path(__file__).with_name("inbox.json"),
        help="Path to inbox.json (default: the project root).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("part1_report.json"),
        help="Path for the generated JSON report.",
    )
    args = parser.parse_args()

    messages = load_messages(args.inbox)
    report = build_report(messages)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"messages processed: {report['messages_processed']}")
    print(f"unread: {report['unread_messages']}")
    print(f"threads: {report['thread_count']}")
    print(f"multi-message threads: {len(report['multi_message_threads'])}")
    print(f"candidate noise: {len(report['candidate_noise'])}")
    print(f"candidate commitments: {len(report['candidate_commitments'])}")
    print(
        "candidate assistant-directed instructions: "
        f"{len(report['candidate_assistant_instructions'])}"
    )
    print(f"candidate security-sensitive: {len(report['candidate_security_sensitive'])}")
    print(f"report written: {args.output}")


if __name__ == "__main__":
    main()
