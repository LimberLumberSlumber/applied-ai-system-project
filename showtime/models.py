from dataclasses import dataclass, field


@dataclass
class BusyBlock:
    start: int  # minutes since midnight
    end: int
    label: str = "busy"


@dataclass
class Title:
    name: str
    kind: str  # "movie" or "show"
    runtime: int  # movie length, or typical episode length, in minutes
    seasons: dict = field(default_factory=dict)  # {season number: episode count}
    director: str = ""
    cast: list = field(default_factory=list)
    genres: list = field(default_factory=list)
    year: int = 0
    source: str = "catalog"


def fmt_time(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def fmt_duration(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours}h {mins}m"
    return f"{hours}h" if hours else f"{mins}m"
