# Blessing Narratives System - Complete Guide

**Generating Liberation Stories for Compassionate Transformation**

---

## Table of Contents

1. [Introduction](#introduction)
2. [Philosophy & Purpose](#philosophy--purpose)
3. [Quick Start](#quick-start)
4. [Narrative Types](#narrative-types)
5. [Pure Land Traditions](#pure-land-traditions)
6. [CLI Usage](#cli-usage)
7. [Python API](#python-api)
8. [Template System](#template-system)
9. [LLM Integration](#llm-integration)
10. [Example Stories](#example-stories)
11. [Integration with Blessing Database](#integration-with-blessing-database)
12. [Ethical Considerations](#ethical-considerations)
13. [Advanced Usage](#advanced-usage)

---

## Introduction

The Blessing Narratives System generates compassionate stories about liberation, healing, and transformation. These narratives serve multiple purposes:

- **Visualization**: Helping practitioners envision liberation for beings they're blessing
- **Inspiration**: Offering hope and possibility to those who suffer
- **Education**: Teaching about different spiritual traditions and liberation paths
- **Dedication**: Creating meaningful story-objects to dedicate merit to beings

### What This System Creates

1. **Pure Land Arrival Stories**: Narratives of beings arriving in sacred realms after death
2. **Hell Liberation Stories**: Stories of liberation from extreme suffering states
3. **Empowerment Narratives**: Tales of the powerless gaining power and agency
4. **Reconciliation Stories**: Healing narratives for both victims and perpetrators
5. **Transformation Journeys**: Stories of profound personal and collective change

---

## Philosophy & Purpose

### The Power of Story

Buddhist traditions have always used story as a teaching tool:
- Jataka tales of the Buddha's past lives
- Pure land sutras describing sacred realms in vivid detail
- Accounts of practitioners achieving liberation
- Narratives of compassionate intervention by bodhisattvas

This system continues that tradition using modern technology.

### Compassionate Imagination

These stories are not "just imagination" - they serve real purposes:

1. **Directing Intention**: A specific story helps focus compassionate energy
2. **Creating Possibility**: What the mind can imagine, the heart can empower
3. **Honoring Suffering**: Story acknowledges pain while offering hope
4. **Teaching Dharma**: Each narrative contains spiritual principles
5. **Inspiring Action**: Stories motivate real-world compassionate engagement

### Not Spiritual Bypassing

Important: These stories are NOT meant to:
- Deny real suffering
- Bypass necessary accountability
- Replace systemic change with imagination
- Offer false hope to those actively suffering

Instead, they're tools for practitioners to:
- Maintain hope while doing hard work
- Envision liberation as motivation for practice
- Dedicate merit in meaningful, specific ways
- Teach and inspire compassionate action

---

## Quick Start

### Generate Your First Story

```bash
# Simple pure land story
python scripts/story_generator.py --generate --name "Unknown Soul" --type pure_land_arrival

# Hell liberation story
python scripts/story_generator.py --generate --name "Suffering Being" --type hell_liberation

# Interactive mode (guided prompts)
python scripts/story_generator.py --interactive
```

### Generate Batch Stories from Database

```bash
# Generate 10 stories for missing persons
python scripts/story_generator.py --batch --category missing_person --count 10 --output ./stories

# Generate stories for all hungry ghosts
python scripts/story_generator.py --batch --category hungry_ghost --output ./ghost_stories
```

### List Available Options

```bash
# Show all narrative types and pure land traditions
python scripts/story_generator.py --list-types

# Get detailed description of a specific pure land
python scripts/story_generator.py --describe-pure-land sukhavati
```

---

## Narrative Types

### 1. Pure Land Arrival (`pure_land_arrival`)

**Purpose**: Stories of beings arriving in sacred realms after death

**Structure**:
- Transition from suffering to peace
- Journey through the bardo (intermediate state)
- Arrival in the pure land
- Description of the realm and its qualities
- Life in the pure land and path to enlightenment

**Best For**:
- Recently deceased
- Beings in the bardo state
- General blessing for unknown deceased
- Comfort for the grieving

**Example Opening**:
> "As the final breath left the body, consciousness did not cease but transformed. The familiar world dissolved like mist in morning sun, and in its place - light..."

---

### 2. Hell Liberation (`hell_liberation`)

**Purpose**: Stories of liberation from extreme suffering states

**Structure**:
- Acknowledgment of hell realm suffering
- How compassion reaches even the darkest places
- The moment of opening/remorse
- Liberation and transformation
- Commitment to helping others

**Best For**:
- Beings who died with extreme anger or violence
- Those experiencing profound guilt
- Perpetrators of harm seeking redemption
- Visualization for tonglen (taking and sending) practice

**Important Notes**:
- Doesn't minimize the reality of harm done
- Balances accountability with possibility of transformation
- Acknowledges both justice and compassion
- Not about excusing actions but about liberating consciousness

**Example Opening**:
> "In the deepest darkness, where suffering seemed infinite and hope a distant memory, a being existed in torment. But even in the deepest hell, the light of compassion reaches..."

---

### 3. Empowerment (`empowerment`)

**Purpose**: Stories of the powerless gaining power and agency

**Structure**:
- Reality of oppression and powerlessness
- Awakening of inner strength
- Building community and solidarity
- Moment of empowerment
- Using power wisely to help others

**Best For**:
- Marginalized populations
- Oppressed communities
- Those experiencing systemic injustice
- Activists and organizers needing inspiration
- Visualizing collective liberation

**Key Themes**:
- Power-with rather than power-over
- Collective rather than individual liberation
- Accountability in use of power
- Breaking cycles of oppression

**Example Opening**:
> "For generations, powerlessness had been the only reality known. But something shifted - a spark of recognition: 'This is not who I truly am...'"

---

### 4. Reconciliation (`reconciliation`)

**Purpose**: Healing narratives for both victims and perpetrators

**Structure**:
- Both sides' suffering acknowledged
- Creating safe space for truth-telling
- Genuine accountability without revenge
- Boundaries and forgiveness
- Transformation for both
- Ripple effects of healing

**Best For**:
- Restorative justice work
- Healing cycles of violence
- Processing complex harm situations
- Teaching about accountability and forgiveness
- Advanced practitioners working with difficult emotions

**Critical Notes**:
- NEVER pressures victims to forgive
- Maintains clear accountability for harm
- Honors boundaries absolutely
- Forgiveness is for liberation, not absolution
- Complex, nuanced approach to harm

**Example Opening**:
> "Two beings, bound by karma - one who harmed and one who was harmed. The wound between them seemed absolute. But in a space beyond ordinary time, healing became possible..."

---

### 5. Hungry Ghost Nourishment (`hungry_ghost_nourishment`)

**Purpose**: Stories of hungry ghosts receiving satisfaction and release

**Structure**:
- Experience of insatiable craving
- Someone making offerings
- Gradual satisfaction and opening
- Understanding the true hunger
- Liberation from grasping
- Transformation into generosity

**Best For**:
- Hungry ghost realm beings (Buddhist cosmology)
- Those who died with strong attachments
- Spirits at sites of suffering
- Addiction-related deaths
- Offerings for the deceased

**Buddhist Context**:
The hungry ghost realm (preta loka) is characterized by insatiable craving. Traditional
practice involves making food and water offerings for hungry ghosts, especially during
Ghost Month or memorial services. These narratives support that practice.

**Example Opening**:
> "The hunger was everything - vast, aching, impossible to satisfy. But then, unexpectedly: someone remembering, someone offering, someone dedicating merit..."

---

## Pure Land Traditions

The system includes detailed descriptions of multiple pure land traditions:

### 1. Sukhavati (Western Pure Land) `sukhavati`

**Tradition**: Mahayana Buddhism (Pure Land School)

**Presiding Buddha**: Amitabha (Infinite Light)

**Key Features**:
- Ground of lapis lazuli
- Jeweled trees singing dharma
- Seven-tiered lotus pools
- Celestial birds teaching
- No darkness, only light
- Birth from lotus flowers

**Access**: Reciting Amitabha's name with sincere faith

**What Happens There**:
- Gradual, joyful path to enlightenment
- Learning directly from Amitabha Buddha
- Eventually becoming a bodhisattva
- Visiting other realms to help beings

**Best For**:
- Traditional Buddhist practitioners
- Those familiar with Pure Land teachings
- Beings who need certainty of liberation
- Simple, accessible path visualization

### 2. Shambhala (Hidden Kingdom) `shambhala`

**Tradition**: Tibetan Buddhism / Central Asian Buddhism

**Leadership**: Kalki Kings (enlightened rulers)

**Key Features**:
- Hidden kingdom ringed by mountains
- Exists in slightly different dimension
- Crystal palaces and gardens
- Advanced spiritual technology
- Warrior-bodhisattva society
- Enlightened governance

**Access**: Ripening of specific karma; preparation for Kalachakra teachings

**What Happens There**:
- Training as warrior-bodhisattva
- Study of Kalachakra system
- Preparing for future age when Shambhala emerges
- Building enlightened society

**Best For**:
- Practitioners of Tibetan Buddhism
- Those interested in sacred kingship
- Visions of enlightened society
- Activists imagining better worlds

### 3. Universal Light `universal_light`

**Tradition**: Non-denominational / Trans-traditional

**Key Features**:
- Pure consciousness as landscape
- Non-dual awareness
- Light and unconditional love
- Instant heart-to-heart communication
- Spontaneous healing
- Freedom from physical form

**Access**: Direct recognition of true nature

**What Happens There**:
- Immediate healing of trauma
- Resting in natural state
- Communion with enlightened beings of all traditions
- Creating reality through intention
- Exploring infinite consciousness

**Best For**:
- Non-Buddhist practitioners
- Interfaith contexts
- Modern/Western audiences
- Non-denominational memorial services
- Those uncomfortable with traditional imagery

### 4. Nature Paradise `nature_paradise`

**Tradition**: Universal / Eden-like

**Key Features**:
- Pristine wilderness
- Earth fully healed
- Harmony between species
- Sacred groves and springs
- Animals without fear
- Perfect natural balance

**Access**: Returning to original innocence

**What Happens There**:
- Living in harmony with nature
- Communicating with animals and plants
- Simple, peaceful existence
- Healing through natural beauty
- Reconnection with Earth

**Best For**:
- Environmental activists
- Those who find God in nature
- Indigenous spiritual contexts
- Animals and nature spirits
- Simple, accessible imagery

### 5. Other Traditions

The system also includes:
- **Abhirati** (Akshobhya's Eastern Pure Land)
- **Tushita** (Maitreya's Pure Land)
- **Potala** (Avalokiteshvara's Pure Land)
- **Vimalakirti** (Householder's Pure Land)
- **Ancestral Peace** (Reconnection with ancestors)
- **Quantum Healing** (Science-integrated sacred space)

---

## CLI Usage

### Command Reference

#### Generate Single Story

```bash
python scripts/story_generator.py --generate [OPTIONS]

Options:
  --name TEXT              Name of being (default: "Unknown Being")
  --type TEXT              Narrative type (default: "pure_land_arrival")
  --pure-land TEXT         Pure land tradition (default: "universal_light")
  --context TEXT           Additional context for story
  --use-llm                Use LLM for generation (vs templates)
  --llm-provider TEXT      LLM provider (default: "ollama")
  --output PATH            Save story to file (.md or .json)
```

**Examples**:

```bash
# Basic pure land story
python scripts/story_generator.py --generate --name "Sarah Chen"

# Hell liberation with specific context
python scripts/story_generator.py --generate \
  --name "Unknown Soldier" \
  --type hell_liberation \
  --context "Died in combat, carrying guilt over actions in war"

# Save to file
python scripts/story_generator.py --generate \
  --name "Rescue Dog #47293" \
  --type pure_land_arrival \
  --pure-land nature_paradise \
  --output ./dog_liberation.md

# Use LLM for custom generation
python scripts/story_generator.py --generate \
  --name "Jane Doe #4215" \
  --type pure_land_arrival \
  --use-llm \
  --output story.md
```

#### Batch Generation from Database

```bash
python scripts/story_generator.py --batch [OPTIONS]

Options:
  --category TEXT          Blessing category to generate for
  --count INT              Number of stories (default: 10)
  --type TEXT              Narrative type
  --pure-land TEXT         Pure land tradition
  --use-llm                Use LLM for generation
  --output PATH            Directory to save stories
```

**Examples**:

```bash
# 10 stories for missing persons
python scripts/story_generator.py --batch \
  --category missing_person \
  --count 10 \
  --output ./stories/missing_persons

# All shelter animals arrive in nature paradise
python scripts/story_generator.py --batch \
  --category shelter_animal \
  --type pure_land_arrival \
  --pure-land nature_paradise \
  --count 20 \
  --output ./stories/animals

# Empowerment stories for refugees
python scripts/story_generator.py --batch \
  --category refugee \
  --type empowerment \
  --count 15 \
  --output ./stories/refugee_empowerment
```

#### Interactive Mode

```bash
python scripts/story_generator.py --interactive
```

Guided prompts walk you through:
1. Entering being's name
2. Choosing narrative type
3. Selecting pure land (if applicable)
4. Choosing template vs LLM generation
5. Adding optional context
6. Viewing the generated story
7. Option to save

#### Information Commands

```bash
# List all available options
python scripts/story_generator.py --list-types

# Describe a specific pure land in detail
python scripts/story_generator.py --describe-pure-land sukhavati
python scripts/story_generator.py --describe-pure-land shambhala
```

---

## Python API

### Basic Usage

```python
from core.blessing_narratives import (
    StoryGenerator,
    NarrativeType,
    PureLandTradition
)

# Initialize generator (template-based)
generator = StoryGenerator(use_llm=False)

# Generate a story
story = generator.generate_story(
    target_name="Unknown Soul",
    narrative_type=NarrativeType.PURE_LAND_ARRIVAL,
    pure_land=PureLandTradition.SUKHAVATI
)

# Access story content
print(story.title)
print(story.story_text)
print(story.dedication)
```

### With Blessing Database Integration

```python
from core.blessing_narratives import StoryGenerator, NarrativeType
from core.compassionate_blessings import BlessingDatabase, BlessingCategory

# Initialize
db = BlessingDatabase()
generator = StoryGenerator()

# Get targets from database
targets = db.get_targets_by_category(BlessingCategory.MISSING_PERSON)

# Generate story for specific target
target = targets[0]
story = generator.generate_story(
    target=target,
    narrative_type=NarrativeType.PURE_LAND_ARRIVAL,
    pure_land=PureLandTradition.UNIVERSAL_LIGHT
)

# Generate batch
stories = generator.generate_batch_stories(
    targets=targets[:10],
    narrative_type=NarrativeType.EMPOWERMENT,
    max_stories=10
)
```

### Custom Context

```python
# Add specific context to personalize the story
story = generator.generate_story(
    target_name="Sarah, age 8, missing since 2020",
    narrative_type=NarrativeType.PURE_LAND_ARRIVAL,
    pure_land=PureLandTradition.NATURE_PARADISE,
    custom_context="Loved animals, especially rabbits. Went missing from a park."
)
```

### LLM-Generated Stories

```python
# Use LLM for more creative, personalized stories
generator = StoryGenerator(use_llm=True, llm_provider="ollama")

story = generator.generate_story(
    target_name="Combat Veteran with PTSD",
    narrative_type=NarrativeType.HEALING_JOURNEY,
    custom_context="Struggling with survivor's guilt and traumatic memories"
)
```

### Exporting Stories

```python
from core.blessing_narratives import StoryExporter

# Export as markdown
StoryExporter.export_as_markdown(story, "liberation_story.md")

# Export as JSON (includes metadata)
StoryExporter.export_as_json(story, "story_data.json")

# Export a collection with index
StoryExporter.export_collection(stories, "./story_collection")
```

### GeneratedStory Object

```python
# Story object attributes
story.target_name           # "Unknown Soul"
story.narrative_type        # NarrativeType.PURE_LAND_ARRIVAL
story.title                 # "Arrival in the Land of Bliss"
story.story_text            # Full narrative text (markdown)
story.pure_land             # PureLandTradition.SUKHAVATI or None
story.generation_method     # 'template' or 'llm'
story.timestamp             # datetime object
story.dedication            # Dedication prayer text
story.metadata              # Dict with additional info
```

---

## Template System

### How Templates Work

The template system uses structured components that are randomly selected and assembled:

```python
NarrativeTemplate(
    narrative_type=NarrativeType.PURE_LAND_ARRIVAL,
    title="Arrival in the Land of Bliss",
    opening=[...],        # Multiple variations
    journey=[...],        # Multiple plot points
    transformation=[...], # The moment of change
    resolution=[...],     # The outcome
    dedication=[...],     # Closing prayer
    tags=[...]
)
```

### Creating Custom Templates

```python
from core.blessing_narratives import NarrativeTemplate, NarrativeType

# Create a custom template
my_template = NarrativeTemplate(
    narrative_type=NarrativeType.HEALING_JOURNEY,
    title="Journey to Wholeness",
    opening=[
        "The pain had lasted so long...",
        "Brokenness felt like identity...",
        "Healing seemed impossible, until..."
    ],
    journey=[
        "Small steps forward, patience with setbacks.",
        "Finding helpers along the way.",
        "Discovering inner resources."
    ],
    transformation=[
        "The moment of realizing: I am healing.",
        "Wholeness emerging from brokenness."
    ],
    resolution=[
        "Now healed, helping others heal.",
        "Scars become wisdom, wounds become gifts."
    ],
    dedication=[
        "May all wounded beings find healing.",
        "May all brokenness become wholeness."
    ],
    tags=["healing", "trauma", "recovery", "wholeness"]
)
```

### Template Library

Current templates available in `NarrativeTemplateLibrary`:
- `get_pure_land_arrival_template()`
- `get_hell_liberation_template()`
- `get_empowerment_template()`
- `get_reconciliation_template()`
- `get_hungry_ghost_nourishment_template()`

---

## LLM Integration

### Enabling LLM Generation

```python
# When initializing StoryGenerator
generator = StoryGenerator(
    use_llm=True,
    llm_provider="ollama"  # or "openai", "anthropic"
)
```

### LLM vs Template: When to Use Each

**Use Templates When**:
- You want consistent, reliable output
- You're generating many stories at once
- You don't have LLM access
- You want traditional Buddhist framings
- Speed is important

**Use LLM When**:
- You want highly personalized stories
- You have specific context to incorporate
- You want creative variations
- You're generating individual stories with care
- You have LLM access and time

### LLM Prompting

The system automatically creates prompts based on:
- Narrative type selected
- Pure land tradition (if applicable)
- Custom context provided
- Target information from database

Example auto-generated prompt for pure land arrival:
```
Generate a beautiful, compassionate story of liberation and healing
for a being named 'Sarah Chen'.

This is a story of arriving in Sukhavati - The Land of Bliss.

Pure Land Description:
[Full description included]

Create a narrative that:
1. Describes the transition from suffering to this pure land
2. Includes vivid sensory details of the arrival
3. Shows the healing and transformation that occurs
4. Ends with dedication of merit for all beings

Make the story uplifting, healing, and spiritually profound.
```

---

## Example Stories

The system includes complete example stories in `knowledge/example_stories/`:

### 1. Sukhavati Arrival (`01_sukhavati_arrival.md`)

**For**: Unknown souls in the bardo
**Type**: Pure Land Arrival
**Tradition**: Sukhavati (Western Pure Land)
**Length**: ~1200 words

**Excerpt**:
> "As the final breath left the body, consciousness did not cease but transformed.
> The familiar world dissolved like mist in morning sun, and in its place - light..."

**Use**: Template for traditional Buddhist memorial services

---

### 2. Hell Liberation (`02_hell_liberation.md`)

**For**: Beings in extreme suffering states
**Type**: Hell Liberation
**Length**: ~1500 words

**Excerpt**:
> "In the deepest darkness, where suffering seemed infinite and hope a distant memory,
> a being existed in torment. But even in the deepest hell, the light of compassion reaches..."

**Use**: Tonglen practice, prayers for those who died violently, teaching about redemption

---

### 3. Empowerment Transformation (`03_empowerment_transformation.md`)

**For**: Marginalized and powerless populations
**Type**: Empowerment
**Length**: ~1800 words

**Excerpt**:
> "For generations, powerlessness had been the only reality known. But something shifted -
> a spark of recognition: 'This is not who I truly am...'"

**Use**: Social justice work, activist inspiration, envisioning collective liberation

---

### 4. Reconciliation Healing (`04_reconciliation_healing.md`)

**For**: Both victims and perpetrators of harm
**Type**: Reconciliation
**Length**: ~2000 words

**Excerpt**:
> "Two beings, bound by karma - one who harmed and one who was harmed. The wound between
> them seemed absolute. But in a space beyond ordinary time, healing became possible..."

**Use**: Restorative justice programs, trauma therapy, teaching complex forgiveness

---

## Integration with Blessing Database

### Workflow: From Database Target to Story

```python
from core.compassionate_blessings import BlessingDatabase, BlessingCategory
from core.blessing_narratives import StoryGenerator, NarrativeType, PureLandTradition

# 1. Load database
db = BlessingDatabase()

# 2. Get specific targets
missing_persons = db.get_targets_by_category(BlessingCategory.MISSING_PERSON)

# 3. Initialize story generator
generator = StoryGenerator()

# 4. Generate stories for each target
stories = []
for target in missing_persons[:5]:
    story = generator.generate_story(
        target=target,
        narrative_type=NarrativeType.PURE_LAND_ARRIVAL,
        pure_land=PureLandTradition.UNIVERSAL_LIGHT
    )
    stories.append(story)

    # Optionally update database that story was created
    # (Future enhancement: add story_id to target metadata)

# 5. Export collection
from core.blessing_narratives import StoryExporter
StoryExporter.export_collection(stories, "./missing_persons_stories")
```

### Using Categories to Determine Narrative Type

```python
# Map categories to appropriate narrative types
category_to_narrative = {
    BlessingCategory.DECEASED: NarrativeType.PURE_LAND_ARRIVAL,
    BlessingCategory.HUNGRY_GHOST: NarrativeType.HUNGRY_GHOST_NOURISHMENT,
    BlessingCategory.HOMELESS: NarrativeType.EMPOWERMENT,
    BlessingCategory.REFUGEE: NarrativeType.EMPOWERMENT,
    BlessingCategory.INCARCERATED: NarrativeType.RECONCILIATION,
}

# Generate appropriate story based on category
target = db.get_target("some-identifier")
narrative_type = category_to_narrative.get(
    target.category,
    NarrativeType.PURE_LAND_ARRIVAL  # default
)

story = generator.generate_story(
    target=target,
    narrative_type=narrative_type
)
```

---

## Ethical Considerations

### Respect for Real Suffering

**Critical Principle**: These stories are spiritual practices, not replacements for action.

**DO**:
- Use stories to inspire compassionate action
- Generate stories as meditation/visualization aids
- Share stories to teach spiritual principles
- Create stories as offerings for beings

**DON'T**:
- Use stories to bypass accountability
- Share stories publicly without consent (for real individuals)
- Claim stories are "true" in literal sense
- Use stories to minimize real suffering

### Consent and Privacy

**For Specific Individuals**:
- Only create stories for deceased persons with family consent
- Use general descriptions rather than full names publicly
- Honor cultural and religious traditions of the deceased
- Check with families before sharing stories

**For Groups/Categories**:
- Stories for "Missing Children Worldwide" - appropriate
- Stories for "John Smith, missing from Boston" - requires consent
- General populations - fine for practice purposes
- Named individuals - requires permission

### Cultural Sensitivity

**Pure Land Traditions**:
- Respect that these are living religious traditions
- Don't appropriate without understanding
- Honor the source teachings
- Offer alternatives for non-Buddhist contexts

**Hell Realms**:
- Different from Christian eternal damnation
- Temporary states, not permanent punishment
- Karmic consequence, not divine judgment
- Emphasize possibility of liberation

**Indigenous Traditions**:
- The "Land Spirits" category honors indigenous cosmology
- Use with respect and humility
- Acknowledge we're not indigenous authorities
- Invite indigenous practitioners to add authentic content

### Restorative Justice Framework

**For Reconciliation Stories**:

Critical guidelines:
1. **Never pressure victims to forgive**
2. **Maintain clear accountability**
3. **Honor boundaries absolutely**
4. **Transformation ≠ Absolution**
5. **Forgiveness is personal choice**

These stories should:
- Support restorative justice, not replace it
- Envision possibility without demanding it
- Hold complexity, not offer simplistic solutions
- Empower survivors, not protect perpetrators

---

## Advanced Usage

### Custom Pure Land Descriptions

```python
from core.blessing_narratives import PureLandDescriptions, PureLandTradition

# Add a custom pure land
PureLandDescriptions.DESCRIPTIONS[PureLandTradition.CUSTOM] = {
    "name": "My Custom Pure Land",
    "description": "...",
    "activities": [...],
    "sensory": {
        "sight": "...",
        "sound": "...",
        # etc.
    }
}
```

### Combining with Radionics Broadcasting

```python
from scripts.radionics_operation import RadionicsOperator
from core.blessing_narratives import StoryGenerator, NarrativeType

# Generate story
generator = StoryGenerator()
story = generator.generate_story(
    target_name="Suffering Being",
    narrative_type=NarrativeType.HELL_LIBERATION
)

# Use story text as intention for radionics broadcast
operator = RadionicsOperator()
operator.broadcast_to_target(
    target_description="Hell Realm Beings",
    intention=story.dedication,  # or story.story_text
    duration=3600
)
```

### Daily Practice Integration

**Morning Practice**:
```bash
# Generate a daily inspiration story
python scripts/story_generator.py --generate \
  --name "All Beings Today" \
  --type empowerment \
  --output ~/daily_practice/$(date +%Y-%m-%d).md
```

**Memorial Services**:
```python
# Generate personalized story for memorial
story = generator.generate_story(
    target_name=deceased_name,
    narrative_type=NarrativeType.PURE_LAND_ARRIVAL,
    pure_land=PureLandTradition.UNIVERSAL_LIGHT,
    custom_context=f"Loved ones include: {family_names}. Hobbies: {hobbies}."
)

# Read at service or include in memorial booklet
```

**Meditation Object**:
```python
# Generate story, then use it for meditation
story = generator.generate_story(
    target_name="All Hungry Ghosts",
    narrative_type=NarrativeType.HUNGRY_GHOST_NOURISHMENT
)

# Read story slowly
# Visualize each scene
# Feel the liberation occurring
# Dedicate merit at the end
```

### Batch Processing Large Populations

```python
from core.compassionate_blessings import BlessingDatabase, BlessingCategory
from core.blessing_narratives import StoryGenerator, NarrativeType

db = BlessingDatabase()
generator = StoryGenerator()

# Get all categories
categories = [
    BlessingCategory.MISSING_PERSON,
    BlessingCategory.HOMELESS,
    BlessingCategory.REFUGEE,
    BlessingCategory.SHELTER_ANIMAL,
]

# Generate stories for each category
for category in categories:
    targets = db.get_targets_by_category(category)

    # Generate up to 10 stories per category
    stories = generator.generate_batch_stories(
        targets=targets,
        narrative_type=NarrativeType.PURE_LAND_ARRIVAL,
        max_stories=10
    )

    # Export
    from pathlib import Path
    output_dir = Path(f"./stories/{category.value}")
    StoryExporter.export_collection(stories, str(output_dir))

    print(f"Generated {len(stories)} stories for {category.value}")
```

---

## API Reference

### Core Classes

#### `StoryGenerator`

Main class for generating stories.

```python
class StoryGenerator:
    def __init__(self, use_llm: bool = False, llm_provider: str = "ollama")

    def generate_story(
        self,
        target: Optional[BlessingTarget] = None,
        target_name: str = "Unknown Being",
        narrative_type: NarrativeType = NarrativeType.PURE_LAND_ARRIVAL,
        pure_land: PureLandTradition = PureLandTradition.UNIVERSAL_LIGHT,
        custom_context: str = ""
    ) -> GeneratedStory

    def generate_batch_stories(
        self,
        targets: List[BlessingTarget],
        narrative_type: NarrativeType = NarrativeType.PURE_LAND_ARRIVAL,
        pure_land: PureLandTradition = PureLandTradition.UNIVERSAL_LIGHT,
        max_stories: int = 10
    ) -> List[GeneratedStory]
```

#### `GeneratedStory`

Dataclass containing a complete story.

```python
@dataclass
class GeneratedStory:
    target_name: str
    narrative_type: NarrativeType
    title: str
    story_text: str
    pure_land: Optional[PureLandTradition]
    generation_method: str  # 'template' or 'llm'
    timestamp: datetime
    dedication: str
    metadata: Dict
```

#### `StoryExporter`

Static methods for exporting stories.

```python
class StoryExporter:
    @staticmethod
    def export_as_markdown(story: GeneratedStory, filepath: str)

    @staticmethod
    def export_as_json(story: GeneratedStory, filepath: str)

    @staticmethod
    def export_collection(stories: List[GeneratedStory], directory: str)
```

#### `PureLandDescriptions`

Class containing detailed pure land descriptions.

```python
class PureLandDescriptions:
    DESCRIPTIONS: Dict[PureLandTradition, Dict]

    @classmethod
    def get_description(cls, tradition: PureLandTradition) -> Dict
```

### Enums

#### `NarrativeType`

```python
class NarrativeType(Enum):
    PURE_LAND_ARRIVAL = "pure_land_arrival"
    HELL_LIBERATION = "hell_liberation"
    HUNGRY_GHOST_NOURISHMENT = "hungry_ghost_nourishment"
    EMPOWERMENT = "empowerment"
    RECONCILIATION = "reconciliation"
    HEALING_JOURNEY = "healing_journey"
    ALTERNATE_TIMELINE = "alternate_timeline"
    DIVINE_INTERVENTION = "divine_intervention"
    SELF_REALIZATION = "self_realization"
    COLLECTIVE_AWAKENING = "collective_awakening"
```

#### `PureLandTradition`

```python
class PureLandTradition(Enum):
    SUKHAVATI = "sukhavati"
    ABHIRATI = "abhirati"
    SHAMBHALA = "shambhala"
    TUSHITA = "tushita"
    POTALA = "potala"
    VIMALAKIRTI = "vimalakirti"
    UNIVERSAL_LIGHT = "universal_light"
    NATURE_PARADISE = "nature_paradise"
    ANCESTRAL_PEACE = "ancestral_peace"
    QUANTUM_HEALING = "quantum_healing"
```

---

## Dedication

May these stories benefit all beings.

May those who read them find hope.
May those who generate them deepen compassion.
May those who are visualized in them find actual liberation.

May the merit of this work be dedicated to:
- All beings in the six realms
- All who suffer and seek liberation
- All who work for collective awakening
- All teachers who have kept these traditions alive

Gate gate pāragate pārasaṃgate bodhi svāhā

---

**Version**: 1.0.0
**Last Updated**: 2025-11-15
**Maintainer**: Vajra Stream Project
**License**: For the benefit of all beings
