import os

search_dir = "c:\\Users\\Y\\proj\\vajra-stream"
queries = [
    "start_autonomous_mode",
    "start_blessing_loop",
    "AutonomousAgent",
    "OrchestratorService",
    "_autonomous_cycle",
    "autonomous_active",
]

for root, dirs, files in os.walk(search_dir):
    if ".git" in root or ".venv" in root or "node_modules" in root:
        continue
    for file in files:
        if (
            file.endswith(".py")
            or file.endswith(".ts")
            or file.endswith(".tsx")
            or file.endswith(".json")
            or file.endswith(".js")
        ):
            path = os.path.join(root, file)
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    for query in queries:
                        if query in content:
                            print(f"Found '{query}' in {path}")
            except Exception:
                pass
