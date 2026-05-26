"""Check tool schemas"""

import json

from backend.core.llm_agent.tools import get_tool_schemas

for s in get_tool_schemas():
    print(f"Tool: {s['name']}")
    print(f"  params: {json.dumps(s['parameters'])}")
    print()
