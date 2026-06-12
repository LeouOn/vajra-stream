"""
88 Buddhas ×3 Practice — Full Liturgy with TTS Audio Output

Runs 3 complete cycles of the 88-Buddha Great Repentance practice:
- 88 names per cycle × 3 = 264 recitations
- Dedication every 21 names (13 dedications total)
- Full mala dedication every 108 names
- Chinese TTS via Microsoft Edge TTS (zh-CN-YunxiNeural)
- Audio plays through system speakers in real-time
- Text liturgy generated and saved
- Progress reported live
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure project root is on path (script lives in scripts/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix Windows console encoding for Chinese/emoji output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core.buddha_tts import BuddhaTTSReciter
from core.eighty_eight_buddhas import get_eighty_eight_buddhas

# ─── Config ────────────────────────────────────────────────

CYCLES = 3
NAMES_PER_DEDICATION = 21
MALA_SIZE = 108
VOICE = "zh-CN-YunxiNeural"  # Male voice, traditional sutra feel
RATE = "-25%"  # Slower for sacred recitation
OUTPUT_DIR = Path("generated/buddha_practice")
INTENTION = "愿一切众生离苦得乐，早证菩提。\nMay all beings be free from suffering and attain enlightenment."

# ─── Helpers ───────────────────────────────────────────────


def format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


async def play_audio_file(path: str):
    """Play an MP3 file through system speakers."""
    try:
        import sounddevice as sd
        import soundfile as sf

        data, samplerate = sf.read(path)
        sd.play(data, samplerate)
        sd.wait()
    except ImportError:
        pass  # soundfile not available — audio still generated
    except Exception as e:
        print(f"  ⚠️ Playback skip: {e}")


# ─── Main Practice ─────────────────────────────────────────


async def run_practice():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  八十八佛大懺悔文 · 88 BUDDHAS GREAT REPENTANCE")
    print("  ×3 Cycles · TTS Audio · Live Sound Output")
    print("=" * 60)
    print()

    # Load Buddhas
    svc = get_eighty_eight_buddhas()
    seq = svc.get_confession_sequence()
    past = seq["fifty_three_past_buddhas"]
    conf = seq["thirty_five_confession_buddhas"]
    all_buddhas = past + conf
    total = len(all_buddhas)
    print(f"📿 Loaded {total} Buddhas ({len(past)} past + {len(conf)} confession)")
    print(f"🔄 Cycles: {CYCLES}  |  Total recitations: {CYCLES * total}")
    print(f"🎙️  Voice: {VOICE}  |  Rate: {RATE}")
    print(f"💾 Output: {OUTPUT_DIR.absolute()}")
    print()

    # Generate and save the text liturgy
    liturgy_path = OUTPUT_DIR / f"liturgy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    liturgy_text = svc.generate_repentance_narrative(INTENTION)
    with open(liturgy_path, "w", encoding="utf-8") as f:
        f.write(liturgy_text["liturgy"])
    print(f"📝 Liturgy saved: {liturgy_path}")
    print()

    # Initialize TTS
    reciter = BuddhaTTSReciter(voice=VOICE)
    if not reciter.available:
        print("❌ Edge TTS not available. Install: pip install edge-tts")
        return
    print("🎙️  TTS engine ready. Beginning practice...")
    print()

    # Track stats
    total_recited = 0
    mala_count = 0
    dedications = 0
    cycle = 0
    audio_files = []
    start_time = time.time()

    # ─── Opening ───
    print("─" * 60)
    print("🔔 OPENING ASPIRATION")
    print("─" * 60)
    opening_text = "大慈大悲愍众生 大喜大舍济含识 南無"
    print(f"  {opening_text}")
    opening_path = await reciter.speak(opening_text, rate="-35%")
    if opening_path:
        audio_files.append(opening_path)
        await play_audio_file(opening_path)
    print()

    # ─── Main Recitation ───
    for cycle_num in range(1, CYCLES + 1):
        cycle = cycle_num
        print(f"{'═' * 60}")
        print(f"🔄 CYCLE {cycle_num}/{CYCLES}")
        print(f"{'═' * 60}")

        for i, buddha in enumerate(all_buddhas):
            name = buddha.get("name_chinese", "")
            pinyin = buddha.get("name_pinyin", "")
            if not name:
                continue

            total_recited += 1
            mala_count += 1

            # Progress display
            elapsed = time.time() - start_time
            rate_per_min = (total_recited / elapsed * 60) if elapsed > 0 else 0
            remaining = (CYCLES * total - total_recited) / max(rate_per_min, 1)
            pct = (total_recited / (CYCLES * total)) * 100

            bar_len = 30
            filled = int(bar_len * (i + 1) / total)
            bar = "█" * filled + "░" * (bar_len - filled)

            print(
                f"\r  [{bar}] {pct:5.1f}% | #{total_recited}: {name[:20]} | "
                f"{format_time(elapsed)} elapsed | ~{format_time(remaining)} remaining",
                end="",
            )

            # Recite via TTS
            text = f"南無{name}" if not name.startswith("南無") else name
            path = await reciter.speak(text, rate=RATE)
            if path:
                audio_files.append(path)
                await play_audio_file(path)

            # Dedication every N names
            if mala_count > 0 and mala_count % NAMES_PER_DEDICATION == 0:
                dedications += 1
                print()  # newline after progress bar
                print(f"  📿 Dedication #{dedications} (after {mala_count} names)")
                dedication_text = "愿以此功德 普及于一切 我等与众生 皆共成佛道"
                ded_path = await reciter.speak(dedication_text, rate="-40%")
                if ded_path:
                    audio_files.append(ded_path)
                    await play_audio_file(ded_path)

            # Full mala (108) dedication
            if mala_count > 0 and mala_count % MALA_SIZE == 0:
                print(f"\n  🔔 FULL MALA DEDICATION ({mala_count} names) 🔔")
                full_ded = "愿以此功德 普及于一切 我等与众生 皆共成佛道。回向法界一切众生，同证无上正等正觉。"
                full_path = await reciter.speak(full_ded, rate="-40%")
                if full_path:
                    audio_files.append(full_path)
                    await play_audio_file(full_path)
                mala_count = 0

        print()  # final newline after cycle
        print(f"  ✅ Cycle {cycle_num} complete — {total} names recited")
        print()

    # ─── Closing Dedication ───
    print("─" * 60)
    print("🔔 CLOSING DEDICATION")
    print("─" * 60)
    closing_text = "功德圆满。愿以此念诵八十八佛之功德，回向法界一切众生，离苦得乐，早证菩提。愿一切众生具足乐及乐因，愿一切众生永离苦及苦因，愿一切众生不离无苦之乐，愿一切众生远离爱憎住平等舍。"
    print(f"  {closing_text[:100]}...")
    closing_path = await reciter.speak(closing_text, rate="-35%")
    if closing_path:
        audio_files.append(closing_path)
        await play_audio_file(closing_path)

    # ─── Summary ───
    total_time = time.time() - start_time
    print()
    print("=" * 60)
    print("  🙏 PRACTICE COMPLETE — 功德圆满 🙏")
    print("=" * 60)
    print(f"  📿 Total recitations:    {total_recited}")
    print(f"  🔄 Cycles completed:     {cycle}")
    print(f"  📿 Dedications:           {dedications}")
    print(f"  🎵 Audio files generated: {len(audio_files)}")
    print(f"  ⏱️  Total time:            {format_time(total_time)}")
    print(f"  📝 Liturgy:               {liturgy_path}")
    print(f"  💾 Audio dir:             {OUTPUT_DIR.absolute()}")
    print(f"  🎯 Intention:             {INTENTION[:60]}...")
    print()
    print("  May the merit of this practice benefit all beings")
    print("  throughout the ten directions and three times.")
    print("  以此功德，普及于一切，我等与众生，皆共成佛道。")
    print("=" * 60)

    # Save manifest
    manifest_path = OUTPUT_DIR / f"manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    import json

    manifest = {
        "practice": "88 Buddhas Great Repentance ×3",
        "completed_at": datetime.now().isoformat(),
        "cycles": CYCLES,
        "total_recitations": total_recited,
        "dedications": dedications,
        "audio_files": len(audio_files),
        "total_time_seconds": total_time,
        "voice": VOICE,
        "intention": INTENTION,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"\n📋 Manifest saved: {manifest_path}")


if __name__ == "__main__":
    asyncio.run(run_practice())
