import time

from container import container


def test_raw_container():
    print("Testing container scalar generation...")
    # Container auto-initializes on access

    start = time.time()
    result = container.scalar_waves.generate(
        method="hybrid",
        count=1000000,
        intensity=1.0
    )
    end = time.time()

    print(f"Time taken: {end - start:.2f}s")
    print("Result keys:", result.keys())
    print("Mops calculated:", result.get("mops"))

if __name__ == "__main__":
    test_raw_container()
