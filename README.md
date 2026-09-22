**Student: M.HimaBindu
##GitHub Repo link : https://github.com/HimaBindu424/Assignment-6


Architecture:
====================
        This project is a Python pipeline that reads messages, classifies them, retrieves related thread context, and asks the model to draft replies. Email text is treated as data, while trusted Python code controls actions. Potentially dangerous messages are blocked or escalated, and sending requires human approval before writing to the outbox. The attacker would need to bypass the safety checks and the approval gate to make the system act for them .


## Design choices :
==========================

- Framework: None . The system is a python pipeline  with a linear workflow with simple tasks . so using a framework would be an overhead.
- Retrieval:  thread-walk.  An inbox already carries its own structure in
  `thread_id`, so walking the thread is both cheaper and more precise than
  embeddings for this task. Keyword search is the fallback for cross-thread lookups.
- Reversible vs irreversible.** R3 capability treats sending as an irreversible action and
    requires approval before writing to `outbox/`. Dry-run shows the proposal and
    writes nothing. 
- Where the gate sits:   `run_r3()` displays the model-generated proposal and
    calls `confirm()` before `write_simulated_action()` writes the message. The model
    cannot write to `outbox/` directly. 
- Escalation line: Prompt injection, financial risk, and selected messages that
    contain secrets are not automated. Related thread messages are available as
    context only up to the selected message's timestamp, and sensitive values are
    redacted before the model sees them.

Dispositions:
===========================
The system uses five dispositions: reply, archive, defer, delegate, and escalate. These describe the action or next step assigned to each message during inbox triage


Retrieval approach:
============================
The system uses thread-based retrieval, it finds messages with the same thread_id and includes only messages available up to the selected message’s timestamp, with sensitive values redacted before model processing

Part5 :

Persistent preference demonstration: 
=====================================

The system records the preference from m041 that Sam does not accept meetings before 11:00 AM. After the process exits and restarts, it retrieves this preference from memory.json and applies it to m043, which proposes a Monday meeting at 9:00 AM; the system therefore does not accept 9:00 AM and suggests a time at or after 11:00 AM

Part7 :
======================================
run the command "python demo.py --cap R6" to view the dashboard updated at dashboard.json/dashboard.html

Part8 :
======================================
run the command "python demo.py --cap X1 --sender raghav@paperjet.io" to list all unread
mail from one sender. The tracker writes unread_mail.json and records an
unread_mail_listed event in trace.jsonl. Sender matching is case-insensitive and an
empty result is returned when that sender has no unread messages.

run the command "python demo.py --cap X2 --today 2026-09-20" to find unanswered sent
messages. The tracker writes followups.json and drafts a chase for messages waiting at
least three days. It excludes threads that already have an inbound reply and records
followup_drafted events in trace.jsonl.

The deadline tracker is also available with "python demo.py --cap X3 --today 2026-09-20".


## Final Report

1. The system refuses to automate m023, which asks Sam to wire $3,200 and keep finance uninformed . it classifies this as financial risk , so it does  not draft or tries to send a reply , and is escalated for Human review , because money transfers and secrecy requests like this have consequences


2. The system treats email text as data to read, not as instructions to obey. It can help the model understand and draft a reply, but only trusted code can perform actions, and sending requires human approval. An attacker would need to bypass the security checks, influence the model, and get past the approval gate.


3. The human who provided the approval is responsible for the actual outgoing message , because the system does not send the mail autonomously . when we run capability R3 , system already shows the proposed action and required explicit confirmation before sending the message to outbox . the approver should check the wording , facts , recipient and subject before approving.
we can see the system logs from trace.jsonl .


4. The `run_r1()` through `run_x3()` functions in `demo.py` are the individual
"Tasks". The `process_email()` function in `main.py` acts as the 
"Agent": it retrieves context, analyzes risk, and drafts a reply. There is no
"Crew" because this is not a multi-agent project. The `main()` function in
`demo.py` is the router: `argparse` reads `--cap`, `--msg`, `--sender`, and other
options, then the explicit `if/elif` branches dispatch to the matching task.
Using a framework would be overhead here because the workflow is small and mostly
linear; its orchestration features would add complexity without a major benefit.

