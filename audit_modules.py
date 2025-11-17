"""
Vajra Stream Module Audit
Check which core modules are wrapped and which are missing
"""

import sys
from pathlib import Path

# Core modules
core_modules = [
    "advanced_scalar_waves",
    "integrated_scalar_radionics",
    "meridian_visualization",
    "energetic_anatomy",
    "blessing_narratives",
    "compassionate_blessings",
    "audio_generator",
    "enhanced_audio_generator",
    "tts_engine",
    "tts_integration",
    "enhanced_tts",
    "rothko_generator",
    "energetic_visualization",
    "visual_renderer_simple",
    "time_cycle_broadcaster",
    "astrology",
    "astrocartography",
    "prayer_wheel",
    "intelligent_composer",
    "healing_systems",
    "radionics_engine",
    "llm_integration"
]

# Check which are wrapped
wrapped_in_modules = {
    "scalar_waves": ["advanced_scalar_waves"],
    "radionics": ["integrated_scalar_radionics", "radionics_engine"],
    "anatomy": ["meridian_visualization", "energetic_anatomy"],
    "blessings": ["blessing_narratives", "compassionate_blessings"]
}

print("VAJRA STREAM MODULE AUDIT")
print("=" * 70)
print()

wrapped = []
for module_file, core_list in wrapped_in_modules.items():
    for core in core_list:
        wrapped.append(core)

print("✅ WRAPPED MODULES:")
for core in sorted(wrapped):
    module = [k for k, v in wrapped_in_modules.items() if core in v][0]
    print(f"   {core:30s} → modules/{module}.py")

print()
print("❌ MISSING MODULES:")
missing = [m for m in core_modules if m not in wrapped]
for core in sorted(missing):
    print(f"   {core}")

print()
print(f"Coverage: {len(wrapped)}/{len(core_modules)} modules ({len(wrapped)/len(core_modules)*100:.0f}%)")
print()

# Group missing by category
audio_modules = [m for m in missing if 'audio' in m or 'tts' in m]
visual_modules = [m for m in missing if 'visual' in m or 'rothko' in m]
astro_modules = [m for m in missing if 'astro' in m]
other_modules = [m for m in missing if m not in audio_modules and m not in visual_modules and m not in astro_modules]

print("MISSING BY CATEGORY:")
print()
if audio_modules:
    print("  Audio/TTS:")
    for m in audio_modules:
        print(f"    - {m}")
print()
if visual_modules:
    print("  Visualization:")
    for m in visual_modules:
        print(f"    - {m}")
print()
if astro_modules:
    print("  Astrology:")
    for m in astro_modules:
        print(f"    - {m}")
print()
if other_modules:
    print("  Other:")
    for m in other_modules:
        print(f"    - {m}")
