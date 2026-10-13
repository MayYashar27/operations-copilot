import json

import random

from datetime import datetime, timedelta

from pathlib import Path





random.seed(42)



DATA_DIR = Path(__file__).parent / "data"

REQUESTS_FILE = DATA_DIR / "requests.json"

MONITOR_FILE = DATA_DIR / "monitor_snapshots.json"



WORK_START_HOUR = 8

WORK_END_HOUR = 17

REQUESTS_PER_DAY = 200



CLASSIFICATIONS = [

    "login_issue",

    "payment_issue",

    "technical_issue",

    "general_information",

]



AGENTS = [f"A{i:02d}" for i in range(1, 16)]





NORMAL_CONTENT = {

    "login_issue": [

        (

            "Password reset request",

            "Customer forgot the account password and requested assistance resetting it."

        ),

        (

            "Incorrect password",

            "Customer could not sign in because an incorrect password was entered."

        ),

        (

            "Account access question",

            "Customer requested assistance accessing the account."

        ),

    ],

    "payment_issue": [

        (

            "Payment question",

            "Customer contacted support regarding a recent payment."

        ),

        (

            "Pending transaction",

            "Customer asked about a transaction that is still pending."

        ),

        (

            "Billing inquiry",

            "Customer requested clarification regarding a charge."

        ),

    ],

    "technical_issue": [

        (

            "Technical assistance",

            "Customer requested assistance with a technical issue."

        ),

        (

            "Browser problem",

            "Customer reported difficulty using the service from the browser."

        ),

        (

            "Notification issue",

            "Customer reported that a notification was not received."

        ),

    ],

    "general_information": [

        (

            "Service information",

            "Customer requested general information about the service."

        ),

        (

            "Operating hours",

            "Customer asked about service center operating hours."

        ),

        (

            "Account information",

            "Customer requested information about account settings."

        ),

    ],

}





DAY_1_LOGIN_INCIDENT = [

    (

        "Cannot access account after update",

        "Customer reported being unable to access the account after updating the application."

    ),

    (

        "Login fails after app update",

        "Customer reported repeated login failures after installing the latest application update."

    ),

    (

        "Unable to sign in",

        "Customer could not sign in after updating the application. Standard troubleshooting did not resolve the issue."

    ),

    (

        "Login stopped working",

        "Customer reported that login stopped working after the latest application version was installed."

    ),

]





DAY_2_MOBILE_INCIDENT = {

    "login_issue": [

        (

            "Mobile app freezes during login",

            "Customer reports that the mobile application freezes while attempting to sign in."

        ),

        (

            "App returns to login screen",

            "Customer enters valid credentials but the mobile application returns to the login screen."

        ),

    ],

    "payment_issue": [

        (

            "Payment page not loading",

            "Customer reports that the payment page in the mobile application remains blank."

        ),

        (

            "Payment button not responding",

            "Customer cannot complete payment because the mobile application becomes unresponsive."

        ),

    ],

    "technical_issue": [

        (

            "Mobile application closes",

            "Customer reports that the mobile application closes unexpectedly during use."

        ),

        (

            "Blank screen in mobile app",

            "Customer reports blank screens across multiple areas of the mobile application."

        ),

    ],

    "general_information": [

        (

            "Cannot view account information",

            "Customer cannot access information because pages in the mobile application fail to load."

        ),

        (

            "Information section unavailable",

            "Customer reports that the information section in the mobile application remains stuck loading."

        ),

    ],

}





def random_time_in_hour(date_string: str, hour: int) -> datetime:

    base = datetime.fromisoformat(date_string).replace(

        hour=hour,

        minute=0,

        second=0,

        microsecond=0,

    )



    return base + timedelta(

        minutes=random.randint(0, 59),

        seconds=random.randint(0, 59),

    )





def build_request(

    request_id: int,

    request_time: datetime,

    classification: str,

    subject: str,

    documentation: str,

    incident: bool = False,

) -> dict:



    wait_time = random.randint(2, 7)



    if incident:

        wait_time = random.randint(8, 18)



    transferred = (

        random.random() < 0.75

        if incident

        else random.random() < 0.20

    )



    return {

        "request_id": request_id,

        "request_time": request_time.isoformat(),

        "agent_id": random.choice(AGENTS),

        "subject": subject,

        "classification": classification,

        "wait_time_minutes": wait_time,

        "status": "transferred" if transferred else "resolved",

        "transferred_to": (

            "technical_support"

            if transferred

            else None

        ),

        "documentation": documentation,

    }





