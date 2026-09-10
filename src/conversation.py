import json
import re
from datetime import datetime
from pathlib import Path

_CONVERSATION_ID_RE = re.compile(r"^[\w\-.]+$")


def _validate_id(conversation_id: str) -> None:
    """Reject IDs that could escape the conversations directory."""
    if not _CONVERSATION_ID_RE.match(conversation_id):
        raise ValueError(f"Invalid conversation id: {conversation_id!r}")


def _extract_preview(messages: list[dict]) -> str:
    """Return a short preview string from the last user or assistant message."""
    for msg in reversed(messages):
        if msg.get("role") not in ("user", "assistant"):
            continue
        content = msg.get("content", "").strip()
        if content:
            return content[:60] + ("..." if len(content) > 60 else "")
    return ""


class ConversationManager:
    def __init__(self):
        self.dir = Path.home() / ".tass" / "conversations"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._created_at: dict[str, str] = {}  # cache to avoid re-reading files

    def list_conversations(self) -> list[dict]:
        conversations = []
        for f in sorted(self.dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text())
                conversations.append({
                    "id": data["id"],
                    "updated_at": data["updated_at"],
                    "cwd": data["cwd"],
                    "message_count": len(data["messages"]),
                    "preview": data.get("preview", ""),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return conversations

    def load(self, conversation_id: str) -> list[dict] | None:
        _validate_id(conversation_id)
        path = self.dir / f"{conversation_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            # cache created_at so future saves don't re-read
            self._created_at[conversation_id] = data.get("created_at", datetime.now().isoformat())
            return data["messages"]
        except (json.JSONDecodeError, KeyError):
            return None

    def save(self, conversation_id: str, messages: list[dict], cwd: str):
        _validate_id(conversation_id)
        path = self.dir / f"{conversation_id}.json"

        created_at = self._created_at.get(conversation_id)
        if created_at is None:
            if path.exists():
                try:
                    existing = json.loads(path.read_text())
                    created_at = existing.get("created_at")
                except json.JSONDecodeError:
                    pass
            if created_at is None:
                created_at = datetime.now().isoformat()
        self._created_at[conversation_id] = created_at

        data = {
            "id": conversation_id,
            "cwd": cwd,
            "created_at": created_at,
            "updated_at": datetime.now().isoformat(),
            "preview": _extract_preview(messages),
            "messages": messages,
        }
        path.write_text(json.dumps(data, indent=2))

