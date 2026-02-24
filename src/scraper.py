import requests
import re
from collections import defaultdict

def get_when_to_meet_data(url_or_id):
    if "when2meet.com/?" in url_or_id:
        url = url_or_id
    elif "?" in url_or_id:
        url = f"https://www.when2meet.com/{url_or_id}"
    else:
        url = f"https://www.when2meet.com/?{url_or_id.lstrip('?')}"
    
    print(f"Fetching data from: {url}")
    response = requests.get(url)
    response.raise_for_status()
    html = response.text
    
    people = re.findall(r"PeopleNames\[(\d+)\]\s*=\s*'([^']+)';\s*PeopleIDs\[\1\]\s*=\s*(\d+);", html)
    people_dict = {int(pid): name for _, name, pid in people}
    
    time_of_slots = re.findall(r"TimeOfSlot\[(\d+)\]=(\d+);", html)
    time_of_slots = [int(ts) for _, ts in sorted(time_of_slots, key=lambda x: int(x[0]))]

    slots = re.findall(r"AvailableAtSlot\[(\d+)\]\.push\((\d+)\);", html)
    slot_map = defaultdict(set)
    for slot, person in slots:
        slot_map[int(slot)].add(int(person))
        
    return people_dict, slot_map, time_of_slots
