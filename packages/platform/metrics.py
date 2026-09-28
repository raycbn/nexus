from collections import Counter
from threading import Lock


class MetricsRegistry:
    def __init__(self) -> None:
        self._counters: Counter[str] = Counter()
        self._lock = Lock()

    def increment(self, name: str, value: int = 1) -> None:
        if value < 0:
            raise ValueError("metric increment must be non-negative")
        with self._lock:
            self._counters[name] += value

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def prometheus(self) -> str:
        lines: list[str] = []
        for name, value in sorted(self.snapshot().items()):
            metric = _normalize(name)
            lines.append(f"# TYPE {metric} counter")
            lines.append(f"{metric} {value}")
        return "\n".join(lines) + ("\n" if lines else "")


def _normalize(name: str) -> str:
    return "nexus_" + "".join(
        character if character.isalnum() or character == "_" else "_" for character in name
    )


metrics = MetricsRegistry()
