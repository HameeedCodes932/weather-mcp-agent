import json
import os
from datetime import datetime, timezone


class ConversationMemory:
    def __init__(self, storage_dir: str = "memory"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _session_path(self, session_id: str) -> str:
        return os.path.join(self.storage_dir, f"{session_id}.json")

    def _load_session(self, session_id: str) -> dict:
        path = self._session_path(session_id)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return {
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
        }

    def _save_session(self, data: dict) -> None:
        path = self._session_path(data["session_id"])
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save_message(self, session_id: str, role: str, content: str) -> None:
        data = self._load_session(session_id)
        data["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._save_session(data)

    def get_history(self, session_id: str, max_messages: int = 20) -> list[dict]:
        data = self._load_session(session_id)
        return data["messages"][-max_messages:]

    def clear_session(self, session_id: str) -> None:
        path = self._session_path(session_id)
        if os.path.exists(path):
            os.remove(path)

    def list_sessions(self) -> list[str]:
        sessions = []
        for fname in os.listdir(self.storage_dir):
            if fname.endswith(".json"):
                sessions.append(fname[:-5])
        return sessions
