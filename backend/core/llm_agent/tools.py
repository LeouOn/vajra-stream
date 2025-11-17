"""
LLM Agent Tool Calling Interface for Vajra Stream

Provides a standardized interface for LLM agents to interact with the Vajra Stream
radionics system via tool calling (function calling).

Each function is designed to be called by an LLM agent and returns structured data
that can be used in the agent's responses.
"""

from typing import Dict, List, Optional, Any
import requests
from enum import Enum


class APIClient:
    """Client for making requests to Vajra Stream API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def _get(self, endpoint: str) -> Dict[str, Any]:
        """Make GET request"""
        response = requests.get(f"{self.base_url}{endpoint}")
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make POST request"""
        response = requests.post(f"{self.base_url}{endpoint}", json=data or {})
        response.raise_for_status()
        return response.json()

    def _put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make PUT request"""
        response = requests.put(f"{self.base_url}{endpoint}", json=data)
        response.raise_for_status()
        return response.json()

    def _delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request"""
        response = requests.delete(f"{self.base_url}{endpoint}")
        response.raise_for_status()
        return response.json()


# Global API client instance
_client = None


def get_client() -> APIClient:
    """Get or create API client"""
    global _client
    if _client is None:
        _client = APIClient()
    return _client


# ============================================================================
# RNG ATTUNEMENT TOOLS
# ============================================================================

def create_rng_session(
    baseline_tone_arm: float = 5.0,
    sensitivity: float = 1.0
) -> Dict[str, Any]:
    """
    Create a new RNG attunement session for monitoring psychoenergetic activity.

    Use this when:
    - User wants to monitor RNG during practice
    - Starting manual radionics session
    - Need floating needle detection

    Args:
        baseline_tone_arm: Baseline setting (0-10), default 5.0
        sensitivity: Sensitivity multiplier (0.1-5.0), default 1.0

    Returns:
        {"session_id": "rng_1234567890_abcdef12"}
    """
    client = get_client()
    return client._post("/api/v1/rng/session/create", {
        "baseline_tone_arm": baseline_tone_arm,
        "sensitivity": sensitivity
    })


def get_rng_reading(session_id: str) -> Dict[str, Any]:
    """
    Get current RNG reading including needle state and floating needle score.

    Use this for:
    - Monitoring psychoenergetic activity
    - Checking for floating needle (score > 0.6)
    - Real-time feedback during practice

    Args:
        session_id: RNG session ID from create_rng_session

    Returns:
        {
            "tone_arm": 5.2,
            "needle_position": 15.3,
            "needle_state": "rising",
            "floating_needle_score": 0.73,
            "coherence_index": 0.65,
            "entropy": 0.82
        }
    """
    client = get_client()
    return client._get(f"/api/v1/rng/session/{session_id}/reading")


def stop_rng_session(session_id: str) -> Dict[str, Any]:
    """
    Stop RNG session and get final summary.

    Args:
        session_id: RNG session ID

    Returns:
        Complete session statistics including floating needle count
    """
    client = get_client()
    return client._post(f"/api/v1/rng/session/{session_id}/stop")


# ============================================================================
# BLESSING SLIDESHOW TOOLS
# ============================================================================

