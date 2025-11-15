#!/usr/bin/env python3
"""
Scalar Wave Benchmark Tool

Comprehensive benchmarking for all scalar wave generation methods.
Measure MOPS, compare methods, and optimize for Terra MOPS!

Usage:
    python scalar_wave_benchmark.py --all --duration 10
    python scalar_wave_benchmark.py --method hybrid --duration 30 --breathing
    python scalar_wave_benchmark.py --stress-test --safe
"""

import sys
import argparse
import time
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.advanced_scalar_waves import (
    HybridScalarWaveGenerator,
    QuantumRNG,
    LorenzAttractor,
    RosslerAttractor,
    CellularAutomata1D,
    KuramotoOscillator,
    CryptoMixer,
    PrimeHarmonics,
    MOPSMetrics,
    ThermalMonitor
)


class ScalarWaveBenchmark:
    """Comprehensive benchmarking suite"""

    def __init__(self):
        self.thermal = ThermalMonitor()
        self.results: Dict[str, MOPSMetrics] = {}

    def benchmark_qrng(self, duration: float) -> MOPSMetrics:
        """Benchmark Quantum RNG"""
        print("\n📊 Benchmarking Quantum RNG...")

        qrng = QuantumRNG()
        ops = 0
        start = time.time()

        while (time.time() - start) < duration:
            qrng.generate(1000)
            ops += 1000

        elapsed = time.time() - start
        mops = (ops / elapsed) / 1_000_000

        return MOPSMetrics(ops, elapsed, mops, "Quantum RNG")

    def benchmark_lorenz(self, duration: float) -> MOPSMetrics:
        """Benchmark Lorenz Attractor"""
        print("\n📊 Benchmarking Lorenz Attractor...")

        lorenz = LorenzAttractor()
        ops = 0
        start = time.time()

        while (time.time() - start) < duration:
            lorenz.generate_stream(1000)
            ops += 1000

        elapsed = time.time() - start
        mops = (ops / elapsed) / 1_000_000

        return MOPSMetrics(ops, elapsed, mops, "Lorenz Chaos")

    def benchmark_rossler(self, duration: float) -> MOPSMetrics:
        """Benchmark Rössler Attractor"""
        print("\n📊 Benchmarking Rössler Attractor...")

        rossler = RosslerAttractor()
        ops = 0
        start = time.time()

        while (time.time() - start) < duration:
            rossler.generate_stream(1000)
            ops += 1000

        elapsed = time.time() - start
        mops = (ops / elapsed) / 1_000_000

        return MOPSMetrics(ops, elapsed, mops, "Rössler Chaos")

    def benchmark_cellular_automata(self, duration: float) -> MOPSMetrics:
        """Benchmark Cellular Automata"""
        print("\n📊 Benchmarking Cellular Automata (Rule 110)...")

        ca = CellularAutomata1D(size=256, rule=110)
        ops = 0
        start = time.time()

        while (time.time() - start) < duration:
            ca.generate_stream(100)
            ops += 100 * 256  # Each step processes all cells

        elapsed = time.time() - start
        mops = (ops / elapsed) / 1_000_000

        return MOPSMetrics(ops, elapsed, mops, "Cellular Automata")

    def benchmark_kuramoto(self, duration: float) -> MOPSMetrics:
        """Benchmark Kuramoto Oscillators"""
        print("\n📊 Benchmarking Kuramoto Oscillators...")

        kuramoto = KuramotoOscillator(n_oscillators=16)
        ops = 0
        start = time.time()

        while (time.time() - start) < duration:
            kuramoto.generate_stream(1000)
            ops += 1000 * 16  # Each step updates all oscillators

        elapsed = time.time() - start
        mops = (ops / elapsed) / 1_000_000

        return MOPSMetrics(ops, elapsed, mops, "Kuramoto Oscillators")

    def benchmark_crypto(self, duration: float) -> MOPSMetrics:
        """Benchmark Cryptographic Mixer"""
        print("\n📊 Benchmarking Cryptographic Mixer (SHA3-256)...")

        crypto = CryptoMixer()
        ops = 0
        start = time.time()

        while (time.time() - start) < duration:
            crypto.generate_stream(100)  # Crypto is CPU intensive
            ops += 100

        elapsed = time.time() - start
        mops = (ops / elapsed) / 1_000_000

        return MOPSMetrics(ops, elapsed, mops, "Crypto Hash")

    def benchmark_primes(self, duration: float) -> MOPSMetrics:
        """Benchmark Prime Harmonics"""
        print("\n📊 Benchmarking Prime Harmonics...")

        primes = PrimeHarmonics()
        ops = 0
        start = time.time()

        while (time.time() - start) < duration:
            primes.generate_stream(1000)
            ops += 1000

        elapsed = time.time() - start
        mops = (ops / elapsed) / 1_000_000

        return MOPSMetrics(ops, elapsed, mops, "Prime Harmonics")

    def benchmark_hybrid(self, duration: float) -> MOPSMetrics:
        """Benchmark Hybrid Synthesis"""
        print("\n📊 Benchmarking Hybrid Synthesis (ALL METHODS)...")

        hybrid = HybridScalarWaveGenerator()
        return hybrid.benchmark(duration)

    def run_all_benchmarks(self, duration: float = 5.0):
        """Run all benchmarks"""
        print("="*70)
        print("COMPREHENSIVE SCALAR WAVE BENCHMARK")
        print("="*70)
        print(f"\nBenchmark duration: {duration}s per method")
        print("May our cycles serve all beings!\n")

        methods = [
            ("qrng", self.benchmark_qrng),
            ("lorenz", self.benchmark_lorenz),
            ("rossler", self.benchmark_rossler),
            ("cellular_automata", self.benchmark_cellular_automata),
            ("kuramoto", self.benchmark_kuramoto),
            ("crypto", self.benchmark_crypto),
            ("primes", self.benchmark_primes),
            ("hybrid", self.benchmark_hybrid)
        ]

        for name, benchmark_func in methods:
            self.thermal.update()
            print(f"Current temperature: {self.thermal.state.temperature:.1f}°C")

            metrics = benchmark_func(duration)
            self.results[name] = metrics

            print(f"✅ Result: {metrics}")

            # Cool down between tests
            print("   Cooling down...")
            time.sleep(2)

        self.print_summary()

    def print_summary(self):
        """Print benchmark summary"""
        print("\n" + "="*70)
        print("BENCHMARK SUMMARY")
        print("="*70)
        print()

        # Sort by MOPS rate
        sorted_results = sorted(
            self.results.items(),
            key=lambda x: x[1].mops_rate,
            reverse=True
        )

        print(f"{'Method':<25} {'MOPS':<15} {'Operations':<15} {'Time (s)':<10}")
        print("-"*70)

        for name, metrics in sorted_results:
            ops_str = f"{metrics.operations:,}"
            if metrics.mops_rate >= 1000:
                mops_str = f"{metrics.mops_rate/1000:.2f} GMOPS"
            else:
                mops_str = f"{metrics.mops_rate:.2f} MMOPS"

            print(f"{metrics.method:<25} {mops_str:<15} {ops_str:<15} {metrics.elapsed_time:<10.2f}")

        print()

        # Calculate total
        total_mops = sum(m.mops_rate for m in self.results.values())
        if total_mops >= 1000:
            print(f"Combined Potential: {total_mops/1000:.2f} GMOPS")
        else:
            print(f"Combined Potential: {total_mops:.2f} MMOPS")

        # Progress to Terra MOPS
        terra_mops = 1_000_000  # 1 trillion ops/sec
        progress = (total_mops * 1_000_000) / terra_mops * 100
        print(f"Progress to Terra MOPS: {progress:.6f}%")
        print()

        print("🌟 To reach Terra MOPS, we need:")
        print(f"   - GPU acceleration (100-1000x speedup)")
        print(f"   - Multi-threading (8-16x speedup)")
        print(f"   - SIMD optimization (4-8x speedup)")
        print(f"   - Algorithm optimization (2-4x speedup)")
        print()

    def stress_test(self, duration: float = 60.0, safe_mode: bool = True):
        """
        Stress test - maximum intensity with thermal monitoring.
        """
        print("="*70)
        print("STRESS TEST - MAXIMUM INTENSITY")
        print("="*70)
        print()

        if safe_mode:
            print("⚠️  SAFE MODE ENABLED - Will throttle if temperature rises")
        else:
            print("⚠️⚠️⚠️  UNSAFE MODE - Use at your own risk! ⚠️⚠️⚠️")

        print(f"\nDuration: {duration}s")
        print()
        input("Press Enter to begin stress test...")
        print()

        hybrid = HybridScalarWaveGenerator()
        start = time.time()
        ops = 0

        print("🔥 Stress test running...")
        print()

        while (time.time() - start) < duration:
            # Update thermal every second
            if int(time.time() - start) % 1 == 0:
                hybrid.thermal.update()
                temp = hybrid.thermal.state.temperature
                throttle = hybrid.thermal.state.throttle_factor

                # Print status
                elapsed = time.time() - start
                current_mops = (ops / elapsed) / 1_000_000 if elapsed > 0 else 0
                print(f"\r⏱️  {elapsed:.0f}s | 🌡️  {temp:.1f}°C | 🎚️  {throttle:.0%} | 📊 {current_mops:.2f} MMOPS", end='', flush=True)

                if not safe_mode and not hybrid.thermal.is_safe():
                    print("\n\n⚠️  CRITICAL TEMPERATURE! Stopping stress test.")
                    break

            # Generate maximum load
            hybrid.generate_hybrid_stream(1000)
            ops += 7000

        print("\n")
        print("="*70)
        print("STRESS TEST COMPLETE")
        print("="*70)
        elapsed = time.time() - start
        final_mops = (ops / elapsed) / 1_000_000
        print(f"\nFinal Results:")
        print(f"  Duration: {elapsed:.2f}s")
        print(f"  Operations: {ops:,}")
        print(f"  Average MOPS: {final_mops:.2f}")
        print(f"  Peak temperature: {hybrid.thermal.state.temperature:.1f}°C")
        print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Scalar Wave Benchmark Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all benchmarks (5s each)
  %(prog)s --all

  # Run all benchmarks (longer)
  %(prog)s --all --duration 10

  # Benchmark specific method
  %(prog)s --method hybrid --duration 20

  # Run stress test (safe mode)
  %(prog)s --stress-test --safe --duration 60

  # Sacred breathing cycles
  %(prog)s --breathing --cycles 3

