"""QA verification for Task 11 — solar arc directions."""
from core.astrology import AstrologicalCalculator
from datetime import datetime, timezone
import swisseph as swe

calc = AstrologicalCalculator()
n = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
t = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

sad = calc.get_solar_arc_directions(n, (0, 0), t)
arc = sad["solar_arc_degrees"]

natal_pos = calc.get_planetary_positions(n, (0, 0))
jd = calc.get_julian_day(n)
_, ascmc = swe.houses_ex(jd, 0.0, 0.0, b"P")
natal_asc = float(ascmc[0])
natal_mc = float(ascmc[1])

print("Verifying contract: directed = (natal + arc) mod 360 for every body")
print("---")
all_ok = True
planets = [
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
]
for p in planets:
    expected = (natal_pos[p]["longitude"] + arc) % 360.0
    actual = sad["directed"][p]["exact_longitude"]
    ok = abs(expected - actual) < 1e-9
    all_ok = all_ok and ok
    nat = natal_pos[p]["longitude"]
    print(f"{p:8s}: natal={nat:.6f}  expected={expected:.6f}  actual={actual:.6f}  ok={ok}")

for name, natal in [("asc", natal_asc), ("mc", natal_mc)]:
    expected = (natal + arc) % 360.0
    actual = sad["directed"][name]["exact_longitude"]
    ok = abs(expected - actual) < 1e-9
    all_ok = all_ok and ok
    print(f"{name:8s}: natal={natal:.6f}  expected={expected:.6f}  actual={actual:.6f}  ok={ok}")

print("---")
print("ALL OK:", all_ok)
