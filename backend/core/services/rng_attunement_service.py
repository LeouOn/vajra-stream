"""
RNG Attunement Reading Service
Inspired by Ken Ogger's Super Scio and E-meter technology
Provides quantum-random readings that may be influenced by psychic/paranormal activity
"""

import numpy as np
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from collections import deque
import hashlib
import secrets


class NeedleState(str, Enum):
    """E-meter style needle states"""
    STUCK = "stuck"  # No movement
    RISING = "rising"  # Moving up (increasing charge)
    FALLING = "falling"  # Moving down (releasing charge)
    FLOATING = "floating"  # Floating needle - indicator of release/EP
    ROCKSLAM = "rockslam"  # Violent oscillation (indicates charge)
    THETA_BOP = "theta_bop"  # Rhythmic movement


class ReadingQuality(str, Enum):
    """Quality of the attunement reading"""
    EXCELLENT = "excellent"  # Clear, stable signal
    GOOD = "good"  # Stable with minor fluctuations
    FAIR = "fair"  # Some noise
    POOR = "poor"  # High noise, unstable
    DISRUPTED = "disrupted"  # External interference


@dataclass
class AttunementReading:
    """Single RNG attunement reading"""
    timestamp: float
    raw_value: float  # Raw RNG value 0.0-1.0
    tone_arm: float  # E-meter tone arm position 0.0-10.0
    needle_position: float  # Needle deflection -100 to +100
    needle_state: NeedleState
    quality: ReadingQuality
    entropy: float  # Measure of randomness/chaos
    coherence: float  # Measure of order/pattern
    trend: float  # Rising (+) or falling (-)
    floating_needle_score: float  # 0.0-1.0, higher = more likely FN


@dataclass
class AttunementSession:
    """RNG Attunement session tracking"""
    session_id: str
    start_time: float
    readings: deque = field(default_factory=lambda: deque(maxlen=1000))
    baseline_tone_arm: float = 5.0
    sensitivity: float = 1.0
    is_active: bool = True
    total_readings: int = 0
    floating_needle_count: int = 0
    last_fn_time: Optional[float] = None

    def add_reading(self, reading: AttunementReading):
        """Add a reading to the session"""
        self.readings.append(reading)
        self.total_readings += 1
        if reading.needle_state == NeedleState.FLOATING:
            self.floating_needle_count += 1
            self.last_fn_time = reading.timestamp


