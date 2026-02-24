from datetime import datetime, timedelta

def parse_date(date_str):
    return datetime.strptime(date_str, "%m/%d")

def parse_time(time_str):
    if len(time_str) == 3:
        time_str = "0" + time_str
    elif len(time_str) == 4 and time_str[1].isdigit():
        pass
    return datetime.strptime(time_str, "%I%p")

def calc_timeslots(start_date_str, end_date_str, start_time_str, end_time_str, slots_per_hour):
    d1 = parse_date(start_date_str)
    d2 = parse_date(end_date_str)
    t1 = parse_time(start_time_str)
    t2 = parse_time(end_time_str)

    if t2 <= t1:
        t2 += timedelta(days=1)

    hours_per_day = (t2 - t1).seconds // 3600
    day_span = (d2 - d1).days + 1
    total_slots = hours_per_day * day_span * slots_per_hour
    actual_slots_per_day = hours_per_day * slots_per_hour

    return total_slots, actual_slots_per_day

def get_slot_info(timestamp, first_date):
    dt = datetime.fromtimestamp(timestamp)
    days_since_start = (dt.date() - first_date).days
    
    week_index = days_since_start // 7
    pay_period_index = days_since_start // 14
    
    hour = dt.hour
    if hour == 0: t_str = "12AM"
    elif hour < 12: t_str = f"{hour}AM"
    elif hour == 12: t_str = "12PM"
    else: t_str = f"{hour-12}PM"
    
    if dt.minute > 0:
        t_str = f"{t_str[:-2]}:{dt.minute:02d}{t_str[-2:]}"

    return dt.date(), week_index, pay_period_index, t_str
