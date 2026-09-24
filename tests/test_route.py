import sqlite3
import re
from router import route_log

# Initialize in-memory test database[cite: 14]
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE failed_dlq (uuid TEXT, ts TEXT, source TEXT, raw TEXT, reason TEXT)")
conn.execute("CREATE TABLE unknown_dlq (uuid TEXT, ts TEXT, source TEXT, raw TEXT, status TEXT)")
conn.execute("CREATE TABLE normalized_logs (uuid TEXT, ts TEXT, source TEXT, ocsf_class TEXT, fields TEXT)")

# Hash Map Partitioning: Group rules by their source device
KNOWN_PATTERNS_MAP = {
    "vpn-gw-01": [
        {
            "ocsf_class": "Authentication",
            "regex": re.compile(r"login OK user-(?P<username>\w+) src (?P<src_ip>\d+\.\d+\.\d+\.\d+)")
        }
    ]
}

print("Running ULPF Router Diagnostics...\n")

# Test 1: Empty String (Expected: Failed DLQ)[cite: 14]
uuid_1, status_1 = route_log(conn, "", "router-core", KNOWN_PATTERNS_MAP)
print(f"Test 1 (Empty): Routed to '{status_1}' queue.")

# Test 2: Plain/Unknown String (Expected: Unknown DLQ)[cite: 14]
uuid_2, status_2 = route_log(conn, "Firewall blocked payload 0x884", "fw-edge-03", KNOWN_PATTERNS_MAP)
print(f"Test 2 (Unknown): Routed to '{status_2}' queue.")

# Test 3: Known Pattern (Expected: Normalized)[cite: 14]
uuid_3, status_3 = route_log(conn, "login OK user-jemith src 10.2.0.9", "vpn-gw-01", KNOWN_PATTERNS_MAP)
print(f"Test 3 (Known): Routed to '{status_3}' queue.")

# Verify the OCSF normalization output
normalized_row = conn.execute("SELECT fields, ocsf_class FROM normalized_logs WHERE uuid=?", (uuid_3,)).fetchone()
print(f"\nNormalized Output for Test 3:\nClass: {normalized_row[1]}\nFields: {normalized_row[0]}")