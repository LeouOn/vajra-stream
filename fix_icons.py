"""Fix mojibake icons in OutlookDashboard.tsx and GuidedRitualFlow.tsx"""
import re
from pathlib import Path

emoji_map = {
    # OutlookDashboard global intentions
    "icon: '???',": "icon: '\U0001F54A',",  # World Peace - dove
    "icon: '??',": "icon: '\U0001F48E',",    # Prosperity - gem
    "icon: '??',": "icon: '\u2600\ufe0f',",  # Sun (same pattern, different context)
}

# Just do a broad fix: replace any garbled icon value with clean emoji based on the label
def fix_outlook():
    p = Path("frontend/src/components/UI/OutlookDashboard.tsx")
    text = p.read_text(encoding="utf-8")
    
    # Map by label keyword
    fixes = [
        ("World Peace", "\U0001F54A"),     # dove
        ("World Prosperity", "\U0001F48E"), # gem
        ("End Disease", "\u2600\ufe0f"),    # sun
        ("Happiness", "\U0001F31F"),        # glowing star
        ("Reforestation", "\U0001F332"),    # evergreen tree
        ("Clean Pollution", "\U0001F30A"),  # water wave
    ]
    
    for label, emoji in fixes:
        # Find pattern: icon: '...' followed by label
        # Replace the icon value
        pattern = r"(icon: ')[^']*(?',\s*\{ id: '[^']*', label: '" + re.escape(label) + r")"
        text = re.sub(pattern, lambda m: m.group(1) + emoji + m.group(2), text)
    
    # Also fix: planet A freq -> planet . freq  
    text = text.replace("preset.planet} A", "preset.planet} \u00b7")  # middle dot
    
    # Fix genre labels
    text = text.replace("label: '?? Healing'", "label: '\U0001F49A Healing'")
    text = text.replace("label: '?? Victory'", "label: '\u2694\ufe0f Victory'")
    text = text.replace("label: '?? Alchemist'", "label: '\u2697 Alchemist'")
    text = text.replace("label: '?? Dharani'", "label: '\U0001F549 Dharani'")
    
    p.write_text(text, encoding="utf-8")
    print(f"Fixed {p.name}")

def fix_guided():
    p = Path("frontend/src/components/UI/GuidedRitualFlow.tsx")
    text = p.read_text(encoding="utf-8")
    
    # Fix intention preset labels
    text = text.replace("label: '?? World Peace'", "label: '\U0001F54A World Peace'")
    text = text.replace("label: '?? Prosperity'", "label: '\U0001F48E Prosperity'")
    text = text.replace("label: '?? Healing'", "label: '\u2764\ufe0f Healing'")
    text = text.replace("label: '?? Reforestation'", "label: '\U0001F332 Reforestation'")
    text = text.replace("label: '?? Purification'", "label: '\U0001F575 Purification'")
    text = text.replace("label: '?? Liberation'", "label: '\U0001F31F Liberation'")
    
    # Fix genre option labels  
    text = text.replace("label: '?? Healing'", "label: '\U0001F49A Healing'")
    text = text.replace("label: '?? Victory'", "label: '\u2694\ufe0f Victory'")
    text = text.replace("label: '?? Alchemist'", "label: '\u2697 Alchemist'")
    text = text.replace("label: '?? Dharani'", "label: '\U0001F549 Dharani'")
    text = text.replace("label: '?? Compassion'", "label: '\U0001F49B Compassion'")
    text = text.replace("label: '?? Wisdom'", "label: '\U0001F4A1 Wisdom'")
    text = text.replace("label: '?? Protection'", "label: '\U0001F6E1 Protection'")
    
    p.write_text(text, encoding="utf-8")
    print(f"Fixed {p.name}")

fix_outlook()
fix_guided()
print("Done!")
