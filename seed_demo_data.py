"""
Seed realistic demo data into SID's file-based system.
Creates a full week of activity across multiple vendors so the dashboard
actually has something meaningful to display.
"""

import json
import os
from datetime import datetime, timedelta
import random
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Vendors we'll seed data for ───
VENDORS = ["FBSPL", "ElevateReach", "CollarSearch", "NextPlayRecruitment"]

# ─── Realistic job postings by category ───
JOBS = {
    "SFG": [
        {"title": "Insurance Agent", "salary": "$55K - $75K/yr", "location": {"type": "Remote", "region": "US"}},
        {"title": "Financial Advisor", "salary": "$60K - $90K/yr", "location": {"type": "Remote", "region": "US"}},
        {"title": "Benefits Coordinator", "salary": "$45K - $60K/yr", "location": {"type": "Hybrid", "region": "US"}},
        {"title": "Claims Analyst", "salary": "$50K - $70K/yr", "location": {"type": "Remote", "region": "US"}},
    ],
    "MS": [
        {"title": "Account Manager", "salary": "$65K - $85K/yr", "location": {"type": "Remote", "region": "US"}},
        {"title": "Business Development Rep", "salary": "$50K - $70K/yr", "location": {"type": "Remote", "region": "US"}},
        {"title": "Operations Manager", "salary": "$70K - $95K/yr", "location": {"type": "Hybrid", "region": "US"}},
    ],
    "NYL": [
        {"title": "Life Insurance Agent", "salary": "$55K - $80K/yr", "location": {"type": "Remote", "region": "US"}},
        {"title": "Retirement Planning Specialist", "salary": "$60K - $85K/yr", "location": {"type": "Remote", "region": "US"}},
    ],
    "TECH": [
        {"title": "Junior Web Developer", "salary": "$55K - $75K/yr", "location": {"type": "Remote", "region": "US"}},
        {"title": "IT Support Specialist", "salary": "$40K - $55K/yr", "location": {"type": "On-site", "region": "US"}},
        {"title": "Data Entry Clerk", "salary": "$35K - $45K/yr", "location": {"type": "Remote", "region": "US"}},
    ],
}

ACCOUNTS = [
    {"id": "indeed-usd", "platform": "Indeed", "label": "Indeed - USD", "currency": "USD"},
    {"id": "indeed-inr", "platform": "Indeed", "label": "Indeed - INR", "currency": "INR"},
    {"id": "linkedin", "platform": "LinkedIn", "label": "LinkedIn", "currency": "USD"},
]

BUDGETS = {
    "USD": ["$15/day, $30 max", "$20/day, $40 max", "$25/day, $50 max", "$10/day, $20 max"],
    "INR": ["₹460/day, ₹920 max", "₹600/day, ₹1200 max", "₹350/day, ₹700 max"],
}

BENEFITS = [
    ["Health", "Vision", "Dental", "401(k)", "PTO"],
    ["Health", "Dental", "Flexible Schedule"],
    ["Health", "Vision", "Dental", "Life Insurance", "PTO", "Remote Work"],
    ["Health", "401(k)", "Flexible Schedule", "PTO"],
]

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def make_uid(vendor, cat, idx, ts):
    return f"{vendor}-{cat}-{idx}-{int(ts.timestamp() * 1000)}"

