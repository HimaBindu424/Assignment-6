## Final Report

1. The system refuses to automate m023, which asks Sam to wire $3,200 and keep finance uninformed . it classifies this as financial risk , so it does  not draft or tries to send a reply , and is escalated for Human review , because money transfers and secrecy requests like this have consequences


2. The system treats email text as data to read, not as instructions to obey . It can help the model understand and draft a reply, but only trusted code can perform actions, and sending requires human approval. An attacker would need to bypass the security checks, influence the model, and get past the approval gate.


3. The human who provided the approval is responsible for the actual outgoing message , because the system does not send the mail autonomously . when we run capability R3 , system already shows the proposed action and required explicit confirmation before sending the message to outbox . the approver should check the wording , facts , recipient and subject before approving.
we can see the system logs from trace.jsonl .


4. All the run functions defined in demo.py i.e.. run_r1 , run_r2 , run_r3 ...run_x3 are individual executable 
"Tasks" performing specific functionality . the below code written manually is acting as a router :

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

There is no "Crew" in this project , as this is not a multi agent project . 
The process_email() function defined in main.py acts as an "Agent" which retrieves the mail context , analyzes risk and drafts a reply. the functionality we built using argparse library and the routing using the if/elif would have been provided by the framework . In this particular scenario , using a framework would have been an overhead , since this project is small , mostly linear workflow with a single model assisted agent and simple tasks . The framework’s orchestration features would add complexity to the project without adding any major benefits . 

