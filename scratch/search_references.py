from pathlib import Path

root_dir = Path("c:/Users/Y/proj/vajra-stream")
results = []

for p in root_dir.glob("**/*"):
    if p.is_file() and p.suffix in (".py", ".js", ".jsx", ".ts", ".tsx"):
        if ".venv" in p.parts or "node_modules" in p.parts or ".git" in p.parts:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            if "enhanced_settings" in content or "EnhancedConfig" in content:
                results.append(
                    (p.relative_to(root_dir), content.count("enhanced_settings"), content.count("EnhancedConfig"))
                )
        except Exception:
            pass

print("Search results (File, 'enhanced_settings' count, 'EnhancedConfig' count):")
for r in results:
    print(r)
