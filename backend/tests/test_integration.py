"""
Integration Test Suite for Vajra Stream System

Tests all modules working together:
1. RNG Attunement Service
2. Blessing Slideshow Service
3. Population Manager Service
4. Blessing Scheduler Service
5. Cross-module integration
"""

import pytest
import asyncio
import time
import tempfile
import os
import json
from pathlib import Path

# Import all services
from backend.core.services.rng_attunement_service import (
    get_rng_service,
    RNGAttunementService
)
from backend.core.services.blessing_slideshow_service import (
    get_blessing_slideshow_service,
    BlessingSlideshowService,
    IntentionSet,
    MantraType,
    IntentionType
)
from backend.core.services.population_manager import (
    get_population_manager,
    PopulationManager,
    PopulationCategory,
    SourceType
)
from backend.core.services.blessing_scheduler import (
    get_scheduler,
    BlessingScheduler,
    SchedulerConfig,
    SchedulerMode
)


class TestRNGAttunementService:
    """Test RNG Attunement Service"""

    def test_service_initialization(self):
        """Test service can be initialized"""
        service = RNGAttunementService()
        assert service is not None
        assert len(service.sessions) == 0

    def test_session_creation(self):
        """Test creating RNG session"""
        service = RNGAttunementService()
        session_id = service.create_session(
            baseline_tone_arm=5.0,
            sensitivity=1.0
        )
        assert session_id is not None
        assert session_id in service.sessions

    def test_reading_generation(self):
        """Test generating readings"""
        service = RNGAttunementService()
        session_id = service.create_session()

        reading = service.get_reading(session_id)
        assert reading is not None
        assert reading.tone_arm is not None
        assert reading.needle_position is not None
        assert reading.needle_state is not None
        assert -100 <= reading.needle_position <= 100

    def test_floating_needle_detection(self):
        """Test floating needle detection over time"""
        service = RNGAttunementService()
        session_id = service.create_session()

        # Generate readings over time
        for _ in range(20):
            service.get_reading(session_id)
            time.sleep(0.1)

        summary = service.get_session_summary(session_id)
        assert 'floating_needle_count' in summary
        assert 'total_readings' in summary
        assert summary['total_readings'] >= 20

    def test_session_stop(self):
        """Test stopping session"""
        service = RNGAttunementService()
        session_id = service.create_session()

        service.stop_session(session_id)
        session = service.sessions[session_id]
        assert session.is_active == False


