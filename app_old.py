from tools import (
    count_requests,
    get_requests_by_classification,
    get_average_wait_time,
    get_monitor_metrics,
    compare_values,
    get_requests_by_time_bucket,
    get_classification_count,
    get_request_details,
)


START_TIME = "2026-08-25T12:00:00"
END_TIME = "2026-08-25T13:00:00"

BASELINE_START_TIME = "2026-08-25T11:00:00"
BASELINE_END_TIME = "2026-08-25T12:00:00"


print("=== REQUEST COUNT ===")
print(
    count_requests(
        START_TIME,
        END_TIME
    )
)


print("\n=== REQUESTS BY CLASSIFICATION ===")
print(
    get_requests_by_classification(
        START_TIME,
        END_TIME
    )
)


print("\n=== AVERAGE WAIT TIME ===")
print(
    get_average_wait_time(
        START_TIME,
        END_TIME
    )
)


print("\n=== MONITOR METRICS ===")
print(
    get_monitor_metrics(
        START_TIME,
        END_TIME
    )
)


print("\n=== REQUEST VOLUME COMPARISON ===")

current_period = count_requests(
    START_TIME,
    END_TIME
)

baseline_period = count_requests(
    BASELINE_START_TIME,
    BASELINE_END_TIME
)

comparison = compare_values(
    current=current_period["request_count"],
    baseline=baseline_period["request_count"]
)

print("Current period:", current_period)
print("Baseline period:", baseline_period)
print("Comparison:", comparison)

print("\n=== REQUESTS BY TIME BUCKET ===")

print(
    get_requests_by_time_bucket(
        START_TIME,
        END_TIME,
        bucket_minutes=5
    )
)

print("\n=== LOGIN ISSUE COMPARISON ===")

current_login_issues = get_classification_count(
    START_TIME,
    END_TIME,
    "login_issue"
)

baseline_login_issues = get_classification_count(
    BASELINE_START_TIME,
    BASELINE_END_TIME,
    "login_issue"
)

login_comparison = compare_values(
    current=current_login_issues["request_count"],
    baseline=baseline_login_issues["request_count"]
)

print("Current period:", current_login_issues)
print("Baseline period:", baseline_login_issues)
print("Comparison:", login_comparison)

print("\n=== LOGIN ISSUE REQUEST DETAILS ===")

login_request_details = get_request_details(
    START_TIME,
    END_TIME,
    "login_issue"
)

print(login_request_details)