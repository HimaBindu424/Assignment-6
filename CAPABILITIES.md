# CAPABILITIES.md 


**Student:** M.HimaBindu
**Repository:** https://github.com/HimaBindu424/Assignment-6"


## Capabilities

| id | name | tier | one-line claim |
|----|------|------|----------------|
| R1 | Zero the inbox | B | every message gets one disposition and reason, with none undecided |
| R2 | Grounded reply | B | drafts cite the earlier message they used |
| R3 | Gate the irreversible | C | model-generated sends require approval or --dry-run; unsafe messages stop |
| R4 | Persistent preference | C | a stated meeting preference is stored and recalled after restart |
| R5 | Refuse embedded instructions | C | detects and reports embedded instructions, refuses them, and leaves messages in place |
| R6 | Dashboard | C | pending actions, flagged messages, commitments, and conflicts are surfaced |
| X1 | Unread mail by sender | A | lists all unread messages from a given sender |
| X2 | Follow-up tracking | B | unanswered sent mail, with a drafted chase |
| X3 | Automatic deadline tracker | C | extracts dated deadlines, classifies status, and cites source messages |

The exact command, observable outcome and evidence for each is in
`capabilities.sample.json`. That file is the machine-readable version and is what a
marking script reads; this file is for a human. Keep the two in step.



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