def generate_day(

    date_string: str,

    request_id_start: int,

    incident_hour: int,

    incident_type: str,

) -> list[dict]:



    requests = []

    request_id = request_id_start



    # Normal hourly distribution.

    hourly_counts = {

        8: 18,

        9: 19,

        10: 20,

        11: 19,

        12: 20,

        13: 20,

        14: 20,

        15: 21,

        16: 18,

    }



    # Create a visible volume anomaly.

    hourly_counts[incident_hour] = 45



    # Reduce other hours so the day stays close to ~200 requests.

    hours_to_reduce = [

        hour

        for hour in hourly_counts

        if hour != incident_hour

    ]



    while sum(hourly_counts.values()) > REQUESTS_PER_DAY:

        hour = random.choice(hours_to_reduce)



        if hourly_counts[hour] > 12:

            hourly_counts[hour] -= 1



    for hour, count in hourly_counts.items():



        for _ in range(count):



            is_incident_window = hour == incident_hour



            # DAY 1:

            # dominant login classification + update pattern.

            if incident_type == "login_update" and is_incident_window:



                if random.random() < 0.70:

                    classification = "login_issue"

                    subject, documentation = random.choice(

                        DAY_1_LOGIN_INCIDENT

                    )

                    incident = True

                else:

                    classification = random.choice(

                        CLASSIFICATIONS

                    )

                    subject, documentation = random.choice(

                        NORMAL_CONTENT[classification]

                    )

                    incident = False



            # DAY 2:

            # balanced classifications but common mobile-app pattern.

            elif incident_type == "cross_category_mobile" and is_incident_window:



                classification = random.choice(

                    CLASSIFICATIONS

                )



                if random.random() < 0.75:

                    subject, documentation = random.choice(

                        DAY_2_MOBILE_INCIDENT[classification]

                    )

                    incident = True

                else:

                    subject, documentation = random.choice(

                        NORMAL_CONTENT[classification]

                    )

                    incident = False



            # DAY 3:

            # no semantic incident.

            # The problem will exist in monitor/staffing data.

            else:

                classification = random.choice(

                    CLASSIFICATIONS

                )

                subject, documentation = random.choice(

                    NORMAL_CONTENT[classification]

                )

                incident = (

                    incident_type == "capacity"

                    and is_incident_window

                )



            request_time = random_time_in_hour(

                date_string,

                hour,

            )



            requests.append(

                build_request(

                    request_id=request_id,

                    request_time=request_time,

                    classification=classification,

                    subject=subject,

                    documentation=documentation,

                    incident=incident,

                )

            )



            request_id += 1



    return requests





def generate_monitor_day(

    date_string: str,

    incident_hour: int,

    incident_type: str,

) -> list[dict]:



    snapshots = []



    current = datetime.fromisoformat(date_string).replace(

        hour=WORK_START_HOUR,

        minute=0,

        second=0,

        microsecond=0,

    )



    end = datetime.fromisoformat(date_string).replace(

        hour=WORK_END_HOUR,

        minute=0,

        second=0,

        microsecond=0,

    )



    answered_calls = 0

    abandoned_calls = 0



    while current <= end:



        in_incident_hour = current.hour == incident_hour



        if incident_type == "capacity" and in_incident_hour:

            agents_on_shift = 8

            agents_on_calls = random.randint(7, 8)

            available_agents = max(

                agents_on_shift - agents_on_calls,

                0,

            )

            average_wait = round(

                random.uniform(10, 17),

                2,

            )

            abandoned_calls += random.randint(2, 5)



        elif in_incident_hour:

            agents_on_shift = 12

            agents_on_calls = random.randint(9, 12)

            available_agents = max(

                agents_on_shift - agents_on_calls,

                0,

            )

            average_wait = round(

                random.uniform(7, 13),

                2,

            )

            abandoned_calls += random.randint(1, 3)



        else:

            agents_on_shift = 12

            agents_on_calls = random.randint(5, 9)

            available_agents = (

                agents_on_shift - agents_on_calls

            )

            average_wait = round(

                random.uniform(2, 6),

                2,

            )

            abandoned_calls += random.randint(0, 1)



        answered_calls += random.randint(6, 12)



        snapshots.append({

            "timestamp": current.isoformat(),

            "agents_on_shift": agents_on_shift,

            "agents_on_calls": agents_on_calls,

            "available_agents": available_agents,

            "average_wait_time_minutes": average_wait,

            "answered_calls": answered_calls,

            "abandoned_calls": abandoned_calls,

        })



        current += timedelta(minutes=5)



    return snapshots





