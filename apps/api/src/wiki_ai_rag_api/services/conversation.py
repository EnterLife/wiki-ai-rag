from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class ConversationTurn:
    question: str
    answer: str


class ConversationMemory:
    def __init__(self) -> None:
        self._turns: dict[str, deque[ConversationTurn]] = defaultdict(deque)
        self._lock = Lock()

    def build_retrieval_query(self, *, session_id: str | None, question: str, max_turns: int) -> str:
        if not session_id:
            return question
        with self._lock:
            turns = list(self._turns.get(session_id, ()))
        if not turns:
            return question

        recent_questions = [turn.question for turn in turns[-max_turns:]]
        return "\n".join([*recent_questions, question])

    def record_turn(
        self,
        *,
        session_id: str | None,
        question: str,
        answer: str,
        max_turns: int,
    ) -> None:
        if not session_id:
            return
        with self._lock:
            turns = self._turns[session_id]
            turns.append(ConversationTurn(question=question, answer=answer))
            while len(turns) > max_turns:
                turns.popleft()

    def clear(self) -> None:
        with self._lock:
            self._turns.clear()


conversation_memory = ConversationMemory()


def reset_conversation_memory() -> None:
    conversation_memory.clear()
