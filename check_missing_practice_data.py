"""Check what knowledge is MISSING from practice definitions."""
import json
import os


def main():
    practices_dir = "knowledge/practices"
    files = [f for f in os.listdir(practices_dir) if f.endswith(".json")]
    for f in sorted(files):
        with open(os.path.join(practices_dir, f), encoding="utf-8") as fh:
            d = json.load(fh)
        missing = []
        for key in ["mantra_sanskrit", "mantra_transliteration", "mantra_english",
                    "mantra_count", "id", "name", "frequency", "color", "benefits"]:
            if key not in d or d[key] in (None, "", "?"):
                missing.append(key)
        print(f"{f.replace('.json', '')}:")
        print(f"  mantra_sanskrit: {str(d.get('mantra_sanskrit', d.get('mantra', '?')))[:60]}")
        print(f"  mantra_transliteration: {str(d.get('mantra_transliteration', '?'))[:60]}")
        print(f"  mantra_english: {str(d.get('mantra_english', '?'))[:50]}")
        print(f"  mantra_count: {d.get('mantra_count', '?')}")
        print(f"  frequency: {d.get('frequency', '?')}")
        print(f"  color: {d.get('color', '?')}")
        if missing:
            print(f"  MISSING/EMPTY: {missing}")
        print()


if __name__ == "__main__":
    main()
