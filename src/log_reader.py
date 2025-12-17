"""Log dosyası okuma ve izleme modülü."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Generator


@dataclass
class LogEntry:
    """Tek bir log satırını temsil eder."""
    source_name: str
    source_type: str
    line: str
    line_number: int


class LogReader:
    """Log dosyalarını okuyan ve izleyen sınıf."""

    def __init__(self, log_sources: list[dict]):
        self.log_sources = log_sources
        self._file_positions: dict[str, int] = {}

    def _get_file_position(self, path: str) -> int:
        """Dosyanın son okunan pozisyonunu döndür."""
        return self._file_positions.get(path, 0)

    def _set_file_position(self, path: str, position: int) -> None:
        """Dosyanın son okunan pozisyonunu kaydet."""
        self._file_positions[path] = position

    def read_new_lines(self, source: dict) -> Generator[LogEntry, None, None]:
        """Bir log kaynağından yeni satırları oku."""
        path = source["path"]
        name = source["name"]
        log_type = source["type"]

        if not Path(path).exists():
            return

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                # Dosya boyutunu kontrol et (log rotation durumu)
                file_size = os.path.getsize(path)
                last_position = self._get_file_position(path)

                # Dosya küçülmüşse (rotation), baştan başla
                if file_size < last_position:
                    last_position = 0

                f.seek(last_position)
                line_number = 0

                for line in f:
                    line = line.strip()
                    if line:
                        line_number += 1
                        yield LogEntry(
                            source_name=name,
                            source_type=log_type,
                            line=line,
                            line_number=line_number
                        )

                self._set_file_position(path, f.tell())

        except PermissionError:
            print(f"[UYARI] {path} dosyasına erişim izni yok")
        except Exception as e:
            print(f"[HATA] {path} okunurken hata: {e}")

    def read_all_new_lines(self) -> list[LogEntry]:
        """Tüm kaynaklardan yeni satırları oku."""
        entries = []
        for source in self.log_sources:
            entries.extend(self.read_new_lines(source))
        return entries

    def read_last_n_lines(self, source: dict, n: int = 100) -> list[LogEntry]:
        """Bir log kaynağından son n satırı oku."""
        path = source["path"]
        name = source["name"]
        log_type = source["type"]

        if not Path(path).exists():
            return []

        entries = []
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                start = max(0, len(lines) - n)

                for i, line in enumerate(lines[start:], start=start + 1):
                    line = line.strip()
                    if line:
                        entries.append(LogEntry(
                            source_name=name,
                            source_type=log_type,
                            line=line,
                            line_number=i
                        ))

            # Pozisyonu dosya sonuna ayarla
            self._set_file_position(path, os.path.getsize(path))

        except PermissionError:
            print(f"[UYARI] {path} dosyasına erişim izni yok")
        except Exception as e:
            print(f"[HATA] {path} okunurken hata: {e}")

        return entries

    def initialize_positions(self) -> None:
        """Tüm dosyaların pozisyonlarını dosya sonuna ayarla (sadece yeni logları izle)."""
        for source in self.log_sources:
            path = source["path"]
            if Path(path).exists():
                try:
                    self._set_file_position(path, os.path.getsize(path))
                except Exception:
                    pass


def batch_entries(entries: list[LogEntry], batch_size: int) -> Generator[list[LogEntry], None, None]:
    """Log entry'lerini batch'lere böl."""
    for i in range(0, len(entries), batch_size):
        yield entries[i:i + batch_size]
