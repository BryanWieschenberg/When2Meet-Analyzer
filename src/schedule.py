import pandas as pd
from collections import defaultdict
from config_loader import config

class Schedule:
    def __init__(self):
        self.schedule = pd.DataFrame()

    def weekly_target(self, emp):
        week_min = config.ALL_WEEK_MIN
        week_max = config.RA_WEEK_MAX if emp.is_ra else config.NONRA_WEEK_MAX
        if emp.priority == "L":
            return week_min
        if emp.priority == "H":
            return week_max
        mid = (week_min + week_max) / 2
        return round(mid / 2) * 2

    def payperiod_target(self, emp):
        pp_min = config.ALL_PP_MIN
        pp_max = config.RA_PP_MAX if emp.is_ra else config.NONRA_PP_MAX
        if emp.priority == "L":
            return pp_min
        if emp.priority == "H":
            return pp_max
        mid = (pp_min + pp_max) / 2
        return round(mid / 2) * 2

    def block_is_available(self, df, name, start_slot, num_slots):
        end_slot = start_slot + num_slots - 1
        if end_slot > len(df):
            return False
        return df.loc[start_slot:end_slot, name].sum() == num_slots

    def can_assign_normal(self, emp, day_hours, week_hours, pp_hours, name, week_idx, pp_idx, day_key, block_hours):
        if day_hours[(name, day_key)] + block_hours > config.DAILY_SOFT_MAX:
            return False
        week_cap = config.RA_WEEK_MAX if emp.is_ra else config.NONRA_WEEK_MAX
        pp_cap = config.RA_PP_MAX if emp.is_ra else config.NONRA_PP_MAX
        if week_hours[(name, week_idx)] + block_hours > week_cap:
            return False
        if pp_hours[(name, pp_idx)] + block_hours > pp_cap:
            return False
        return True

    def can_assign_relaxed(self, emp, day_hours, week_hours, pp_hours, name, week_idx, pp_idx, day_key, block_hours):
        if day_hours[(name, day_key)] + block_hours > config.DAILY_HARD_MAX:
            return False
        week_cap = config.RA_WEEK_MAX if emp.is_ra else config.NONRA_WEEK_MAX
        pp_cap = config.RA_PP_MAX if emp.is_ra else config.NONRA_PP_MAX
        if week_hours[(name, week_idx)] + block_hours > week_cap:
            return False
        if pp_hours[(name, pp_idx)] + block_hours > pp_cap:
            return False
        return True

    def score_candidate(self, emp, name, week_idx, week_hours, pp_idx, pp_hours, day_key, day_hours, worked_days_count):
        w_cur = week_hours[(name, week_idx)]
        p_cur = pp_hours[(name, pp_idx)]
        w_tgt = self.weekly_target(emp)
        p_tgt = self.payperiod_target(emp)

        w_need = max(0.0, w_tgt - w_cur)
        p_need = max(0.0, p_tgt - p_cur)

        has_today = day_hours[(name, day_key)] > 0.0
        
        weights = config.WEIGHTS
        day_penalty = weights.get("day_penalty", 5.0) if has_today else 0.0
        diversity_bonus = max(0.0, 5 - worked_days_count[(name, week_idx)]) * weights.get("diversity", 0.5)

        pr_nudge = 0.0
        if emp.priority == "H":
            pr_nudge = weights.get("priority_h", 1.0)
        elif emp.priority == "L":
            pr_nudge = weights.get("priority_l", -1.0)

        return (w_need * weights.get("weekly_need", 2.0)) + \
               (p_need * weights.get("pp_need", 1.0)) + \
               diversity_bonus + pr_nudge - day_penalty

    def build_schedule(self, availability_csv_path, employees, schedule_start_date, time_of_slots):
        from utils import get_slot_info
        df = pd.read_csv(availability_csv_path, index_col=0)
        valid_names = {e.name for e in employees}
        df = df[[c for c in df.columns if c in valid_names]].copy()

        week_hours = defaultdict(float)
        pp_hours = defaultdict(float)
        day_hours = defaultdict(float)
        worked_days_count = defaultdict(int)
        day_worked_flag = defaultdict(set)
        
        current_shifts = [] 
        assignments = []

        total_slots = len(time_of_slots)
        res_slots = config.BLOCK_SLOTS_MIN
        
        current_slot_idx = 0
        emp_obj_map = {e.name: e for e in employees}

        while current_slot_idx < total_slots:
            if current_slot_idx + res_slots > total_slots:
                break
            
            is_contiguous = True
            for i in range(res_slots - 1):
                if time_of_slots[current_slot_idx + i + 1] - time_of_slots[current_slot_idx + i] != 900:
                    is_contiguous = False
                    current_slot_idx = current_slot_idx + i + 1
                    break
            
            if not is_contiguous:
                continue

            start_slot_1based = current_slot_idx + 1
            ts = time_of_slots[current_slot_idx]
            day_date, week_idx, pp_idx, start_t = get_slot_info(ts, schedule_start_date)
            day_key = day_date.isoformat()

            current_shifts = [s for s in current_shifts if s['end_slot'] > start_slot_1based]
            seats_to_fill = config.EMPLOYEES_PER_SLOT - len(current_shifts)
            
            for _ in range(seats_to_fill):
                active_names = [s['name'] for s in current_shifts]
                available = [name for name in df.columns if name not in active_names and self.block_is_available(df, name, start_slot_1based, res_slots)]
                
                if not available:
                    break

                chosen = None
                norm_ok = [n for n in available if self.can_assign_normal(emp_obj_map[n], day_hours, week_hours, pp_hours, n, week_idx, pp_idx, day_key, config.BLOCK_HOURS_MIN)]
                if norm_ok:
                    scored = [(self.score_candidate(emp_obj_map[n], n, week_idx, week_hours, pp_idx, pp_hours, day_key, day_hours, worked_days_count), n) for n in norm_ok]
                    scored.sort(reverse=True)
                    chosen = scored[0][1]
                else:
                    rel_ok = [n for n in available if self.can_assign_relaxed(emp_obj_map[n], day_hours, week_hours, pp_hours, n, week_idx, pp_idx, day_key, config.BLOCK_HOURS_MIN)]
                    if rel_ok:
                        scored = [(self.score_candidate(emp_obj_map[n], n, week_idx, week_hours, pp_idx, pp_hours, day_key, day_hours, worked_days_count), n) for n in rel_ok]
                        scored.sort(reverse=True)
                        chosen = scored[0][1]

                if chosen:
                    actual_hours = config.BLOCK_HOURS_MIN
                    actual_slots = res_slots
                    
                    max_ext_blocks = (config.BLOCK_HOURS_MAX - config.BLOCK_HOURS_MIN) // (res_slots // config.SLOTS_PER_HOUR)
                    for _ in range(max_ext_blocks):
                        next_start_idx = current_slot_idx + actual_slots
                        if next_start_idx + res_slots > total_slots:
                            break
                        
                        ts_curr = time_of_slots[next_start_idx - 1] 
                        ts_next = time_of_slots[next_start_idx]     
                        if (ts_next - ts_curr) != 900:
                            break

                        next_hours = actual_hours + (res_slots // config.SLOTS_PER_HOUR)
                        if self.block_is_available(df, chosen, next_start_idx + 1, res_slots) and \
                           self.can_assign_normal(emp_obj_map[chosen], day_hours, week_hours, pp_hours, chosen, week_idx, pp_idx, day_key, next_hours):
                            actual_hours = next_hours
                            actual_slots += res_slots
                        else:
                            break
                    
                    current_shifts.append({'name': chosen, 'end_slot': start_slot_1based + actual_slots})
                    
                    week_hours[(chosen, week_idx)] += actual_hours
                    pp_hours[(chosen, pp_idx)] += actual_hours
                    day_hours[(chosen, day_key)] += actual_hours
                    if day_key not in day_worked_flag[chosen]:
                        worked_days_count[(chosen, week_idx)] += 1
                        day_worked_flag[chosen].add(day_key)
                    
                    emp = emp_obj_map[chosen]
                    emp.hours_weekly = week_hours[(chosen, week_idx)]
                    emp.hours_payperiod = pp_hours[(chosen, pp_idx)]
            
            assigned_names = [s['name'] for s in current_shifts]
            end_ts = time_of_slots[current_slot_idx + res_slots - 1] + 900 
            _, _, _, end_t = get_slot_info(end_ts, schedule_start_date)
            
            assignments.append({
                "week": week_idx + 1,
                "pay_period": pp_idx + 1,
                "day": day_key,
                "start_time": start_t,
                "end_time": end_t,
                "employees": ", ".join(assigned_names),
                "seats_filled": len(assigned_names)
            })

            current_slot_idx += res_slots

        schedule_df = pd.DataFrame(assignments)
        schedule_df.to_csv("schedule.csv", index=False)

        print("\n=== Weekly Hours Summary ===")
        if not schedule_df.empty:
            total_seats = len(schedule_df) * config.EMPLOYEES_PER_SLOT
            filled_seats = schedule_df["seats_filled"].sum()
            fill_rate = (filled_seats / total_seats) * 100 if total_seats > 0 else 0

            active_data = []
            for _, row in schedule_df.iterrows():
                names = [n.strip() for n in str(row["employees"]).split(",") if n.strip()]
                for n in names:
                    active_data.append({
                        "employee": n,
                        "week": row["week"],
                        "pay_period": row["pay_period"],
                        "hours": (res_slots / config.SLOTS_PER_HOUR)
                    })
            
            if active_data:
                summary_df = pd.DataFrame(active_data)
                pivot = summary_df.pivot_table(index="employee", columns="week", values="hours", aggfunc="sum").fillna(0)
                print(pivot.sort_index())

                print("\n=== Pay-Period Hours Summary ===")
                pp_pivot = summary_df.pivot_table(index="employee", columns="pay_period", values="hours", aggfunc="sum").fillna(0)
                print(pp_pivot.sort_index())
                
                print(f"\n=== Schedule Metrics ===")
                print(f"Fill Rate: {fill_rate:.1f}% ({int(filled_seats)}/{total_seats} seats filled)")

                missing = sorted(list(set(valid_names) - set(summary_df["employee"].unique())))
                if missing:
                    print(f"Note: No shifts assigned to {', '.join(missing)}")
            else:
                print("No employees assigned")

        return schedule_df