class RNGAttunementService:
    """
    Service for generating RNG-based attunement readings

    This system uses multiple entropy sources to generate random numbers
    that practitioners believe may be influenced by consciousness/intention.

    Inspired by:
    - Ken Ogger's Super Scio E-meter concepts
    - PEAR lab consciousness-RNG research
    - Scientology auditing technology
    - Radionics attunement principles
    """

    def __init__(self):
        self.sessions: Dict[str, AttunementSession] = {}
        self.global_baseline = 5.0
        self._entropy_pool = deque(maxlen=100)
        self._initialize_entropy_pool()

    def _initialize_entropy_pool(self):
        """Initialize entropy pool with high-quality random data"""
        for _ in range(100):
            # Use cryptographic random as base entropy
            entropy_bytes = secrets.token_bytes(32)
            # Mix with timestamp for uniqueness
            timestamp_bytes = str(time.time()).encode()
            combined = hashlib.sha256(entropy_bytes + timestamp_bytes).digest()
            # Convert to float 0.0-1.0
            entropy_value = int.from_bytes(combined[:4], 'big') / (2**32)
            self._entropy_pool.append(entropy_value)

    def _generate_quantum_like_random(self) -> float:
        """
        Generate quantum-like random number

        Uses multiple entropy sources and combines them in ways that
        radionics practitioners believe may be influenced by consciousness.

        Returns: Float between 0.0 and 1.0
        """
        # Primary: cryptographic random
        primary = secrets.randbelow(2**32) / (2**32)

        # Secondary: numpy random (Mersenne Twister)
        secondary = np.random.random()

        # Tertiary: time-based micro-fluctuations
        time_component = (time.time() * 1000000) % 1.0

        # Entropy pool contribution
        pool_sample = sum(list(self._entropy_pool)[-5:]) / 5.0 if self._entropy_pool else 0.5

        # Combine with weighted average
        # This combination is where consciousness influence might occur
        combined = (
            primary * 0.4 +
            secondary * 0.3 +
            time_component * 0.2 +
            pool_sample * 0.1
        )

        # Add to entropy pool for feedback
        self._entropy_pool.append(combined)

        return combined

    def _calculate_entropy(self, recent_values: List[float]) -> float:
        """
        Calculate Shannon entropy of recent readings
        High entropy = high randomness/chaos
        """
        if len(recent_values) < 2:
            return 0.5

        # Bin the values
        hist, _ = np.histogram(recent_values, bins=10, range=(0, 1))
        # Normalize
        hist = hist / len(recent_values)
        # Calculate entropy
        entropy = -np.sum([p * np.log2(p) for p in hist if p > 0])
        # Normalize to 0-1 (max entropy for 10 bins is log2(10) ≈ 3.32)
        normalized_entropy = entropy / 3.32

        return float(normalized_entropy)

    def _calculate_coherence(self, recent_values: List[float]) -> float:
        """
        Calculate coherence (inverse of variance)
        High coherence = low variance = more ordered/patterned
        """
        if len(recent_values) < 2:
            return 0.5

        variance = np.var(recent_values)
        # Coherence is inverse of variance, normalized
        coherence = 1.0 / (1.0 + variance * 10)

        return float(coherence)

    def _detect_needle_state(
        self,
        current_position: float,
        recent_positions: List[float],
        recent_velocities: List[float]
    ) -> NeedleState:
        """
        Detect E-meter style needle state

        FLOATING: Small, rhythmic oscillations around zero (indicates release/EP)
        RISING: Consistent upward movement (increasing charge)
        FALLING: Consistent downward movement (releasing charge)
        ROCKSLAM: Violent, rapid oscillations (indicates charge on item)
        THETA_BOP: Regular, rhythmic movement
        STUCK: Little to no movement
        """
        if len(recent_positions) < 5:
            return NeedleState.STUCK

        # Calculate movement statistics
        velocity_std = np.std(recent_velocities) if recent_velocities else 0
        position_range = max(recent_positions) - min(recent_positions)
        avg_velocity = np.mean(recent_velocities) if recent_velocities else 0

        # Floating Needle: small oscillations, low velocity, near zero
        if (position_range < 5 and
            velocity_std < 2 and
            abs(np.mean(recent_positions)) < 10):
            return NeedleState.FLOATING

        # Rock Slam: high velocity variation, large swings
        if velocity_std > 10 and position_range > 30:
            return NeedleState.ROCKSLAM

        # Theta Bop: regular oscillation pattern
        # Check for periodicity using autocorrelation
        if len(recent_positions) >= 10:
            positions_array = np.array(recent_positions)
            autocorr = np.correlate(positions_array - np.mean(positions_array),
                                   positions_array - np.mean(positions_array),
                                   mode='same')
            if np.max(autocorr[1:]) > 0.7 * autocorr[len(autocorr)//2]:
                return NeedleState.THETA_BOP

        # Rising: consistent upward trend
        if avg_velocity > 2 and position_range > 10:
            return NeedleState.RISING

        # Falling: consistent downward trend
        if avg_velocity < -2 and position_range > 10:
            return NeedleState.FALLING

        # Default: stuck
        return NeedleState.STUCK

    def _calculate_floating_needle_score(
        self,
        needle_state: NeedleState,
        coherence: float,
        recent_positions: List[float]
    ) -> float:
        """
        Calculate likelihood of genuine Floating Needle (0.0-1.0)

        A true FN in auditing indicates:
        - End Phenomenon (EP) reached
        - Charge released on item
        - Good indicator to end process
        """
        score = 0.0

        # Base score from needle state
        if needle_state == NeedleState.FLOATING:
            score += 0.6
        elif needle_state == NeedleState.THETA_BOP:
            score += 0.3
        elif needle_state == NeedleState.STUCK:
            score += 0.1

        # Bonus for high coherence (organized pattern)
        score += coherence * 0.3

        # Bonus for positions near zero (neutral)
        if recent_positions:
            avg_pos = abs(np.mean(recent_positions))
            if avg_pos < 5:
                score += 0.1

        return min(1.0, score)

    def _assess_reading_quality(
        self,
        entropy: float,
        coherence: float,
        needle_state: NeedleState
    ) -> ReadingQuality:
        """
        Assess overall quality of the reading
        """
        # Excellent: high coherence, moderate entropy, stable needle
        if (coherence > 0.7 and
            0.3 < entropy < 0.7 and
            needle_state in [NeedleState.FLOATING, NeedleState.THETA_BOP]):
            return ReadingQuality.EXCELLENT

        # Good: decent coherence, reasonable entropy
        if coherence > 0.5 and 0.2 < entropy < 0.8:
            return ReadingQuality.GOOD

        # Disrupted: rockslam or extreme values
        if needle_state == NeedleState.ROCKSLAM or entropy > 0.9:
            return ReadingQuality.DISRUPTED

        # Poor: low coherence, extreme entropy
        if coherence < 0.3 or entropy < 0.1 or entropy > 0.9:
            return ReadingQuality.POOR

        # Default: Fair
        return ReadingQuality.FAIR

    def create_session(
        self,
        session_id: Optional[str] = None,
        baseline_tone_arm: float = 5.0,
        sensitivity: float = 1.0
    ) -> str:
        """
        Create a new attunement session

        Args:
            session_id: Optional session identifier
            baseline_tone_arm: Starting tone arm position (0-10, default 5)
            sensitivity: Reading sensitivity multiplier (default 1.0)

        Returns:
            Session ID
        """
        if session_id is None:
            session_id = f"rng_session_{int(time.time())}_{secrets.token_hex(4)}"

        session = AttunementSession(
            session_id=session_id,
            start_time=time.time(),
            baseline_tone_arm=baseline_tone_arm,
            sensitivity=sensitivity
        )

        self.sessions[session_id] = session
        return session_id

    def get_reading(self, session_id: str) -> Optional[AttunementReading]:
        """
        Get a new attunement reading for a session

        This is the main method that generates readings which may be
        influenced by psychic/paranormal activity according to radionics theory.

        Args:
            session_id: The session to generate reading for

        Returns:
            AttunementReading or None if session not found
        """
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            return None

        # Generate quantum-like random value
        raw_value = self._generate_quantum_like_random()

        # Calculate tone arm position (0-10 scale)
        # Tone arm represents overall charge level
        tone_arm_delta = (raw_value - 0.5) * 2 * session.sensitivity
        tone_arm = session.baseline_tone_arm + tone_arm_delta
        tone_arm = max(0, min(10, tone_arm))  # Clamp to 0-10

        # Calculate needle position (-100 to +100)
        # Needle represents momentary charge fluctuations
        recent_raw = [r.raw_value for r in list(session.readings)[-20:]]
        if recent_raw:
            baseline = np.mean(recent_raw)
        else:
            baseline = 0.5

        needle_delta = (raw_value - baseline) * 200 * session.sensitivity
        needle_position = max(-100, min(100, needle_delta))

        # Get recent positions for analysis
        recent_positions = [r.needle_position for r in list(session.readings)[-20:]]
        recent_velocities = []
        if len(recent_positions) >= 2:
            recent_velocities = [
                recent_positions[i] - recent_positions[i-1]
                for i in range(1, len(recent_positions))
            ]

        # Calculate entropy and coherence
        recent_values = recent_raw + [raw_value]
        entropy = self._calculate_entropy(recent_values)
        coherence = self._calculate_coherence(recent_values)

        # Detect needle state
        needle_state = self._detect_needle_state(
            needle_position,
            recent_positions + [needle_position],
            recent_velocities
        )

        # Calculate trend
        if len(recent_positions) >= 5:
            trend = float(np.mean(recent_velocities[-5:]))
        else:
            trend = 0.0

        # Calculate floating needle score
        fn_score = self._calculate_floating_needle_score(
            needle_state,
            coherence,
            recent_positions + [needle_position]
        )

        # Assess quality
        quality = self._assess_reading_quality(entropy, coherence, needle_state)

        # Create reading
        reading = AttunementReading(
            timestamp=time.time(),
            raw_value=raw_value,
            tone_arm=tone_arm,
            needle_position=needle_position,
            needle_state=needle_state,
            quality=quality,
            entropy=entropy,
            coherence=coherence,
            trend=trend,
            floating_needle_score=fn_score
        )

        # Add to session
        session.add_reading(reading)

        return reading

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get summary statistics for a session"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        readings = list(session.readings)
        if not readings:
            return {
                "session_id": session_id,
                "total_readings": 0,
                "duration_seconds": 0,
                "status": "no_data"
            }

        return {
            "session_id": session_id,
            "total_readings": session.total_readings,
            "floating_needle_count": session.floating_needle_count,
            "last_fn_time": session.last_fn_time,
            "duration_seconds": time.time() - session.start_time,
            "avg_tone_arm": float(np.mean([r.tone_arm for r in readings])),
            "avg_coherence": float(np.mean([r.coherence for r in readings])),
            "avg_entropy": float(np.mean([r.entropy for r in readings])),
            "needle_state_distribution": {
                state.value: sum(1 for r in readings if r.needle_state == state)
                for state in NeedleState
            },
            "quality_distribution": {
                quality.value: sum(1 for r in readings if r.quality == quality)
                for quality in ReadingQuality
            },
            "is_active": session.is_active
        }

    def stop_session(self, session_id: str) -> bool:
        """Stop an active session"""
        session = self.sessions.get(session_id)
        if session:
            session.is_active = False
            return True
        return False

    def get_all_sessions(self) -> List[str]:
        """Get all session IDs"""
        return list(self.sessions.keys())


# Global service instance
_rng_service: Optional[RNGAttunementService] = None


def get_rng_service() -> RNGAttunementService:
    """Get or create the global RNG service instance"""
    global _rng_service
    if _rng_service is None:
        _rng_service = RNGAttunementService()
    return _rng_service
