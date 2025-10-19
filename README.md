# When2Meet Analyzer

A lightweight Python-based tool that scrapes When2Meet availability data and automatically generates optimized schedules based on user-defined conditions.

This was built to increase efficiency during my time as an Operations Manager at TCNJ, serrving as an assistant to help us schedule our desk assistants. However, it is flexible enough to adapt for any scheduling scenario, including but not limited to clubs, classes, research groups, or projects.

---

## Features

- **Scrapes When2Meet data automatically:** Parses participant availability directly from a shared When2Meet link and generates a CSV file based off it
- **Generates optimal meeting times:** Finds the best time slots based on certain conditions (like whether the person has another on-campus job, prefers more/less hours, etc.)
- **Exportable results:** Outputs results as CSV for quick sharing and analysis

---

## How It Works

1. Parses your When2Meet event link for internal scheduling data
4. Applies scheduling algorithm based on user availability and given conditions
5. Outputs recommended scheduling times

---

## Installation & Execution

```bash
git clone https://github.com/BryanWieschenberg/When2Meet-Analyzer.git
cd When2Meet-Analyzer
python main.py <when2meet_url> <start_date MM:dd> <end_date MM:dd> <start_hour ttAM/PM> <end_hour ttAM/PM>
