from fastapi import APIRouter

from backend.app.api.v1.endpoints import anatomy as anatomy_endpoint
from backend.app.api.v1.endpoints import astrology as astrology_endpoint
from backend.app.api.v1.endpoints import audio as audio_endpoint
from backend.app.api.v1.endpoints import automation as automation_endpoint
from backend.app.api.v1.endpoints import blessing_slideshow as slideshow_endpoint
from backend.app.api.v1.endpoints import blessings as blessings_endpoint
from backend.app.api.v1.endpoints import dharma_tales as dharma_tales_endpoint
from backend.app.api.v1.endpoints import divination as divination_endpoint
from backend.app.api.v1.endpoints import llm as llm_endpoint
from backend.app.api.v1.endpoints import mops as mops_endpoint
from backend.app.api.v1.endpoints import operator as operator_endpoint
from backend.app.api.v1.endpoints import outlook as outlook_endpoint
from backend.app.api.v1.endpoints import personal_healing as personal_healing_endpoint
from backend.app.api.v1.endpoints import populations as populations_endpoint
from backend.app.api.v1.endpoints import prayer_wheel as prayer_wheel_endpoint
from backend.app.api.v1.endpoints import radionics as radionics_endpoint
from backend.app.api.v1.endpoints import radionics_narratives as radionics_narratives_endpoint
from backend.app.api.v1.endpoints import rng_attunement as rng_endpoint
from backend.app.api.v1.endpoints import scalar_waves as scalar_endpoint
from backend.app.api.v1.endpoints import sessions as sessions_endpoint
from backend.app.api.v1.endpoints import sigils as sigils_endpoint
from backend.app.api.v1.endpoints import time_cycles as time_cycles_endpoint
from backend.app.api.v1.endpoints import visualization as visualization_endpoint
from backend.app.api.v1.endpoints import agent_suggestions as agent_suggestions_endpoint
from backend.app.api.v1.endpoints import tts as tts_endpoint
from backend.app.api.v1.endpoints import ritual_engine as ritual_engine_endpoint

api_router = APIRouter()

api_router.include_router(audio_endpoint.router, prefix="/audio", tags=["audio"])
api_router.include_router(sessions_endpoint.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(astrology_endpoint.router, prefix="/astrology", tags=["astrology"])

# Terra MOPS and Healing System routers
api_router.include_router(scalar_endpoint.router, prefix="/scalar", tags=["scalar-waves"])
api_router.include_router(radionics_endpoint.router, prefix="/radionics", tags=["radionics"])
api_router.include_router(radionics_narratives_endpoint.router, prefix="/radionics", tags=["radionics-narratives"])
api_router.include_router(anatomy_endpoint.router, prefix="/anatomy", tags=["anatomy"])
api_router.include_router(blessings_endpoint.router, prefix="/blessings", tags=["blessings"])
api_router.include_router(visualization_endpoint.router, prefix="/visualization", tags=["visualization"])
api_router.include_router(rng_endpoint.router, tags=["rng-attunement"])
api_router.include_router(slideshow_endpoint.router, tags=["blessing-slideshow"])
api_router.include_router(populations_endpoint.router, prefix="/populations", tags=["populations"])
api_router.include_router(automation_endpoint.router, tags=["automation"])
api_router.include_router(dharma_tales_endpoint.router, prefix="/dharma", tags=["dharma-tales"])
api_router.include_router(personal_healing_endpoint.router, prefix="/healing", tags=["healing"])
api_router.include_router(llm_endpoint.router, tags=["llm"])
api_router.include_router(mops_endpoint.router, tags=["mops"])
api_router.include_router(sigils_endpoint.router, tags=["sigils"])
api_router.include_router(divination_endpoint.router, tags=["divination"])
api_router.include_router(prayer_wheel_endpoint.router, tags=["prayer-wheel"])
api_router.include_router(time_cycles_endpoint.router, tags=["time-cycles"])
api_router.include_router(operator_endpoint.router, prefix="/operator", tags=["operator"])
api_router.include_router(outlook_endpoint.router, prefix="/outlook", tags=["outlook"])
api_router.include_router(agent_suggestions_endpoint.router, tags=["agent_suggestions"])
api_router.include_router(tts_endpoint.router, prefix="/tts", tags=["tts"])
api_router.include_router(ritual_engine_endpoint.router, prefix="/ritual", tags=["ritual-engine"])
