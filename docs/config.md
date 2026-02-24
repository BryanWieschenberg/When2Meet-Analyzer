# Configuration Guide

The `config.json` file controls the scheduling algorithm's behavior, employee settings, and various constraints.

## Constraints

This section defines the rules the scheduler must follow.

### Role-Based Hour Caps

- **`ra`**: Settings for Resident Assistants (or other restricted roles)
  - `week_max`: Maximum hours per week
  - `pp_max`: Maximum hours per pay period
- **`non_ra`**: Settings for standard employees
  - `week_max`: Maximum hours per week
  - `pp_max`: Maximum hours per pay period

### Global Constraints

- **`all`**: Minimum targets for all active participants
  - `week_min`: Minimum target hours per week
  - `pp_min`: Minimum target hours per pay period
- **`daily_soft_max`**: The algorithm tries not to exceed this many hours per day
- **`daily_hard_max`**: The absolute maximum hours an employee can work in a single day
- **`slots_per_hour`**: Number of When2Meet slots in one hour (usually 4 for 15-minute intervals)

### Shift & Capacity Settings

- **`block_hours_min`**: The minimum duration of any single assigned shift (e.g., 2 hours)
- **`block_hours_max`**: The maximum duration a shift can be extended to (e.g., 4 hours)
- **`employees_per_slot`**: How many people should be working at the same time for any given time block

### Algorithm Weights

These values influence how the algorithm scores potential candidates for a shift. Higher values make that factor more important.

- **`weekly_need`**: Priority given to meeting the weekly hour target.
- **`pp_need`**: Priority given to meeting the pay-period hour target.
- **`diversity`**: Bonus for spreading shifts across different days of the week
- **`priority_h` / `priority_l`**: Nudges for employees marked with High (H) or Low (L) priority
- **`day_penalty`**: Penalty for assigning multiple shifts to the same person on the same day

## Employees

This section defines a list of employee objects who have specific settings.

- **`name`**: The exact name of the employee as it appears on that When2Meet link
- **`is_ra`**: `true` if this person is an RA and should follow RA hour caps; `false` otherwise (default: `false`)
- **`priority`**: Nudge the algorithm to give this person more or fewer shifts (default: `M`)
  - `H`: High Priority (more likely to get shifts)
  - `M`: Medium Priority (standard)
  - `L`: Low Priority (less likely to get shifts)
