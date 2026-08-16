from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import Generic, TypeVar

T = TypeVar("T")


class Extractor(ABC):
    @abstractmethod
    def extract(self) -> list[Path]:
        """Return local paths to extracted source files."""


class Parser(ABC, Generic[T]):
    @abstractmethod
    def parse(self, files: list[Path]) -> Sequence[T]:
        """Turn extracted files into domain records."""


class Loader(ABC, Generic[T]):
    @abstractmethod
    def load(self, records: Sequence[T]) -> None:
        """Persist parsed records."""