def seed_week():
    """Seed Mon-Sun of the current week with realistic data."""
    today = datetime(2026, 3, 29, 12, 0, 0)  # Sunday March 29, 2026

    # Find Monday of this week
    monday = today - timedelta(days=today.weekday())  # Monday March 23

    print(f"Seeding week: {monday.strftime('%b %d')} - {(monday + timedelta(days=6)).strftime('%b %d, %Y')}")

    # Plan the week: which vendors get assignments on which days
    # Realistic: heavy Mon-Wed, lighter Thu-Fri, minimal Sat, nothing Sun
    weekly_plan = {
        0: {"FBSPL": 4, "ElevateReach": 3, "CollarSearch": 2, "NextPlayRecruitment": 2},  # Mon
        1: {"FBSPL": 3, "ElevateReach": 2, "CollarSearch": 3, "NextPlayRecruitment": 1},  # Tue
        2: {"FBSPL": 2, "ElevateReach": 3, "CollarSearch": 1, "NextPlayRecruitment": 2},  # Wed
        3: {"FBSPL": 3, "ElevateReach": 1, "CollarSearch": 2, "NextPlayRecruitment": 0},  # Thu
        4: {"FBSPL": 2, "ElevateReach": 2, "CollarSearch": 0, "NextPlayRecruitment": 1},  # Fri
        5: {"FBSPL": 1, "ElevateReach": 0, "CollarSearch": 0, "NextPlayRecruitment": 0},  # Sat
        6: {},  # Sun - nothing
    }

    # Track active postings across the week for closing
    all_assignments = {}  # vendor -> list of all assignments created this week

    for day_offset in range(7):
        current_day = monday + timedelta(days=day_offset)
        date_str = current_day.strftime("%Y-%m-%d")
        day_plan = weekly_plan.get(day_offset, {})

        print(f"\n  {current_day.strftime('%A %b %d')}:")

        for vendor, num_assignments in day_plan.items():
            if num_assignments == 0:
                continue

            if vendor not in all_assignments:
                all_assignments[vendor] = []

            # Create assignments
            assignments = []
            for i in range(num_assignments):
                cat = random.choice(list(JOBS.keys()))
                job = random.choice(JOBS[cat])
                account = random.choice(ACCOUNTS)
                currency = account["currency"]
                budget = random.choice(BUDGETS.get(currency, BUDGETS["USD"]))

                # Close date: 2-4 days after assignment
                close_offset = random.randint(2, 4)
                close_date = current_day + timedelta(days=close_offset)

                # Assignment time: morning hours ET
                hour = random.randint(7, 10)
                minute = random.randint(0, 59)
                assigned_at = current_day.replace(hour=hour, minute=minute)

                uid = make_uid(vendor, cat, i, assigned_at)

                assignment = {
                    "id": f"{cat}-{i}",
                    "uid": uid,
                    "title": job["title"],
                    "category": cat,
                    "account": account["id"],
                    "budget": budget,
                    "budgetInstructions": budget,
                    "closeDate": close_date.strftime("%Y-%m-%d"),
                    "location": job["location"],
                    "salary": job["salary"],
                    "benefits": random.choice(BENEFITS),
                    "description": f"<p>We are seeking a qualified {job['title']} to join our team.</p>",
                    "status": "active",
                    "assignedAt": assigned_at.isoformat(),
                    "assignedBy": "manager",
                }

                assignments.append(assignment)
                all_assignments[vendor].append({
                    "assignment": assignment,
                    "assigned_date": date_str,
                })

            # Save assignments file
            assignments_dir = os.path.join(BASE_DIR, "assignments", vendor.lower())
            ensure_dir(assignments_dir)

            assignments_data = {
                "date": date_str,
                "vendor": vendor,
                "assignments": assignments,
            }

            filepath = os.path.join(assignments_dir, f"{date_str}.json")
            with open(filepath, "w") as f:
                json.dump(assignments_data, f, indent=2)

            print(f"    {vendor}: {num_assignments} assignments")

            # ─── Generate activity (posting + closing) ───
            # Vendors typically post same day or next day
            # And some older postings close
            posted_items = []
            closed_items = []

            # Post ~70% of today's assignments (realistic: not everything gets posted same day)
            for a_info in all_assignments[vendor]:
                a = a_info["assignment"]
                a_date = a_info["assigned_date"]

                # Only post things assigned today or yesterday
                a_day = datetime.strptime(a_date, "%Y-%m-%d")
                days_since = (current_day - a_day).days

                if days_since == 0 and random.random() < 0.6:
                    # Post same day, afternoon
                    post_hour = random.randint(11, 16)
                    post_time = current_day.replace(hour=post_hour, minute=random.randint(0, 59))

                    posted_items.append({
                        "id": a["id"],
                        "title": a["title"],
                        "category": a["category"],
                        "account": a["account"],
                        "indeedLink": f"https://www.indeed.com/job/{a['uid']}",
                        "postedAt": post_time.isoformat(),
                    })
                    a["status"] = "posted"

                elif days_since == 1 and a["status"] == "active" and random.random() < 0.8:
                    # Post next day morning
                    post_hour = random.randint(8, 11)
                    post_time = current_day.replace(hour=post_hour, minute=random.randint(0, 59))

                    posted_items.append({
                        "id": a["id"],
                        "title": a["title"],
                        "category": a["category"],
                        "account": a["account"],
                        "indeedLink": f"https://www.indeed.com/job/{a['uid']}",
                        "postedAt": post_time.isoformat(),
                    })
                    a["status"] = "posted"

                # Close postings that hit their close date
                if a["status"] == "posted" and a["closeDate"] == date_str:
                    applicants = random.randint(8, 45)
                    budget_spent = f"${random.randint(15, 60):.2f}"
                    close_time = current_day.replace(hour=random.randint(14, 17), minute=random.randint(0, 59))

                    closed_items.append({
                        "id": a["id"],
                        "title": a["title"],
                        "category": a["category"],
                        "postedDate": a_date,
                        "closedDate": date_str,
                        "applicants": applicants,
                        "budgetSpent": budget_spent,
                        "indeedLink": f"https://www.indeed.com/job/{a['uid']}",
                        "closedAt": close_time.isoformat(),
                    })
                    a["status"] = "closed"

            # Save activity if anything happened
            if posted_items or closed_items:
                activity_dir = os.path.join(BASE_DIR, "activity", vendor.lower())
                ensure_dir(activity_dir)

                activity_data = {
                    "date": date_str,
                    "vendor": vendor,
                    "posted": posted_items,
                    "closed": closed_items,
                }

                filepath = os.path.join(activity_dir, f"{date_str}.json")
                with open(filepath, "w") as f:
                    json.dump(activity_data, f, indent=2)

                if posted_items:
                    print(f"    {vendor}: {len(posted_items)} posted")
                if closed_items:
                    print(f"    {vendor}: {len(closed_items)} closed ({sum(c['applicants'] for c in closed_items)} applicants)")

    # ─── Update the assignments files to reflect final statuses ───
    print("\n  Updating assignment statuses...")
    for vendor, items in all_assignments.items():
        # Group by date
        by_date = {}
        for item in items:
            d = item["assigned_date"]
            if d not in by_date:
                by_date[d] = []
            by_date[d].append(item["assignment"])

        for date_str, assignments in by_date.items():
            assignments_dir = os.path.join(BASE_DIR, "assignments", vendor.lower())
            filepath = os.path.join(assignments_dir, f"{date_str}.json")

            data = {
                "date": date_str,
                "vendor": vendor,
                "assignments": assignments,
            }
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

    # ─── Seed some alerts ───
    print("\n  Seeding alerts...")
    alerts_dir = os.path.join(BASE_DIR, "alerts")
    ensure_dir(alerts_dir)

    alert_templates = [
        {"type": "missing_csv", "title": "Missing EOD Upload", "message": "No end-of-day screenshot uploaded for yesterday.", "priority": "medium"},
        {"type": "action_required", "title": "2 Postings Expiring Tomorrow", "message": "Insurance Agent and Financial Advisor close dates are tomorrow. Review or extend.", "priority": "high"},
        {"type": "info", "title": "Resume ZIP Processed", "message": "24 candidates extracted from latest upload.", "priority": "low"},
        {"type": "warning", "title": "Budget Running High", "message": "Indeed INR account spent 85% of weekly budget.", "priority": "high"},
    ]

    for vendor in ["FBSPL", "ElevateReach"]:
        num_alerts = random.randint(1, 3)
        alerts = []
        for i in range(num_alerts):
            template = random.choice(alert_templates)
            alerts.append({
                "id": f"alert-{vendor.lower()}-{i}",
                "type": template["type"],
                "title": template["title"],
                "message": template["message"],
                "priority": template["priority"],
                "created_at": (today - timedelta(hours=random.randint(1, 48))).isoformat(),
                "dismissed": False,
            })

        filepath = os.path.join(alerts_dir, f"{vendor}.json")
        with open(filepath, "w") as f:
            json.dump({"alerts": alerts}, f, indent=2)
        print(f"    {vendor}: {num_alerts} alerts")

    print("\nDone! Demo data seeded for the full week.")
    print("Restart or refresh the dashboard to see the data.")


if __name__ == "__main__":
    seed_week()
