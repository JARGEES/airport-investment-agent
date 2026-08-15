from __future__ import annotations

import uuid
from collections import OrderedDict
from typing import Optional

MAX_CONVERSATIONS = 100
MAX_HISTORY_MESSAGES = 50


class ConversationStore:
    def __init__(self, max_conversations: int = MAX_CONVERSATIONS) -> None:
        self._store: OrderedDict[str, list[dict]] = OrderedDict()
        self._max = max_conversations

    def get_or_create(self, conversation_id: Optional[str] = None) -> tuple[str, list[dict]]:
        if conversation_id and conversation_id in self._store:
            self._store.move_to_end(conversation_id)
            return conversation_id, self._store[conversation_id]

        cid = conversation_id or str(uuid.uuid4())
        self._store[cid] = []
        self._store.move_to_end(cid)

        while len(self._store) > self._max:
            self._store.popitem(last=False)

        return cid, self._store[cid]

    def append(self, conversation_id: str, message: dict) -> None:
        if conversation_id not in self._store:
            self._store[conversation_id] = []
        self._store[conversation_id].append(message)
        if len(self._store[conversation_id]) > MAX_HISTORY_MESSAGES:
            self._store[conversation_id] = self._store[conversation_id][-MAX_HISTORY_MESSAGES:]

    def get_history(self, conversation_id: str) -> list[dict]:
        return list(self._store.get(conversation_id, []))


store = ConversationStore()