def create_blessing_slideshow(
    directory_path: str,
    mantra: str = "chenrezig",
    intentions: List[str] = None,
    repetitions_per_photo: int = 108,
    display_duration_ms: int = 2000,
    loop_mode: bool = True,
    rng_session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a blessing slideshow session for a directory of photos.

    Use this when:
    - User wants to bless photos
    - Manual compassion practice
    - Need visual witness for radionics

    Args:
        directory_path: Absolute path to directory with photos
        mantra: Mantra to use (chenrezig, tara, medicine_buddha, etc.)
        intentions: List of intentions (love, healing, peace, etc.)
        repetitions_per_photo: Number of mantra repetitions per photo
        display_duration_ms: How long to display each photo (ms)
        loop_mode: Whether to loop back to start
        rng_session_id: Optional RNG session to link

    Returns:
        {"session_id": "blessing_slideshow_...", "total_photos": 50}
    """
    if intentions is None:
        intentions = ["love", "healing", "peace"]

    client = get_client()
    return client._post("/api/v1/slideshow/session/create", {
        "directory_path": directory_path,
        "intention_set": {
            "primary_mantra": mantra,
            "intentions": intentions,
            "repetitions_per_photo": repetitions_per_photo,
            "dedication": "May all beings benefit"
        },
        "loop_mode": loop_mode,
        "display_duration_ms": display_duration_ms,
        "rng_session_id": rng_session_id
    })


def get_current_slide(session_id: str) -> Dict[str, Any]:
    """
    Get current slide information including photo details and progress.

    Args:
        session_id: Slideshow session ID

    Returns:
        Complete current slide info including photo, session, overlay, progress
    """
    client = get_client()
    return client._get(f"/api/v1/slideshow/session/{session_id}/current")


def stop_slideshow(session_id: str) -> Dict[str, Any]:
    """
    Stop slideshow and get final statistics.

    Args:
        session_id: Slideshow session ID

    Returns:
        Final statistics including photos blessed, mantras repeated
    """
    client = get_client()
    return client._post(f"/api/v1/slideshow/session/{session_id}/stop")


# ============================================================================
# POPULATION MANAGEMENT TOOLS
# ============================================================================

def create_population(
    name: str,
    category: str,
    source_type: str,
    description: str = "",
    directory_path: Optional[str] = None,
    mantra_preference: str = "chenrezig",
    intentions: List[str] = None,
    priority: int = 5,
    is_urgent: bool = False
) -> Dict[str, Any]:
    """
    Create a new target population for automated blessings.

    Use this when:
    - User wants to add a new population
    - Setting up automated rotation
    - Organizing blessing targets

    Args:
        name: Clear, descriptive name
        category: missing_persons, refugees, disaster_victims, etc.
        source_type: local_directory, manual, etc.
        description: Optional description
        directory_path: Required for local_directory source
        mantra_preference: Preferred mantra
        intentions: List of intentions
        priority: Priority 1-10 (higher = more important)
        is_urgent: Whether urgent

    Returns:
        Complete population object with ID
    """
    if intentions is None:
        intentions = ["love", "healing", "peace"]

    client = get_client()
    return client._post("/api/v1/populations/create", {
        "name": name,
        "description": description,
        "category": category,
        "source_type": source_type,
        "directory_path": directory_path,
        "mantra_preference": mantra_preference,
        "intentions": intentions,
        "repetitions_per_photo": 108,
        "display_duration_ms": 2000,
        "priority": priority,
        "is_urgent": is_urgent,
        "tags": [],
        "notes": ""
    })


def list_populations(
    active_only: bool = False,
    category: Optional[str] = None,
    urgent_only: bool = False
) -> List[Dict[str, Any]]:
    """
    Get list of all populations with optional filtering.

    Args:
        active_only: Only return active populations
        category: Filter by specific category
        urgent_only: Only return urgent populations

    Returns:
        List of population objects
    """
    client = get_client()
    params = []
    if active_only:
        params.append("active_only=true")
    if category:
        params.append(f"category={category}")
    if urgent_only:
        params.append("urgent_only=true")

    query = "?" + "&".join(params) if params else ""
    return client._get(f"/api/v1/populations/{query}")


def get_population_statistics() -> Dict[str, Any]:
    """
    Get overall statistics across all populations.

    Returns:
        Statistics including totals, categories, blessings sent
    """
    client = get_client()
    return client._get("/api/v1/populations/statistics/overall")


def update_population(
    population_id: str,
    **updates
) -> Dict[str, Any]:
    """
    Update a population's settings.

    Args:
        population_id: Population ID
        **updates: Fields to update (priority, is_urgent, etc.)

    Returns:
        Updated population object
    """
    client = get_client()
    return client._put(f"/api/v1/populations/{population_id}", updates)


# ============================================================================
# AUTOMATION/SCHEDULER TOOLS
# ============================================================================

def start_automation(
    duration_per_population: int = 1800,
    transition_pause: int = 30,
    link_rng: bool = True,
    continuous_mode: bool = True,
    only_active: bool = True,
    min_priority: int = 1
) -> Dict[str, Any]:
    """
    Start automated 24/7 rotation through populations.

    Use this when:
    - User wants hands-off automatic operation
    - Setting up continuous compassion practice
    - Need fair distribution of blessing time

    Args:
        duration_per_population: Seconds to spend on each population
        transition_pause: Seconds between populations
        link_rng: Whether to create RNG session per population
        continuous_mode: Loop indefinitely if True
        only_active: Only include active populations
        min_priority: Minimum priority to include (1-10)

    Returns:
        {"session_id": "scheduler_...", "populations_in_queue": 15}
    """
    client = get_client()
    return client._post("/api/v1/automation/start", {
        "mode": "round_robin",
        "duration_per_population": duration_per_population,
        "transition_pause": transition_pause,
        "link_rng": link_rng,
        "auto_dedicate": True,
        "continuous_mode": continuous_mode,
        "only_active": only_active,
        "min_priority": min_priority
    })


def get_automation_status(session_id: str) -> Dict[str, Any]:
    """
    Get current automation status (lightweight, for frequent polling).

    Use this for:
    - Real-time monitoring
    - UI updates every 5-10 seconds
    - Progress tracking

    Args:
        session_id: Automation session ID

    Returns:
        Current status including population, progress, elapsed time
    """
    client = get_client()
    return client._get(f"/api/v1/automation/{session_id}/status")


def get_automation_stats(session_id: str) -> Dict[str, Any]:
    """
    Get complete automation statistics.

    Args:
        session_id: Automation session ID

    Returns:
        Complete statistics including history, totals, sessions completed
    """
    client = get_client()
    return client._get(f"/api/v1/automation/{session_id}/stats")


def stop_automation(session_id: str) -> Dict[str, Any]:
    """
    Stop automated rotation and get final statistics.

    Args:
        session_id: Automation session ID

    Returns:
        Final statistics for entire automation session
    """
    client = get_client()
    return client._post(f"/api/v1/automation/{session_id}/stop")


def pause_automation(session_id: str) -> Dict[str, Any]:
    """
    Pause automated rotation (can be resumed later).

    Args:
        session_id: Automation session ID

    Returns:
        Confirmation message
    """
    client = get_client()
    return client._post(f"/api/v1/automation/{session_id}/pause")


def resume_automation(session_id: str) -> Dict[str, Any]:
    """
    Resume paused automation.

    Args:
        session_id: Automation session ID

    Returns:
        Confirmation message
    """
    client = get_client()
    return client._post(f"/api/v1/automation/{session_id}/resume")


# ============================================================================
# TOOL REGISTRY (for LLM agents)
# ============================================================================

TOOL_REGISTRY = {
    "create_rng_session": create_rng_session,
    "get_rng_reading": get_rng_reading,
    "stop_rng_session": stop_rng_session,
    "create_blessing_slideshow": create_blessing_slideshow,
    "get_current_slide": get_current_slide,
    "stop_slideshow": stop_slideshow,
    "create_population": create_population,
    "list_populations": list_populations,
    "get_population_statistics": get_population_statistics,
    "update_population": update_population,
    "start_automation": start_automation,
    "get_automation_status": get_automation_status,
    "get_automation_stats": get_automation_stats,
    "stop_automation": stop_automation,
    "pause_automation": pause_automation,
    "resume_automation": resume_automation
}


def get_tool_schemas() -> List[Dict[str, Any]]:
    """
    Get JSON schemas for all available tools.

    Returns schemas in OpenAI function calling format.
    Can be used with Claude, GPT-4, or other LLMs that support tool calling.

    Returns:
        List of tool schemas
    """
    return [
        {
            "name": "create_rng_session",
            "description": "Create a new RNG attunement session for monitoring psychoenergetic activity during radionics practice",
            "parameters": {
                "type": "object",
                "properties": {
                    "baseline_tone_arm": {
                        "type": "number",
                        "description": "Baseline tone arm setting (0-10), default 5.0"
                    },
                    "sensitivity": {
                        "type": "number",
                        "description": "Sensitivity multiplier (0.1-5.0), default 1.0"
                    }
                }
            }
        },
        {
            "name": "get_rng_reading",
            "description": "Get current RNG reading to check for psychoenergetic activity. floating_needle_score > 0.6 indicates release/completion",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RNG session ID from create_rng_session"
                    }
                },
                "required": ["session_id"]
            }
        },
        {
            "name": "create_blessing_slideshow",
            "description": "Create a blessing slideshow for a directory of photos with mantras and intentions",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Absolute path to directory containing photos"
                    },
                    "mantra": {
                        "type": "string",
                        "enum": ["chenrezig", "tara", "medicine_buddha", "vajrasattva", "manjushri", "amitabha", "universal"],
                        "description": "Mantra to use (default: chenrezig)"
                    },
                    "intentions": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["love", "healing", "peace", "protection", "prosperity", "wisdom", "reunion", "safety", "liberation", "compassion", "clarity", "strength"]
                        },
                        "description": "List of intentions to transmit"
                    },
                    "rng_session_id": {
                        "type": "string",
                        "description": "Optional RNG session ID to link for monitoring"
                    }
                },
                "required": ["directory_path"]
            }
        },
        {
            "name": "create_population",
            "description": "Create a new target population for automated blessings",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Clear, descriptive name for the population"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["missing_persons", "refugees", "disaster_victims", "conflict_zones", "hospital_patients", "humanitarian_crisis", "memorial", "custom"],
                        "description": "Category of population"
                    },
                    "source_type": {
                        "type": "string",
                        "enum": ["local_directory", "manual"],
                        "description": "Where photos come from"
                    },
                    "directory_path": {
                        "type": "string",
                        "description": "Path to photos (required for local_directory)"
                    },
                    "priority": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Priority level (1-10, higher = more important)"
                    }
                },
                "required": ["name", "category", "source_type"]
            }
        },
        {
            "name": "start_automation",
            "description": "Start automated 24/7 rotation through all populations with fair time distribution",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_per_population": {
                        "type": "integer",
                        "description": "Seconds to spend on each population (default 1800 = 30 min)"
                    },
                    "continuous_mode": {
                        "type": "boolean",
                        "description": "Loop indefinitely if true (default true)"
                    },
                    "link_rng": {
                        "type": "boolean",
                        "description": "Monitor RNG for each population (default true)"
                    }
                }
            }
        },
        {
            "name": "get_automation_status",
            "description": "Get current automation status for monitoring. Call every 5-10 seconds for UI updates",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Automation session ID"
                    }
                },
                "required": ["session_id"]
            }
        },
        {
            "name": "list_populations",
            "description": "Get list of all populations with optional filtering",
            "parameters": {
                "type": "object",
                "properties": {
                    "active_only": {
                        "type": "boolean",
                        "description": "Only return active populations"
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by specific category"
                    }
                }
            }
        },
        {
            "name": "get_population_statistics",
            "description": "Get overall statistics across all populations including totals and categories",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    ]


# Example usage for LLM agents
if __name__ == "__main__":
    # Example: Complete automated workflow
    print("Creating population...")
    pop = create_population(
        name="Test Population",
        category="custom",
        source_type="manual",
        description="Test population for demonstration"
    )
    print(f"Created: {pop['id']}")

    print("\nListing all populations...")
    pops = list_populations()
    print(f"Total populations: {len(pops)}")

    print("\nGetting statistics...")
    stats = get_population_statistics()
    print(f"Total blessings sent: {stats['total_blessings_sent']}")

    # More examples would follow...
