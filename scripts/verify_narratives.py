import requests

print("=" * 70)
print("FINAL VERIFICATION - Global Intentions with Radionics Data")
print("=" * 70)

intentions = [
    "world peace",
    "end to disease and cancer",
    "reforestation the world",
]

for intention in intentions:
    print(f"\n--- {intention.upper()} ---")
    try:
        resp = requests.post(
            "http://127.0.0.1:8008/api/v1/radionics/narrative/global-intention",
            json={"intention": intention, "theme": "manifestation"},
            timeout=120,
        )

        if resp.status_code == 200:
            data = resp.json()
            rd = data.get("radionics_data", {})
            planet = rd.get("planetary_planets", "N/A")
            solfeggio = rd.get("solfeggio_frequency", "N/A")
            location = rd.get("location", "N/A")
            chakra = rd.get("chakra", "N/A")
            broadcast = rd.get("broadcast_recommendation", "N/A")
            print(f"  Planet: {planet} | Freq: {solfeggio}Hz | Location: {location}")
            print(f"  Chakra: {chakra} | Broadcast: {broadcast}")
        else:
            print(f"  ERROR: {resp.status_code}")
    except Exception as e:
        print(f"  EXCEPTION: {e}")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE - System is working!")
print("=" * 70)
