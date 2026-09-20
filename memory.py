"""Small JSON-backed memory store for facts that persist between runs."""

import json
from pathlib import Path


MEMORY_FILE = Path(__file__).with_name("memory.json")


def _load_memory():
    if not MEMORY_FILE.exists():
        return {}
    with MEMORY_FILE.open("r", encoding="utf-8") as file:
        memory = json.load(file)
    if not isinstance(memory, dict):
        raise ValueError("memory.json must contain a JSON object")
    return memory


def _save_memory(memory):
    MEMORY_FILE.write_text(json.dumps(memory, indent=2), encoding="utf-8")


def remember(key, value, source="user"):
    """Store one fact, replacing an older value for the same key."""
    if not isinstance(key, str) or not key.strip():
        return {"status": "error", "message": "Memory key cannot be empty."}
    if not isinstance(source, str) or not source.strip():
        return {"status": "error", "message": "Memory source cannot be empty."}

    memory = _load_memory()
    previous = memory.get(key)
    memory[key] = {"value": value, "source": source}
    _save_memory(memory)
    response = {
        "status": "ok",
        "message": "Memory saved.",
        "key": key,
        "value": value,
        "source": source,
    }
    if previous is not None:
        response["message"] = "Memory conflict resolved by keeping the latest value."
        response["previous"] = previous
    return response


def recall(query=""):
    """Return stored facts whose keys or values contain the query."""
    memory = _load_memory()
    if not query or query == "*":
        return memory

    query = query.casefold()
    return {
        key: entry
        for key, entry in memory.items()
        if query in key.casefold()
        or query in str(entry.get("value", "")).casefold()
        or query in str(entry.get("source", "")).casefold()
    }