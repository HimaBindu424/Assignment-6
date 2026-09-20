"""Minimal Part 5 runner for persistent preferences."""

import argparse
import json

from memory import recall, remember


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    remember_parser = subparsers.add_parser("remember")
    remember_parser.add_argument("key")
    remember_parser.add_argument("value")
    remember_parser.add_argument("--source", default="user")

    recall_parser = subparsers.add_parser("recall")
    recall_parser.add_argument("query", nargs="?", default="*")

    args = parser.parse_args()
    if args.command == "remember":
        result = remember(args.key, args.value, args.source)
    else:
        result = recall(args.query)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()