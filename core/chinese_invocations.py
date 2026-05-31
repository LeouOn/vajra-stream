"""
Chinese Ritual Invocations
Traditional Chinese liturgical phrases for ritual work.
Includes Daoist, Buddhist, and classical Chinese invocation formulas
with characters, pinyin, and English translation.
"""

CHINESE_INVOCATIONS = {
    "opening": [
        {
            "chinese": "道可道，非常道；名可名，非常名。",
            "pinyin": "Dào kě dào, fēi cháng dào; míng kě míng, fēi cháng míng.",
            "translation": "The Dao that can be spoken is not the eternal Dao; the name that can be named is not the eternal name.",
            "source": "道德经 (Dào Dé Jīng), Chapter 1"
        },
        {
            "chinese": "太上老君，急急如律令！",
            "pinyin": "Tài Shàng Lǎo Jūn, jí jí rú lǜ lìng!",
            "translation": "By the command of the Most High Lord Lao, swiftly, swiftly, in accordance with the statutes and ordinances!",
            "source": "Daoist Ritual Invocation"
        },
        {
            "chinese": "天地玄宗，万炁本根。",
            "pinyin": "Tiān dì xuán zōng, wàn qì běn gēn.",
            "translation": "The profound origin of Heaven and Earth, the root source of all vital energies.",
            "source": "金光神咒 (Golden Light Spirit Spell)"
        },
    ],
    "purification": [
        {
            "chinese": "太上台星，应变无停。驱邪缚魅，保命护身。",
            "pinyin": "Tài shàng tái xīng, yìng biàn wú tíng. Qū xié fù mèi, bǎo mìng hù shēn.",
            "translation": "The celestial stars of the Most High respond without ceasing. Expel evil, bind demons, protect life, guard the body.",
            "source": "净心神咒 (Heart-Purifying Spell)"
        },
        {
            "chinese": "灵宝天尊，安慰身形。弟子魂魄，五脏玄冥。",
            "pinyin": "Líng bǎo tiān zūn, ān wèi shēn xíng. Dì zǐ hún pò, wǔ zàng xuán míng.",
            "translation": "Celestial Worthy of Numinous Treasure, comfort my form. May this disciple's hun and po, and the five organs, be mysteriously tranquil.",
            "source": "净身神咒 (Body-Purifying Spell)"
        },
    ],
    "dedication": [
        {
            "chinese": "愿以此功德，庄严佛净土。上报四重恩，下济三途苦。",
            "pinyin": "Yuàn yǐ cǐ gōng dé, zhuāng yán fó jìng tǔ. Shàng bào sì chóng ēn, xià jì sān tú kǔ.",
            "translation": "May the merit of this practice adorn the Buddha's Pure Land. Repay the fourfold kindness above, relieve the suffering of the three paths below.",
            "source": "回向偈 (Dedication Verse)"
        },
        {
            "chinese": "若有见闻者，悉发菩提心。尽此一报身，同生极乐国。",
            "pinyin": "Ruò yǒu jiàn wén zhě, xī fā pú tí xīn. Jǐn cǐ yī bào shēn, tóng shēng jí lè guó.",
            "translation": "May all who see and hear this give rise to bodhicitta. When this life of retribution ends, may we together be born in the Land of Ultimate Bliss.",
            "source": "回向偈 (Dedication Verse)"
        },
        {
            "chinese": "功德回向法界一切众生，同证无上正等正觉。",
            "pinyin": "Gōng dé huí xiàng fǎ jiè yī qiè zhòng shēng, tóng zhèng wú shàng zhèng děng zhèng jué.",
            "translation": "Dedicate all merit to every sentient being throughout the Dharma realm; may all together realize unsurpassed, perfect enlightenment.",
            "source": "大乘回向 (Mahayana Dedication)"
        },
    ],
    "blessing": [
        {
            "chinese": "福生无量天尊",
            "pinyin": "Fú shēng wú liàng tiān zūn",
            "translation": "May the Celestial Worthy grant boundless blessings",
            "source": "Daoist Blessing"
        },
        {
            "chinese": "消灾延寿药师佛",
            "pinyin": "Xiāo zāi yán shòu yào shī fó",
            "translation": "May the Medicine Buddha dispel disasters and extend life",
            "source": "Medicine Buddha invocation"
        },
    ],
    "sealing": [
        {
            "chinese": "天圆地方，律令九章。吾今封印，万邪不侵。",
            "pinyin": "Tiān yuán dì fāng, lǜ lìng jiǔ zhāng. Wú jīn fēng yìn, wàn xié bù qīn.",
            "translation": "Heaven is round, Earth is square, the statutes have nine chapters. I now seal this; no evil of any kind shall intrude.",
            "source": "封印咒 (Sealing Spell)"
        },
    ],
}


def get_chinese_invocation(category: str = "opening", index: int = 0) -> dict:
    """Get a Chinese ritual invocation by category."""
    invocations = CHINESE_INVOCATIONS.get(category, [])
    if not invocations:
        return {"chinese": "南无阿弥陀佛", "pinyin": "Námó Āmítuófó", "translation": "Homage to Amitabha Buddha"}
    idx = index % len(invocations)
    return invocations[idx]


CHINESE_DHARANI_PINYIN = {
    "great_compassion": {
        "title": "大悲咒",
        "pinyin_title": "Dà Bēi Zhòu",
        "first_lines_chinese": "南無喝囉怛那哆囉夜耶 南無阿唎耶",
        "first_lines_pinyin": "Námó hēluō dánà duōluō yèyé Námó ālìyé",
    },
    "heart_sutra": {
        "title": "般若波羅蜜多心經",
        "pinyin_title": "Bōrě Bōluómìduō Xīnjīng",
        "mantra_chinese": "揭諦 揭諦 波羅揭諦 波羅僧揭諦 菩提 薩婆訶",
        "mantra_pinyin": "Jiē dì jiē dì, bō luó jiē dì, bō luó sēng jiē dì, pú tí sà pó hē",
    },
    "medicine_buddha": {
        "title": "藥師灌頂真言",
        "pinyin_title": "Yàoshī Guàndǐng Zhēnyán",
        "mantra_chinese": "唵 鞞殺逝 鞞殺逝 鞞殺社 三沒揭諦 莎訶",
        "mantra_pinyin": "Ǎn pí shā shì, pí shā shì, pí shā shè, sān mò jiē dì, suō hē",
    },
    "cundi": {
        "title": "準提神咒",
        "pinyin_title": "Zhǔntí Shén Zhòu",
        "mantra_chinese": "唵 折隸 主隸 準提 娑婆訶",
        "mantra_pinyin": "Ǎn zhé lì, zhǔ lì, zhǔn tí, suō pó hē",
    },
    "amitabha": {
        "title": "往生咒",
        "pinyin_title": "Wǎngshēng Zhòu",
        "mantra_chinese": "南無阿彌多婆夜 哆他伽多夜 哆地夜他 阿彌利都婆毗",
        "mantra_pinyin": "Námó āmíduōpóyè duōtuōqiéduōyè duōdìyètuō āmílìdūpópí",
    },
    "shurangama": {
        "title": "楞嚴咒 (首段)",
        "pinyin_title": "Léngyán Zhòu (shǒu duàn)",
        "mantra_chinese": "南無薩怛他 蘇伽多耶 阿囉訶帝 三藐三菩陀寫",
        "mantra_pinyin": "Námó sàdátuō sūqiéduōyé āluōhēdì sānmiǎo sānpútuóxiě",
    },
}
