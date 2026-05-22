import requests

print("=" * 70)
print("TESTING GLOBAL INTENTION NARRATIVES WITH RADIONICS INTEGRATION")
print("=" * 70)

# Test the global intentions list
print("\n1. Available Global Intentions:")
resp = requests.get("http://127.0.0.1:8008/api/v1/radionics/radionic-global-intentions", timeout=10)
if resp.status_code == 200:
    data = resp.json()
    for item in data["intentions"]:
        print(
            f"   - {item['intention']}: Planet={item['planet']}, Freq={item['frequency_hz']}Hz, Chakra={item['chakra']}, Location={item['location']}, Solfeggio={item['solfeggio_recommendation']}Hz"
        )
else:
    print("   ERROR:", resp.status_code, resp.text)

print("\n" + "=" * 70)
print("TESTING NARRATIVE GENERATION FOR EACH GLOBAL INTENTION")
print("=" * 70)

intentions = [
    "world peace",
    "world prosperity",
    "end to disease and cancer",
    "happiness",
    "reforestation the world",
    "cleaning up pollution",
]

for intention in intentions:
    print(f"\n--- Testing: {intention.upper()} ---")
    try:
        resp = requests.post(
            "http://127.0.0.1:8008/api/v1/radionics/narrative/global-intention",
            json={"intention": intention, "theme": "manifestation"},
            timeout=120,
        )

        if resp.status_code == 200:
            data = resp.json()
            print("Status: SUCCESS")
            rd = data.get("radionics_data", {})
            print("  Radionics Data:")
            print(f"    - Solfeggio: {rd.get('solfeggio_frequency')}Hz ({rd.get('solfeggio_name', '')})")
            print(f"    - Planet: {rd.get('planetary_planets')} at {rd.get('planetary_frequency')}Hz")
            print(f"    - Location: {rd.get('location')}")
            print(f"    - Chakra: {rd.get('chakra')}")
            print(f"    - Broadcast: {rd.get('broadcast_recommendation', 'N/A')}")
            narrative = data.get("narrative", "")
            print(f"  Narrative (first 200 chars): {narrative[:200]}...")
            if data.get("affirmation"):
                print(f"  Affirmation: {data.get('affirmation')[:100]}...")
        else:
            print(f"Status: ERROR {resp.status_code}")
            print(f"  Response: {resp.text[:200]}")
    except Exception as e:
        print(f"EXCEPTION: {e}")

print("\n" + "=" * 70)
print("ALL TESTS COMPLETE")
print("=" * 70)
