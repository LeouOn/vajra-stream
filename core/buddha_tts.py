"""
88 Buddhas Chinese TTS Recitation
Uses Microsoft Edge TTS for natural Chinese pronunciation of Buddha names.
Supports full liturgy recitation with configurable speed and voice.
"""

import asyncio
import os
import tempfile
from typing import Any

# ─── Chinese TTS Voices ───
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"  # Female, clear, natural
ALT_VOICES = [
    "zh-CN-YunxiNeural",  # Male, warm
    "zh-CN-XiaoyiNeural",  # Female, lively
    "zh-TW-HsiaoChenNeural",  # Taiwanese female
    "zh-HK-HiuGaaiNeural",  # Cantonese female
]

PREFERRED_VOICE = "zh-CN-YunxiNeural"  # Male voice for sutra chanting — more traditional feel


class BuddhaTTSReciter:
    """
    Chinese TTS recitation engine for the 88-Buddha liturgy.

    Uses Microsoft Edge TTS for natural Mandarin pronunciation.
    Supports full confession recitation, individual Buddha name recitation,
    and speed/pitch adjustment.
    """

    def __init__(self, voice: str = PREFERRED_VOICE):
        self.voice = voice
        self._available = False
        self._check_availability()

    def _check_availability(self):
        try:
            import edge_tts  # noqa: F401 — availability probe; the import IS the capability test

            self._available = True
        except ImportError:
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    async def speak(
        self, text: str, rate: str = "-20%", volume: str = "+0%", output_file: str | None = None
    ) -> str | None:
        """
        Speak Chinese text using edge-tts.

        Args:
            text: Chinese text to speak
            rate: Speech rate adjustment ("-50%" to "+100%")
            volume: Volume adjustment
            output_file: If provided, save to this file instead of temp file

        Returns:
            Path to audio file if successful, None otherwise
        """
        if not self._available:
            return None

        try:
            import edge_tts

            temp_path = output_file or os.path.join(tempfile.gettempdir(), f"buddha_tts_{hash(text) % 10000}.mp3")
            communicate = edge_tts.Communicate(text, self.voice, rate=rate, volume=volume)
            await communicate.save(temp_path)
            return temp_path
        except Exception as e:
            print(f"TTS error: {e}")
            return None

    async def recite_buddha_name(self, name_chinese: str, name_pinyin: str = "", rate: str = "-30%") -> str | None:
        """
        Recite a single Buddha name slowly and reverently.

        Format: "南無[name]佛" or just the name if it already has 南無
        """
        # Parse the name — remove 南無 if present for cleaner TTS, or keep it
        clean_name = name_chinese.replace("南無", "").strip()
        text = f"南無{clean_name}"

        # Slower rate for sacred recitation
        return await self.speak(text, rate=rate)

    async def recite_confession_sequence(self, buddha_names: list[dict], pause_between: float = 0.3) -> list[str]:
        """
        Recite a sequence of Buddha names with pauses between each.

        Returns list of file paths.
        """
        files = []
        for i, buddha in enumerate(buddha_names):
            name = buddha.get("name_chinese", buddha.get("chinese", ""))
            pinyin = buddha.get("name_pinyin", buddha.get("pinyin", ""))
            if not name:
                continue
            path = await self.recite_buddha_name(name, pinyin)
            if path:
                files.append(path)
            # Small pause between names for reverence
            await asyncio.sleep(pause_between)
        return files

    async def recite_full_liturgy(self, liturgy_text: str) -> str | None:
        """
        Recite the full 88-Buddha liturgy.

        Uses slower rate for the opening/dedication and normal rate
        for the Buddha name list.
        """
        lines = liturgy_text.splitlines()
        # Only recite the meaningful lines (skip structural lines)
        recitable_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip empty lines and structural markers
            if (
                not stripped
                or stripped.startswith("─")
                or stripped.startswith("I.")
                or stripped.startswith("II.")
                or stripped.startswith("III.")
                or stripped.startswith("IV.")
                or stripped.startswith("V.")
            ):
                continue
            # Skip lines that are just "... and all"
            if stripped.startswith("..."):
                continue
            if stripped:
                recitable_lines.append(stripped)

        text = "。".join(recitable_lines[:80])  # Limit to ~80 lines (88 names + dedication)
        return await self.speak(text, rate="-25%")

    async def recite_with_timing(self, buddha_list: list[dict], mala_count: int = 108) -> dict[str, Any]:
        """
        Recite Buddha names synchronized with mala counting.
        Plays each name at timed intervals.

        Returns dict with:
            - audio_files: list of paths
            - total_time: estimated seconds
            - buddhas_recited: count
        """
        audio_files = []
        total_buddhas = len(buddha_list)

        for i in range(min(mala_count, total_buddhas * 2)):
            idx = i % total_buddhas
            buddha = buddha_list[idx]
            name = buddha.get("name_chinese", buddha.get("chinese", ""))
            if not name:
                continue

            # Every 21 recitations, recite a dedication phrase
            if i > 0 and i % 21 == 0:
                dedication = "愿以此功德，普及于一切，我等与众生，皆共成佛道"
                path = await self.speak(dedication, rate="-40%")
                if path:
                    audio_files.append({"type": "dedication", "path": path, "count": i})

            path = await self.recite_buddha_name(name, rate="-30%")
            if path:
                audio_files.append({"type": "buddha", "path": path, "index": idx, "name": name, "count": i + 1})

        return {
            "audio_files": audio_files,
            "total_recited": len([a for a in audio_files if a.get("type") == "buddha"]),
            "dedications": len([a for a in audio_files if a.get("type") == "dedication"]),
            "total_buddhas_in_collection": total_buddhas,
        }


# Convenience
async def recite_random_buddha():
    """Quick test: recite a random Buddha name."""
    from core.eighty_eight_buddhas import get_eighty_eight_buddhas

    svc = get_eighty_eight_buddhas()
    b = svc.random_buddha()
    reciter = BuddhaTTSReciter()
    path = await reciter.recite_buddha_name(b.name_chinese, b.name_pinyin)
    return b, path


if __name__ == "__main__":

    async def main():
        reciter = BuddhaTTSReciter()
        print(f"TTS Available: {reciter.available}")
        print(f"Voice: {reciter.voice}")

        # Test single Buddha name
        print("\n=== Testing single Buddha name ===")
        b, path = await recite_random_buddha()
        print(f"Buddha: {b.name_chinese}")
        print(f"Pinyin: {b.name_pinyin}")
        print(f"Audio saved to: {path}")

        # Test sequence
        print("\n=== Testing full confession sequence ===")
        from core.eighty_eight_buddhas import get_eighty_eight_buddhas

        svc = get_eighty_eight_buddhas()
        seq = svc.get_confession_sequence()
        all_buddhas = seq["fifty_three_past_buddhas"] + seq["thirty_five_confession_buddhas"]
        result = await reciter.recite_with_timing(all_buddhas, mala_count=10)  # Just 10 for test
        print(f"Recited {result['total_recited']} Buddha names")

    asyncio.run(main())
