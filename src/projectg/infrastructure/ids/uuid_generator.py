"""UUID-backed implementation of the application identifier port."""

from uuid import uuid4


class Uuid4IdGenerator:
    def next_id(self) -> str:
        return str(uuid4())
