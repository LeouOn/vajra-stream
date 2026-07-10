"""Fix mojibake — simple direct string replacement"""
from pathlib import Path

def fix_outlook():
    p = Path("frontend/src/components/UI/OutlookDashboard.tsx")
    lines = p.read_text(encoding="utf-8").split("\n")
    new_lines = []
    for line in lines:
        if "icon:" in line and "string;" not in line:
            if "World Peace" in line:
                line = line.split("icon:")[0] + "icon: '\U0001F54A' },  // dove"
            elif "World Prosperity" in line:
                line = line.split("icon:")[0] + "icon: '\U0001F48E' },  // gem"
            elif "End Disease" in line:
                line = line.split("icon:")[0] + "icon: '\u2600\ufe0f' },  // sun"
            elif "Happiness" in line:
                line = line.split("icon:")[0] + "icon: '\U0001F31F' },  // star"
            elif "Reforestation" in line:
                line = line.split("icon:")[0] + "icon: '\U0001F332' },  // tree"
            elif "Clean Pollution" in line:
                line = line.split("icon:")[0] + "icon: '\U0001F30A' },  // wave"
        if "preset.planet} A" in line or "preset.planet} \ufffd" in line:
            line = line.replace("preset.planet} A ", "preset.planet} \u00b7 ")
            line = line.replace("preset.planet} \ufffd ", "preset.planet} \u00b7 ")
        new_lines.append(line)
    p.write_text("\n".join(new_lines), encoding="utf-8")
    print("OutlookDashboard.tsx fixed")

def fix_guided():
    p = Path("frontend/src/components/UI/GuidedRitualFlow.tsx")
    text = p.read_text(encoding="utf-8")
    # Just replace the entire preset arrays section
    lines = text.split("\n")
    new_lines = []
    for line in lines:
        if "label:" in line and "value:" not in line:
            # Genre options - single label
            if "Healing" in line and "genre" not in line:
                line = line.replace("label: '", "label: '\U0001F49A ")
            elif "Victory" in line and "genre" not in line:
                line = line.replace("label: '", "label: '\u2694\ufe0f ")
            elif "Alchemist" in line and "genre" not in line:
                line = line.replace("label: '", "label: '\u2697 ")
            elif "Dharani" in line and "genre" not in line:
                line = line.replace("label: '", "label: '\U0001F549 ")
        elif "label:" in line and "value:" in line:
            # Intention presets with value
            if "World Peace" in line:
                line = "  { label: '\U0001F54A World Peace'"
            elif "Prosperity" in line:
                line = "  { label: '\U0001F48E Prosperity'"
            elif "Healing" in line and "value:" in line:
                line = "  { label: '\u2764\ufe0f Healing'"
            elif "Reforestation" in line:
                line = "  { label: '\U0001F332 Reforestation'"
            elif "Purification" in line:
                line = "  { label: '\U0001F575\ufe0f Purification'"
            elif "Liberation" in line:
                line = "  { label: '\U0001F31F Liberation'"
        new_lines.append(line)
    p.write_text("\n".join(new_lines), encoding="utf-8")
    print("GuidedRitualFlow.tsx fixed")

fix_outlook()
fix_guided()
print("Done!")