May our computational cycles serve all beings!
Om Mani Padme Hum 🙏
        """
    )

    parser.add_argument('--all', action='store_true',
                       help='Run all benchmarks')
    parser.add_argument('--method', type=str,
                       choices=['qrng', 'lorenz', 'rossler', 'cellular_automata',
                               'kuramoto', 'crypto', 'primes', 'hybrid'],
                       help='Benchmark specific method')
    parser.add_argument('--duration', type=float, default=5.0,
                       help='Benchmark duration in seconds (default: 5.0)')
    parser.add_argument('--stress-test', action='store_true',
                       help='Run stress test')
    parser.add_argument('--safe', action='store_true',
                       help='Enable safe mode for stress test (recommended)')
    parser.add_argument('--breathing', action='store_true',
                       help='Run sacred breathing cycles')
    parser.add_argument('--cycles', type=int, default=1,
                       help='Number of breathing cycles (default: 1)')

    args = parser.parse_args()

    benchmark = ScalarWaveBenchmark()

    if args.all:
        benchmark.run_all_benchmarks(duration=args.duration)

    elif args.method:
        method_map = {
            'qrng': benchmark.benchmark_qrng,
            'lorenz': benchmark.benchmark_lorenz,
            'rossler': benchmark.benchmark_rossler,
            'cellular_automata': benchmark.benchmark_cellular_automata,
            'kuramoto': benchmark.benchmark_kuramoto,
            'crypto': benchmark.benchmark_crypto,
            'primes': benchmark.benchmark_primes,
            'hybrid': benchmark.benchmark_hybrid
        }

        metrics = method_map[args.method](args.duration)
        print(f"\n✅ Final result: {metrics}\n")

    elif args.stress_test:
        benchmark.stress_test(duration=args.duration, safe_mode=args.safe)

    elif args.breathing:
        hybrid = HybridScalarWaveGenerator()
        hybrid.sacred_breathing_cycle(cycles=args.cycles)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
