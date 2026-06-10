from backend.core.services.astrology_chart_service import astrology_chart_service
from backend.core.services.geocoding_service import geocoding_service


def test():
    print("Testing Geocoding...")
    geo = geocoding_service.get_coordinates_and_timezone("Los Angeles")
    print(f"LA Geo: {geo}")

    print("\nTesting Natal Chart...")
    natal = astrology_chart_service.get_natal_chart("User", "1990-05-15T14:30:00Z", "Los Angeles")
    if "data" in natal:
        print(f"Natal Sun: {natal['data']['sun']}")
    else:
        print(f"Natal error: {natal}")

    print("\nTesting Transit (Daily Horoscope)...")
    transit = astrology_chart_service.get_daily_transit("User", "1990-05-15T14:30:00Z", "Los Angeles")
    if "data" in transit:
        print(f"Transit Aspects Count: {len(transit['data']['aspects'])}")
    else:
        print(f"Transit error: {transit}")

    print("\nTesting Synastry...")
    synastry = astrology_chart_service.get_synastry(
        "User1", "1990-05-15T14:30:00Z", "Los Angeles", "User2", "1992-08-23T08:15:00Z", "New York"
    )
    if "data" in synastry:
        print(f"Synastry Aspects Count: {len(synastry['data']['aspects'])}")
    else:
        print(f"Synastry error: {synastry}")


if __name__ == "__main__":
    test()
