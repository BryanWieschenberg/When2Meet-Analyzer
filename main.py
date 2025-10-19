from collections import defaultdict
import sys
import requests
import pandas as pd
import re
from datetime import date, datetime, timedelta
from dataclasses import dataclass, field

from constants import SLOTS_PER_HOUR, SLOTS_PER_DAY, BLOCK_HOURS
from schedule import Schedule

@dataclass
class Employee:
    id: int
    name: str
    is_ca: bool
    priority: str
    hours_weekly: int
    hours_payperiod: int
    shifts: list = field(default_factory=list)

def parse_date(date_str):
    return datetime.strptime(date_str, "%m/%d")

def parse_time(time_str):
    return datetime.strptime(time_str, "%I%p")

def calc_timeslots(start_date, end_date, start_time, end_time):
    d1 = parse_date(start_date)
    d2 = parse_date(end_date)
    t1 = parse_time(start_time)
    t2 = parse_time(end_time)

    if t2 <= t1:
        t2 += timedelta(days=1)

    hours_per_day = (t2 - t1).seconds // 3600
    day_span = (d2 - d1).days + 1
    total_hours = hours_per_day * day_span * SLOTS_PER_HOUR
    actual_slots_per_day = hours_per_day * SLOTS_PER_HOUR

    return total_hours, actual_slots_per_day

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python main.py <when2meet_url> <start_date MM/dd> <end_date MM/dd> <start_hour ttAM/PM> <end_hour ttAM/PM>")
        sys.exit(1)

    url, start_date, end_date, start_time, end_time, *rest = sys.argv[1:]
    exceptions = []
    if rest:
        arg_str = " ".join(rest).strip()
        arg_str = arg_str.strip("[]")
        exceptions = [x.strip() for x in arg_str.split(",") if x.strip()]

    timeslots, actual_slots_per_day = calc_timeslots(start_date, end_date, start_time, end_time)

    if "https://when2meet.com/?/" not in url:
        url = f"https://when2meet.com/?{url}"

    html = requests.get(url).text

    people = re.findall(r"PeopleNames\[(\d+)\]\s*=\s*'([^']+)';\s*PeopleIDs\[\1\]\s*=\s*(\d+);", html)
    people_dict = {int(pid): name for _, name, pid in people}
    slots = re.findall(r"AvailableAtSlot\[(\d+)\]\.push\((\d+)\);", html)

    slot_map = {}
    for slot, person in slots:
        slot = int(slot)
        person = int(person)
        slot_map.setdefault(slot, set()).add(person)

    all_slots = range(1, timeslots + 1)

    data = {}
    for pid, name in people_dict.items():
        if name in exceptions: continue
        data[name] = [1 if pid in slot_map.get(slot, []) else 0 for slot in all_slots]

    df = pd.DataFrame(data, index=[i + 1 for i in all_slots])
    df = df.reindex(range(1, timeslots + 1), fill_value=0)

    df.to_csv("availability.csv")

    employees = []
    with open("availability.csv", "r") as f:
        reader = pd.read_csv(f)
        for col in reader.columns[1:]:
            employees.append(Employee(
                id=len(employees), name=col, is_ca=False, priority="M",
                hours_weekly=0, hours_payperiod=0, shifts=[]
            ))
    
    with open("rules.txt", "r") as f:
        section = None
        for line in map(str.strip, f):
            if not line:
                continue
            if line.startswith("/"):
                section = line[1:].upper()
                continue
            if section in "RA":
                next(e for e in employees if e.name == line).is_ca = True
            elif section == "PRIORITY":
                name, pr = map(str.strip, line.split(",", 1))
                next(e for e in employees if e.name == name).priority = pr

    t1 = parse_time(start_time)
    start_hour = t1.hour

    schedule = Schedule()
        
    schedule.build_schedule(
        "availability.csv",
        employees,
        date(2025, 9, 20),
        actual_slots_per_day,
        start_hour
    )
