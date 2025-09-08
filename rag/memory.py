from __future__ import annotations

from typing import List, Tuple
import redis
from config import settings

class RedisMemory:
    """Multi-turn chat memory using Redis for persistence"""

    def __init__(self, url: str | None = None, max_turns: int = 20) -> None:
        self.r = redis.from_url(url or settings.REDIS_URL, decode_responses=True)
        self.max_turns = max_turns

    def _key(self, session_id: str) -> str:
        return f"chat:{session_id}"

    def append(self, session_id: str, role: str, content: str) -> None:
        key = self._key(session_id)
        self.r.rpush(key, f"{role}:{content}")
        # Trim history to last N entries (2 entries per turn is fine)
        self.r.ltrim(key, -2 * self.max_turns, -1)

    def get(self, session_id: str, limit: int | None = None) -> List[str]:
        key = self._key(session_id)
        if limit is None:
            return self.r.lrange(key, 0, -1)
        # last N entries
        return self.r.lrange(key, -limit, -1)

    def reset(self, session_id: str) -> None:
        self.r.delete(self._key(session_id))

    @staticmethod
    def as_pairs(history_rows: List[str]) -> List[Tuple[str, str]]:
        """
        Convert ["user:...", "assistant:...", ...] -> [(user, ...), (assistant, ...)]
        """
        pairs: List[Tuple[str, str]] = []
        for row in history_rows:
            if ":" in row:
                role, content = row.split(":", 1)
                pairs.append((role.strip(), content.strip()))
        return pairs

    @staticmethod
    def format_for_prompt(history_rows: List[str]) -> str:
        """
        Render history into a compact text block for LLM prompting.
        """
        lines: List[str] = []
        for row in history_rows:
            if ":" in row:
                role, content = row.split(":", 1)
                role = role.strip().capitalize()
                lines.append(f"{role}: {content.strip()}")
        return "\n".join(lines)
