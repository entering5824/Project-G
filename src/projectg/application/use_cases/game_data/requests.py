"""Request models for game-data pack operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GameDataPathRequest:
    path: str
