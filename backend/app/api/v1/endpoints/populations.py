"""
Target Populations API Endpoints

CRUD operations for managing populations that receive automated blessings.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from backend.core.services.population_manager import (
    get_population_manager,
    PopulationCategory,
    SourceType
)

router = APIRouter(tags=["populations"])


# Request/Response Models
class CreatePopulationRequest(BaseModel):
    """Request to create new population"""
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=1000)
    category: PopulationCategory
    source_type: SourceType
    directory_path: Optional[str] = None
    source_url: Optional[str] = None
    mantra_preference: str = "chenrezig"
    intentions: List[str] = Field(default_factory=lambda: ["love", "healing", "peace"])
    repetitions_per_photo: int = Field(108, ge=1, le=10000)
    display_duration_ms: int = Field(2000, ge=100, le=60000)
    priority: int = Field(5, ge=1, le=10)
    is_urgent: bool = False
    tags: List[str] = Field(default_factory=list)
    notes: str = ""

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Missing Persons - California 2024",
                "description": "Database of missing persons from California",
                "category": "missing_persons",
                "source_type": "local_directory",
                "directory_path": "/path/to/photos",
                "mantra_preference": "chenrezig",
                "intentions": ["reunion", "safety", "love"],
                "priority": 7
            }
        }


class UpdatePopulationRequest(BaseModel):
    """Request to update population"""
    name: Optional[str] = None
    description: Optional[str] = None
    directory_path: Optional[str] = None
    source_url: Optional[str] = None
    mantra_preference: Optional[str] = None
    intentions: Optional[List[str]] = None
    repetitions_per_photo: Optional[int] = None
    display_duration_ms: Optional[int] = None
    priority: Optional[int] = None
    is_urgent: Optional[bool] = None
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class PopulationResponse(BaseModel):
    """Population data"""
    id: str
    name: str
    description: str
    category: str
    source_type: str
    source_url: Optional[str]
    directory_path: Optional[str]
    mantra_preference: str
    intentions: List[str]
    repetitions_per_photo: int
    display_duration_ms: int
    priority: int
    is_urgent: bool
    is_active: bool
    added_time: float
    last_blessed_time: Optional[float]
    total_blessings_sent: int
    total_mantras_repeated: int
    total_session_duration: float
    photo_count: int
    tags: List[str]
    notes: str
    offline_available: bool
    last_sync_time: Optional[float]


class StatisticsResponse(BaseModel):
    """Overall statistics"""
    total_populations: int
    active_populations: int
    urgent_populations: int
    total_blessings_sent: int
    total_mantras_repeated: int
    total_session_duration: float
    categories: Dict[str, int]
    never_blessed: int
    offline_available: int


# Endpoints

@router.post("/create", response_model=PopulationResponse)
async def create_population(request: CreatePopulationRequest):
    """
    Create a new target population

    Creates a population that can be included in automated blessing rotations.

    **Required**:
    - name: Clear, descriptive name
    - category: Type of population
    - source_type: Where data comes from

    **Source Types**:
    - local_directory: Photos in a local folder (offline-capable)
    - manual: Manually added (no photos)
    - rss_feed, news_api, gdacs, relief_web: Online sources (Phase 3)

    **For local_directory**: Must provide directory_path
    **For online sources**: Must provide source_url
    """
    manager = get_population_manager()

    try:
        population = manager.create_population(
            name=request.name,
            description=request.description,
            category=request.category,
            source_type=request.source_type,
            directory_path=request.directory_path,
            source_url=request.source_url,
            mantra_preference=request.mantra_preference,
            intentions=request.intentions,
            repetitions_per_photo=request.repetitions_per_photo,
            display_duration_ms=request.display_duration_ms,
            priority=request.priority,
            is_urgent=request.is_urgent,
            tags=request.tags,
            notes=request.notes
        )

        return PopulationResponse(**population.to_dict())

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{population_id}", response_model=PopulationResponse)
async def get_population(population_id: str):
    """Get a specific population by ID"""
    manager = get_population_manager()
    population = manager.get_population(population_id)

    if not population:
        raise HTTPException(status_code=404, detail="Population not found")

    return PopulationResponse(**population.to_dict())


@router.get("/", response_model=List[PopulationResponse])
async def get_all_populations(
    active_only: bool = Query(False, description="Only return active populations"),
    category: Optional[str] = Query(None, description="Filter by category"),
    urgent_only: bool = Query(False, description="Only return urgent populations")
):
    """
    Get all populations

    **Filters**:
    - active_only: Only include is_active=True
    - category: Only include specific category
    - urgent_only: Only include is_urgent=True
    """
    manager = get_population_manager()

    populations = manager.get_all_populations()

    # Apply filters
    if active_only:
        populations = [p for p in populations if p.is_active]

    if category:
        try:
            cat = PopulationCategory(category)
            populations = [p for p in populations if p.category == cat]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    if urgent_only:
        populations = [p for p in populations if p.is_urgent]

    return [PopulationResponse(**p.to_dict()) for p in populations]


@router.put("/{population_id}", response_model=PopulationResponse)
async def update_population(population_id: str, request: UpdatePopulationRequest):
    """
    Update a population

    Only provide fields you want to change.
    Omitted fields remain unchanged.
    """
    manager = get_population_manager()

    # Filter out None values
    updates = {k: v for k, v in request.dict().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    population = manager.update_population(population_id, **updates)

    if not population:
        raise HTTPException(status_code=404, detail="Population not found")

    return PopulationResponse(**population.to_dict())


@router.delete("/{population_id}")
async def delete_population(population_id: str):
    """
    Delete a population

    **Warning**: This permanently deletes the population and all its history.
    Consider deactivating (is_active=False) instead.
    """
    manager = get_population_manager()

    success = manager.delete_population(population_id)

    if not success:
        raise HTTPException(status_code=404, detail="Population not found")

    return {"message": "Population deleted successfully", "id": population_id}


@router.get("/statistics/overall", response_model=StatisticsResponse)
async def get_statistics():
    """
    Get overall statistics across all populations

    Includes:
    - Total counts
    - Blessing totals
    - Distribution by category
    - Offline availability
    """
    manager = get_population_manager()
    stats = manager.get_statistics()
    return StatisticsResponse(**stats)


@router.post("/export")
async def export_populations():
    """
    Export all populations for backup

    Returns JSON data that can be saved and later imported.
    Useful for backup, transfer between devices, or offline storage.
    """
    manager = get_population_manager()
    data = manager.export_data()
    return data


@router.post("/import")
async def import_populations(
    data: Dict[str, Any],
    merge: bool = Query(False, description="Merge with existing vs. replace all")
):
    """
    Import populations from backup

    **merge=False** (default): Replaces all existing populations
    **merge=True**: Merges with existing, updates if ID conflicts

    Use for:
    - Restoring from backup
    - Importing pre-configured populations
    - Syncing between devices
    """
    manager = get_population_manager()

    try:
        count = manager.import_data(data, merge=merge)
        return {
            "message": f"Successfully imported {count} populations",
            "count": count,
            "merge": merge
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")


@router.get("/categories/list")
async def list_categories():
    """
    Get list of all available categories

    Returns category values and descriptions.
    """
    return [
        {
            "value": cat.value,
            "name": cat.value.replace("_", " ").title(),
            "description": _get_category_description(cat)
        }
        for cat in PopulationCategory
    ]


@router.get("/source-types/list")
async def list_source_types():
    """Get list of all available source types"""
    return [
        {
            "value": src.value,
            "name": src.value.replace("_", " ").title(),
            "description": _get_source_description(src),
            "requires_path": src == SourceType.LOCAL_DIRECTORY,
            "requires_url": src in [SourceType.RSS_FEED, SourceType.NEWS_API, SourceType.GDACS, SourceType.RELIEF_WEB, SourceType.CUSTOM_API],
            "online_only": src != SourceType.LOCAL_DIRECTORY and src != SourceType.MANUAL
        }
        for src in SourceType
    ]


def _get_category_description(cat: PopulationCategory) -> str:
    """Get description for category"""
    descriptions = {
        PopulationCategory.MISSING_PERSONS: "Missing persons databases and cases",
        PopulationCategory.UNIDENTIFIED_REMAINS: "Unidentified human remains",
        PopulationCategory.DISASTER_VICTIMS: "Victims of natural disasters",
        PopulationCategory.CONFLICT_ZONES: "Populations in conflict zones",
        PopulationCategory.REFUGEES: "Refugee and displaced populations",
        PopulationCategory.HOSPITAL_PATIENTS: "Hospital patients (with permission)",
        PopulationCategory.NATURAL_DISASTER: "Natural disaster affected areas",
        PopulationCategory.HUMANITARIAN_CRISIS: "Humanitarian crisis situations",
        PopulationCategory.MEMORIAL: "Memorial and remembrance",
        PopulationCategory.ENDANGERED_SPECIES: "Endangered species",
        PopulationCategory.CUSTOM: "Custom category"
    }
    return descriptions.get(cat, "")


def _get_source_description(src: SourceType) -> str:
    """Get description for source type"""
    descriptions = {
        SourceType.MANUAL: "Manually added by user",
        SourceType.LOCAL_DIRECTORY: "Photos in local directory (offline-capable)",
        SourceType.RSS_FEED: "RSS/Atom feed (online)",
        SourceType.NEWS_API: "News API service (online)",
        SourceType.GDACS: "Global Disaster Alert System (online)",
        SourceType.RELIEF_WEB: "UN ReliefWeb API (online)",
        SourceType.CUSTOM_API: "Custom API endpoint (online)"
    }
    return descriptions.get(src, "")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    manager = get_population_manager()
    stats = manager.get_statistics()

    return {
        "status": "healthy",
        "service": "populations",
        "total_populations": stats['total_populations'],
        "active_populations": stats['active_populations']
    }