def main():



    DATA_DIR.mkdir(

        parents=True,

        exist_ok=True,

    )



    scenarios = [

        (

            "2026-08-25",

            10001,

            12,

            "login_update",

        ),

        (

            "2026-08-26",

            20001,

            14,

            "cross_category_mobile",

        ),

        (

            "2026-08-27",

            30001,

            15,

            "capacity",

        ),

    ]



    all_requests = []

    all_monitor = []



    for (

        date_string,

        request_id_start,

        incident_hour,

        incident_type,

    ) in scenarios:



        all_requests.extend(

            generate_day(

                date_string,

                request_id_start,

                incident_hour,

                incident_type,

            )

        )



        all_monitor.extend(

            generate_monitor_day(

                date_string,

                incident_hour,

                incident_type,

            )

        )



    all_requests.sort(

        key=lambda request: request["request_time"]

    )



    all_monitor.sort(

        key=lambda snapshot: snapshot["timestamp"]

    )



    with REQUESTS_FILE.open(

        "w",

        encoding="utf-8",

    ) as file:

        json.dump(

            all_requests,

            file,

            indent=2,

            ensure_ascii=False,

        )



    with MONITOR_FILE.open(

        "w",

        encoding="utf-8",

    ) as file:

        json.dump(

            all_monitor,

            file,

            indent=2,

            ensure_ascii=False,

        )



    print(

        f"Generated {len(all_requests)} requests."

    )



    print(

        f"Generated {len(all_monitor)} monitor snapshots."

    )



    print(f"Requests: {REQUESTS_FILE}")

    print(f"Monitor:  {MONITOR_FILE}")







# --- Agent Performance Intelligence extension ---
# Existing request and monitor schemas remain backward-compatible.
AGENT_SHIFTS_FILE = DATA_DIR / "agent_shifts.json"
GROUND_TRUTH_FILE = DATA_DIR / "demo_ground_truth.json"  # Never feed to the LLM.

EXTRA_DATES = ["2026-08-28", "2026-08-31", "2026-09-01", "2026-09-02",
               "2026-09-03", "2026-09-04", "2026-09-07"]
ALL_DATES = ["2026-08-25", "2026-08-26", "2026-08-27"] + EXTRA_DATES
DESTINATIONS = ["technical_support", "billing", "back_office", "supervisor"]


def choose_agent(day_index, classification):
    # A09 receives a higher share of complex technical cases and fewer cases overall.
    weights = [0.70 if a == "A09" else 1.0 for a in AGENTS]
    if classification == "technical_issue":
        weights[AGENTS.index("A09")] = 2.8
    return random.choices(AGENTS, weights=weights, k=1)[0]


def enrich_request(req, day_index):
    classification = req["classification"]
    agent = choose_agent(day_index, classification)
    req["agent_id"] = agent
    transferred = req["status"] == "transferred"

    # A04 progressively transfers more cases, concentrating on Technical Support.
    if agent == "A04":
        transferred = random.random() < (0.20 + 0.055 * day_index)
    elif agent == "A09":
        transferred = random.random() < (0.45 if classification == "technical_issue" else 0.17)
    elif agent == "A07":
        transferred = random.random() < (0.18 + 0.015 * day_index)

    destination = None
    if transferred:
        destination = random.choices(DESTINATIONS, weights=[5, 3, 2, 1], k=1)[0]
        if agent == "A04" and day_index >= 5:
            destination = random.choices(DESTINATIONS, weights=[17, 1, 1, 1], k=1)[0]
    req["status"] = "transferred" if transferred else "resolved"
    req["transferred_to"] = destination
    req["resolved_first_line"] = not transferred

    # Handling time is distinct from customer wait time.
    handling = random.uniform(4.0, 8.0)
    if classification == "technical_issue":
        handling += random.uniform(2.0, 5.0)
    if agent == "A09" and classification == "technical_issue":
        handling += random.uniform(3.0, 6.0)
    if agent == "A07":
        handling *= max(0.48, 1.0 - day_index * 0.065)
    req["handling_time_minutes"] = round(handling, 2)

    # Documentation describes the agent's work, not just the customer's complaint.
    customer_description = req["documentation"]
    action = ("Escalated to " + destination.replace("_", " ") + " for follow-up."
              if transferred else "Verified details and resolved the request on first line.")
    req["customer_description"] = customer_description
    req["documentation"] = f"{customer_description} {action}"
    if agent == "A07" and day_index >= 5 and random.random() < 0.82:
        req["documentation"] = random.choice([
            "Handled.", "Customer contacted support. Done.", "Issue checked."
        ])
    return req


