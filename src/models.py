from dataclasses import dataclass, field

@dataclass
class Employee:
    id: int
    name: str
    is_ra: bool
    priority: str
    hours_weekly: float = 0.0
    hours_payperiod: float = 0.0
    shifts: list = field(default_factory=list)
