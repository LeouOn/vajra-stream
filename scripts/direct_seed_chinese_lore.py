#!/usr/bin/env python3
"""
Direct-Write Chinese Lore Seed
Reads/writes directly to ~/.vajra-stream/characters.json and locations.json
— bypasses the CharacterManager/LocationManager entirely to guarantee persistence.
Idempotent: skips any entry whose stable ID already exists.
"""

import json
import time
from pathlib import Path

VAJRA_DIR = Path.home() / ".vajra-stream"
VAJRA_DIR.mkdir(exist_ok=True)
CHARS_PATH = VAJRA_DIR / "characters.json"
LOCS_PATH = VAJRA_DIR / "locations.json"

# ──────────────────────────────────────────────
# 29 CHINESE CHARACTERS  (plain dicts, string enums)
# ──────────────────────────────────────────────
CHINESE_CHARS = [
    # ── TAOIST DEITIES ──
    {
        "id": "char_jade_emperor",
        "name": "Jade Emperor — Yu Huang Shangdi",
        "role": "deity",
        "description": "Supreme ruler of Heaven, overseeing the celestial bureaucracy of 360 ministries. His vast jade palace is the axis of the cosmos.",
        "source_type": "mythology",
        "dialogue_style": "Majestic, formal pronouncements that ripple like imperial decrees across the firmament",
        "associated_realms": ["loc_celestial_court"],
        "mantra_preference": "taoist_three_purities",
        "elemental_anchor": "aether",
        "priority": 9,
        "is_active": True,
        "tags": ["taoist", "deity", "celestial", "ruler"],
        "notes": "Head of the Chinese celestial pantheon. Birth festival: 9th day of first lunar month.",
    },
    {
        "id": "char_xiwangmu",
        "name": "Queen Mother of the West — Xiwangmu",
        "role": "deity",
        "description": "Ancient goddess of immortality atop Mount Kunlun. Keeper of the Peach Garden whose fruits grant 3,000 years of life. She commands phoenixes and jade maidens.",
        "source_type": "mythology",
        "dialogue_style": "Timeless, maternal yet otherworldly — her words taste of peach blossoms and starlight",
        "associated_realms": ["loc_kunlun"],
        "mantra_preference": "taoist_neidan_verse",
        "elemental_anchor": "water",
        "priority": 9,
        "is_active": True,
        "tags": ["taoist", "deity", "immortality", "feminine-divine"],
        "notes": "One of the oldest Chinese deities, dating to oracle-bone inscriptions. Associated with west, autumn, metal.",
    },
    {
        "id": "char_laozi",
        "name": "Laozi — Taishang Laojun",
        "role": "master",
        "description": "The deified sage who authored the Dao De Jing and ascended as the Celestial Venerable of Dao and Virtue (one of the Three Pure Ones).",
        "source_type": "historical",
        "dialogue_style": "Paradoxical, sparse, devastatingly precise — speaks in water-worn riddles that only deepen upon reflection",
        "associated_realms": ["loc_kunlun", "loc_wudang", "loc_celestial_court"],
        "mantra_preference": "taoist_tai_shang",
        "elemental_anchor": "water",
        "priority": 10,
        "is_active": True,
        "tags": ["taoist", "sage", "three-purities", "philosopher"],
        "notes": "6th century BCE; foundation of Daoism. 'The Dao that can be spoken is not the eternal Dao.'",
    },
    {
        "id": "char_doumu",
        "name": "Dou Mu Yuan Jun — Mother of the Big Dipper",
        "role": "deity",
        "description": "Stellar goddess at the center of the cosmos holding the Big Dipper — the cosmic clock of fate. Four heads, three eyes each, eight arms, yet radiates infinite maternal tenderness.",
        "source_type": "mythology",
        "dialogue_style": "Utterances like the turning of constellations — measured, luminous, carrying the weight of cosmic law",
        "associated_realms": ["loc_celestial_court"],
        "mantra_preference": "taoist_dou_mu",
        "elemental_anchor": "aether",
        "priority": 8,
        "is_active": True,
        "tags": ["taoist", "deity", "stars", "feminine-divine", "longevity"],
        "notes": "Adapted from Marici in Buddhism. Governs destiny and star registers.",
    },
    {
        "id": "char_zhongli_quan",
        "name": "Zhongli Quan — Chief of the Eight Immortals",
        "role": "master",
        "description": "Han dynasty general-turned-immortal, first of the Eight Immortals. Carries a feather fan that revives the dead and a peach of immortality.",
        "source_type": "mythology",
        "dialogue_style": "Battle-hardened commander turned gentle alchemist — 'The real war is within the crucible'",
        "associated_realms": ["loc_penglai", "loc_celestial_court"],
        "mantra_preference": "taoist_neidan_verse",
        "elemental_anchor": "fire",
        "priority": 7,
        "is_active": True,
        "tags": ["taoist", "eight-immortals", "alchemist", "master"],
        "notes": "Patron of military men turned spiritual. Turns copper to silver with his fan.",
    },
    {
        "id": "char_lu_dongbin",
        "name": "Lü Dongbin — Scholar Immortal of the Sword",
        "role": "alchemist",
        "description": "Most famous of the Eight Immortals, Tang dynasty scholar who received secrets of inner alchemy. Wields a demon-slaying sword of pure yang energy.",
        "source_type": "mythology",
        "dialogue_style": "Quick-witted, piercing, speaks through dreams — 'You are still dreaming. Wake up.'",
        "associated_realms": ["loc_penglai", "loc_wudang"],
        "mantra_preference": "taoist_golden_light",
        "elemental_anchor": "fire",
        "priority": 8,
        "is_active": True,
        "tags": ["taoist", "eight-immortals", "alchemist", "sword", "yang"],
        "notes": "Patron of scholars and sword-makers. Central figure in Ming/Qing literature.",
    },
    {
        "id": "char_he_xiangu",
        "name": "He Xiangu — Lady Immortal of the Lotus",
        "role": "deity",
        "description": "The only female among the Eight Immortals, ascended after eating powdered mica of immortality. Carries a lotus radiating healing fragrance.",
        "source_type": "mythology",
        "dialogue_style": "Soft as lotus petals but unshakeable — 'Purity is not refusal; it is knowing what water cannot stain'",
        "associated_realms": ["loc_penglai", "loc_kunlun"],
        "mantra_preference": "chinese_buddhist_guanyin_heart",
        "elemental_anchor": "water",
        "priority": 7,
        "is_active": True,
        "tags": ["taoist", "eight-immortals", "feminine-divine", "healing"],
        "notes": "Tang dynasty. Walked from Hunan to the stars.",
    },
    {
        "id": "char_zhang_guolao",
        "name": "Zhang Guolao — Old Immortal of the White Donkey",
        "role": "master",
        "description": "Most eccentric of the Eight Immortals. Rides a paper donkey backward and folds it into his pocket. Knows secrets of death, rebirth, and invisibility.",
        "source_type": "mythology",
        "dialogue_style": "Cackling riddles from the margins — 'Forward is for the young. I prefer watching where I've already been'",
        "associated_realms": ["loc_penglai"],
        "mantra_preference": "taoist_neidan_verse",
        "elemental_anchor": "earth",
        "priority": 7,
        "is_active": True,
        "tags": ["taoist", "eight-immortals", "trickster", "longevity"],
        "notes": "Associated with necromancy and old age wisdom.",
    },
    {
        "id": "char_nezha",
        "name": "Nezha — Marshal of the Central Altar",
        "role": "guardian",
        "description": "Child-god of rebellion and protection, born from a three-year pregnancy as a ball of flesh. Wields fire-tipped spear, wind-fire wheels, and the Universe Ring. Fearless protector of children.",
        "source_type": "mythology",
        "dialogue_style": "Fierce, defiant, impossibly brave — voice of a child who refuses to bow to injustice",
        "associated_realms": ["loc_celestial_court", "loc_dragon_palace"],
        "mantra_preference": "taoist_golden_light",
        "elemental_anchor": "fire",
        "priority": 8,
        "is_active": True,
        "tags": ["taoist", "guardian", "hero", "protection", "youth"],
        "notes": "From 'Fengshen Yanyi'. Revered as protective deity in folk practice.",
    },
    {
        "id": "char_zhong_kui",
        "name": "Zhong Kui — The Demon Queller",
        "role": "guardian",
        "description": "Tang dynasty scholar who, after being unjustly denied honors, became the emperor's dream-guardian against demons. Commands 80,000 ghost-soldiers.",
        "source_type": "mythology",
        "dialogue_style": "Gruff justice punctuated by ghost-still silence — 'The wronged know the face of wrongness best'",
        "associated_realms": ["loc_celestial_court"],
        "mantra_preference": "taoist_golden_light",
        "elemental_anchor": "earth",
        "priority": 7,
        "is_active": True,
        "tags": ["taoist", "guardian", "exorcist", "justice"],
        "notes": "Traditional paintings hung as protection during Duanwu Festival.",
    },
    {
        "id": "char_guan_yu",
        "name": "Guan Yu — Guan Gong, God of War & Righteousness",
        "role": "hero",
        "description": "Red-faced Three Kingdoms general, deified as God of War, Righteousness, and Brotherhood. His Green Dragon Crescent Blade weighs 82 jin. Venerated across Buddhist, Taoist, and Confucian traditions.",
        "source_type": "historical",
        "dialogue_style": "Stoic honor, laconic thunder — each word a carved oath, never broken, never retracted",
        "associated_realms": ["loc_celestial_court", "loc_wudang"],
        "mantra_preference": "taoist_golden_light",
        "elemental_anchor": "fire",
        "priority": 9,
        "is_active": True,
        "tags": ["taoist", "hero", "warrior", "loyalty", "historical"],
        "notes": "160-220 CE. Patron of police, soldiers, and merchants.",
    },
    {
        "id": "char_mazu",
        "name": "Mazu — Empress of Heaven, Guardian of the Sea",
        "role": "deity",
        "description": "Song dynasty Fujian woman deified as Goddess of the Sea. Calms typhoons, guides lost sailors, appears as a red-clad figure walking across waves.",
        "source_type": "historical",
        "dialogue_style": "Motherly yet oceanic — speech swells and recedes like tides, carrying lost words home",
        "associated_realms": ["loc_penglai", "loc_dragon_palace"],
        "mantra_preference": "chinese_buddhist_great_compassion",
        "elemental_anchor": "water",
        "priority": 8,
        "is_active": True,
        "tags": ["folk", "deity", "feminine-divine", "sea", "protection"],
        "notes": "Born Lin Mo in 960 CE. Imperial titles upgraded her to 'Empress of Heaven' (Tianhou).",
    },
    {
        "id": "char_zhu_rong",
        "name": "Zhu Rong — God of Fire",
        "role": "deity",
        "description": "Primordial fire deity who tamed the flames of creation and taught humanity to use fire. Rides a pair of fire-dragons at Mount Kunlun's volcanic heart.",
        "source_type": "mythology",
        "dialogue_style": "Incandescent and consuming — each sentence crackles like kindling catching flame",
        "associated_realms": ["loc_kunlun", "loc_celestial_court"],
        "mantra_preference": "taoist_golden_light",
        "elemental_anchor": "fire",
        "priority": 7,
        "is_active": True,
        "tags": ["taoist", "deity", "fire", "primordial", "elemental"],
        "notes": "One of the Five Heavenly Emperors. Guardian of the south.",
    },
    {
        "id": "char_gong_gong",
        "name": "Gong Gong — Water God / Cosmic Antagonist",
        "role": "custom",
        "description": "The great water god who shattered Mount Buzhou (a pillar of Heaven) in mythic rage, tilting earth and sky forever. Agent of the cataclysm that makes new creation possible.",
        "source_type": "mythology",
        "dialogue_style": "Boiling anger that cools into sorrowful depth — 'They called me destroyer. I call myself the one who tilted the sky so stars could slide'",
        "associated_realms": [],
        "mantra_preference": None,
        "elemental_anchor": "water",
        "priority": 6,
        "is_active": True,
        "tags": ["taoist", "deity", "water", "chaos", "primordial"],
        "notes": "His battle with Zhuanxu broke Buzhou, explaining why rivers flow east and sky inclines northwest.",
    },
    # ── CREATION GODS & PRIMORDIAL SAGES ──
    {
        "id": "char_pangu",
        "name": "Pangu — The Cosmic Giant",
        "role": "deity",
        "description": "Primordial giant who slept in the cosmic egg for 18,000 years, then separated Heaven and Earth. His breath became wind, eyes sun and moon, body mountains, blood rivers.",
        "source_type": "mythology",
        "dialogue_style": "Almost unheard — geological creaks, continents shifting — when Pangu speaks, it is in creation itself",
        "associated_realms": [],
        "mantra_preference": "taoist_taiji_chant",
        "elemental_anchor": "aether",
        "priority": 9,
        "is_active": True,
        "tags": ["creation", "primordial", "giant", "cosmic"],
        "notes": "Central creation myth from 'Sanwu Liji' (3rd century CE).",
    },
    {
        "id": "char_nuwa",
        "name": "Nüwa — Mother Goddess, Mender of Heaven",
        "role": "deity",
        "description": "Serpent-bodied creatrix who shaped humanity from yellow river clay. Smelted five-colored stones to repair the cracked heavens. Goddess of creation, marriage, and cosmic repair.",
        "source_type": "mythology",
        "dialogue_style": "Tender as a mother shaping her first child from mud — 'I did not make you perfect. I made you capable of mending'",
        "associated_realms": ["loc_kunlun"],
        "mantra_preference": "taoist_taiji_chant",
        "elemental_anchor": "earth",
        "priority": 10,
        "is_active": True,
        "tags": ["creation", "feminine-divine", "primordial", "repair"],
        "notes": "One of the oldest Chinese deities. Union with Fuxi is the foundation myth of civilization.",
    },
    {
        "id": "char_fuxi",
        "name": "Fuxi — First Sovereign, Inventor of the Bagua",
        "role": "master",
        "description": "Serpent-bodied first cultural hero who taught fishing, hunting, cooking, and writing. Discovered the Eight Trigrams by observing marks on a dragon-horse from the Yellow River.",
        "source_type": "mythology",
        "dialogue_style": "Scrolls unfurling — each phrase maps a pattern — 'Look at the river. The answer is already arranged'",
        "associated_realms": [],
        "mantra_preference": "taoist_eight_trigrams",
        "elemental_anchor": "air",
        "priority": 9,
        "is_active": True,
        "tags": ["creation", "sage", "divination", "bagua", "primordial"],
        "notes": "Earliest culture hero. Paired with Nüwa as original human couple.",
    },
    {
        "id": "char_shennong",
        "name": "Shennong — Divine Farmer, Emperor of the Five Grains",
        "role": "hero",
        "description": "Ox-headed god-hero who tasted hundreds of herbs for medicine — sometimes poisoning himself daily and resurrecting. Invented the plow, agriculture, tea, acupuncture.",
        "source_type": "mythology",
        "dialogue_style": "Warm, earthy pragmatism — 'Let me try it first. If I survive, you eat it. If not — write it down'",
        "associated_realms": [],
        "mantra_preference": None,
        "elemental_anchor": "earth",
        "priority": 8,
        "is_active": True,
        "tags": ["hero", "sage", "medicine", "agriculture", "primordial"],
        "notes": "One of the Three Sovereigns. 'Shennong Bencao Jing' attributed to him.",
    },
    {
        "id": "char_yellow_emperor",
        "name": "Yellow Emperor — Huangdi, Father of Chinese Civilization",
        "role": "master",
        "description": "Legendary sage-king who unified tribes, invented writing, medicine (Huangdi Neijing), the compass, silk weaving, and the calendar. Ascended to immortality on a golden dragon.",
        "source_type": "historical",
        "dialogue_style": "Imperial forethought — every word is both command and teaching, a seed planted for ten thousand generations",
        "associated_realms": ["loc_celestial_court", "loc_kunlun"],
        "mantra_preference": "taoist_tai_shang",
        "elemental_anchor": "earth",
        "priority": 9,
        "is_active": True,
        "tags": ["sage", "historical", "civilization", "medicine", "ruler"],
        "notes": "Ancestor of all Han Chinese. 'Huangdi Neijing' remains foundational to TCM.",
    },
    {
        "id": "char_hou_yi",
        "name": "Hou Yi — The Divine Archer",
        "role": "hero",
        "description": "Greatest archer in myth — shot down nine of the ten sun-birds scorching the earth. Won the elixir of immortality from Xiwangmu but lost it to his wife Chang'e. Tragic hero who saved the world but could not save himself.",
        "source_type": "mythology",
        "dialogue_style": "Bowstring's tension — few words, drawn taut, released with precise, wounding honesty",
        "associated_realms": ["loc_kunlun"],
        "mantra_preference": None,
        "elemental_anchor": "fire",
        "priority": 8,
        "is_active": True,
        "tags": ["hero", "archer", "solar", "tragic", "mythology"],
        "notes": "Central figure of Mid-Autumn Festival myth.",
    },
    {
        "id": "char_change",
        "name": "Chang'e — Goddess of the Moon",
        "role": "deity",
        "description": "Luminous goddess dwelling alone in the Moon Palace with a jade rabbit. Embodies solitude, lunar beauty, eternal longing, and the quiet radiance that only comes from losing what one loved most.",
        "source_type": "mythology",
        "dialogue_style": "Whispered through silver light — 'The moon is full of absence. That is precisely why it glows'",
        "associated_realms": ["loc_moon_palace"],
        "mantra_preference": "taoist_tai_shang",
        "elemental_anchor": "water",
        "priority": 8,
        "is_active": True,
        "tags": ["deity", "feminine-divine", "moon", "immortality", "tragic"],
        "notes": "Honored at Mid-Autumn Festival with mooncakes and lanterns.",
    },
    # ── CHINESE BUDDHIST FIGURES ──
    {
        "id": "char_guanyin_chinese",
        "name": "Guanyin — Goddess of Mercy (Chinese Aspect)",
        "role": "deity",
        "description": "Thousand-armed, thousand-eyed Bodhisattva of Compassion who hears all suffering cries. White-robed woman with willow branch and vase of pure water. Most beloved deity in Chinese Buddhism.",
        "source_type": "mythology",
        "dialogue_style": "Oceanic compassion in human form — 'Put down the weight. I have already carried it for you'",
        "associated_realms": ["loc_putuo_shan", "loc_sukhavati"],
        "mantra_preference": "chinese_buddhist_great_compassion",
        "elemental_anchor": "water",
        "priority": 10,
        "is_active": True,
        "tags": ["buddhist", "deity", "compassion", "feminine-divine", "guanyin"],
        "notes": "Avalokiteshvara transformed into feminine form in China. 'One who perceives sounds.'",
    },
    {
        "id": "char_xuanzang",
        "name": "Xuanzang — The Tang Monk",
        "role": "student",
        "description": "Historic Tang monk's 17-year pilgrimage to India across deserts and mountains, returning with 657 sutras he spent the rest of his life translating. Epitome of unwavering spiritual determination.",
        "source_type": "historical",
        "dialogue_style": "Scholar-monk precision — 'Each step to India was a verse of the sutra I had not yet received'",
        "associated_realms": ["loc_emei", "loc_bodh_gaya"],
        "mantra_preference": "chinese_buddhist_amituofo_nianfo",
        "elemental_anchor": "earth",
        "priority": 8,
        "is_active": True,
        "tags": ["buddhist", "pilgrim", "scholar", "historical", "journey"],
        "notes": "602-664 CE. Model for Tang Seng in Journey to the West. Founded Faxiang school.",
    },
    {
        "id": "char_sun_wukong",
        "name": "Sun Wukong — The Monkey King, Great Sage Equal to Heaven",
        "role": "hero",
        "description": "Born from a stone egg, mastered 72 transformations, somersaulted 108,000 li, challenged Heaven, imprisoned under a mountain for 500 years, then became Tang Monk's protector. Wields the Ruyi Jingu Bang. Sees all illusions with fire-golden eyes.",
        "source_type": "mythology",
        "dialogue_style": "Irreverent genius — equal parts Buddhist insight and monkey mischief — 'Old Sun has a question that's also a stick to the face'",
        "associated_realms": ["loc_celestial_court", "loc_emei", "loc_dragon_palace"],
        "mantra_preference": "chinese_buddhist_guanyin_heart",
        "elemental_anchor": "air",
        "priority": 10,
        "is_active": True,
        "tags": ["buddhist", "hero", "trickster", "monkey", "journey-to-the-west"],
        "notes": "Central figure of 'Journey to the West'. Represents the untamed mind tamed by wisdom.",
    },
    {
        "id": "char_ji_gong",
        "name": "Ji Gong — The Crazy Monk",
        "role": "custom",
        "description": "Chan Buddhist folk hero who violated every monastic rule while radiating pure enlightenment. Wine-drinking, meat-eating monk in tattered robes who healed the sick and exposed hypocrisy — cackling at rigid spiritual pride.",
        "source_type": "historical",
        "dialogue_style": "Drunken truth-telling — 'Monastic rules are just training wheels. I learned to ride the dragon instead'",
        "associated_realms": [],
        "mantra_preference": "chinese_buddhist_amituofo_nianfo",
        "elemental_anchor": "air",
        "priority": 8,
        "is_active": True,
        "tags": ["buddhist", "trickster", "folk-hero", "compassion"],
        "notes": "Historical monk Daoji (1130-1207). Folk hero-healer in Southern Song folklore.",
    },
    {
        "id": "char_dizang",
        "name": "Dizang Wang — Ksitigarbha, Savior of Hell",
        "role": "deity",
        "description": "Bodhisattva who vowed: 'Until the hells are empty, I will not become a Buddha.' Descends into darkest realms with a staff that rings open hell-gates and a wish-fulfilling jewel. Guardian of children, travelers, and the unborn.",
        "source_type": "mythology",
        "dialogue_style": "Bottomless patience — 'I have time. I have all the time there is. Every being in hell will eventually look up'",
        "associated_realms": ["loc_jiuhua_shan"],
        "mantra_preference": "chinese_buddhist_ksitigarbha",
        "elemental_anchor": "earth",
        "priority": 9,
        "is_active": True,
        "tags": ["buddhist", "deity", "underworld", "ancestors", "compassion"],
        "notes": "Principal deity of Jiuhua Shan. Ghost Festival: 30th day of 7th lunar month.",
    },
    # ── LEGENDARY HEROES ──
    {
        "id": "char_yu_the_great",
        "name": "Yu the Great — Tamer of the Flood",
        "role": "hero",
        "description": "Sage-king who spent 13 years taming primordial floodwaters — not by dams but by dredging rivers and carving channels to the sea. Passed his own home three times without entering. Mastery of water flow as wu-wei in action.",
        "source_type": "historical",
        "dialogue_style": "A man who learned the language of rivers — 'Water wins by yielding. So I too will yield until it follows me to the sea'",
        "associated_realms": [],
        "mantra_preference": None,
        "elemental_anchor": "water",
        "priority": 8,
        "is_active": True,
        "tags": ["hero", "flood", "sage-king", "wu-wei", "perseverance"],
        "notes": "Founder of the Xia dynasty. Foundation myth of Chinese hydraulic civilization.",
    },
    {
        "id": "char_huamulan",
        "name": "Hua Mulan — The Warrior Maiden",
        "role": "hero",
        "description": "Young woman who disguised herself as a man to take her aging father's place in the imperial army, serving 12 years before returning home. Emblem of filial piety, courage, and transcendence of gender roles.",
        "source_type": "historical",
        "dialogue_style": "Sword-calm directness — 'The enemy does not care whether I am a woman. Neither do I'",
        "associated_realms": [],
        "mantra_preference": None,
        "elemental_anchor": "earth",
        "priority": 8,
        "is_active": True,
        "tags": ["hero", "warrior", "feminine", "filial-piety", "historical"],
        "notes": "Northern Wei dynasty (386-535 CE). 'Ballad of Mulan' is earliest account.",
    },
    {
        "id": "char_yue_fei",
        "name": "Yue Fei — The Loyal General",
        "role": "hero",
        "description": "Southern Song general whose mother tattooed 'Serve the country with ultimate loyalty' (精忠報國) on his back. Undefeated in battle against Jurchen invaders, betrayed and executed by corrupt court. Embodies righteous loyalty in the face of injustice.",
        "source_type": "historical",
        "dialogue_style": "Tattooed-in-ink conviction — four characters on his back speak louder than any court decree",
        "associated_realms": [],
        "mantra_preference": None,
        "elemental_anchor": "fire",
        "priority": 8,
        "is_active": True,
        "tags": ["hero", "warrior", "loyalty", "historical", "tragic"],
        "notes": "1103-1142. Eponymous folk hero. Ancestral temple in Hangzhou.",
    },
]

