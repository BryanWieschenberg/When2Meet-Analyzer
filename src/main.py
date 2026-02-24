import sys
import pandas as pd
from datetime import datetime
from time import perf_counter
from config_loader import config
from models import Employee
from scraper import get_when_to_meet_data
from schedule import Schedule

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python main.py <when2meet_url> <start_date MM/dd> <end_date MM/dd> <start_hour ttAM/PM> <end_hour ttAM/PM> [exceptions]")
        sys.exit(1)

    start = perf_counter()
    url_arg, start_date_str, end_date_str, start_time_str, end_time_str, *rest = sys.argv[1:]
    
    exceptions = []
    if rest:
        arg_str = " ".join(rest).strip("[]")
        exceptions = [x.strip() for x in arg_str.split(",") if x.strip()]


    try:
        people_dict, slot_map, time_of_slots = get_when_to_meet_data(url_arg)
    except Exception as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

    total_slots = len(time_of_slots)
    all_slots = range(total_slots)
    data = {}
    for pid, name in people_dict.items():
        if name in exceptions: 
            continue
        data[name] = [1 if pid in slot_map.get(slot, []) else 0 for slot in all_slots]

    df = pd.DataFrame(data, index=[i+1 for i in all_slots])
    df.to_csv("availability.csv")
    print(f"Availability data saved to availability.csv ({len(df.columns)} people, {len(df)} slots)")

    employees = []
    emp_config_map = {e["name"]: e for e in config.employees}
    
    for name in df.columns:
        emp_data = emp_config_map.get(name, {})
        employees.append(Employee(
            id=len(employees),
            name=name,
            is_ra=emp_data.get("is_ra", False),
            priority=emp_data.get("priority", "M")
        ))

    anchor_date = datetime.strptime(start_date_str, "%m/%d").replace(year=datetime.now().year).date()

    schedule = Schedule()
    schedule.build_schedule(
        "availability.csv",
        employees,
        anchor_date,
        time_of_slots
    )
    
    elapsed = perf_counter() - start
    print("\nSchedule generation complete. Results saved to schedule.csv")
    print(f"Generated in {elapsed:.3f} seconds")
