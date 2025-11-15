#!/usr/bin/env python3
"""
Energetic Anatomy - Multi-Traditional Subtle Body Systems

Integrates three major wisdom traditions:
- Taoist Meridian System (Chinese Medicine)
- Tibetan Buddhist Subtle Body (Channels, Winds, Drops)
- Hindu Yogic System (Chakras, Nadis, Kundalini)

Provides comprehensive data models, cross-system correspondences,
and integration with audio/visual/radionics systems.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict, Union
from datetime import time
import json


# ============================================================================
# ENUMERATIONS
# ============================================================================

class Tradition(Enum):
    """Spiritual/medical tradition"""
    TAOIST = "taoist"
    TIBETAN = "tibetan"
    HINDU = "hindu"


class Element(Enum):
    """Five elements (Chinese) + additional"""
    WOOD = "wood"
    FIRE = "fire"
    EARTH = "earth"
    METAL = "metal"
    WATER = "water"
    SPACE = "space"  # Akasha/ether
    LIGHT = "light"  # Mind element
    CONSCIOUSNESS = "consciousness"


class YinYang(Enum):
    """Yin/Yang polarity"""
    YIN = "yin"
    YANG = "yang"
    BALANCED = "balanced"


class Quality(Enum):
    """Gunas (Hindu) / qualities"""
    SATTVA = "sattva"  # Purity, balance
    RAJAS = "rajas"    # Activity, passion
    TAMAS = "tamas"    # Inertia, darkness


class FlowDirection(Enum):
    """Direction of energy flow"""
    ASCENDING = "ascending"
    DESCENDING = "descending"
    CIRCULAR = "circular"
    BIDIRECTIONAL = "bidirectional"
    SPIRAL = "spiral"


class ChannelType(Enum):
    """Type of energetic channel"""
    CENTRAL = "central"
    LEFT = "left"
    RIGHT = "right"
    MERIDIAN = "meridian"
    SECONDARY = "secondary"


# ============================================================================
# BASE CLASSES
# ============================================================================

@dataclass
class EnergeticPoint:
    """Base class for any energetic point/location"""
    id: str
    name: str
    tradition: Tradition
    location: Tuple[float, float, float]  # 3D coordinates (x, y, z)
    description: str = ""
    element: Optional[Element] = None
    frequency: Optional[float] = None  # Hz
    color: Tuple[int, int, int] = (255, 255, 255)  # RGB
    audio_mantra: str = ""
    associated_practices: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'tradition': self.tradition.value,
            'location': list(self.location),
            'description': self.description,
            'element': self.element.value if self.element else None,
            'frequency': self.frequency,
            'color': list(self.color),
            'audio_mantra': self.audio_mantra,
            'associated_practices': self.associated_practices,
            'metadata': self.metadata
        }


@dataclass
class EnergeticChannel:
    """Base class for energetic channels/pathways"""
    id: str
    name: str
    tradition: Tradition
    pathway: List[Tuple[float, float, float]]  # 3D path coordinates
    color: Tuple[int, int, int] = (255, 255, 255)
    element: Optional[Element] = None
    flow_direction: FlowDirection = FlowDirection.BIDIRECTIONAL
    points_on_channel: List[EnergeticPoint] = field(default_factory=list)
    description: str = ""
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'tradition': self.tradition.value,
            'pathway': [list(p) for p in self.pathway],
            'color': list(self.color),
            'element': self.element.value if self.element else None,
            'flow_direction': self.flow_direction.value,
            'points': [p.to_dict() for p in self.points_on_channel],
            'description': self.description,
            'metadata': self.metadata
        }


@dataclass
class EnergeticCenter:
    """Base class for energetic centers (chakras, dantians, etc.)"""
    id: str
    name: str
    tradition: Tradition
    location: Tuple[float, float, float]
    element: Optional[Element] = None
    color: Tuple[int, int, int] = (255, 255, 255)
    frequency: Optional[float] = None
    bija_mantra: str = ""
    blocked_state: str = ""
    balanced_state: str = ""
    practices: List[str] = field(default_factory=list)
    description: str = ""
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'tradition': self.tradition.value,
            'location': list(self.location),
            'element': self.element.value if self.element else None,
            'color': list(self.color),
            'frequency': self.frequency,
            'bija_mantra': self.bija_mantra,
            'blocked_state': self.blocked_state,
            'balanced_state': self.balanced_state,
            'practices': self.practices,
            'description': self.description,
            'metadata': self.metadata
        }


# ============================================================================
# TAOIST SYSTEM
# ============================================================================

@dataclass
class AcupuncturePoint(EnergeticPoint):
    """Acupuncture point on a meridian"""
    point_code: str = ""  # e.g., "LU-1"
    classical_location: str = ""
    modern_location: str = ""
    needling_depth: str = ""
    functions: List[str] = field(default_factory=list)
    indications: List[str] = field(default_factory=list)
    point_categories: List[str] = field(default_factory=list)  # e.g., "Mu point"

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            'point_code': self.point_code,
            'classical_location': self.classical_location,
            'modern_location': self.modern_location,
            'needling_depth': self.needling_depth,
            'functions': self.functions,
            'indications': self.indications,
            'point_categories': self.point_categories
        })
        return base


@dataclass
class Meridian(EnergeticChannel):
    """Taoist meridian/channel"""
    organ: str = ""
    yin_yang: Optional[YinYang] = None
    emotion_negative: str = ""
    emotion_positive: str = ""
    peak_hours: Tuple[int, int] = (0, 0)  # 24-hour format
    season: str = ""
    direction: str = ""
    healing_sound: str = ""
    sense: str = ""
    tissue: str = ""
    climate: str = ""
    meridian_type: str = "primary"  # primary or extraordinary

    def get_acupoints(self) -> List[AcupuncturePoint]:
        """Get acupuncture points on this meridian"""
        return [p for p in self.points_on_channel if isinstance(p, AcupuncturePoint)]

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            'organ': self.organ,
            'yin_yang': self.yin_yang.value if self.yin_yang else None,
            'emotion_negative': self.emotion_negative,
            'emotion_positive': self.emotion_positive,
            'peak_hours': list(self.peak_hours),
            'season': self.season,
            'direction': self.direction,
            'healing_sound': self.healing_sound,
            'sense': self.sense,
            'tissue': self.tissue,
            'climate': self.climate,
            'meridian_type': self.meridian_type
        })
        return base


@dataclass
class Dantian(EnergeticCenter):
    """Taoist dantian/elixir field"""
    level: str = "lower"  # lower, middle, upper
    cultivation_focus: str = ""  # Jing, Qi, or Shen
    depth: str = ""  # How deep inside the body

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            'level': self.level,
            'cultivation_focus': self.cultivation_focus,
            'depth': self.depth
        })
        return base


# ============================================================================
# TIBETAN BUDDHIST SYSTEM
# ============================================================================

@dataclass
class TibetanChannel(EnergeticChannel):
    """Tibetan subtle body channel"""
    channel_type: ChannelType = ChannelType.SECONDARY
    width_description: str = ""
    top_opening: str = ""
    bottom_opening: str = ""
    nature: str = ""  # wisdom, method, dharmadhatu
    quality: Optional[Quality] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            'channel_type': self.channel_type.value,
            'width_description': self.width_description,
            'top_opening': self.top_opening,
            'bottom_opening': self.bottom_opening,
            'nature': self.nature,
            'quality': self.quality.value if self.quality else None
        })
        return base


@dataclass
class TibetanChakra(EnergeticCenter):
    """Tibetan chakra/wheel"""
    petals: int = 0
    petal_direction: str = "down"  # up, down, horizontal
    buddha: str = ""
    wisdom: str = ""
    syllable: str = ""
    syllable_color: Tuple[int, int, int] = (255, 255, 255)
    purifies: str = ""  # Negative state purified
    pure_form: str = ""  # Result of purification
    mudra: str = ""
    direction: str = ""  # Cardinal direction

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            'petals': self.petals,
            'petal_direction': self.petal_direction,
            'buddha': self.buddha,
            'wisdom': self.wisdom,
            'syllable': self.syllable,
            'syllable_color': list(self.syllable_color),
            'purifies': self.purifies,
            'pure_form': self.pure_form,
            'mudra': self.mudra,
            'direction': self.direction
        })
        return base


@dataclass
class Wind(EnergeticPoint):
    """Tibetan wind/lung"""
    wind_type: str = "root"  # root or branch
    function: str = ""
    disturbed_state: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            'wind_type': self.wind_type,
            'function': self.function,
            'disturbed_state': self.disturbed_state
        })
        return base


@dataclass
class Drop:
    """Tibetan drop/tigle"""
    id: str
    name: str
    drop_type: str  # white, red, indestructible
    location: str
    nature: str
    function: str
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'drop_type': self.drop_type,
            'location': self.location,
            'nature': self.nature,
            'function': self.function,
            'metadata': self.metadata
        }


# ============================================================================
# HINDU YOGIC SYSTEM
# ============================================================================

@dataclass
class Chakra(EnergeticCenter):
    """Hindu/Yogic chakra"""
    sanskrit_name: str = ""
    petals: int = 0
    petal_mantras: List[str] = field(default_factory=list)
    yantra_geometry: str = ""
    deity: str = ""
    goddess: str = ""
    animal: str = ""
    kosha: str = ""  # Bodily sheath
    sense: str = ""
    body_parts: List[str] = field(default_factory=list)
    gland: str = ""
    plexus: str = ""
    blocked_issues: List[str] = field(default_factory=list)
    open_qualities: List[str] = field(default_factory=list)
    developmental_stage: str = ""
    right: str = ""  # Fundamental human right
    spin_direction: str = "clockwise"  # When viewed from front

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            'sanskrit_name': self.sanskrit_name,
            'petals': self.petals,
            'petal_mantras': self.petal_mantras,
            'yantra_geometry': self.yantra_geometry,
            'deity': self.deity,
            'goddess': self.goddess,
            'animal': self.animal,
            'kosha': self.kosha,
            'sense': self.sense,
            'body_parts': self.body_parts,
            'gland': self.gland,
            'plexus': self.plexus,
            'blocked_issues': self.blocked_issues,
            'open_qualities': self.open_qualities,
            'developmental_stage': self.developmental_stage,
            'right': self.right,
            'spin_direction': self.spin_direction
        })
        return base


@dataclass
class Nadi(EnergeticChannel):
    """Hindu/Yogic nadi"""
    nadi_type: str = "secondary"  # sushumna, ida, pingala, or secondary
    quality: Optional[Quality] = None
    temperature: str = "neutral"  # hot, cold, neutral
    gender_association: str = "neutral"  # masculine, feminine, neutral
    nostril: Optional[str] = None  # left, right, both, or None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            'nadi_type': self.nadi_type,
            'quality': self.quality.value if self.quality else None,
            'temperature': self.temperature,
            'gender_association': self.gender_association,
            'nostril': self.nostril
        })
        return base


@dataclass
class Granthi:
    """Energetic knot in Hindu system"""
    id: str
    name: str
    sanskrit_name: str
    location: str  # Which chakra
    blocks: str
    must_pierce: str
    practices_to_pierce: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'sanskrit_name': self.sanskrit_name,
            'location': self.location,
            'blocks': self.blocks,
            'must_pierce': self.must_pierce,
            'practices_to_pierce': self.practices_to_pierce,
            'metadata': self.metadata
        }


@dataclass
class Kundalini:
    """Kundalini shakti"""
    id: str = "kundalini"
    name: str = "Kundalini Shakti"
    current_location: str = "muladhara"  # Which chakra
    state: str = "dormant"  # dormant, stirring, rising, awakened
    coils: float = 3.5
    nature: str = "Divine feminine energy, shakti seeking union with Shiva"
    awakening_signs: List[str] = field(default_factory=list)
    preparation_required: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'current_location': self.current_location,
            'state': self.state,
            'coils': self.coils,
            'nature': self.nature,
            'awakening_signs': self.awakening_signs,
            'preparation_required': self.preparation_required,
            'warnings': self.warnings
        }


# ============================================================================
# CROSS-SYSTEM CORRESPONDENCE
# ============================================================================

@dataclass
class SystemCorrespondence:
    """Mapping between systems"""
    id: str
    taoist_element: Optional[Union[Meridian, Dantian, AcupuncturePoint]] = None
    tibetan_element: Optional[Union[TibetanChannel, TibetanChakra, Wind]] = None
    hindu_element: Optional[Union[Chakra, Nadi]] = None
    correspondence_type: str = "approximate"  # exact, approximate, conceptual
    notes: str = ""
    confidence: float = 0.8  # 0.0 to 1.0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'taoist': self.taoist_element.id if self.taoist_element else None,
            'tibetan': self.tibetan_element.id if self.tibetan_element else None,
            'hindu': self.hindu_element.id if self.hindu_element else None,
            'type': self.correspondence_type,
            'notes': self.notes,
            'confidence': self.confidence
        }


# ============================================================================
# DATABASE/REGISTRY CLASSES
# ============================================================================

class EnergeticAnatomyDatabase:
    """Central database for all energetic anatomy elements"""

    def __init__(self):
        # Taoist system
        self.meridians: Dict[str, Meridian] = {}
        self.dantians: Dict[str, Dantian] = {}
        self.acupoints: Dict[str, AcupuncturePoint] = {}

        # Tibetan system
        self.tibetan_channels: Dict[str, TibetanChannel] = {}
        self.tibetan_chakras: Dict[str, TibetanChakra] = {}
        self.winds: Dict[str, Wind] = {}
        self.drops: Dict[str, Drop] = {}

        # Hindu system
        self.chakras: Dict[str, Chakra] = {}
        self.nadis: Dict[str, Nadi] = {}
        self.granthis: Dict[str, Granthi] = {}
        self.kundalini: Optional[Kundalini] = None

        # Cross-system
        self.correspondences: Dict[str, SystemCorrespondence] = {}

        # Initialize with default data
        self._initialize_systems()

    def _initialize_systems(self):
        """Initialize all three systems with default data"""
        self._init_taoist_system()
        self._init_tibetan_system()
        self._init_hindu_system()
        self._init_correspondences()

    def _init_taoist_system(self):
        """Initialize Taoist meridians and dantians"""
        # Three Dantians
        self.dantians['lower'] = Dantian(
            id='lower_dantian',
            name='Lower Dantian',
            tradition=Tradition.TAOIST,
            location=(0.0, -0.3, 0.0),  # Below navel
            element=Element.WATER,
            color=(0, 0, 139),  # Dark blue
            frequency=108.0,
            bija_mantra='HU',
            level='lower',
            cultivation_focus='Jing (Essence)',
            depth='3 finger-widths below navel, deep inside',
            balanced_state='Physical vitality, grounding, longevity',
            practices=['Grounding meditation', 'Standing practice', 'Jing cultivation']
        )

        self.dantians['middle'] = Dantian(
            id='middle_dantian',
            name='Middle Dantian',
            tradition=Tradition.TAOIST,
            location=(0.0, 0.2, 0.0),  # Heart level
            element=Element.FIRE,
            color=(255, 0, 0),  # Red
            frequency=144.0,
            bija_mantra='AH',
            level='middle',
            cultivation_focus='Qi (Energy)',
            depth='Center of chest',
            balanced_state='Emotional balance, compassion, qi circulation',
            practices=['Heart-mind meditation', 'Qi cultivation', 'Emotional alchemy']
        )

        self.dantians['upper'] = Dantian(
            id='upper_dantian',
            name='Upper Dantian',
            tradition=Tradition.TAOIST,
            location=(0.0, 0.7, 0.1),  # Between eyebrows
            element=Element.LIGHT,
            color=(255, 255, 255),  # White/gold
            frequency=216.0,
            bija_mantra='EEE',
            level='upper',
            cultivation_focus='Shen (Spirit)',
            depth='Center of head',
            balanced_state='Spiritual awareness, clarity, consciousness expansion',
            practices=['Meditation', 'Shen cultivation', 'Spiritual refinement']
        )

        # Primary Meridians (abbreviated - full data would be much longer)
        # Lung Meridian
        self.meridians['lung'] = Meridian(
            id='lung_meridian',
            name='Lung Meridian',
            tradition=Tradition.TAOIST,
            pathway=[],  # Would have detailed 3D path
            element=Element.METAL,
            color=(255, 255, 255),  # White
            flow_direction=FlowDirection.DESCENDING,
            organ='Lung',
            yin_yang=YinYang.YIN,
            emotion_negative='Grief, sadness',
            emotion_positive='Courage, righteousness',
            peak_hours=(3, 5),
            season='Autumn',
            direction='West',
            healing_sound='SSSS',
            sense='Smell (nose)',
            tissue='Skin',
            climate='Dryness',
            description='Hand Taiyin Lung Meridian - governs respiration and receiving qi from heaven'
        )

        # Heart Meridian
        self.meridians['heart'] = Meridian(
            id='heart_meridian',
            name='Heart Meridian',
            tradition=Tradition.TAOIST,
            pathway=[],
            element=Element.FIRE,
            color=(255, 0, 0),
            flow_direction=FlowDirection.DESCENDING,
            organ='Heart',
            yin_yang=YinYang.YIN,
            emotion_negative='Anxiety, agitation',
            emotion_positive='Joy, love',
            peak_hours=(11, 13),
            season='Summer',
            direction='South',
            healing_sound='HAWWW',
            sense='Speech (tongue)',
            tissue='Blood vessels',
            climate='Heat',
            description='Hand Shaoyin Heart Meridian - houses the shen (spirit), consciousness'
        )

        # Kidney Meridian
        self.meridians['kidney'] = Meridian(
            id='kidney_meridian',
            name='Kidney Meridian',
            tradition=Tradition.TAOIST,
            pathway=[],
            element=Element.WATER,
            color=(0, 0, 255),
            flow_direction=FlowDirection.ASCENDING,
            organ='Kidney',
            yin_yang=YinYang.YIN,
            emotion_negative='Fear',
            emotion_positive='Wisdom, willpower',
            peak_hours=(17, 19),
            season='Winter',
            direction='North',
            healing_sound='CHOOO',
            sense='Hearing (ears)',
            tissue='Bones',
            climate='Cold',
            description='Foot Shaoyin Kidney Meridian - stores essence, governs reproduction and willpower'
        )

        # Liver Meridian
        self.meridians['liver'] = Meridian(
            id='liver_meridian',
            name='Liver Meridian',
            tradition=Tradition.TAOIST,
            pathway=[],
            element=Element.WOOD,
            color=(0, 255, 0),
            flow_direction=FlowDirection.ASCENDING,
            organ='Liver',
            yin_yang=YinYang.YIN,
            emotion_negative='Anger, frustration',
            emotion_positive='Kindness, generosity',
            peak_hours=(1, 3),
            season='Spring',
            direction='East',
            healing_sound='SHHH',
            sense='Vision (eyes)',
            tissue='Tendons',
            climate='Wind',
            description='Foot Jueyin Liver Meridian - ensures smooth qi flow, planning, vision'
        )

        # Spleen Meridian
        self.meridians['spleen'] = Meridian(
            id='spleen_meridian',
            name='Spleen Meridian',
            tradition=Tradition.TAOIST,
            pathway=[],
            element=Element.EARTH,
            color=(255, 255, 0),
            flow_direction=FlowDirection.ASCENDING,
            organ='Spleen',
            yin_yang=YinYang.YIN,
            emotion_negative='Worry, overthinking',
            emotion_positive='Groundedness, trust',
            peak_hours=(9, 11),
            season='Late summer',
            direction='Center',
            healing_sound='WHOO',
            sense='Taste (mouth)',
            tissue='Muscles',
            climate='Dampness',
            description='Foot Taiyin Spleen Meridian - governs digestion and transformation'
        )

    def _init_tibetan_system(self):
        """Initialize Tibetan channels, chakras, and winds"""
        # Three Main Channels
        self.tibetan_channels['uma'] = TibetanChannel(
            id='central_channel',
            name='Central Channel (Avadhuti/Uma)',
            tradition=Tradition.TIBETAN,
            pathway=[],  # Spine pathway
            color=(0, 0, 255),  # Blue
            channel_type=ChannelType.CENTRAL,
            width_description='Width of arrow shaft to staff',
            top_opening='Crown of head (Brahma aperture)',
            bottom_opening='Tip of sexual organ',
            nature='Dharmadhatu, wisdom',
            element=Element.SPACE,
            description='When winds enter here, realization arises'
        )

        self.tibetan_channels['roma'] = TibetanChannel(
            id='right_channel',
            name='Right Channel (Rasana/Roma)',
            tradition=Tradition.TIBETAN,
            pathway=[],
            color=(255, 0, 0),  # Red
            channel_type=ChannelType.RIGHT,
            nature='Method, skillful means',
            element=Element.FIRE,
            quality=Quality.RAJAS,
            description='Solar, masculine, carries conceptual thoughts'
        )

        self.tibetan_channels['kyangma'] = TibetanChannel(
            id='left_channel',
            name='Left Channel (Lalana/Kyangma)',
            tradition=Tradition.TIBETAN,
            pathway=[],
            color=(255, 255, 255),  # White
            channel_type=ChannelType.LEFT,
            nature='Wisdom, emptiness',
            element=Element.WATER,
            quality=Quality.TAMAS,
            description='Lunar, feminine, carries afflictive emotions'
        )

        # Five Chakras (Tibetan system)
        self.tibetan_chakras['crown'] = TibetanChakra(
            id='ushnisha_chakra',
            name='Crown Chakra (Ushnisha)',
            tradition=Tradition.TIBETAN,
            location=(0.0, 0.9, 0.0),
            element=Element.SPACE,
            color=(255, 255, 255),  # Multi-colored/white
            frequency=963.0,
            petals=32,
            petal_direction='down',
            buddha='Vairochana',
            wisdom='Dharmadhatu wisdom',
            syllable='OM',
            syllable_color=(255, 255, 255),
            purifies='Delusion/Ignorance',
            pure_form='Buddha body',
            mudra='Dharmachakra mudra',
            direction='Center/All directions',
            balanced_state='Recognition of space-like awareness'
        )

        self.tibetan_chakras['throat'] = TibetanChakra(
            id='sambhoga_chakra',
            name='Throat Chakra',
            tradition=Tradition.TIBETAN,
            location=(0.0, 0.6, 0.0),
            element=Element.FIRE,
            color=(255, 0, 0),
            frequency=741.0,
            petals=16,
            petal_direction='up',
            buddha='Amitabha',
            wisdom='Discriminating wisdom',
            syllable='AH',
            syllable_color=(255, 0, 0),
            purifies='Attachment/Desire',
            pure_form='Buddha speech',
            mudra='Meditation mudra',
            direction='West',
            balanced_state='Pure speech, communication of truth'
        )

        self.tibetan_chakras['heart'] = TibetanChakra(
            id='dharma_chakra',
            name='Heart Chakra',
            tradition=Tradition.TIBETAN,
            location=(0.0, 0.2, 0.0),
            element=Element.WATER,
            color=(255, 255, 255),  # White
            frequency=528.0,
            petals=8,
            petal_direction='down',
            buddha='Akshobhya',
            wisdom='Mirror-like wisdom',
            syllable='HUM',
            syllable_color=(0, 0, 255),
            purifies='Anger/Aversion',
            pure_form='Buddha mind',
            mudra='Earth-touching mudra',
            direction='East',
            balanced_state='Indestructible awareness, most important chakra',
            description='Indestructible drop resides here - seat of very subtle mind'
        )

        self.tibetan_chakras['navel'] = TibetanChakra(
            id='nirmana_chakra',
            name='Navel Chakra',
            tradition=Tradition.TIBETAN,
            location=(0.0, -0.1, 0.0),
            element=Element.FIRE,
            color=(255, 255, 0),
            frequency=285.0,
            petals=64,
            petal_direction='up',
            buddha='Ratnasambhava',
            wisdom='Equality wisdom',
            syllable='TRAM',
            syllable_color=(255, 255, 0),
            purifies='Pride',
            pure_form='Buddha qualities',
            mudra='Giving mudra',
            direction='South',
            balanced_state='Tummo inner heat, transformation',
            description='Tummo fire arises here - key practice site'
        )

        self.tibetan_chakras['secret'] = TibetanChakra(
            id='sukha_chakra',
            name='Secret Chakra',
            tradition=Tradition.TIBETAN,
            location=(0.0, -0.5, 0.0),
            element=Element.EARTH,
            color=(128, 0, 128),  # Multi-colored
            frequency=174.0,
            petals=32,
            petal_direction='up',
            buddha='Amoghasiddhi',
            wisdom='All-accomplishing wisdom',
            syllable='HA',
            syllable_color=(0, 255, 0),
            purifies='Jealousy',
            pure_form='Buddha emanations',
            mudra='Fearlessness mudra',
            direction='North',
            balanced_state='Foundation, grounding, bliss'
        )

        # Five Root Winds
        self.winds['life_supporting'] = Wind(
            id='life_supporting_wind',
            name='Life-Supporting Wind',
            tradition=Tradition.TIBETAN,
            location=(0.0, 0.7, 0.0),
            element=Element.SPACE,
            color=(255, 255, 255),
            wind_type='root',
            function='Breathing, swallowing, spitting',
            disturbed_state='Anxiety, mental instability',
            description='Sog Dzin Kyi Lung - resides at crown/head'
        )

        self.winds['upward_moving'] = Wind(
            id='upward_moving_wind',
            name='Upward-Moving Wind',
            tradition=Tradition.TIBETAN,
            location=(0.0, 0.6, 0.0),
            element=Element.FIRE,
            color=(255, 0, 0),
            wind_type='root',
            function='Speech, effort, memory',
            disturbed_state='Speech problems, breathlessness',
            description='Yen Gyen Kyi Lung - resides at throat'
        )

        self.winds['pervading'] = Wind(
            id='pervading_wind',
            name='Pervading Wind',
            tradition=Tradition.TIBETAN,
            location=(0.0, 0.2, 0.0),
            element=Element.WATER,
            color=(0, 0, 255),
            wind_type='root',
            function='Movement of limbs, contraction/expansion',
            disturbed_state='Heart palpitations, circulation issues',
            description='Khyab Jey Kyi Lung - resides at heart'
        )

        self.winds['fire_accompanying'] = Wind(
            id='fire_accompanying_wind',
            name='Fire-Accompanying Wind',
            tradition=Tradition.TIBETAN,
            location=(0.0, -0.1, 0.0),
            element=Element.EARTH,
            color=(255, 255, 0),
            wind_type='root',
            function='Digestion, metabolism',
            disturbed_state='Digestive problems',
            description='Me Nyam Kyi Lung - resides at navel'
        )

        self.winds['downward_voiding'] = Wind(
            id='downward_voiding_wind',
            name='Downward-Voiding Wind',
            tradition=Tradition.TIBETAN,
            location=(0.0, -0.5, 0.0),
            element=Element.EARTH,
            color=(0, 255, 0),
            wind_type='root',
            function='Excretion, ejaculation, menstruation',
            disturbed_state='Reproductive/eliminative problems',
            description='Tur Sel Kyi Lung - resides at secret place'
        )

        # Drops
        self.drops['white'] = Drop(
            id='white_drop',
            name='White Drop',
            drop_type='white',
            location='Crown chakra and upper body',
            nature='Bliss, method, masculine',
            function='Descends during practice, source from father'
        )

        self.drops['red'] = Drop(
            id='red_drop',
            name='Red Drop',
            drop_type='red',
            location='Navel chakra and lower body',
            nature='Warmth, wisdom, feminine',
            function='Ascends during practice, source from mother'
        )

        self.drops['indestructible'] = Drop(
            id='indestructible_drop',
            name='Indestructible Drop',
            drop_type='indestructible',
            location='Heart chakra center',
            nature='Union of white and red, very subtle mind and wind',
            function='Seat of consciousness, leaves body only at death'
        )

    def _init_hindu_system(self):
        """Initialize Hindu chakras, nadis, and related elements"""
        # Seven Main Chakras
        self.chakras['muladhara'] = Chakra(
            id='muladhara',
            name='Root Chakra',
            sanskrit_name='Muladhara',
            tradition=Tradition.HINDU,
            location=(0.0, -0.5, 0.0),
            element=Element.EARTH,
            color=(255, 0, 0),  # Red
            frequency=396.0,
            petals=4,
            petal_mantras=['वं', 'शं', 'षं', 'सं'],
            bija_mantra='LAM',
            yantra_geometry='Yellow square',
            deity='Ganesha',
            goddess='Dakini',
            animal='Elephant (7 trunks)',
            kosha='Annamaya (physical body)',
            sense='Smell (nose)',
            body_parts=['Legs', 'Feet', 'Bones', 'Large intestine'],
            gland='Adrenals',
            plexus='Sacral plexus',
            blocked_issues=['Survival fears', 'Scarcity mindset', 'Insecurity', 'Disconnection from body'],
            open_qualities=['Groundedness', 'Stability', 'Vitality', 'Trust in life'],
            developmental_stage='0-7 years',
            right='To exist, to have',
            balanced_state='Grounded, secure, stable, vital',
            blocked_state='Fearful, insecure, ungrounded, survival anxiety',
            description='Foundation chakra where kundalini sleeps coiled 3.5 times'
        )

        self.chakras['svadhisthana'] = Chakra(
            id='svadhisthana',
            name='Sacral Chakra',
            sanskrit_name='Svadhisthana',
            tradition=Tradition.HINDU,
            location=(0.0, -0.3, 0.0),
            element=Element.WATER,
            color=(255, 127, 0),  # Orange
            frequency=417.0,
            petals=6,
            petal_mantras=['बं', 'भं', 'मं', 'यं', 'रं', 'लं'],
            bija_mantra='VAM',
            yantra_geometry='Silver crescent moon',
            deity='Brahma',
            goddess='Rakini',
            animal='Crocodile (Makara)',
            kosha='Pranamaya (energy body)',
            sense='Taste (tongue)',
            body_parts=['Reproductive organs', 'Kidneys', 'Bladder'],
            gland='Gonads (ovaries/testes)',
            plexus='Lumbar plexus',
            blocked_issues=['Guilt', 'Sexual shame', 'Creative blocks', 'Emotional repression'],
            open_qualities=['Creativity', 'Pleasure', 'Emotional flow', 'Healthy sexuality'],
            developmental_stage='7-14 years',
            right='To feel, to want',
            balanced_state='Creative, emotionally fluid, pleasurable',
            blocked_state='Guilty, sexually repressed, creatively blocked'
        )

        self.chakras['manipura'] = Chakra(
            id='manipura',
            name='Solar Plexus Chakra',
            sanskrit_name='Manipura',
            tradition=Tradition.HINDU,
            location=(0.0, 0.0, 0.0),
            element=Element.FIRE,
            color=(255, 255, 0),  # Yellow
            frequency=528.0,
            petals=10,
            petal_mantras=['डं', 'ढं', 'णं', 'तं', 'थं', 'दं', 'धं', 'नं', 'पं', 'फं'],
            bija_mantra='RAM',
            yantra_geometry='Red inverted triangle',
            deity='Rudra',
            goddess='Lakini',
            animal='Ram',
            kosha='Pranamaya (energy body)',
            sense='Sight (eyes)',
            body_parts=['Digestive system', 'Liver', 'Pancreas', 'Stomach'],
            gland='Pancreas',
            plexus='Solar plexus',
            blocked_issues=['Shame', 'Powerlessness', 'Poor boundaries', 'Digestive issues'],
            open_qualities=['Confidence', 'Will', 'Transformation', 'Personal power'],
            developmental_stage='14-21 years',
            right='To act, to be autonomous',
            balanced_state='Confident, empowered, strong digestion',
            blocked_state='Shameful, powerless, weak boundaries'
        )

        self.chakras['anahata'] = Chakra(
            id='anahata',
            name='Heart Chakra',
            sanskrit_name='Anahata',
            tradition=Tradition.HINDU,
            location=(0.0, 0.2, 0.0),
            element=Element.SPACE,  # Air/Vayu
            color=(0, 255, 0),  # Green
            frequency=639.0,
            petals=12,
            petal_mantras=['कं', 'खं', 'गं', 'घं', 'ङं', 'चं', 'छं', 'जं', 'झं', 'ञं', 'टं', 'ठं'],
            bija_mantra='YAM',
            yantra_geometry='Smoke-colored hexagram (two triangles)',
            deity='Isha',
            goddess='Kakini',
            animal='Antelope or deer',
            kosha='Pranamaya/Manomaya (energy/mental body)',
            sense='Touch (skin)',
            body_parts=['Heart', 'Lungs', 'Chest', 'Arms', 'Hands'],
            gland='Thymus',
            plexus='Cardiac plexus',
            blocked_issues=['Grief', 'Loneliness', 'Inability to love', 'Codependency'],
            open_qualities=['Compassion', 'Love', 'Acceptance', 'Connection'],
            developmental_stage='21-28 years',
            right='To love and be loved',
            balanced_state='Compassionate, loving, connected, peaceful',
            blocked_state='Grief-stricken, lonely, unable to love or be loved',
            description='Unstruck sound (anahata nada) - meeting place of upper and lower chakras'
        )

        self.chakras['vishuddha'] = Chakra(
            id='vishuddha',
            name='Throat Chakra',
            sanskrit_name='Vishuddha',
            tradition=Tradition.HINDU,
            location=(0.0, 0.6, 0.0),
            element=Element.SPACE,  # Akasha/ether
            color=(0, 0, 255),  # Blue
            frequency=741.0,
            petals=16,
            petal_mantras=['अ', 'आ', 'इ', 'ई', 'उ', 'ऊ', 'ऋ', 'ॠ', 'लृ', 'ॡ', 'ए', 'ऐ', 'ओ', 'औ', 'अं', 'अः'],
            bija_mantra='HAM',
            yantra_geometry='White circle (full moon)',
            deity='Sadashiva (half male, half female)',
            goddess='Shakini',
            animal='White elephant',
            kosha='Manomaya (mental body)',
            sense='Hearing (ears)',
            body_parts=['Throat', 'Neck', 'Jaw', 'Ears', 'Mouth'],
            gland='Thyroid',
            plexus='Pharyngeal plexus',
            blocked_issues=['Lies', 'Inability to express', 'Fear of speaking', 'Excessive talking'],
            open_qualities=['Truth', 'Authentic expression', 'Communication', 'Listening'],
            developmental_stage='28-35 years',
            right='To speak and be heard',
            balanced_state='Truthful, expressive, good listener',
            blocked_state='Dishonest, unable to express, poor listener'
        )

        self.chakras['ajna'] = Chakra(
            id='ajna',
            name='Third Eye Chakra',
            sanskrit_name='Ajna',
            tradition=Tradition.HINDU,
            location=(0.0, 0.7, 0.1),
            element=Element.LIGHT,  # Mind/Manas
            color=(75, 0, 130),  # Indigo
            frequency=852.0,
            petals=2,
            petal_mantras=['हं', 'क्षं'],
            bija_mantra='OM',
            yantra_geometry='White circle with inverted triangle',
            deity='Paramashiva',
            goddess='Hakini',
            animal='None (transcends animal nature)',
            kosha='Vijnanamaya (wisdom body)',
            sense='Sixth sense (intuition, inner seeing)',
            body_parts=['Brain', 'Eyes', 'Pineal gland'],
            gland='Pineal',
            plexus='Cavernous plexus',
            blocked_issues=['Delusion', 'Closed mind', 'Attachment to intellect', 'No vision'],
            open_qualities=['Insight', 'Intuition', 'Wisdom', 'Clear vision'],
            developmental_stage='35+ years',
            right='To see, to know',
            balanced_state='Intuitive, wise, clear-seeing',
            blocked_state='Deluded, closed-minded, no intuition',
            description='Meeting point where ida and pingala converge into sushumna'
        )

        self.chakras['sahasrara'] = Chakra(
            id='sahasrara',
            name='Crown Chakra',
            sanskrit_name='Sahasrara',
            tradition=Tradition.HINDU,
            location=(0.0, 0.9, 0.0),
            element=Element.CONSCIOUSNESS,
            color=(138, 43, 226),  # Violet
            frequency=963.0,
            petals=1000,  # Infinity
            petal_mantras=[],  # All 50 Sanskrit letters repeated 20 times
            bija_mantra='OM or silence',
            yantra_geometry='Full moon/circle of light',
            deity='Shiva (pure consciousness)',
            goddess='Shakti reunited with Shiva',
            animal='None',
            kosha='Anandamaya (bliss body)',
            sense='Transcendent knowing',
            body_parts=['Entire nervous system', 'Brain', 'Higher cortex'],
            gland='Pituitary (or entire endocrine system)',
            plexus='Cerebral cortex',
            blocked_issues=['Disconnection', 'Lack of meaning', 'Spiritual crisis', 'Depression'],
            open_qualities=['Unity', 'Enlightenment', 'Bliss', 'Cosmic consciousness'],
            developmental_stage='Lifelong unfoldment',
            right='To know truth, to be free',
            balanced_state='Unified awareness, enlightenment, bliss',
            blocked_state='Disconnected, meaningless, spiritually bereft',
            description='Thousand-petaled lotus - seat of realization and union'
        )

        # Three Main Nadis
        self.nadis['sushumna'] = Nadi(
            id='sushumna',
            name='Sushumna',
            tradition=Tradition.HINDU,
            pathway=[],  # Spine pathway
            color=(255, 215, 0),  # Golden
            nadi_type='sushumna',
            quality=Quality.SATTVA,
            temperature='neutral',
            gender_association='neutral',
            element=Element.FIRE,
            flow_direction=FlowDirection.ASCENDING,
            description='Central channel - path of kundalini ascent from muladhara to sahasrara'
        )

        self.nadis['ida'] = Nadi(
            id='ida',
            name='Ida',
            tradition=Tradition.HINDU,
            pathway=[],  # Spirals left around sushumna
            color=(255, 255, 255),  # White/pale
            nadi_type='ida',
            quality=Quality.TAMAS,
            temperature='cold',
            gender_association='feminine',
            nostril='left',
            element=Element.WATER,
            flow_direction=FlowDirection.SPIRAL,
            description='Left channel - lunar, cooling, feminine, receptive energy. Associated with Ganga river.'
        )

        self.nadis['pingala'] = Nadi(
            id='pingala',
            name='Pingala',
            tradition=Tradition.HINDU,
            pathway=[],  # Spirals right around sushumna
            color=(255, 0, 0),  # Red
            nadi_type='pingala',
            quality=Quality.RAJAS,
            temperature='hot',
            gender_association='masculine',
            nostril='right',
            element=Element.FIRE,
            flow_direction=FlowDirection.SPIRAL,
            description='Right channel - solar, heating, masculine, active energy. Associated with Yamuna river.'
        )

        # Three Granthis
        self.granthis['brahma'] = Granthi(
            id='brahma_granthi',
            name='Brahma Granthi',
            sanskrit_name='ब्रह्म ग्रन्थि',
            location='muladhara',
            blocks='Attachment to physical security, survival fears, material attachment',
            must_pierce='To move beyond physical identification and body consciousness',
            practices_to_pierce=['Asana', 'Pranayama', 'Meditation on impermanence']
        )

        self.granthis['vishnu'] = Granthi(
            id='vishnu_granthi',
            name='Vishnu Granthi',
            sanskrit_name='विष्णु ग्रन्थि',
            location='anahata',
            blocks='Emotional attachments, personal relationships, ego identification',
            must_pierce='To move beyond personal love and ego-based relationships',
            practices_to_pierce=['Bhakti yoga', 'Metta', 'Dissolution of "I and mine"']
        )

        self.granthis['rudra'] = Granthi(
            id='rudra_granthi',
            name='Rudra Granthi',
            sanskrit_name='रुद्र ग्रन्थि',
            location='ajna',
            blocks='Attachment to psychic powers, subtle ego, spiritual pride',
            must_pierce='To reach non-dual awareness and full enlightenment',
            practices_to_pierce=['Self-inquiry', 'Surrender of all attainment', 'Recognition of emptiness']
        )

        # Kundalini
        self.kundalini = Kundalini(
            current_location='muladhara',
            state='dormant',
            awakening_signs=[
                'Spontaneous movements (kriyas)',
                'Heat at base of spine',
                'Visions of light',
                'Blissful states',
                'Psychic experiences',
                'Automatic pranayama or asanas'
            ],
            preparation_required=[
                'Purification practices (shatkarma)',
                'Strong physical body (asana)',
                'Breath control (pranayama)',
                'Mental discipline (meditation)',
                'Ethical foundation (yamas/niyamas)',
                'Guidance from realized teacher'
            ],
            warnings=[
                'Premature awakening can cause serious problems',
                'Requires strong nadis and chakras',
                'Must have teacher guidance',
                'Not a goal to force',
                'Prepare properly over years'
            ]
        )

    def _init_correspondences(self):
        """Initialize cross-system correspondences"""
        # Lower energy centers
        self.correspondences['lower_center'] = SystemCorrespondence(
            id='lower_center',
            taoist_element=self.dantians.get('lower'),
            tibetan_element=self.tibetan_chakras.get('secret'),
            hindu_element=self.chakras.get('muladhara'),
            correspondence_type='approximate',
            notes='All three systems have a lower energy center focused on foundation, vitality, and physical energy',
            confidence=0.85
        )

        # Heart centers
        self.correspondences['heart_center'] = SystemCorrespondence(
            id='heart_center',
            taoist_element=self.dantians.get('middle'),
            tibetan_element=self.tibetan_chakras.get('heart'),
            hindu_element=self.chakras.get('anahata'),
            correspondence_type='exact',
            notes='Heart center is remarkably consistent across all three systems - seat of consciousness, compassion, and integration',
            confidence=0.95
        )

        # Upper centers
        self.correspondences['upper_center'] = SystemCorrespondence(
            id='upper_center',
            taoist_element=self.dantians.get('upper'),
            tibetan_element=self.tibetan_chakras.get('crown'),
            hindu_element=self.chakras.get('sahasrara'),
            correspondence_type='approximate',
            notes='Upper centers all focus on spiritual awareness, consciousness, and connection to the divine',
            confidence=0.90
        )

        # Central channels
        self.correspondences['central_channel'] = SystemCorrespondence(
            id='central_channel',
            tibetan_element=self.tibetan_channels.get('uma'),
            hindu_element=self.nadis.get('sushumna'),
            correspondence_type='exact',
            notes='Both systems describe a central channel through which spiritual energy rises',
            confidence=0.95
        )

    # Query methods
    def get_all_chakras(self) -> List[Chakra]:
        """Get all Hindu chakras"""
        return list(self.chakras.values())

    def get_all_meridians(self) -> List[Meridian]:
        """Get all Taoist meridians"""
        return list(self.meridians.values())

    def get_all_tibetan_chakras(self) -> List[TibetanChakra]:
        """Get all Tibetan chakras"""
        return list(self.tibetan_chakras.values())

    def get_element_points(self, element: Element) -> List[Union[Meridian, Chakra, TibetanChakra]]:
        """Get all points associated with a specific element"""
        points = []

        # Check meridians
        for meridian in self.meridians.values():
            if meridian.element == element:
                points.append(meridian)

        # Check chakras
        for chakra in self.chakras.values():
            if chakra.element == element:
                points.append(chakra)

        # Check Tibetan chakras
        for tchakra in self.tibetan_chakras.values():
            if tchakra.element == element:
                points.append(tchakra)

        return points

    def get_correspondence(self, element_id: str) -> Optional[SystemCorrespondence]:
        """Get cross-system correspondence for an element"""
        # Search all correspondences
        for corr in self.correspondences.values():
            if corr.taoist_element and corr.taoist_element.id == element_id:
                return corr
            if corr.tibetan_element and corr.tibetan_element.id == element_id:
                return corr
            if corr.hindu_element and corr.hindu_element.id == element_id:
                return corr
        return None

    def search_by_keyword(self, keyword: str) -> Dict[str, List]:
        """Search all systems for keyword"""
        keyword = keyword.lower()
        results = {
            'meridians': [],
            'chakras': [],
            'tibetan_chakras': [],
            'winds': [],
            'dantians': []
        }

        # Search meridians
        for m in self.meridians.values():
            if (keyword in m.name.lower() or
                keyword in m.description.lower() or
                keyword in m.organ.lower()):
                results['meridians'].append(m)

        # Search chakras
        for c in self.chakras.values():
            if (keyword in c.name.lower() or
                keyword in c.sanskrit_name.lower() or
                keyword in c.description.lower()):
                results['chakras'].append(c)

        # Search Tibetan chakras
        for tc in self.tibetan_chakras.values():
            if keyword in tc.name.lower() or keyword in tc.description.lower():
                results['tibetan_chakras'].append(tc)

        # Search winds
        for w in self.winds.values():
            if keyword in w.name.lower() or keyword in w.description.lower():
                results['winds'].append(w)

        # Search dantians
        for d in self.dantians.values():
            if keyword in d.name.lower() or keyword in d.description.lower():
                results['dantians'].append(d)

        return results

    def export_to_json(self, filepath: str):
        """Export entire database to JSON"""
        data = {
            'taoist': {
                'meridians': {k: v.to_dict() for k, v in self.meridians.items()},
                'dantians': {k: v.to_dict() for k, v in self.dantians.items()},
                'acupoints': {k: v.to_dict() for k, v in self.acupoints.items()}
            },
            'tibetan': {
                'channels': {k: v.to_dict() for k, v in self.tibetan_channels.items()},
                'chakras': {k: v.to_dict() for k, v in self.tibetan_chakras.items()},
                'winds': {k: v.to_dict() for k, v in self.winds.items()},
                'drops': {k: v.to_dict() for k, v in self.drops.items()}
            },
            'hindu': {
                'chakras': {k: v.to_dict() for k, v in self.chakras.items()},
                'nadis': {k: v.to_dict() for k, v in self.nadis.items()},
                'granthis': {k: v.to_dict() for k, v in self.granthis.items()},
                'kundalini': self.kundalini.to_dict() if self.kundalini else None
            },
            'correspondences': {k: v.to_dict() for k, v in self.correspondences.items()}
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_chakra_by_name(db: EnergeticAnatomyDatabase, name: str) -> Optional[Chakra]:
    """Get Hindu chakra by name or sanskrit name"""
    name_lower = name.lower()
    for chakra in db.chakras.values():
        if (name_lower in chakra.name.lower() or
            name_lower in chakra.sanskrit_name.lower() or
            chakra.id == name_lower):
            return chakra
    return None


def get_meridian_by_element(db: EnergeticAnatomyDatabase, element: Element, yin_yang: Optional[YinYang] = None) -> List[Meridian]:
    """Get meridians by element and optionally yin/yang"""
    results = []
    for meridian in db.meridians.values():
        if meridian.element == element:
            if yin_yang is None or meridian.yin_yang == yin_yang:
                results.append(meridian)
    return results


# Example usage
if __name__ == "__main__":
    print("Energetic Anatomy System - Multi-Traditional Integration\n")

    # Initialize database
    db = EnergeticAnatomyDatabase()

    print("=== SYSTEM STATISTICS ===")
    print(f"Taoist Meridians: {len(db.meridians)}")
    print(f"Taoist Dantians: {len(db.dantians)}")
    print(f"Tibetan Channels: {len(db.tibetan_channels)}")
    print(f"Tibetan Chakras: {len(db.tibetan_chakras)}")
    print(f"Tibetan Winds: {len(db.winds)}")
    print(f"Hindu Chakras: {len(db.chakras)}")
    print(f"Hindu Nadis: {len(db.nadis)}")
    print(f"Hindu Granthis: {len(db.granthis)}")
    print(f"Cross-System Correspondences: {len(db.correspondences)}\n")

    # Example: Get heart chakra
    heart = get_chakra_by_name(db, "anahata")
    if heart:
        print("=== HEART CHAKRA (ANAHATA) ===")
        print(f"Sanskrit: {heart.sanskrit_name}")
        print(f"Location: {heart.location}")
        print(f"Element: {heart.element.value}")
        print(f"Color: RGB{heart.color}")
        print(f"Frequency: {heart.frequency} Hz")
        print(f"Bija Mantra: {heart.bija_mantra}")
        print(f"Petals: {heart.petals}")
        print(f"Deity: {heart.deity}")
        print(f"Balanced State: {heart.balanced_state}\n")

    # Example: Get correspondence
    corr = db.get_correspondence('heart_center')
    if corr:
        print("=== HEART CENTER CORRESPONDENCE ===")
        print(f"Taoist: {corr.taoist_element.name if corr.taoist_element else 'N/A'}")
        print(f"Tibetan: {corr.tibetan_element.name if corr.tibetan_element else 'N/A'}")
        print(f"Hindu: {corr.hindu_element.name if corr.hindu_element else 'N/A'}")
        print(f"Type: {corr.correspondence_type}")
        print(f"Confidence: {corr.confidence * 100}%")
        print(f"Notes: {corr.notes}\n")

    # Example: Search
    results = db.search_by_keyword("fire")
    print("=== SEARCH RESULTS FOR 'FIRE' ===")
    print(f"Meridians: {[m.name for m in results['meridians']]}")
    print(f"Chakras: {[c.name for c in results['chakras']]}")
    print(f"Tibetan Chakras: {[tc.name for tc in results['tibetan_chakras']]}")

    print("\n✨ Energetic Anatomy System Initialized Successfully! ✨")
