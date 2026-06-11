import os

search_dir = "c:\\Users\\Y\\proj\\vajra-stream\\frontend"
queries = ["/operator/chat", "/llm/chat", "chat_with_operator", "/chat"]

for root, dirs, files in os.walk(search_dir):
    if "node_modules" in root or ".git" in root or "dist" in root:
        continue
    for file in files:
        if file.endswith(".jsx") or file.endswith(".tsx") or file.endswith(".js") or file.endswith(".ts"):
            path = os.path.join(root, file)
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    for query in queries:
                        if query in content:
                            print(f"Found '{query}' in {path}")
            except Exception:
                pass
