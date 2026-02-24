import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

class Config:
    def __init__(self):
        self.raw_data = load_config()
        self.constraints = self.raw_data.get("constraints", {})
        self.employees = self.raw_data.get("employees", [])

        self.SLOTS_PER_HOUR = self.constraints.get("slots_per_hour", 4)
        self.BLOCK_HOURS_MIN = self.constraints.get("block_hours_min", 2)
        self.BLOCK_HOURS_MAX = self.constraints.get("block_hours_max", 4)
        self.EMPLOYEES_PER_SLOT = self.constraints.get("employees_per_slot", 1)
        
        self.BLOCK_SLOTS_MIN = self.SLOTS_PER_HOUR * self.BLOCK_HOURS_MIN
        self.BLOCK_SLOTS_MAX = self.SLOTS_PER_HOUR * self.BLOCK_HOURS_MAX
        self.SLOTS_PER_DAY = 24 * self.SLOTS_PER_HOUR

        self.RA_WEEK_MAX = self.constraints.get("ra", {}).get("week_max", 9)
        self.RA_PP_MAX = self.constraints.get("ra", {}).get("pp_max", 18)

        self.NONRA_WEEK_MAX = self.constraints.get("non_ra", {}).get("week_max", 15)
        self.NONRA_PP_MAX = self.constraints.get("non_ra", {}).get("pp_max", 30)

        self.ALL_WEEK_MIN = self.constraints.get("all", {}).get("week_min", 3)
        self.ALL_PP_MIN = self.constraints.get("all", {}).get("pp_min", 6)

        self.DAILY_SOFT_MAX = self.constraints.get("daily_soft_max", 4)
        self.DAILY_HARD_MAX = self.constraints.get("daily_hard_max", 6)

        self.WEIGHTS = self.constraints.get("weights", {
            "weekly_need": 2.0,
            "pp_need": 1.0,
            "diversity": 0.5,
            "priority_h": 1.0,
            "priority_l": -1.0,
            "day_penalty": 5.0
        })

config = Config()
