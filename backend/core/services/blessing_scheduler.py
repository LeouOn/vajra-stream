"""
Blessing Scheduler Service

Automates rotation through target populations for continuous blessing.
Phase 1: Round Robin mode for equal time distribution.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import secrets

from backend.core.services.population_manager import (
    get_population_manager,
    TargetPopulation
)
from backend.core.services.blessing_slideshow_service import (
    get_blessing_slideshow_service,
    IntentionSet,
    MantraType,
    IntentionType
)
from backend.core.services.rng_attunement_service import get_rng_service


class SchedulerMode(str, Enum):
    """Scheduler modes"""
    ROUND_ROBIN = "round_robin"  # Equal time to all (Phase 1)
    PRIORITY_BASED = "priority_based"  # More time to higher priority (Phase 2)
    TIME_WEIGHTED = "time_weighted"  # Prioritize neglected (Phase 2)
    RNG_GUIDED = "rng_guided"  # Extend on strong response (Phase 2)
    HYBRID = "hybrid"  # Combine factors (Phase 2)
    MANUAL = "manual"  # User controls


class SchedulerStatus(str, Enum):
    """Scheduler status"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    TRANSITIONING = "transitioning"
    ERROR = "error"


@dataclass
class SchedulerConfig:
    """Configuration for scheduler"""

    # Mode
    mode: SchedulerMode = SchedulerMode.ROUND_ROBIN

    # Timing
    duration_per_population: int = 1800  # seconds (30 min default)
    transition_pause: int = 30  # seconds between populations

    # Integration
    link_rng: bool = True  # Create RNG session per population
    auto_dedicate: bool = True  # Automatic dedication between populations
    continuous_mode: bool = True  # Run indefinitely

    # Limits (for filtering which populations to include)
    only_active: bool = True  # Only include active populations
    min_priority: int = 1  # Minimum priority to include


@dataclass
class PopulationSession:
    """Statistics for one population's blessing session"""
    population_id: str
    population_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: float = 0.0
    slideshow_session_id: Optional[str] = None
    rng_session_id: Optional[str] = None
    photos_blessed: int = 0
    mantras_repeated: int = 0
    rng_floating_needles: int = 0


@dataclass
class SchedulerSession:
    """Active scheduler session"""
    session_id: str
    config: SchedulerConfig
    status: SchedulerStatus
    start_time: float
    populations_queue: List[str]  # List of population IDs
    current_index: int = 0
    current_population_id: Optional[str] = None
    current_slideshow_id: Optional[str] = None
    current_rng_id: Optional[str] = None
    current_start_time: Optional[float] = None
    cycle_count: int = 0  # Number of complete rotations
    session_history: List[PopulationSession] = field(default_factory=list)

    def get_current_population_id(self) -> Optional[str]:
        """Get current population ID"""
        if 0 <= self.current_index < len(self.populations_queue):
            return self.populations_queue[self.current_index]
        return None


