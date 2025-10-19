import pandas as pd
from datetime import timedelta
from collections import defaultdict

from constants import BLOCK_HOURS, BLOCK_SLOTS, SLOTS_PER_DAY, SLOTS_PER_HOUR
from constants import RA_WEEK_MAX, RA_PP_MAX, NONCA_WEEK_MAX, NONCA_PP_MAX
from constants import ALL_WEEK_MIN, ALL_PP_MIN, DAILY_SOFT_MAX, DAILY_HARD_MAX

class Schedule:
    def __init__(self):
        self.schedule = pd.DataFrame()

    def weekly_target(self, emp):
        week_min = ALL_WEEK_MIN
        week_max = RA_WEEK_MAX if emp.is_ca else NONCA_WEEK_MAX
        if emp.priority == "L":
            return week_min
        if emp.priority == "H":
            return week_max
        mid = (week_min + week_max) / 2
        return round(mid / 2) * 2

    def payperiod_target(self, emp):
        pp_min = ALL_PP_MIN
        pp_max = RA_PP_MAX if emp.is_ca else NONCA_PP_MAX
        if emp.priority == "L":
            return pp_min
        if emp.priority == "H":
            return pp_max
        mid = (pp_min + pp_max) / 2
        return round(mid / 2) * 2

    def slot_to_day_week_pp(self, slot1_based, start_date, slots_per_day):
        zero = slot1_based - 1
        day_index = zero // slots_per_day
        week_index = day_index // 7
        pay_period_index = day_index // 14
        day_date = start_date + timedelta(days=day_index)
        return day_index, week_index, pay_period_index, day_date

    def block_is_available(self, df, name, start_slot):
        end_slot = start_slot + BLOCK_SLOTS - 1
        return df.loc[start_slot:end_slot, name].sum() == BLOCK_SLOTS

    def can_assign_normal(self, emp, day_hours, week_hours, pp_hours, name, week_idx, pp_idx, day_key):
        if day_hours[(name, day_key)] + BLOCK_HOURS > DAILY_HARD_MAX:
            return False
        week_cap = RA_WEEK_MAX if emp.is_ca else NONCA_WEEK_MAX
        pp_cap = RA_PP_MAX if emp.is_ca else NONCA_PP_MAX
        if week_hours[(name, week_idx)] + BLOCK_HOURS > week_cap:
            return False
        if pp_hours[(name, pp_idx)] + BLOCK_HOURS > pp_cap:
            return False
        return True

    def can_assign_relaxed(self, emp, day_hours, week_hours, pp_hours, name, week_idx, pp_idx, day_key):
        if day_hours[(name, day_key)] + BLOCK_HOURS > DAILY_SOFT_MAX:
            return False
        week_cap = RA_WEEK_MAX if emp.is_ca else NONCA_WEEK_MAX
        pp_cap = RA_PP_MAX if emp.is_ca else NONCA_PP_MAX
        if week_hours[(name, week_idx)] + BLOCK_HOURS > week_cap:
            return False
        if pp_hours[(name, pp_idx)] + BLOCK_HOURS > pp_cap:
            return False
        return True

    def score_candidate(self, emp, name, week_idx, week_hours, pp_idx, pp_hours, day_key, day_hours, worked_days_set):
        w_cur = week_hours[(name, week_idx)]
        p_cur = pp_hours[(name, pp_idx)]
        w_tgt = self.weekly_target(emp)
        p_tgt = self.payperiod_target(emp)

        w_need = max(0.0, w_tgt - w_cur)
        p_need = max(0.0, p_tgt - p_cur)

        has_today = day_hours[(name, day_key)] > 0.0
        day_penalty = 1.0 if has_today else 0.0

        diversity_bonus = 0.0
        if name in worked_days_set:
            diversity_bonus = max(0.0, 3 - len(worked_days_set[name])) * 0.25

        pr_nudge = 0.0
        if emp.priority == "H":
            pr_nudge = 0.5
        elif emp.priority == "L":
            pr_nudge = -0.25

        return (w_need * 0.6) + (p_need * 0.3) + diversity_bonus + pr_nudge - (day_penalty * 1.0)

    def slot_to_time(self, slot1_based, slots_per_day, start_time_hour):
        zero = slot1_based - 1
        slot_in_day = zero % slots_per_day
        hours_offset = slot_in_day / SLOTS_PER_HOUR
        hour = start_time_hour + hours_offset
        
        if hour >= 24: hour -= 24
        
        if hour == 0: return "12AM"
        elif hour < 12: return f"{int(hour)}AM"
        elif hour == 12: return "12PM"
        else: return f"{int(hour - 12)}PM"

    def build_schedule(self, availability_csv_path, employees, schedule_start_date, slots_per_day, start_time_hour):
        df = pd.read_csv(availability_csv_path, index_col=0)
        valid_names = {e.name for e in employees}
        df = df[[c for c in df.columns if c in valid_names]].copy()

        week_hours = defaultdict(float)
        pp_hours = defaultdict(float)
        day_hours = defaultdict(float)
        worked_days_set = defaultdict(set)
        assignments = []

        total_slots = int(df.shape[0])
        start_slots = list(range(1, total_slots + 1, BLOCK_SLOTS))
        start_slots = [s for s in start_slots if s + BLOCK_SLOTS - 1 <= total_slots]

        emp_by_name = {e.name: e for e in employees}

        for start_slot in start_slots:
            _, week_idx, pp_idx, day_date = self.slot_to_day_week_pp(start_slot, schedule_start_date, slots_per_day)
            day_key = day_date.isoformat()

            start_time_str = self.slot_to_time(start_slot, slots_per_day, start_time_hour)
            end_time_str = self.slot_to_time(start_slot + BLOCK_SLOTS, slots_per_day, start_time_hour)

            available = []
            for name in df.columns:
                if self.block_is_available(df, name, start_slot):
                    available.append(name)

            if not available:
                assignments.append({
                    "week": week_idx + 1,
                    "pay_period": pp_idx + 1,
                    "day": day_key,
                    "start_time": start_time_str,
                    "end_time": end_time_str,
                    "employee": ""
                })
                continue

            normal_ok = []
            for name in available:
                emp = emp_by_name[name]
                if self.can_assign_normal(emp, day_hours, week_hours, pp_hours, name, week_idx, pp_idx, day_key):
                    normal_ok.append(name)

            chosen = None
            relax_used = False

            if normal_ok:
                scored = []
                for name in normal_ok:
                    emp = emp_by_name[name]
                    s = self.score_candidate(emp, name, week_idx, week_hours, pp_idx, pp_hours, day_key, day_hours, worked_days_set)
                    scored.append((s, name))
                scored.sort(reverse=True)
                chosen = scored[0][1]
            else:
                relaxed_ok = []
                for name in available:
                    emp = emp_by_name[name]
                    if self.can_assign_relaxed(emp, day_hours, week_hours, pp_hours, name, week_idx, pp_idx, day_key):
                        relaxed_ok.append(name)
                if relaxed_ok:
                    scored = []
                    for name in relaxed_ok:
                        emp = emp_by_name[name]
                        s = self.score_candidate(emp, name, week_idx, week_hours, pp_idx, pp_hours, day_key, day_hours, worked_days_set)
                        scored.append((s, name))
                    scored.sort(reverse=True)
                    chosen = scored[0][1]
                    relax_used = True

            if chosen is None:
                assignments.append({
                    "week": week_idx + 1,
                    "pay_period": pp_idx + 1,
                    "day": day_key,
                    "start_time": start_time_str,
                    "end_time": end_time_str,
                    "employee": ""
                })
                continue

            emp = emp_by_name[chosen]
            week_hours[(chosen, week_idx)] += BLOCK_HOURS
            pp_hours[(chosen, pp_idx)] += BLOCK_HOURS
            day_hours[(chosen, day_key)] += BLOCK_HOURS
            worked_days_set[chosen].add(day_key)
            emp.hours_weekly = week_hours[(chosen, week_idx)]
            emp.hours_payperiod = pp_hours[(chosen, pp_idx)]
            emp.shifts.append({
                "week": week_idx + 1,
                "pay_period": pp_idx + 1,
                "day": day_key,
                "start_slot": start_slot,
                "end_slot": start_slot + BLOCK_SLOTS - 1,
                "hours": BLOCK_HOURS,
                "relaxed_daily_cap_used": relax_used,
            })

            assignments.append({
                "week": week_idx + 1,
                "pay_period": pp_idx + 1,
                "day": day_key,
                "start_time": start_time_str,
                "end_time": end_time_str,
                "employee": chosen
            })

        schedule_df = pd.DataFrame(assignments)
        schedule_df.to_csv("schedule.csv", index=False)

        print("\n=== Weekly Hours (by person x week) ===")
        if not schedule_df.empty:
            wh = schedule_df[schedule_df["employee"] != ""].copy()
            wh["hours"] = BLOCK_HOURS
            print(wh.pivot_table(index="employee", columns="week", values="hours", aggfunc="sum").fillna(0))

            print("\n=== Pay-Period Hours (by person x pay period) ===")
            pph = wh.copy()
            print(pph.pivot_table(index="employee", columns="pay_period", values="hours", aggfunc="sum").fillna(0))

        return schedule_df
