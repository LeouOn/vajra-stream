"""
Radionics Narratives API - LLM-powered healing narratives for radionics work
Enhanced with radionics data integration (frequencies, planets, locations)
"""

import logging
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234")
DEFAULT_MODEL = "gemma-4-e4b-it-uncensored-max-opus-4.7"


class RadionicsContext(BaseModel):
    frequency_hz: float | None = None
    frequency_name: str | None = None
    planet: str | None = None
    planet_frequency: float | None = None
    location: str | None = None
    chakra: str | None = None
    intention_type: str | None = None
    scalar_mops: float | None = None


class NarrativeRequest(BaseModel):
    intention: str
    difficulty: str | None = None
    theme: str | None = None
    length: str = "medium"
    include_affirmation: bool = True
    radionics_context: RadionicsContext | None = None


class AffirmationRequest(BaseModel):
    intention: str
    style: str = "empowering"
    radionics_context: RadionicsContext | None = None


class EnhancedNarrativeRequest(BaseModel):
    intention: str
    theme: str = "manifestation"
    radionics_data: dict | None = None


def _generate_with_llm(prompt: str, system_prompt: str, max_tokens: int = 500, temperature: float = 0.8) -> str:
    """Generate text using LM Studio API"""
    import requests

    try:
        response = requests.post(
            f"{LLM_BASE_URL}/v1/chat/completions",
            json={
                "model": DEFAULT_MODEL,
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=60,
        )

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        else:
            logger.error(f"LLM error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=500, detail=f"LLM generation failed: {response.status_code}")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="LLM server not available. Please start LM Studio.")
    except Exception as e:
        logger.error(f"LLM generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


NARRATIVE_SYSTEM = """You are a wise spiritual guide specializing in radionic healing narratives.
You create empowering stories about overcoming difficulties, healing emotional wounds, and transforming challenges into growth.
Your narratives are inspired by Buddhist wisdom, shamanic journeying, and energy healing traditions.
You incorporate sacred frequencies, planetary energies, and sacred locations when relevant.
Format output with clear sections. Keep narratives grounded yet uplifting.
IMPORTANT: When radionics context is provided, weave the frequency, planet, and location energies into the narrative naturally."""

NARRATIVE_TEMPLATES = {
    "overcoming": {
        "system": NARRATIVE_SYSTEM,
        "prompt_template": """Create a healing narrative about overcoming {intention}.

{frequency_context}
{location_context}

Include:
1. A brief opening acknowledging the difficulty
2. A central story/metaphor showing transformation
3. A closing affirmation of healing and strength

Keep it 3-4 paragraphs. Make it personally resonant, not generic.

If planet frequency is provided, mention how the planetary energy supports the transformation.""",
    },
    "transformation": {
        "system": NARRATIVE_SYSTEM,
        "prompt_template": """Create a transformation narrative for {intention}.

{frequency_context}
{planet_context}
{location_context}

Structure:
- Opening: Acknowledge the current struggle
- Middle: Show the path of transformation (use a nature metaphor or journey)
- End: Integration and new wholeness

Length: 3 paragraphs. Vivid imagery, actionable insight.

Weave in the {frequency_hz}Hz frequency energy if provided, describing how it catalyzes the change.""",
    },
    "healing": {
        "system": NARRATIVE_SYSTEM,
        "prompt_template": """Write a healing narrative for {intention}.

{frequency_context}
{chakra_context}
{location_context}

Include:
- Recognition of what needs healing
- Gentle visualization of healing energy flowing at {frequency_hz}Hz
- Integration statement

Length: 2-3 paragraphs. Compassionate and grounding.

The {chakra} chakra energy should be incorporated if provided.""",
    },
    "liberation": {
        "system": NARRATIVE_SYSTEM,
        "prompt_template": """Create a liberation narrative about {intention}.

{planet_context}
{frequency_context}
{location_context}

Drawing from Buddhist non-attachment and shamanic journey work:
- Identify what binds or restricts
- Visualize releasing/transforming with the {frequency_hz}Hz liberation frequency
- Affirm freedom and new possibility

Length: 3 paragraphs. Liberation language.

If planetary energy is provided, describe how {planet} energy supports letting go.""",
    },
    "manifestation": {
        "system": NARRATIVE_SYSTEM,
        "prompt_template": """Write a manifestation narrative for {intention}.

{frequency_context}
{planet_context}
{location_context}
{scalar_context}

Include:
- Clarity of intention and what wishes to manifest
- Aligned action/growth supported by {frequency_hz}Hz frequency
- Trust in the process

Length: 2-3 paragraphs. Forward-looking and empowering.

The scalar wave intensity of {scalar_mops} MOPS amplifies the manifestation if provided.""",
    },
}

AFFIRMATION_SYSTEM = """You are a spiritual coach creating powerful affirmations for energy healing work.
Create clear, positive, present-tense statements that empower transformation.
Keep affirmations concise (1-2 sentences) and impactful.
When radionics context is provided (frequency, planet, chakra), weave it into the affirmation."""


def _build_radionics_context(ctx: RadionicsContext | None) -> dict:
    """Build context strings from radionics data"""
    context = {
        "frequency_hz": ctx.frequency_hz if ctx else 528,
        "frequency_name": ctx.frequency_name if ctx else "528 Hz - Love Frequency",
        "planet": ctx.planet if ctx else None,
        "planet_frequency": ctx.planet_frequency if ctx else None,
        "location": ctx.location if ctx else None,
        "chakra": ctx.chakra if ctx else None,
        "intention_type": ctx.intention_type if ctx else None,
        "scalar_mops": ctx.scalar_mops if ctx else 17.73,
    }

    # Build context strings for prompts
    freq_ctx = (
        f"You are channeling the {context['frequency_hz']}Hz {context['frequency_name']} frequency."
        if context["frequency_hz"]
        else ""
    )
    planet_ctx = (
        f"The {context['planet']} planetary energy at {context['planet_frequency']}Hz is flowing through this work."
        if context["planet"]
        else ""
    )
    location_ctx = (
        f"Sacred energy from {context['location']} is amplifying this intention." if context["location"] else ""
    )
    chakra_ctx = f"The {context['chakra']} chakra is being activated and balanced." if context["chakra"] else ""
    scalar_ctx = (
        f"Scalar waves at {context['scalar_mops']} MOPS are creating a healing field." if context["scalar_mops"] else ""
    )

    return {
        "frequency_context": freq_ctx,
        "planet_context": planet_ctx,
        "location_context": location_ctx,
        "chakra_context": chakra_ctx,
        "scalar_context": scalar_ctx,
        **context,
    }


@router.post("/narrative/generate")
async def generate_narrative(request: NarrativeRequest):
    """Generate a healing narrative based on intention with optional radionics context"""
    try:
        logger.info(f"Generating narrative: intention={request.intention}, difficulty={request.difficulty}")

        theme = request.theme or "overcoming"
        if theme not in NARRATIVE_TEMPLATES:
            theme = "overcoming"

        template = NARRATIVE_TEMPLATES[theme]

        # Build radionics context
        ctx_dict = _build_radionics_context(request.radionics_context)

        # Format prompt with radionics context
        prompt = template["prompt_template"].format(
            intention=request.intention,
            difficulty=request.difficulty or "challenges",
            frequency_context=ctx_dict.get("frequency_context", ""),
            planet_context=ctx_dict.get("planet_context", ""),
            location_context=ctx_dict.get("location_context", ""),
            chakra_context=ctx_dict.get("chakra_context", ""),
            scalar_context=ctx_dict.get("scalar_context", ""),
            frequency_hz=ctx_dict.get("frequency_hz", 528),
            planet=ctx_dict.get("planet", ""),
            chakra=ctx_dict.get("chakra", ""),
            scalar_mops=ctx_dict.get("scalar_mops", 17.73),
        )

        narrative = _generate_with_llm(prompt=prompt, system_prompt=template["system"], max_tokens=600, temperature=0.8)

        return {
            "status": "success",
            "narrative": narrative,
            "intention": request.intention,
            "theme": theme,
            "length": request.length,
            "radionics": {
                "frequency_hz": ctx_dict.get("frequency_hz"),
                "frequency_name": ctx_dict.get("frequency_name"),
                "planet": ctx_dict.get("planet"),
                "planet_frequency": ctx_dict.get("planet_frequency"),
                "location": ctx_dict.get("location"),
                "chakra": ctx_dict.get("chakra"),
                "scalar_mops": ctx_dict.get("scalar_mops"),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating narrative: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/affirmation/generate")
async def generate_affirmation(request: AffirmationRequest):
    """Generate an affirmation based on intention with optional radionics context"""
    try:
        ctx_dict = _build_radionics_context(request.radionics_context)

        prompt = f"""Create a powerful affirmation for: {request.intention}

Style: {request.style}
{frequency_context}
{planet_context}

Format: 1-2 clear sentences in present tense, starting with "I" or "I am"

Example: "I release what no longer serves me and embrace my inner strength."

Generate only the affirmation:"""

        prompt = prompt.replace("{frequency_context}", ctx_dict.get("frequency_context", ""))
        prompt = prompt.replace("{planet_context}", ctx_dict.get("planet_context", ""))

        affirmation = _generate_with_llm(
            prompt=prompt, system_prompt=AFFIRMATION_SYSTEM, max_tokens=100, temperature=0.9
        )

        return {
            "status": "success",
            "affirmation": affirmation,
            "intention": request.intention,
            "style": request.style,
            "radionics": {"frequency_hz": ctx_dict.get("frequency_hz"), "planet": ctx_dict.get("planet")},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating affirmation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/narrative/themes")
async def list_narrative_themes():
    """List available narrative themes"""
    return {"status": "success", "themes": list(NARRATIVE_TEMPLATES.keys())}


@router.post("/narrative/session")
async def create_narrative_session(intention: str, theme: str = "overcoming", include_affirmation: bool = True):
    """Create a full narrative session with narrative and optional affirmation"""
    try:
        narrative_req = NarrativeRequest(
            intention=intention, theme=theme, length="medium", include_affirmation=include_affirmation
        )
        result = await generate_narrative(narrative_req)

        response = {"status": "success", "narrative": result["narrative"], "intention": intention, "theme": theme}

        if include_affirmation:
            aff_req = AffirmationRequest(intention=intention, style="empowering")
            aff_result = await generate_affirmation(aff_req)
            response["affirmation"] = aff_result["affirmation"]

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating narrative session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Radionics data for global intentions
PLANETARY_FREQUENCIES = {
    "world peace": {"planet": "Jupiter", "frequency": 183.58, "chakra": "throat", "intention": "peace"},
    "world prosperity": {"planet": "Venus", "frequency": 221.23, "chakra": "heart", "intention": "empowerment"},
    "end to disease and cancer": {"planet": "Sun", "frequency": 126.22, "chakra": "heart", "intention": "healing"},
    "happiness": {"planet": "Jupiter", "frequency": 183.58, "chakra": "sacral", "intention": "love"},
    "reforestation the world": {"planet": "Earth", "frequency": 136.10, "chakra": "heart", "intention": "healing"},
    "cleaning up pollution": {"planet": "Saturn", "frequency": 147.85, "chakra": "root", "intention": "liberation"},
}

LOCATION_ENERGY = {
    "world peace": "Mount Kailash, Tibet",
    "world prosperity": "Stonehenge, England",
    "end to disease and cancer": "Lourdes, France",
    "happiness": "Hawaii",
    "reforestation the world": "Amazon Rainforest",
    "cleaning up pollution": "Ganges River Delta",
}


@router.post("/narrative/global-intention")
async def generate_global_intention_narrative(request: EnhancedNarrativeRequest):
    """Generate narrative for global intentions with full radionics context.

    This endpoint automatically matches intentions like 'world peace', 'end to disease and cancer',
    etc. with appropriate planetary frequencies, locations, and chakra alignments.
    """
    try:
        intention_lower = request.intention.lower()
        logger.info(f"Generating global intention narrative: {request.intention}")

        # Match intention to radionics data
        matched_data = None
        for key, data in PLANETARY_FREQUENCIES.items():
            if key in intention_lower:
                matched_data = data
                matched_data["location"] = LOCATION_ENERGY.get(key, "Earth")
                matched_data["matched_key"] = key
                break

        if not matched_data:
            # Default matching for any intention
            matched_data = {
                "planet": "Jupiter",
                "frequency": 183.58,
                "chakra": "heart",
                "intention": "peace",
                "location": "Earth",
            }

        # Map intention type to frequency
        frequency_map = {
            "peace": 852,
            "empowerment": 528,
            "healing": 528,
            "love": 528,
            "liberation": 396,
            "protection": 741,
            "wisdom": 963,
            "reconciliation": 639,
        }

        solfeggio_freq = frequency_map.get(matched_data.get("intention", "peace"), 528)

        # Build radionics context
        ctx = RadionicsContext(
            frequency_hz=solfeggio_freq,
            frequency_name=f"{solfeggio_freq} Hz - {'Peace' if matched_data.get('intention') == 'peace' else 'Healing'} Frequency",
            planet=matched_data["planet"],
            planet_frequency=matched_data["frequency"],
            location=matched_data["location"],
            chakra=matched_data["chakra"],
            intention_type=matched_data.get("intention", "peace"),
            scalar_mops=17.73,
        )

        # Create narrative request with radionics context
        narrative_req = NarrativeRequest(
            intention=request.intention, theme=request.theme, length="medium", radionics_context=ctx
        )

        result = await generate_narrative(narrative_req)

        return {
            "status": "success",
            "narrative": result["narrative"],
            "affirmation": result.get("affirmation"),
            "intention": request.intention,
            "theme": request.theme,
            "radionics_data": {
                "solfeggio_frequency": solfeggio_freq,
                "solfeggio_name": f"{solfeggio_freq} Hz - {'DNA Repair' if solfeggio_freq == 528 else 'Peace'}",
                "planetary_planets": matched_data["planet"],
                "planetary_frequency": matched_data["frequency"],
                "location": matched_data["location"],
                "chakra": matched_data["chakra"],
                "intention_type": matched_data.get("intention", "peace"),
                "scalar_mops": 17.73,
                "broadcast_recommendation": f"Broadcast at {solfeggio_freq}Hz combined with {matched_data['planet']} planetary frequency ({matched_data['frequency']}Hz)",
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating global intention narrative: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/radionics/global-intentions")
async def list_global_intentions():
    """List all available global intentions with their radionics data"""
    freq_map = {
        "peace": 852,
        "empowerment": 528,
        "healing": 528,
        "love": 528,
        "liberation": 396,
        "protection": 741,
        "wisdom": 963,
        "reconciliation": 639,
    }
    return {
        "status": "success",
        "intentions": [
            {
                "intention": key,
                "planet": data["planet"],
                "frequency_hz": data["frequency"],
                "chakra": data["chakra"],
                "location": LOCATION_ENERGY.get(key, "Earth"),
                "solfeggio_recommendation": freq_map.get(data["intention"], 528),
            }
            for key, data in PLANETARY_FREQUENCIES.items()
        ],
    }
