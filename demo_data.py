import random

SOURCES = ["Salesforce", "Stripe", "Shopify", "Database", "Webhooks"]

def generate_raw_log(kind: str) -> tuple[str, str]:
    """Generate a raw log string and a source based on kind."""
    source = random.choice(SOURCES)
    if kind == "known":
        return f"login OK user-{random.randint(1000, 9999)} src 192.168.1.{random.randint(1, 255)}", source
    elif kind == "unknown":
        return f"unknown action {random.randint(1000,9999)} from IP 10.0.0.{random.randint(1, 255)}", source
    else:
        return f"Malformed log entry {random.randint(1000, 9999)} missing field values...", source

def get_demo_logs(count: int = 10, unknown_weight: int = 12) -> list[tuple[str, str]]:
    """Generate a batch of raw log strings with their sources."""
    logs = []
    known_weight = 100 - unknown_weight - 8
    for _ in range(count):
        kind = random.choices(
            ["known", "unknown", "failed"], weights=[known_weight, unknown_weight, 8]
        )[0]
        logs.append(generate_raw_log(kind))
    return logs