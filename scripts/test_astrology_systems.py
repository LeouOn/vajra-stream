import asyncio
import os
import sys
from datetime import datetime

import pytz

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set stdout to UTF-8
sys.stdout.reconfigure(encoding="utf-8")

print("🧪 Starting Automated Astrology System Verification...\n")

try:
    from core.astrology import AstrologicalCalculator

    print("✅ Successfully imported AstrologicalCalculator from core.astrology")
except ImportError as e:
    print(f"❌ Failed to import AstrologicalCalculator: {e}")
    sys.exit(1)

try:
    from backend.core.services.vajra_service import vajra_service

    print("✅ Successfully imported vajra_service from backend")
except ImportError as e:
    print(f"❌ Failed to import vajra_service: {e}")
    sys.exit(1)

# Initialize calculator
astro = AstrologicalCalculator()

# Coordinates (San Francisco)
coords = (37.7749, -122.4194)
test_time = datetime.now(pytz.UTC)

print(f"\n--- Testing core calculations for date: {test_time} at {coords} ---")

try:
    data = astro.get_comprehensive_astrology(test_time, coords)
    print("✅ Successfully calculated comprehensive astrology")

    # Verify Western
    assert "western" in data, "Missing western section"
    assert "positions" in data["western"], "Missing western positions"
    assert "elements" in data["western"], "Missing western elements"
    assert "aspects" in data["western"], "Missing western aspects"
    print(
        f"   Western: Ok. Dominant Element: {data['western']['dominant_element']}, Aspects: {len(data['western']['aspects'])}"
    )

    # Verify Indian
    assert "indian" in data, "Missing indian section"
    assert "panchanga" in data["indian"], "Missing panchanga"
    panch = data["indian"]["panchanga"]
    assert "tithi" in panch, "Missing tithi"
    assert "nakshatra" in panch, "Missing nakshatra"
    assert "yoga" in panch, "Missing yoga"
    assert "karana" in panch, "Missing karana"
    assert "vara" in panch, "Missing vara"
    print(
        f"   Indian (Vedic): Ok. Tithi: {panch['tithi']['name']}, Nakshatra: {panch['nakshatra']['name']}, Yoga: {panch['yoga']['name']}"
    )

    # Verify Chinese
    assert "chinese" in data, "Missing chinese section"
    assert "lunar_date" in data["chinese"], "Missing lunar_date"
    assert "bazi" in data["chinese"], "Missing bazi"
    assert "shichen" in data["chinese"], "Missing shichen"
    print(
        f"   Chinese: Ok. Animal: {data['chinese']['zodiac_animal']}, Shichen: {data['chinese']['shichen']['name']}, Date: {data['chinese']['lunar_date']['formatted']}"
    )

    # Verify Planetary Hours
    assert "planetary_hours" in data, "Missing planetary_hours section"
    assert "current_planetary_hour" in data["planetary_hours"], "Missing current ruler"
    assert "day_of_week" in data["planetary_hours"], "Missing day of week"
    assert "hour_of_day" in data["planetary_hours"], "Missing hour of day"
    print(
        f"   Planetary Hours: Ok. Ruler: {data['planetary_hours']['current_planetary_hour']}, Hour of Day: {data['planetary_hours']['hour_of_day']}"
    )

except Exception as e:
    print(f"❌ Core calculations failed validation: {e}")
    sys.exit(1)


print("\n--- Testing Backend Service Integration ---")


async def test_service():
    try:
        service_data = await vajra_service._get_astrology_data()
        print("✅ Successfully fetched service astrology data")

        # Verify backward compatibility
        assert "moon_phase" in service_data, "Missing moon_phase"
        assert "phase_name" in service_data["moon_phase"], "Missing phase_name"
        assert "planetary_positions" in service_data, "Missing planetary_positions"
        assert "auspicious_times" in service_data, "Missing auspicious_times"
        assert "timestamp" in service_data, "Missing timestamp"

        print("   Service data matches legacy requirements for frontend backward compatibility")
        print(
            f"   Legacy Moon Phase: {service_data['moon_phase']['phase_name']} ({service_data['moon_phase']['illumination']:.1f}% illumination)"
        )
        print(f"   Legacy Auspicious Times Sunrise: {service_data['auspicious_times'].get('sunrise')}")

    except Exception as e:
        print(f"❌ Service validation failed: {e}")
        sys.exit(1)


# Run async service test
asyncio.run(test_service())

print("\n🎉 AUTOMATED ASTROLOGY SYSTEM VERIFICATION PASSED SUCCESSFULLY!")
