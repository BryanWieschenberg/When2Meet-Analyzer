import sys
import requests
import pandas as pd
import re

arg = sys.argv
if len(arg) != 2:
    print("Usage: python extractor.py <when2meet_url>")
    sys.exit(1)

if "when2meet.com" in arg[1]:
    url = arg[1]
    match = re.search(r"when2meet\.com/\?([a-zA-Z0-9\-]+)", url)
    if not match:
        print("Invalid when2meet URL")
        sys.exit(1)
    id_code = match.group(1)

url = f"https://www.when2meet.com/?{id_code}"
html = requests.get(url).text

people = re.findall(
    r"PeopleNames\[(\d+)\]\s*=\s*'([^']+)';\s*PeopleIDs\[\1\]\s*=\s*(\d+);", html
)
people_dict = {int(pid): name for _, name, pid in people}

slots = re.findall(r"AvailableAtSlot\[(\d+)\]\.push\((\d+)\);", html)

slot_map = {}
for slot, person in slots:
    slot = int(slot)
    person = int(person)
    slot_map.setdefault(slot, set()).add(person)

all_slots = range(min(slot_map.keys()), max(slot_map.keys()) + 1)

data = {}
for pid, name in people_dict.items():
    data[name] = [
        1 if pid in slot_map.get(slot, []) else 0
        for slot in all_slots
    ]

df = pd.DataFrame(data, index=[i+1 for i in all_slots])

df.to_csv("when2meet_availability.csv")