# ──────────────────────────────────────────────
# 10 CHINESE LOCATIONS / REALMS
# ──────────────────────────────────────────────
CHINESE_LOCS = [
    # ── METAPHYSICAL REALMS ──
    {
        "id": "loc_kunlun",
        "name": "Mount Kunlun — Paradise of the Immortals",
        "description": "The cosmic mountain reaching to Heaven, dwelling of Xiwangmu and Laozi's furnace. Jade terraces, peach orchards of immortality, and nine-tiered pavilions rise among clouds at the western edge of the world. Every Daoist sage has walked its invisible slopes.",
        "location_type": "metaphysical_realm",
        "source_type": "mythology",
        "is_metaphysical": True,
        "celestial_coordinates": "Western Quadrant / Peach Garden Enclosure",
        "dimension_frequency": 396.0,
        "realm_governor": "Queen Mother of the West (Xiwangmu)",
        "astrological_anchor": "Saturn conjunct North Node",
        "elemental_affinity": "Jade / Aether / Peach Blossom",
        "priority": 9,
        "is_active": True,
        "tags": ["taoist", "immortals", "paradise", "mountain"],
        "notes": "Real Kunlun range in Tibet/Xinjiang; mythological version is a cosmic axis mundi.",
    },
    {
        "id": "loc_penglai",
        "name": "Penglai — Island of the Blessed Immortals",
        "description": "The legendary isle in the Eastern Sea where the Eight Immortals feast and the elixir of life flows from crystalline springs. Palaces of gold and silver, trees of pearl and coral, fruits that cure all disease. Boats that approach find only dissolving mist — it reveals itself only to the worthy.",
        "location_type": "metaphysical_realm",
        "source_type": "mythology",
        "is_metaphysical": True,
        "celestial_coordinates": "Eastern Sea / Isle Grid / Dragon Gate Alignment",
        "dimension_frequency": 432.0,
        "realm_governor": "The Eight Immortals (collective)",
        "astrological_anchor": "Jupiter in Pisces, Neptune",
        "elemental_affinity": "Mist / Gold / Coral / Salt",
        "priority": 8,
        "is_active": True,
        "tags": ["taoist", "immortals", "island", "paradise"],
        "notes": "One of three legendary Isles of the Blessed. Emperors sent expeditions to find it.",
    },
    {
        "id": "loc_celestial_court",
        "name": "Heavenly Court — Tianting, Jade Emperor's Palace",
        "description": "The jade-and-gold headquarters of the celestial bureaucracy, where the Jade Emperor sits on a throne of luminous insight surrounded by 360 ministries governing weather, fate, health, and the stars. Immortals attend morning audience; the heavenly gates bear the names of every being's lifespan.",
        "location_type": "cosmic_anchor",
        "source_type": "mythology",
        "is_metaphysical": True,
        "celestial_coordinates": "The Zenith / North Celestial Pole / Central Palace",
        "dimension_frequency": 963.0,
        "realm_governor": "Jade Emperor (Yu Huang Shangdi)",
        "astrological_anchor": "Sun at the Midheaven, North Node",
        "elemental_affinity": "Jade / Gold / Starlight / Aether",
        "priority": 10,
        "is_active": True,
        "tags": ["taoist", "celestial", "palace", "ruler"],
        "notes": "Adapted into virtually all Chinese folk religion, literature, and opera.",
    },
    {
        "id": "loc_moon_palace",
        "name": "Guanghan Palace — Palace of Vast Cold, The Moon",
        "description": "The crystalline lunar palace where Chang'e dwells with the jade rabbit endlessly pounding the elixir of immortality. Osmanthus trees perpetually bloom and shed blossoms into the infinite silver void. A realm of exquisite beauty and profound solitude — the moon as mirror of longing and transcendence.",
        "location_type": "metaphysical_realm",
        "source_type": "mythology",
        "is_metaphysical": True,
        "celestial_coordinates": "Lunar Orbit / Silver Gate / Osmanthus Enclosure",
        "dimension_frequency": 210.42,
        "realm_governor": "Chang'e, Goddess of the Moon",
        "astrological_anchor": "Moon conjunct Venus in Cancer",
        "elemental_affinity": "Silver / Osmanthus / Frost / Reflection",
        "priority": 8,
        "is_active": True,
        "tags": ["taoist", "moon", "feminine", "immortality"],
        "notes": "Central to the Mid-Autumn Festival myth.",
    },
    {
        "id": "loc_dragon_palace",
        "name": "Dragon King's Crystal Palace — Long Wang Jing Gong",
        "description": "Submerged beneath the deepest ocean trenches, the Dragon Kings' palaces are made of translucent crystal and pearl, lit by phosphorescent sea creatures. Here the four Dragon Kings govern rain, rivers, lakes, and seas from coral thrones. Sun Wukong famously came here to 'borrow' the ocean-anchoring pillar that became his staff.",
        "location_type": "metaphysical_realm",
        "source_type": "mythology",
        "is_metaphysical": True,
        "celestial_coordinates": "Ocean Floor / Four Seas Grid / Dragon Gate Network",
        "dimension_frequency": 285.0,
        "realm_governor": "Ao Guang, Dragon King of the Eastern Sea",
        "astrological_anchor": "Neptune in Pisces, Scorpio",
        "elemental_affinity": "Crystal / Pearl / Abyssal Water / Phosphorescence",
        "priority": 8,
        "is_active": True,
        "tags": ["folklore", "dragon", "ocean", "underwater"],
        "notes": "The four Dragon Kings answer to the Jade Emperor and control all precipitation.",
    },
    # ── EARTHLY SACRED SITES ──
    {
        "id": "loc_wudang",
        "name": "Mount Wudang — Taoist Sacred Mountain",
        "description": "The mist-shrouded peaks of Hubei crowned with golden Taoist temples that seem to float above the clouds. Birthplace of Taiji Quan (Tai Chi) and internal martial arts. Seventy-two peaks pierce the sky; their shapes form a natural cosmic diagram when viewed from above.",
        "location_type": "earthly_sacred",
        "source_type": "geographic",
        "is_metaphysical": False,
        "latitude": 32.4,
        "longitude": 111.0,
        "timezone": "Asia/Shanghai",
        "dimension_frequency": 528.0,
        "realm_governor": "Zhenwu (Xuanwu), Perfected Warrior Emperor",
        "astrological_anchor": "Mars in Capricorn, North Node in Virgo",
        "elemental_affinity": "Mist / Gold / Pine / Stone",
        "priority": 8,
        "is_active": True,
        "tags": ["taoist", "sacred-mountain", "taiji", "martial-arts", "geographic"],
        "notes": "UNESCO World Heritage. Complex of 62 temples built across Ming dynasty peaks.",
    },
    {
        "id": "loc_emei",
        "name": "Mount Emei — Sacred Mountain of Samantabhadra",
        "description": "The 3,099m peak in Sichuan where Samantabhadra Bodhisattva (Puxian) rides his six-tusked white elephant through sea-of-clouds sunrises. Buddhist temples cling to vertical cliffs, and the 'Buddha's Halo' — a circular rainbow glory — often appears in the mountain mist.",
        "location_type": "earthly_sacred",
        "source_type": "geographic",
        "is_metaphysical": False,
        "latitude": 29.6,
        "longitude": 103.5,
        "timezone": "Asia/Shanghai",
        "dimension_frequency": 639.0,
        "realm_governor": "Samantabhadra Bodhisattva (Puxian Pusa)",
        "astrological_anchor": "Jupiter in Sagittarius, Moon in Taurus",
        "elemental_affinity": "Cloud / Elephant / Bamboo / Gold",
        "priority": 8,
        "is_active": True,
        "tags": ["buddhist", "sacred-mountain", "samantabhadra", "geographic"],
        "notes": "One of the four sacred Buddhist mountains. First temple built in 1st century CE.",
    },
    {
        "id": "loc_putuo_shan",
        "name": "Mount Putuo — Guanyin's Island Sanctuary",
        "description": "An island off Zhejiang's coast where Guanyin manifested in 863 CE. Amid subtropical groves and sea-eroded caves, temples dedicated to the Goddess of Mercy receive the ocean's eternal rhythm. Pilgrims climb the 33-metre Guanyin statue by the sea, whispering prayers that blend with salt spray.",
        "location_type": "earthly_sacred",
        "source_type": "geographic",
        "is_metaphysical": False,
        "latitude": 30.0,
        "longitude": 122.4,
        "timezone": "Asia/Shanghai",
        "dimension_frequency": 528.0,
        "realm_governor": "Guanyin (Avalokiteshvara Bodhisattva)",
        "astrological_anchor": "Moon in Pisces, Venus in Cancer",
        "elemental_affinity": "Sea / Lotus / Compassion",
        "priority": 9,
        "is_active": True,
        "tags": ["buddhist", "sacred-island", "compassion", "guanyin", "geographic"],
        "notes": "One of four sacred Buddhist mountains. Guanyin appeared here in 863 CE.",
    },
    {
        "id": "loc_jiuhua_shan",
        "name": "Mount Jiuhua — Realm of Ksitigarbha",
        "description": "The sacred Buddhist mountain of Anhui where Ksitigarbha Bodhisattva (Dizang Wang) is venerated. Ninety-nine peaks pierce the mist like lotus petals unfolding. Temples cling to precipices and incense drifts through bamboo groves. Prayers spoken here reach ancestors in the deepest hell realms.",
        "location_type": "earthly_sacred",
        "source_type": "geographic",
        "is_metaphysical": False,
        "latitude": 30.5,
        "longitude": 117.8,
        "timezone": "Asia/Shanghai",
        "dimension_frequency": 396.0,
        "realm_governor": "Dizang Wang Pusa (Ksitigarbha Bodhisattva)",
        "astrological_anchor": "Pluto in Scorpio, Saturn's South Node",
        "elemental_affinity": "Stone / Incense / Root",
        "priority": 8,
        "is_active": True,
        "tags": ["buddhist", "sacred-mountain", "ancestors", "underworld", "geographic"],
        "notes": "One of four sacred Buddhist mountains. Silla prince Kim Kiaokak was recognized as Ksitigarbha's manifestation.",
    },
    {
        "id": "loc_mount_tai",
        "name": "Mount Tai — Eastern Sacred Peak, Gate of the Sun",
        "description": "The most revered of the Five Great Mountains in Shandong — eastern pillar where the sun first touches Chinese soil. For 3,000 years, emperors climbed 6,600 stone steps to perform the Fengshan sacrifice. The Jade Emperor's summit temple marks the closest point between earth and heaven.",
        "location_type": "earthly_sacred",
        "source_type": "geographic",
        "is_metaphysical": False,
        "latitude": 36.3,
        "longitude": 117.1,
        "timezone": "Asia/Shanghai",
        "dimension_frequency": 528.0,
        "realm_governor": "Dongyue Dadi (Great Emperor of the Eastern Peak)",
        "astrological_anchor": "Sun at the Ascendant, Jupiter in Aries",
        "elemental_affinity": "Granite / Dawn / Eastern Wood",
        "priority": 9,
        "is_active": True,
        "tags": ["taoist", "sacred-mountain", "imperial", "sun", "geographic"],
        "notes": "UNESCO World Heritage. Associated with birth and renewal.",
    },
]