def generate_agent_shifts(date_string):
    # Synthetic scheduled hours, not inferred from number of handled requests.
    shifts = []
    for agent in AGENTS:
        start = 8 if int(agent[-2:]) % 2 else 9
        end = 17
        shifts.append({
            "date": date_string, "agent_id": agent,
            "shift_start": f"{date_string}T{start:02d}:00:00",
            "shift_end": f"{date_string}T{end:02d}:00:00",
            "scheduled_hours": end - start
        })
    return shifts


def generate_normal_day(date_string, id_start):
    # Reuse the existing generator's distribution without introducing another incident.
    requests = generate_day(date_string, id_start, 12, "normal")
    # Restore the normal hourly distribution by moving the synthetic noon spike
    # across working hours; total volume remains unchanged.
    noon_requests = [r for r in requests if datetime.fromisoformat(r["request_time"]).hour == 12]
    for req in noon_requests[:25]:
        target_hour = random.choice([8, 9, 10, 11, 13, 14, 15, 16])
        req["request_time"] = random_time_in_hour(date_string, target_hour).isoformat()
    return requests


def generate_normal_monitor_day(date_string):
    # No incident flag: all snapshots should follow normal staffing patterns.
    snapshots = generate_monitor_day(date_string, -1, "normal")
    return snapshots


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    scenarios = [
        ("2026-08-25", 10001, 12, "login_update"),
        ("2026-08-26", 20001, 14, "cross_category_mobile"),
        ("2026-08-27", 30001, 15, "capacity"),
    ]
    all_requests, all_monitor, all_shifts = [], [], []
    for day_index, date_string in enumerate(ALL_DATES):
        if day_index < 3:
            date, id_start, incident_hour, incident_type = scenarios[day_index]
            requests = generate_day(date, id_start, incident_hour, incident_type)
            monitor = generate_monitor_day(date, incident_hour, incident_type)
        else:
            requests = generate_normal_day(date_string, (day_index + 1) * 10000 + 1)
            monitor = generate_normal_monitor_day(date_string)
        all_requests.extend(enrich_request(r, day_index) for r in requests)
        all_monitor.extend(monitor)
        all_shifts.extend(generate_agent_shifts(date_string))

    all_requests.sort(key=lambda r: r["request_time"])
    all_monitor.sort(key=lambda r: r["timestamp"])
    for path, data in [
        (REQUESTS_FILE, all_requests), (MONITOR_FILE, all_monitor),
        (AGENT_SHIFTS_FILE, all_shifts),
    ]:
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)

    # Evaluation-only labels. Keep this file OUT of agent prompts and tool context.
    truth = {
        "operational_incidents": {
            "2026-08-25": "12:00-13:00 login issues after application update",
            "2026-08-26": "14:00-15:00 cross-category mobile app issue",
            "2026-08-27": "15:00-16:00 staffing capacity shortage",
        },
        "agent_scenarios": {
            "A04": "Increasing transfers, concentrated in technical_support",
            "A07": "Decreasing handling time, increasingly repetitive short notes",
            "A09": "Lower volume but disproportionately complex technical cases",
        },
    }
    with GROUND_TRUTH_FILE.open("w", encoding="utf-8") as file:
        json.dump(truth, file, indent=2)
    print(f"Generated {len(all_requests)} requests across {len(ALL_DATES)} days.")
    print(f"Generated {len(all_monitor)} monitor snapshots and {len(all_shifts)} shifts.")
    print(f"Files saved under: {DATA_DIR}")


if __name__ == "__main__":
    main()
