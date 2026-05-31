import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.auspicious_timing import check_auspicious_window

print("--- Auspicious Timing Test ---")
timing = check_auspicious_window("healing")
print(timing.to_dict())

print("\n--- Auspicious Timing Test (Victory) ---")
timing_victory = check_auspicious_window("victory")
print(timing_victory.to_dict())