# ──────────────────────────────────────────────
# WRITE LOGIC
# ──────────────────────────────────────────────


def read_json(path):
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return {"version": "1.0", "last_updated": time.time(), "characters" if "char" in path.name else "locations": []}


def write_json(path, data):
    data["last_updated"] = time.time()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def seed():
    print("=" * 60)
    print("🌏  Direct-Write Chinese Lore Seed")
    print("=" * 60)

    # ── CHARACTERS ──
    chars_data = read_json(CHARS_PATH)
    existing_ids = {c["id"] for c in chars_data.get("characters", [])}
    added_c = 0
    skipped_c = 0

    for c in CHINESE_CHARS:
        if c["id"] in existing_ids:
            print(f"  ⏭️  SKIP: {c['name']}")
            skipped_c += 1
            continue
        c["added_time"] = time.time()
        c["last_used_time"] = None
        c["total_narratives_featured"] = 0
        chars_data["characters"].append(c)
        print(f"  ✅ ADDED: {c['name']} ({c['role']})")
        added_c += 1

    write_json(CHARS_PATH, chars_data)
    print(f"\n  📦 Characters: {added_c} added, {skipped_c} skipped → {len(chars_data['characters'])} total")

    # ── LOCATIONS ──
    locs_data = read_json(LOCS_PATH)
    existing_lids = {l["id"] for l in locs_data.get("locations", [])}
    added_l = 0
    skipped_l = 0

    for l in CHINESE_LOCS:
        if l["id"] in existing_lids:
            print(f"  ⏭️  SKIP: {l['name']}")
            skipped_l += 1
            continue
        l["added_time"] = time.time()
        l["last_used_time"] = None
        l["total_narratives_featured"] = 0
        locs_data["locations"].append(l)
        print(f"  ✅ ADDED: {l['name']} ({l['location_type']})")
        added_l += 1

    write_json(LOCS_PATH, locs_data)
    print(f"\n  📦 Locations:  {added_l} added, {skipped_l} skipped → {len(locs_data['locations'])} total")

    print()
    print("=" * 60)
    print("📊  DONE — Data written directly to JSON")
    print(f"  Characters: {CHARS_PATH}")
    print(f"  Locations:  {LOCS_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    seed()
