# checker_bot.py
import csv
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APPOINTMENTS_CSV = Path("appointments.csv")
STATE_PATH = Path("checker_state.json")


def send_discord_webhook(webhook_url: str, title: str, body: str) -> str:
    if not webhook_url or not webhook_url.strip():
        raise ValueError("DISCORD_WEBHOOK_URL is empty or not set")
    description = body
    if len(description) > 4090:
        description = description[:4087] + "..."
    payload = {
        "embeds": [
            {
                "title": title,
                "description": description,
                "color": 0x5865F2,
            }
        ]
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ICBCAppointmentBot/1.0 (+local)",
    }
    req = urllib.request.Request(
        webhook_url.strip(),
        data=data,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Discord webhook failed: HTTP {e.code} {e.reason} {detail}"
        ) from e
    return "Discord notification sent\n" + body


def load_appointments(file_path: Path) -> dict[str, list[str]]:
    appointments: dict[str, list[str]] = {}
    if not file_path.is_file():
        return appointments

    with file_path.open(mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            location = row["Location"]
            date_time = f"{row['Date']} {row['Time']}"
            appointments.setdefault(location, []).append(date_time)
    return appointments


def slot_key(location: str, date_time: str) -> str:
    return f"{location}|{date_time}"


def load_state() -> tuple[set[str], bool]:
    if not STATE_PATH.is_file():
        return set(), False
    try:
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set(), False
    keys = raw.get("notified_slot_keys")
    notified = {str(k) for k in keys} if isinstance(keys, list) else set()
    if "baseline_done" in raw:
        baseline_done = bool(raw["baseline_done"])
    else:
        # Older state files without the flag: assume first-time setup already happened.
        baseline_done = True
    return notified, baseline_done


def save_state(notified: set[str], baseline_done: bool) -> None:
    STATE_PATH.write_text(
        json.dumps(
            {
                "notified_slot_keys": sorted(notified),
                "baseline_done": baseline_done,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def all_slot_keys(appointments: dict[str, list[str]]) -> set[str]:
    out: set[str] = set()
    for location, slots in appointments.items():
        for dt in slots:
            out.add(slot_key(location, dt))
    return out


def is_empty_snapshot(appointments: dict[str, list[str]]) -> bool:
    if not appointments:
        return True
    return all(len(slots) == 0 for slots in appointments.values())


def parse_slot_sort_key(date_time: str) -> tuple:
    date_str, time_str = date_time.split(maxsplit=1)
    return (date_str, time_str)


def check_for_earlier_slots(
    old_appointments: dict[str, list[str]],
    new_appointments: dict[str, list[str]],
) -> dict[str, list[str]]:
    earlier_slots: dict[str, list[str]] = {}
    for location, new_slots in new_appointments.items():
        old_slots = old_appointments.get(location, [])
        old_earliest = min(old_slots, default=None)
        for new_date_time in new_slots:
            if old_earliest is None or new_date_time < old_earliest:
                earlier_slots.setdefault(location, []).append(new_date_time)
    for location in list(earlier_slots.keys()):
        unique = sorted(set(earlier_slots[location]), key=parse_slot_sort_key)
        earlier_slots[location] = unique
    return earlier_slots


def filter_already_notified(
    earlier_slots: dict[str, list[str]], notified: set[str]
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for location, slots in earlier_slots.items():
        fresh = [s for s in slots if slot_key(location, s) not in notified]
        if fresh:
            out[location] = fresh
    return out


def get_day_of_week(date_str: str) -> str:
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%A")


def format_notification(earlier_slots: dict[str, list[str]]) -> tuple[str, str]:
    if len(earlier_slots) == 1:
        location = next(iter(earlier_slots))
        title = f"ICBC — {location}"
        lines: list[str] = []
        for slot in earlier_slots[location]:
            date_str, time_str = slot.split(maxsplit=1)
            day_of_week = get_day_of_week(date_str)
            lines.append(f"{date_str} ({day_of_week}) {time_str}")
        body = "Earlier opening(s) than your last snapshot:\n" + "\n".join(
            f"- {line}" for line in lines
        )
        return title, body

    title = "ICBC — earlier slots (multiple locations)"
    parts: list[str] = ["Earlier opening(s) than your last snapshot:\n"]
    for location, slots in sorted(earlier_slots.items()):
        parts.append(f"**{location}**")
        for slot in slots:
            date_str, time_str = slot.split(maxsplit=1)
            day_of_week = get_day_of_week(date_str)
            parts.append(f"- {date_str} ({day_of_week}) {time_str}")
        parts.append("")
    return title, "\n".join(parts).strip()


def main() -> None:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    old_appointments = load_appointments(APPOINTMENTS_CSV)
    os.system(f'"{sys.executable}" icbc-appointment.py')

    new_appointments = load_appointments(APPOINTMENTS_CSV)
    notified, baseline_done = load_state()

    # CSV with no matching rows is still "empty"; that must not re-trigger baseline every run.
    if not is_empty_snapshot(old_appointments):
        baseline_done = True

    if is_empty_snapshot(old_appointments) and not baseline_done:
        notified |= all_slot_keys(new_appointments)
        save_state(notified, baseline_done=True)
        print(
            "Baseline: first snapshot (empty CSV); recorded current slots, no Discord notification."
        )
        return

    earlier_slots = check_for_earlier_slots(old_appointments, new_appointments)
    to_notify = filter_already_notified(earlier_slots, notified)

    if to_notify:
        title, body = format_notification(to_notify)
        print(send_discord_webhook(webhook_url, title, body))
        for loc, slots in to_notify.items():
            for s in slots:
                notified.add(slot_key(loc, s))
        save_state(notified, baseline_done=True)
    else:
        print("No new earlier slots to notify (or nothing earlier than last snapshot).")
        save_state(notified, baseline_done=True)


if __name__ == "__main__":
    while True:
        main()
        wait_time = random.uniform(180, 300)
        print(f"Waiting for {wait_time:.2f} seconds before running the next check...")
        time.sleep(wait_time)