class BlessingScheduler:
    """
    Automated blessing scheduler

    Phase 1 Features:
    - Round robin mode (equal time to all)
    - Integration with slideshow + RNG
    - Continuous or limited cycles
    - Automatic transitions
    - Statistics tracking
    """

    def __init__(self):
        self.sessions: Dict[str, SchedulerSession] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.population_manager = get_population_manager()
        self.slideshow_service = get_blessing_slideshow_service()
        self.rng_service = get_rng_service()

    def _build_queue(self, config: SchedulerConfig) -> List[str]:
        """
        Build queue of population IDs based on config

        Phase 1: Simple filtering by active status and priority
        """
        # Get populations
        populations = self.population_manager.get_all_populations()

        # Filter
        if config.only_active:
            populations = [p for p in populations if p.is_active]

        if config.min_priority > 1:
            populations = [p for p in populations if p.priority >= config.min_priority]

        # Phase 1: Round robin - just use order they were added
        # Sort by added time
        populations.sort(key=lambda p: p.added_time)

        return [p.id for p in populations]

    def start_automation(
        self,
        config: Optional[SchedulerConfig] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Start automated blessing rotation

        Args:
            config: Scheduler configuration
            session_id: Optional custom session ID

        Returns:
            Session ID
        """
        if config is None:
            config = SchedulerConfig()

        if session_id is None:
            session_id = f"scheduler_{int(time.time())}_{secrets.token_hex(4)}"

        # Build queue
        queue = self._build_queue(config)

        if not queue:
            raise ValueError("No populations available for automation")

        # Create session
        session = SchedulerSession(
            session_id=session_id,
            config=config,
            status=SchedulerStatus.RUNNING,
            start_time=time.time(),
            populations_queue=queue,
            current_index=0
        )

        self.sessions[session_id] = session

        # Start async task
        task = asyncio.create_task(self._run_automation_loop(session_id))
        self.running_tasks[session_id] = task

        return session_id

    async def _run_automation_loop(self, session_id: str):
        """
        Main automation loop

        Runs continuously, cycling through populations
        """
        session = self.sessions[session_id]

        try:
            while session.status == SchedulerStatus.RUNNING:
                # Get current population
                pop_id = session.get_current_population_id()
                if not pop_id:
                    # Queue exhausted
                    if session.config.continuous_mode:
                        # Loop back to start
                        session.current_index = 0
                        session.cycle_count += 1
                        continue
                    else:
                        # Stop
                        break

                population = self.population_manager.get_population(pop_id)
                if not population:
                    # Population deleted, skip
                    session.current_index += 1
                    continue

                # Bless this population
                await self._bless_population(session_id, population)

                # Check if still running (might have been stopped)
                session = self.sessions.get(session_id)
                if not session or session.status != SchedulerStatus.RUNNING:
                    break

                # Transition pause
                if session.config.transition_pause > 0:
                    session.status = SchedulerStatus.TRANSITIONING
                    await asyncio.sleep(session.config.transition_pause)
                    session.status = SchedulerStatus.RUNNING

                # Move to next
                session.current_index += 1

            # Finished
            session.status = SchedulerStatus.STOPPED

        except Exception as e:
            print(f"Scheduler error: {e}")
            session.status = SchedulerStatus.ERROR
            raise

    async def _bless_population(
        self,
        session_id: str,
        population: TargetPopulation
    ):
        """
        Run blessing session for one population

        Args:
            session_id: Scheduler session ID
            population: Population to bless
        """
        session = self.sessions[session_id]
        pop_session = PopulationSession(
            population_id=population.id,
            population_name=population.name,
            start_time=time.time()
        )

        try:
            # Create RNG session if enabled
            rng_id = None
            if session.config.link_rng:
                rng_id = self.rng_service.create_session(
                    baseline_tone_arm=5.0,
                    sensitivity=1.0
                )
                pop_session.rng_session_id = rng_id
                session.current_rng_id = rng_id

            # Convert intentions
            intentions = [IntentionType(i) for i in population.intentions]

            # Create intention set
            intention_set = IntentionSet(
                primary_mantra=MantraType(population.mantra_preference),
                intentions=intentions,
                repetitions_per_photo=population.repetitions_per_photo
            )

            # Create slideshow
            slideshow_id = self.slideshow_service.create_session(
                directory_path=population.directory_path,
                intention_set=intention_set,
                loop_mode=True,
                display_duration_ms=population.display_duration_ms,
                rng_session_id=rng_id
            )

            pop_session.slideshow_session_id = slideshow_id
            session.current_slideshow_id = slideshow_id
            session.current_population_id = population.id
            session.current_start_time = time.time()

            # Run for configured duration
            elapsed = 0
            while elapsed < session.config.duration_per_population:
                # Check if session still running
                if session.status != SchedulerStatus.RUNNING:
                    break

                # Sleep in small intervals to allow stopping
                await asyncio.sleep(10)
                elapsed = time.time() - session.current_start_time

            # Stop slideshow
            slideshow_stats = self.slideshow_service.stop_session(slideshow_id)

            # Stop RNG if active
            if rng_id:
                rng_stats = self.rng_service.get_session_summary(rng_id)
                self.rng_service.stop_session(rng_id)
                pop_session.rng_floating_needles = rng_stats.get('floating_needle_count', 0)

            # Record statistics
            pop_session.end_time = time.time()
            pop_session.duration = pop_session.end_time - pop_session.start_time
            pop_session.photos_blessed = slideshow_stats.get('photos_blessed', 0)
            pop_session.mantras_repeated = slideshow_stats.get('total_mantras_repeated', 0)

            # Update population stats
            self.population_manager.record_blessing_session(
                population_id=population.id,
                blessings_sent=pop_session.photos_blessed,
                mantras_repeated=pop_session.mantras_repeated,
                session_duration=pop_session.duration
            )

            # Add to history
            session.session_history.append(pop_session)

            # Clear current tracking
            session.current_slideshow_id = None
            session.current_rng_id = None
            session.current_population_id = None

        except Exception as e:
            print(f"Error blessing population {population.name}: {e}")
            # Record partial session
            pop_session.end_time = time.time()
            pop_session.duration = pop_session.end_time - pop_session.start_time
            session.session_history.append(pop_session)
            raise

    def stop_automation(self, session_id: str) -> Dict[str, Any]:
        """
        Stop automated rotation

        Args:
            session_id: Session to stop

        Returns:
            Final statistics
        """
        session = self.sessions.get(session_id)
        if not session:
            return {}

        # Mark as stopped
        session.status = SchedulerStatus.STOPPED

        # Stop current slideshow if active
        if session.current_slideshow_id:
            try:
                self.slideshow_service.stop_session(session.current_slideshow_id)
            except Exception:
                pass

        # Stop current RNG if active
        if session.current_rng_id:
            try:
                self.rng_service.stop_session(session.current_rng_id)
            except Exception:
                pass

        # Cancel async task
        task = self.running_tasks.get(session_id)
        if task and not task.done():
            task.cancel()

        # Return statistics
        return self.get_session_stats(session_id)

    def pause_automation(self, session_id: str) -> bool:
        """Pause automation (can be resumed)"""
        session = self.sessions.get(session_id)
        if not session or session.status != SchedulerStatus.RUNNING:
            return False

        session.status = SchedulerStatus.PAUSED

        # Pause current slideshow if active
        if session.current_slideshow_id:
            try:
                self.slideshow_service.pause_session(session.current_slideshow_id)
            except Exception:
                pass

        return True

    def resume_automation(self, session_id: str) -> bool:
        """Resume paused automation"""
        session = self.sessions.get(session_id)
        if not session or session.status != SchedulerStatus.PAUSED:
            return False

        session.status = SchedulerStatus.RUNNING

        # Resume current slideshow if active
        if session.current_slideshow_id:
            try:
                self.slideshow_service.resume_session(session.current_slideshow_id)
            except Exception:
                pass

        return True

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get current session statistics"""
        session = self.sessions.get(session_id)
        if not session:
            return {}

        total_duration = time.time() - session.start_time
        completed_sessions = [s for s in session.session_history if s.end_time]

        return {
            'session_id': session.session_id,
            'status': session.status.value,
            'mode': session.config.mode.value,
            'start_time': session.start_time,
            'total_duration': total_duration,
            'cycle_count': session.cycle_count,
            'populations_in_queue': len(session.populations_queue),
            'current_index': session.current_index,
            'current_population_id': session.current_population_id,
            'current_slideshow_id': session.current_slideshow_id,
            'current_rng_id': session.current_rng_id,
            'completed_sessions': len(completed_sessions),
            'total_photos_blessed': sum(s.photos_blessed for s in completed_sessions),
            'total_mantras': sum(s.mantras_repeated for s in completed_sessions),
            'total_rng_floating_needles': sum(s.rng_floating_needles for s in completed_sessions),
            'session_history': [
                {
                    'population_id': s.population_id,
                    'population_name': s.population_name,
                    'start_time': s.start_time,
                    'duration': s.duration,
                    'photos_blessed': s.photos_blessed,
                    'mantras_repeated': s.mantras_repeated,
                    'rng_floating_needles': s.rng_floating_needles
                }
                for s in session.session_history
            ]
        }

    def get_current_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current status including current population details"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        current_pop = None
        if session.current_population_id:
            pop = self.population_manager.get_population(session.current_population_id)
            if pop:
                current_pop = {
                    'id': pop.id,
                    'name': pop.name,
                    'category': pop.category.value,
                    'priority': pop.priority,
                    'mantra': pop.mantra_preference,
                    'intentions': pop.intentions,
                    'photo_count': pop.photo_count
                }

        elapsed = 0
        if session.current_start_time:
            elapsed = time.time() - session.current_start_time

        return {
            'session_id': session.session_id,
            'status': session.status.value,
            'current_population': current_pop,
            'elapsed_seconds': elapsed,
            'target_duration': session.config.duration_per_population,
            'progress_percentage': min(100, (elapsed / session.config.duration_per_population) * 100)
        }

    def get_queue(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get upcoming populations in queue"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        queue_info = []
        for i, pop_id in enumerate(session.populations_queue):
            pop = self.population_manager.get_population(pop_id)
            if pop:
                queue_info.append({
                    'position': i,
                    'is_current': i == session.current_index,
                    'id': pop.id,
                    'name': pop.name,
                    'category': pop.category.value,
                    'priority': pop.priority,
                    'is_urgent': pop.is_urgent,
                    'photo_count': pop.photo_count,
                    'last_blessed': pop.last_blessed_time
                })

        return queue_info


# Global instance
_scheduler: Optional[BlessingScheduler] = None


def get_scheduler() -> BlessingScheduler:
    """Get or create global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BlessingScheduler()
    return _scheduler
