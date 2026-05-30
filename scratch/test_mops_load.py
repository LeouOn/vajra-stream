import asyncio
import time

import httpx


async def trigger_mops():
    print("Testing Terra MOPS load generation...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Trigger scalar wave generation (massive load)
        payload = {
            "method": "hybrid",
            "count": 1000000,
            "intensity": 1.0,
            "duration": 5.0
        }

        start = time.time()
        res = await client.post("http://localhost:8000/api/v1/mops/generate", json=payload)

        end = time.time()

        print(f"Status: {res.status_code}")
        print(f"Time taken: {end - start:.2f}s")
        print(f"Response: {res.json()}")

if __name__ == "__main__":
    asyncio.run(trigger_mops())
