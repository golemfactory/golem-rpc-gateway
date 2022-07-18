from datetime import datetime, timezone, timedelta
from random import randint


class NodeRunningTimeRange:
    min: int
    max: int

    def __init__(self, time_range: str):
        self.min, self.max = map(int, time_range.split(","))
        if self.min > self.max:
            raise ValueError(f"Minimum: {self.min} > {self.max}")

    def get_expiry(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(seconds=randint(self.min, self.max))

    def __repr__(self):
        return f"{self.min},{self.max}"
