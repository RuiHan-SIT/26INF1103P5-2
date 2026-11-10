from datetime import datetime
from pathlib import Path
from uuid import uuid4

SUMMARIES_DIR = Path(__file__).resolve().parents[4] / "data" / "summaries"


class SummaryFileStore:
    """Reads and writes optional text-file exports of handover summaries."""

    def __init__(self, folder: Path | str | None = None):
        self._folder = Path(folder) if folder else SUMMARIES_DIR

    def save(self, text: str, user_details: dict[str, str]) -> str:
        if not isinstance(text, str):
            raise TypeError("Summary text must be a string.")

        name = self._safe_component(user_details.get("name", "employee"))
        employee_id = self._safe_component(
            user_details.get("employee_id", "unknown")
        )
        now = datetime.now().astimezone()
        filename = (
            f"{now:%Y-%m-%d}_{name}_{employee_id}_"
            f"{now:%H-%M-%S}_{uuid4().hex[:8]}.txt"
        )

        self._folder.mkdir(parents=True, exist_ok=True)
        self._path_for(filename).write_text(text, encoding="utf-8")
        return filename

    def exists(self, filename: str) -> bool:
        return self._path_for(filename).is_file()

    def read(self, filename: str) -> str:
        return self._path_for(filename).read_text(encoding="utf-8")

    def append(self, filename: str, text: str) -> None:
        path = self._path_for(filename)
        if not path.is_file():
            raise FileNotFoundError(f"Summary file not found: {filename}")

        with path.open("a", encoding="utf-8") as file:
            file.write(text)

    def _path_for(self, filename: str) -> Path:
        if not filename or Path(filename).name != filename:
            raise ValueError("Invalid summary filename.")

        folder = self._folder.resolve()
        path = (folder / filename).resolve()

        if path.parent != folder:
            raise ValueError("Summary file must be inside the summaries folder.")

        return path

    def _safe_component(self, value: str) -> str:
        safe_value = "".join(
            char if char.isalnum() or char in "-_" else "_"
            for char in str(value)
        )
        return safe_value.strip("_") or "unknown"