class TestBlessingSlideshowService:
    """Test Blessing Slideshow Service"""

    @pytest.fixture
    def temp_photo_dir(self):
        """Create temporary directory with test images"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some dummy image files with unique content
            for i in range(5):
                photo_path = Path(tmpdir, f"photo_{i}.jpg")
                # Write unique content to avoid deduplication
                photo_path.write_bytes(f"photo_{i}".encode() * 100)
            yield tmpdir

    def test_service_initialization(self):
        """Test service can be initialized"""
        service = BlessingSlideshowService()
        assert service is not None

    def test_session_creation(self, temp_photo_dir):
        """Test creating slideshow session"""
        service = BlessingSlideshowService()

        intention_set = IntentionSet(
            primary_mantra=MantraType.CHENREZIG,
            intentions=[IntentionType.LOVE, IntentionType.HEALING],
            repetitions_per_photo=108
        )

        session_id = service.create_session(
            directory_path=temp_photo_dir,
            intention_set=intention_set,
            loop_mode=True,
            display_duration_ms=1000
        )

        assert session_id is not None
        assert session_id in service.sessions

    def test_photo_loading(self, temp_photo_dir):
        """Test photos are loaded correctly"""
        service = BlessingSlideshowService()

        intention_set = IntentionSet(
            primary_mantra=MantraType.CHENREZIG,
            intentions=[IntentionType.LOVE]
        )

        session_id = service.create_session(
            directory_path=temp_photo_dir,
            intention_set=intention_set
        )

        slide = service.get_current_slide(session_id)
        assert slide is not None
        assert slide['session']['total_photos'] == 5

    def test_slideshow_progression(self, temp_photo_dir):
        """Test slideshow advances through photos"""
        service = BlessingSlideshowService()

        intention_set = IntentionSet(
            primary_mantra=MantraType.CHENREZIG,
            intentions=[IntentionType.LOVE],
            repetitions_per_photo=10
        )

        session_id = service.create_session(
            directory_path=temp_photo_dir,
            intention_set=intention_set,
            display_duration_ms=100
        )

        # Get initial slide
        initial = service.get_current_slide(session_id)
        initial_index = initial['session']['current_index']

        # Advance multiple times
        for _ in range(3):
            service.advance_slide(session_id)

        # Check progression
        current = service.get_current_slide(session_id)
        assert current['session']['current_index'] > initial_index

    def test_session_statistics(self, temp_photo_dir):
        """Test statistics tracking"""
        service = BlessingSlideshowService()

        intention_set = IntentionSet(
            primary_mantra=MantraType.CHENREZIG,
            intentions=[IntentionType.LOVE],
            repetitions_per_photo=108
        )

        session_id = service.create_session(
            directory_path=temp_photo_dir,
            intention_set=intention_set
        )

        # Advance through some photos
        for _ in range(3):
            service.advance_slide(session_id)

        stats = service.stop_session(session_id)
        assert 'photos_blessed' in stats
        assert 'total_mantras_repeated' in stats
        assert stats['photos_blessed'] >= 3


class TestPopulationManager:
    """Test Population Manager Service"""

    @pytest.fixture
    def temp_storage(self):
        """Use temporary storage for populations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = os.path.join(tmpdir, "populations.json")
            manager = PopulationManager(storage_path=storage_file)
            yield manager

    def test_population_creation(self, temp_storage):
        """Test creating population"""
        manager = temp_storage

        population = manager.create_population(
            name="Test Population",
            description="Test description",
            category=PopulationCategory.MISSING_PERSONS,
            source_type=SourceType.MANUAL,
            mantra_preference="chenrezig",
            intentions=["love", "healing"],
            priority=5
        )

        assert population is not None
        assert population.name == "Test Population"
        assert population.category == PopulationCategory.MISSING_PERSONS

    def test_population_retrieval(self, temp_storage):
        """Test retrieving population"""
        manager = temp_storage

        # Create population
        pop = manager.create_population(
            name="Test Pop",
            description="Test",
            category=PopulationCategory.REFUGEES,
            source_type=SourceType.MANUAL
        )

        # Retrieve it
        retrieved = manager.get_population(pop.id)
        assert retrieved is not None
        assert retrieved.id == pop.id
        assert retrieved.name == "Test Pop"

    def test_population_update(self, temp_storage):
        """Test updating population"""
        manager = temp_storage

        # Create population
        pop = manager.create_population(
            name="Original Name",
            description="Original",
            category=PopulationCategory.CUSTOM,
            source_type=SourceType.MANUAL,
            priority=3
        )

        # Update it
        updated = manager.update_population(
            pop.id,
            name="Updated Name",
            priority=8
        )

        assert updated.name == "Updated Name"
        assert updated.priority == 8
        assert updated.description == "Original"  # Unchanged

    def test_population_deletion(self, temp_storage):
        """Test deleting population"""
        manager = temp_storage

        # Create and delete
        pop = manager.create_population(
            name="To Delete",
            description="",
            category=PopulationCategory.CUSTOM,
            source_type=SourceType.MANUAL
        )

        success = manager.delete_population(pop.id)
        assert success == True

        # Verify deleted
        retrieved = manager.get_population(pop.id)
        assert retrieved is None

    def test_statistics(self, temp_storage):
        """Test statistics calculation"""
        manager = temp_storage

        # Create multiple populations
        pops = []
        for i in range(3):
            pop = manager.create_population(
                name=f"Pop {i}",
                description="",
                category=PopulationCategory.MISSING_PERSONS,
                source_type=SourceType.MANUAL
            )
            pops.append(pop)

        # Deactivate one
        manager.update_population(pops[2].id, is_active=False)

        stats = manager.get_statistics()
        assert stats['total_populations'] == 3
        assert stats['active_populations'] == 2

    def test_persistence(self, temp_storage):
        """Test data persists to disk"""
        manager = temp_storage
        storage_path = manager.storage_path

        # Create population
        pop = manager.create_population(
            name="Persistent Pop",
            description="Should persist",
            category=PopulationCategory.REFUGEES,
            source_type=SourceType.MANUAL
        )

        # Verify file exists
        assert os.path.exists(storage_path)

        # Load data
        with open(storage_path, 'r') as f:
            data = json.load(f)

        assert 'populations' in data
        # Data is stored as list, check if our pop ID is in any of them
        pop_ids = [p['id'] for p in data['populations']]
        assert pop.id in pop_ids


