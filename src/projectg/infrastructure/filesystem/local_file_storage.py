"""Read and write user-selected files for application ports."""

from pathlib import Path


class LocalFileStorage:
    def read(self, key: str) -> bytes:
        return Path(key).read_bytes()

    def write(self, key: str, content: bytes) -> None:
        path = Path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(content)
        temporary.replace(path)

    def delete(self, key: str) -> None:
        Path(key).unlink(missing_ok=True)