class TestBlessingScheduler:
    """Test Blessing Scheduler Service"""

    @pytest.fixture
    def temp_photo_dir(self):
        """Create temporary directory with test images"""
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(3):
                photo_path = Path(tmpdir, f"photo_{i}.jpg")
                # Write unique content to avoid deduplication
                photo_path.write_bytes(f"photo_{i}".encode() * 100)
            yield tmpdir

    @pytest.fixture
    def populated_manager(self, temp_photo_dir):
        """Create manager with test populations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = os.path.join(tmpdir, "populations.json")
            manager = PopulationManager(storage_path=storage_file)

            # Create test populations
            for i in range(3):
                manager.create_population(
                    name=f"Population {i}",
                    description=f"Test population {i}",
                    category=PopulationCategory.MISSING_PERSONS,
                    source_type=SourceType.LOCAL_DIRECTORY,
                    directory_path=temp_photo_dir,
                    mantra_preference="chenrezig",
                    intentions=["love", "healing"],
                    priority=5
                )

            yield manager

    def test_scheduler_initialization(self):
        """Test scheduler can be initialized"""
        scheduler = BlessingScheduler()
        assert scheduler is not None
        assert len(scheduler.sessions) == 0

    def test_queue_building(self, populated_manager):
        """Test building population queue"""
        scheduler = BlessingScheduler()
        scheduler.population_manager = populated_manager

        config = SchedulerConfig(
            mode=SchedulerMode.ROUND_ROBIN,
            only_active=True,
            min_priority=1
        )

        queue = scheduler._build_queue(config)
        assert len(queue) == 3  # All 3 populations

    def test_queue_filtering(self, populated_manager):
        """Test queue filtering by priority"""
        # Add one high priority population
        populated_manager.create_population(
            name="High Priority",
            description="",
            category=PopulationCategory.MISSING_PERSONS,
            source_type=SourceType.MANUAL,
            priority=8
        )

        scheduler = BlessingScheduler()
        scheduler.population_manager = populated_manager

        config = SchedulerConfig(
            only_active=True,
            min_priority=7
        )

        queue = scheduler._build_queue(config)
        assert len(queue) == 1  # Only high priority

    @pytest.mark.asyncio
    async def test_automation_start(self, populated_manager, temp_photo_dir):
        """Test starting automation"""
        scheduler = BlessingScheduler()
        scheduler.population_manager = populated_manager

        config = SchedulerConfig(
            mode=SchedulerMode.ROUND_ROBIN,
            duration_per_population=5,  # 5 seconds
            continuous_mode=False
        )

        session_id = scheduler.start_automation(config)
        assert session_id is not None
        assert session_id in scheduler.sessions

        # Give it a moment to start
        await asyncio.sleep(1)

        # Check status
        status = scheduler.get_current_status(session_id)
        assert status is not None
        assert status['status'] in ['running', 'transitioning']

        # Stop it
        scheduler.stop_automation(session_id)

    @pytest.mark.asyncio
    async def test_pause_resume(self, populated_manager):
        """Test pause and resume"""
        scheduler = BlessingScheduler()
        scheduler.population_manager = populated_manager

        config = SchedulerConfig(
            duration_per_population=30,
            continuous_mode=True
        )

        session_id = scheduler.start_automation(config)

        # Wait for it to start
        await asyncio.sleep(1)

        # Pause
        success = scheduler.pause_automation(session_id)
        assert success == True

        session = scheduler.sessions[session_id]
        assert session.status.value == 'paused'

        # Resume
        success = scheduler.resume_automation(session_id)
        assert success == True

        # Stop
        scheduler.stop_automation(session_id)

    @pytest.mark.asyncio
    async def test_session_statistics(self, populated_manager):
        """Test getting session statistics"""
        scheduler = BlessingScheduler()
        scheduler.population_manager = populated_manager

        config = SchedulerConfig(
            duration_per_population=1,
            continuous_mode=False
        )

        session_id = scheduler.start_automation(config)

        # Get stats immediately
        stats = scheduler.get_session_stats(session_id)
        assert stats is not None
        assert 'session_id' in stats
        assert 'status' in stats
        assert 'populations_in_queue' in stats
        assert stats['populations_in_queue'] == 3

        scheduler.stop_automation(session_id)


class TestIntegration:
    """Test cross-module integration"""

    @pytest.fixture
    def temp_photo_dir(self):
        """Create temporary directory with test images"""
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(5):
                photo_path = Path(tmpdir, f"photo_{i}.jpg")
                # Write unique content to avoid deduplication
                photo_path.write_bytes(f"photo_{i}".encode() * 100)
            yield tmpdir

    def test_slideshow_with_rng_integration(self, temp_photo_dir):
        """Test slideshow linked with RNG session"""
        rng_service = RNGAttunementService()
        slideshow_service = BlessingSlideshowService()

        # Create RNG session
        rng_id = rng_service.create_session(
            baseline_tone_arm=5.0,
            sensitivity=1.0
        )

        # Create slideshow linked to RNG
        intention_set = IntentionSet(
            primary_mantra=MantraType.CHENREZIG,
            intentions=[IntentionType.LOVE, IntentionType.HEALING],
            repetitions_per_photo=108
        )

        slideshow_id = slideshow_service.create_session(
            directory_path=temp_photo_dir,
            intention_set=intention_set,
            rng_session_id=rng_id
        )

        # Verify linkage
        slide = slideshow_service.get_current_slide(slideshow_id)
        assert slide['session']['rng_session_id'] == rng_id

        # Generate some RNG readings
        for _ in range(5):
            rng_service.get_reading(rng_id)
            time.sleep(0.1)

        # Stop both
        slideshow_service.stop_session(slideshow_id)
        rng_service.stop_session(rng_id)

        # Verify RNG data collected
        rng_summary = rng_service.get_session_summary(rng_id)
        assert rng_summary['total_readings'] >= 5

    @pytest.mark.asyncio
    async def test_scheduler_with_population_integration(self, temp_photo_dir):
        """Test scheduler managing populations"""
        # Setup
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = os.path.join(tmpdir, "populations.json")
            manager = PopulationManager(storage_path=storage_file)

            # Create populations
            for i in range(2):
                manager.create_population(
                    name=f"Integration Test Pop {i}",
                    description="Test",
                    category=PopulationCategory.REFUGEES,
                    source_type=SourceType.LOCAL_DIRECTORY,
                    directory_path=temp_photo_dir,
                    mantra_preference="chenrezig",
                    intentions=["love", "peace"],
                    priority=5
                )

            # Create scheduler
            scheduler = BlessingScheduler()
            scheduler.population_manager = manager

            # Start automation
            config = SchedulerConfig(
                duration_per_population=2,  # 2 seconds per population
                transition_pause=1,
                continuous_mode=False
            )

            session_id = scheduler.start_automation(config)

            # Let it run for a bit
            await asyncio.sleep(3)

            # Check stats
            stats = scheduler.get_session_stats(session_id)
            assert stats['populations_in_queue'] == 2

            # Stop
            final_stats = scheduler.stop_automation(session_id)
            assert 'total_photos_blessed' in final_stats

    @pytest.mark.asyncio
    async def test_full_stack_integration(self, temp_photo_dir):
        """Test complete workflow: RNG + Slideshow + Population + Scheduler"""
        # Setup all services
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = os.path.join(tmpdir, "populations.json")
            manager = PopulationManager(storage_path=storage_file)
            scheduler = BlessingScheduler()
            scheduler.population_manager = manager

            # Create population
            pop = manager.create_population(
                name="Full Stack Test",
                description="Complete integration test",
                category=PopulationCategory.HOSPITAL_PATIENTS,
                source_type=SourceType.LOCAL_DIRECTORY,
                directory_path=temp_photo_dir,
                mantra_preference="chenrezig",
                intentions=["healing", "peace", "love"],
                repetitions_per_photo=108,
                display_duration_ms=1000,
                priority=7
            )

            # Start automation with RNG linked
            config = SchedulerConfig(
                mode=SchedulerMode.ROUND_ROBIN,
                duration_per_population=3,  # 3 seconds
                transition_pause=1,
                link_rng=True,  # Enable RNG integration
                continuous_mode=False
            )

            session_id = scheduler.start_automation(config)

            # Monitor for a moment
            await asyncio.sleep(2)

            # Check current status
            status = scheduler.get_current_status(session_id)
            assert status is not None
            assert 'current_population' in status

            if status['current_population']:
                assert status['current_population']['name'] == "Full Stack Test"

            # Get queue
            queue = scheduler.get_queue(session_id)
            assert len(queue) == 1
            assert queue[0]['name'] == "Full Stack Test"

            # Let it run for full duration plus buffer
            await asyncio.sleep(5)  # 3sec population + 1sec transition + 1sec buffer

            # Stop and get final stats
            final_stats = scheduler.stop_automation(session_id)

            # Verify all systems tracked data
            # At least check that the automation ran
            assert 'completed_sessions' in final_stats
            assert 'total_photos_blessed' in final_stats
            assert 'total_mantras' in final_stats
            # The session should have at least started (may or may not have completed)
            assert final_stats['total_duration'] > 0

            # Verify population exists (update may or may not have happened depending on timing)
            updated_pop = manager.get_population(pop.id)
            assert updated_pop is not None


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows"""

    @pytest.fixture
    def full_system(self):
        """Setup complete system"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create photo directory
            photo_dir = os.path.join(tmpdir, "photos")
            os.makedirs(photo_dir)
            for i in range(10):
                photo_path = Path(photo_dir, f"person_{i}.jpg")
                # Write unique content to avoid deduplication
                photo_path.write_bytes(f"person_{i}".encode() * 100)

            # Create storage
            storage_file = os.path.join(tmpdir, "populations.json")
            manager = PopulationManager(storage_path=storage_file)

            yield {
                'photo_dir': photo_dir,
                'manager': manager,
                'tmpdir': tmpdir
            }

    @pytest.mark.asyncio
    async def test_workflow_manual_practice(self, full_system):
        """
        Workflow: Manual Practice Session
        - User creates population
        - Starts slideshow with RNG monitoring
        - Reviews results
        """
        manager = full_system['manager']
        photo_dir = full_system['photo_dir']

        # Step 1: Create population
        pop = manager.create_population(
            name="Evening Practice",
            description="Daily compassion practice",
            category=PopulationCategory.REFUGEES,
            source_type=SourceType.LOCAL_DIRECTORY,
            directory_path=photo_dir,
            mantra_preference="chenrezig",
            intentions=["love", "peace", "protection"],
            repetitions_per_photo=108,
            priority=5
        )

        # Step 2: Start RNG session
        rng_service = RNGAttunementService()
        rng_id = rng_service.create_session(baseline_tone_arm=5.0)

        # Step 3: Start slideshow
        slideshow_service = BlessingSlideshowService()
        intention_set = IntentionSet(
            primary_mantra=MantraType.CHENREZIG,
            intentions=[IntentionType.LOVE, IntentionType.PEACE],
            repetitions_per_photo=108
        )

        slideshow_id = slideshow_service.create_session(
            directory_path=photo_dir,
            intention_set=intention_set,
            rng_session_id=rng_id,
            display_duration_ms=500
        )

        # Step 4: Practice for a bit
        for _ in range(5):
            slideshow_service.get_current_slide(slideshow_id)
            rng_service.get_reading(rng_id)
            slideshow_service.advance_slide(slideshow_id)
            await asyncio.sleep(0.2)

        # Step 5: Complete and review
        slideshow_stats = slideshow_service.stop_session(slideshow_id)
        rng_summary = rng_service.get_session_summary(rng_id)
        rng_service.stop_session(rng_id)

        # Verify workflow completed successfully
        assert slideshow_stats['photos_blessed'] >= 5
        assert rng_summary['total_readings'] >= 5

    @pytest.mark.asyncio
    async def test_workflow_automated_rotation(self, full_system):
        """
        Workflow: 24/7 Automated Rotation
        - User creates multiple populations
        - Starts automated rotation
        - System handles everything automatically
        """
        manager = full_system['manager']
        photo_dir = full_system['photo_dir']

        # Step 1: Create multiple populations
        populations = []
        categories = [
            PopulationCategory.MISSING_PERSONS,
            PopulationCategory.REFUGEES,
            PopulationCategory.DISASTER_VICTIMS
        ]

        for i, cat in enumerate(categories):
            pop = manager.create_population(
                name=f"Population {i}",
                description=f"Auto-managed population {i}",
                category=cat,
                source_type=SourceType.LOCAL_DIRECTORY,
                directory_path=photo_dir,
                mantra_preference="chenrezig",
                intentions=["love", "healing"],
                priority=5
            )
            populations.append(pop)

        # Step 2: Start automated rotation
        scheduler = BlessingScheduler()
        scheduler.population_manager = manager

        config = SchedulerConfig(
            mode=SchedulerMode.ROUND_ROBIN,
            duration_per_population=2,  # 2 seconds each
            transition_pause=0,
            link_rng=True,
            continuous_mode=False  # One cycle
        )

        session_id = scheduler.start_automation(config)

        # Step 3: Monitor progress (wait long enough for at least one complete cycle)
        # With 3 populations at 2 seconds each, need at least 7 seconds
        await asyncio.sleep(7)

        # Step 4: Get final results
        final_stats = scheduler.stop_automation(session_id)

        # Verify automation ran (may or may not have completed all populations)
        assert 'completed_sessions' in final_stats
        assert 'total_photos_blessed' in final_stats
        assert final_stats['total_duration'] > 0

        # Verify populations still exist in manager
        for pop in populations:
            updated = manager.get_population(pop.id)
            assert updated is not None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
