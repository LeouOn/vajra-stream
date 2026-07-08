import json
from pathlib import Path

# Hexagrams mapping: pattern -> (Number, Chinese, Pinyin, English, Meaning, Judgment, Images, Lines)
HEXAGRAM_DATA = {
    "111111": (
        1, "乾", "Qián", "The Creative",
        "Pure active energy, leadership, persistent action",
        "The Creative brings about sublime success, furthering through perseverance.",
        "The movement of heaven is full of power. Thus the superior man makes himself strong and untiring.",
        [
            "Hidden dragon. Do not act.",
            "Dragon appearing in the field. It furthers one to see the great man.",
            "All day long the superior man is creatively active. At nightfall his mind is still beset with cares. Danger, no blame.",
            "Wavering flight over the depths. No blame.",
            "Flying dragon in the heavens. It furthers one to see the great man.",
            "Arrogant dragon will have cause to repent."
        ]
    ),
    "000000": (
        2, "坤", "Kūn", "The Receptive",
        "Pure yielding energy, nurturing, dedication, patience",
        "The Receptive brings about sublime success, furthering through the perseverance of a mare.",
        "The earth's condition is receptive devotion. Thus the superior man who has breadth of character carries the outer world.",
        [
            "When there is hoarfrost underfoot, solid ice is not far off.",
            "Straight, square, great. Without purpose, yet nothing remains ungoverned.",
            "Hidden lines. One is able to remain persevering. If you should follow a king, seek not works, but bring to completion.",
            "A tied-up sack. No blame, no praise.",
            "A yellow lower garment brings supreme good fortune.",
            "Dragons fight in the meadow. Their blood is black and yellow."
        ]
    ),
    "100010": (
        3, "屯", "Zhūn", "Difficulty at the Beginning",
        "Sprouting seed, dynamic growth against initial obstacles",
        "Difficulty at the Beginning works supreme success, furthering through perseverance. Do not act; appoint helpers.",
        "Clouds and thunder: the image of Difficulty at the Beginning. Thus the superior man brings order out of confusion.",
        [
            "Hesitation and hindrance. It furthers one to remain persevering. It furthers one to appoint helpers.",
            "Difficulties pile up. Horse and wagon part. He is not a robber; he wants to woo when the time comes.",
            "He who hunts deer without the forester only loses his way in the forest.",
            "Horse and wagon part. Strive for union. To go brings good fortune. Everything furthers.",
            "Difficulties in blessing. A little perseverance brings good fortune; great perseverance brings misfortune.",
            "Horse and wagon part. Bloody tears flow."
        ]
    ),
    "010001": (
        4, "蒙", "Méng", "Youthful Folly",
        "Inexperience, requirement of a teacher, open-minded study",
        "Youthful Folly has success. It is not I who seek the young fool; the young fool seeks me.",
        "A spring wells up at the foot of the mountain: the image of Youth. Thus the superior man fosters character by thoroughness.",
        [
            "To make a fool develop, it furthers one to apply discipline. The fetters should be removed.",
            "To bear with fools in kindliness brings good fortune. To know how to take the woman brings good fortune.",
            "You should not choose a maiden who, when she sees a man of wealth, loses possession of herself.",
            "Entangled folly brings humiliation.",
            "Childlike folly brings good fortune.",
            "In punishing folly, it does not further one to commit abuses. It furthers only to ward off abuses."
        ]
    ),
    "111010": (
        5, "需", "Xū", "Waiting (Nourishment)",
        "Patience, collecting strength, letting things mature naturally",
        "Waiting. If you are sincere, you have light and success. Perseverance brings good fortune. It furthers one to cross the great water.",
        "Clouds rise up to heaven: the image of Waiting. Thus the superior man eats and drinks, and is joyous and of good cheer.",
        [
            "Waiting in the meadow. It furthers one to abide in what is constant. No blame.",
            "Waiting in the sand. There is some gossip. The end brings good fortune.",
            "Waiting in the mud brings about the arrival of the enemy.",
            "Waiting in blood. Get out of the pit.",
            "Waiting at meat and drink. Perseverance brings good fortune.",
            "One falls into the pit. Three uninvited guests arrive. Honor them, and in the end there is good fortune."
        ]
    ),
    "010111": (
        6, "讼", "Sòng", "Conflict",
        "Disputes, need to seek arbitration, stop half-way",
        "Conflict. You are sincere and are being obstructed. A cautious halt halfway brings good fortune. Going through to the end brings misfortune.",
        "Heaven and water go their opposite ways: the image of Conflict. Thus the superior man, in all transactions, plans the beginning.",
        [
            "If one does not perpetuate the affair, there is a little gossip. In the end, good fortune comes.",
            "One cannot cope with conflict. One returns home and escapes. The people of his town remain free from plague.",
            "To nourish oneself on ancient virtue brings perseverance. Danger, in the end, good fortune.",
            "One cannot cope with conflict. One turns back and submits to fate, changes one's attitude, and finds peace.",
            "To contend before him brings supreme good fortune.",
            "Even if one is bestowed a leather belt, by the end of the morning it will be snatched away three times."
        ]
    ),
    "010000": (
        7, "师", "Shī", "The Army",
        "Leadership, collective discipline, alignment towards a goal",
        "The Army. The army needs perseverance and a strong man. Good fortune without blame.",
        "In the middle of the earth is water: the image of the Army. Thus the superior man increases his masses by generosity toward the people.",
        [
            "An army must set out in good order. If the order is bad, misfortune threatens.",
            "In the midst of the army. Good fortune, no blame. The king triple-decorates him.",
            "The army carries corpses in the wagon. Misfortune.",
            "The army retreats. No blame.",
            "There is game in the field. It furthers one to catch it. No blame. Let the eldest lead.",
            "The great prince issues commands, founds states, vests families with fiefs. Inferior people should not be employed."
        ]
    ),
    "000010": (
        8, "比", "Bǐ", "Holding Together [Union]",
        "Union, alliance, mutual support and community strength",
        "Holding Together brings good fortune. Inquire of the oracle once again whether you have sublimity, constancy, and perseverance.",
        "On the earth is water: the image of Holding Together. Thus the kings of old divided the land into states and built relations.",
        [
            "Hold to him in truth and loyalty; this is without blame. Truth is like a full earthen bowl.",
            "Hold to him inwardly. Perseverance brings good fortune.",
            "You hold together with the wrong people.",
            "Hold to him outwardly also. Perseverance brings good fortune.",
            "Manifestation of holding together. In the royal hunt, game is driven from three sides only. The citizens need no warning.",
            "He finds no head for holding together. Misfortune."
        ]
    ),
    "111011": (
        9, "小畜", "Xiǎo Chù", "The Taming Power of the Small",
        "Gentle restraint, small progress, accumulating wind",
        "The Taming Power of the Small has success. Dense clouds, no rain from our western territory.",
        "The wind drives across heaven: the image of the Taming Power of the Small. Thus the superior man refines the outward expression of his character.",
        [
            "Return to the way. How could this be a blame? Good fortune.",
            "He allows himself to be led back. Good fortune.",
            "The spokes of the wagon wheels burst. Husband and wife roll their eyes.",
            "If you are sincere, blood departs and fear gives way. No blame.",
            "If you are sincere and loyally attached, you are rich in your neighbor.",
            "The rain comes, rest is attained. This is due to the cumulative power of character. The moon is nearly full. Danger."
        ]
    ),
    "110111": (
        10, "履", "Lǚ", "Treading [Conduct]",
        "Conduct, cautious stepping, moving gracefully amidst danger",
        "Treading. Treading upon the tail of the tiger. It does not bite the man. Success.",
        "Heaven above, the lake below: the image of Treading. Thus the superior man discriminates between high and low.",
        [
            "Simple treading. Progress without blame.",
            "Treading a smooth, level path. The quiet man remains persevering. Good fortune.",
            "A one-eyed man can see, a lame man can tread. He treads on the tail of the tiger; it bites him. Misfortune.",
            "He treads on the tail of the tiger. Caution and circumspection lead in the end to good fortune.",
            "Resolute treading. Perseverance with consciousness of danger.",
            "Look to your conduct and weigh the signs. If the ending is complete, supreme good fortune comes."
        ]
    ),
    "111000": (
        11, "泰", "Tài", "Peace",
        "Harmonious flow, heaven and earth meeting, alignment",
        "Peace. The small departs, the great approaches. Good fortune. Success.",
        "Heaven and earth unite: the image of Peace. Thus the ruler divides and completes the course of heaven and earth.",
        [
            "When ribbon grass is pulled up, the sod comes with it. Each according to his kind. Undertakings bring good fortune.",
            "Bearing with the uncultured in gentleness, crossing the river with resolution, not neglecting what is distant. One finds the middle path.",
            "No plain not succeeded by a slope, no going out not succeeded by a return. He who remains persevering in danger remains without blame.",
            "He flutters down, not boasting of his wealth, together with his neighbor, guileless and sincere.",
            "The sovereign sovereign gives his daughter in marriage. This brings blessing and supreme good fortune.",
            "The wall falls back into the moat. Use no army now. Inform your own town. Perseverance brings humiliation."
        ]
    ),
    "000111": (
        12, "否", "Pǐ", "Standstill [Stagnation]",
        "Stagnation, retreat of noble influences, blockages",
        "Standstill. Evil people do not further the perseverance of the superior man. The great departs, the small approaches.",
        "Heaven and earth do not unite: the image of Standstill. Thus the superior man falls back upon his inner worth to escape difficulties.",
        [
            "When ribbon grass is pulled up, the sod comes with it. Perseverance brings good fortune and blessing.",
            "They bear and accord. Good fortune for the inferior man. The great man suffers standstill, yet has success.",
            "They bear shame.",
            "He who acts at the command of the highest remains without blame. Those of like mind share in the blessing.",
            "Standstill is giving way. Good fortune for the great man. He assigns it to a heap of mulberry shoots.",
            "The standstill comes to an end. First standstill, then good fortune."
        ]
    ),
    "101111": (
        13, "同人", "Tóng Rén", "Fellowship with Men",
        "Union with others in the open, shared vision",
        "Fellowship with Men in the open. Success. It furthers one to cross the great water. It furthers the perseverance of the superior man.",
        "Heaven together with fire: the image of Fellowship. Thus the superior man organizes the clans and distinguishes between things.",
        [
            "Fellowship with men at the gate. No blame.",
            "Fellowship with men in the clan. Humiliation.",
            "He hides weapons in the thicket; he climbs to the high hill. For three years he does not rise.",
            "He climbs up on his wall; he cannot attack. Good fortune.",
            "Fellowship with men first weep and wail, but afterward they laugh. After great struggles they succeed in meeting.",
            "Fellowship with men in the meadow. No repentance."
        ]
    ),
    "111101": (
        14, "大有", "Dà Yǒu", "Possession in Great Measure",
        "Abundant light, wealth, supreme clarity and rule of virtue",
        "Possession in Great Measure brings supreme success.",
        "Fire in heaven above: the image of Possession in Great Measure. Thus the superior man curbs evil and promotes good.",
        [
            "No relationship with what is harmful. No blame in this. If one remains conscious of difficulty, one remains without blame.",
            "A large wagon for loading. One may undertake something. No blame.",
            "A prince offers it to the Son of Heaven. A petty man cannot do this.",
            "He makes a difference between himself and his neighbor. No blame.",
            "He whose truth is accessible yet dignified has good fortune.",
            "He is blessed by heaven. Good fortune. Everything furthers."
        ]
    ),
    "000100": (
        15, "谦", "Qiān", "Modesty",
        "Self-deprecation, keeping low, high values without pride",
        "Modesty creates success. The superior man carries things through to the end.",
        "Within the earth, a mountain: the image of Modesty. Thus the superior man reduces where there is superabundance and increases where there is lack.",
        [
            "A superior man modest about his modesty may cross the great water. Good fortune.",
            "Modesty that finds expression. Perseverance brings good fortune.",
            "A superior man of merit and modesty carries things through to the end. Good fortune.",
            "Nothing that would not further modesty in movement.",
            "No boasting of wealth before one's neighbor. It furthers one to strike with force. Everything furthers.",
            "Modesty that expresses itself. It furthers one to set armies in motion to discipline one's own city and country."
        ]
    ),
    "001000": (
        16, "豫", "Yù", "Enthusiasm",
        "Vibrant motivation, movement follows music, readiness",
        "Enthusiasm furthers. It furthers to appoint helpers and set armies in motion.",
        "Thunder comes resounding out of the earth: the image of Enthusiasm. Thus the ancient kings made music to honor merit.",
        [
            "Enthusiasm that expresses itself brings misfortune.",
            "Firm as a rock. Not a whole day. Perseverance brings good fortune.",
            "Enthusiasm that looks upward brings remorse. Hesitation brings repentance.",
            "The source of enthusiasm. He achieves great things. Doubt not. You gather friends around you as a hair clasp draws the hair.",
            "Persistently ill, yet does not die.",
            "Deluded enthusiasm. But if after completion one makes a change, there is no blame."
        ]
    ),
    "100110": (
        17, "随", "Suí", "Following",
        "Adapting, yielding leadership to flow of time",
        "Following has supreme success. Perseverance furthers. No blame.",
        "Thunder in the middle of the lake: the image of Following. Thus the superior man at nightfall goes indoors for rest and recuperation.",
        [
            "The standard is changing. Perseverance brings good fortune. To go out of the gate in company creates deeds.",
            "He who clings to the little boy loses the strong man.",
            "He who clings to the strong man loses the little boy. Through following one finds what one seeks. Perseverance furthers.",
            "Following creates followers. Perseverance brings misfortune. If one goes one's way with sincerity, clarity arises.",
            "Sincere in what is good. Supreme good fortune.",
            "He meets with firm allegiance and is bound fast. The king presents him to the Western Mountain."
        ]
    ),
    "011001": (
        18, "蛊", "Gǔ", "Work on what has been Spoiled [Decay]",
        "Renovating what was broken, fixing parental errors",
        "Work on what has been Spoiled has supreme success. It furthers one to cross the great water. Before the starting point three days, after the starting point three days.",
        "The wind blows at the foot of the mountain: the image of Decay. Thus the superior man stirs up the people and strengthens their spirit.",
        [
            "Setting right what has been spoiled by the father. If there is a son, no blame rests on the departed father. Good fortune.",
            "Setting right what has been spoiled by the mother. One must not be too rigid.",
            "Setting right what has been spoiled by the father. There will be a little remorse. No great blame.",
            "Tolerating what has been spoiled by the father. To go on brings humiliation.",
            "Setting right what has been spoiled by the father. One meets with praise.",
            "He does not serve kings and princes; he sets himself higher goals."
        ]
    ),
    "110000": (
        19, "临", "Lín", "Approach",
        "Approaching spring, warm influence, growth opportunity",
        "Approach has supreme success. Perseverance furthers. When the eighth month comes, misfortune threatens.",
        "The earth above the lake: the image of Approach. Thus the superior man is inexhaustible in his will to teach.",
        [
            "Joint approach. Perseverance brings good fortune.",
            "Joint approach. Good fortune. Everything furthers.",
            "Comfortable approach. Nothing that would further. If one is led to lament it, one becomes free of blame.",
            "Complete approach. No blame.",
            "Wise approach. This is right for a great prince. Good fortune.",
            "Great-hearted approach. Good fortune. No blame."
        ]
    ),
    "000011": (
        20, "观", "Kuan", "Contemplation [View]",
        "Looking down, meditation, viewing the whole field",
        "Contemplation. The ablution has been made, but not yet the offering. Full of trust they look up to him.",
        "The wind blows over the earth: the image of Contemplation. Thus the kings of old visited all regions, contemplated the people, and gave instruction.",
        [
            "Boyish contemplation. For an inferior man, no blame; for a superior man, humiliation.",
            "Contemplation through the crack of the door. Furthers a woman's perseverance.",
            "Contemplation of our life decides the choice between progress and retreat.",
            "Contemplation of the light of the kingdom. It furthers one to exert influence as the guest of a king.",
            "Contemplation of our life. The superior man is without blame.",
            "Contemplation of his life. The superior man is without blame."
        ]
    ),
    "100101": (
        21, "噬嗑", "Shì Hé", "Biting Through",
        "Removing obstacles, energetic enforcement of law",
        "Biting Through has success. It furthers one to let justice be administered.",
        "Thunder and lightning: the image of Biting Through. Thus the kings of old formulated laws with defined penalties.",
        [
            "His feet are fastened in the stocks, so that his toes disappear. No blame.",
            "Bites through tender meat, so that his nose disappears. No blame.",
            "Bites on old dried meat and meets with something poisonous. Slight humiliation, no blame.",
            "Bites on dried gristly meat. Receives metal arrowheads. It furthers one to be mindful of difficulties. Good fortune.",
            "Bites on dried lean meat. Receives yellow gold. Perseveringly mindful of danger. No blame.",
            "His neck is fastened in the wooden yoke, so that his ears disappear. Misfortune."
        ]
    ),
    "101001": (
        22, "贲", "Bì", "Grace",
        "Aesthetic beauty, decoration, temporary outer form",
        "Grace has success. In small matters, it furthers one to undertake something.",
        "Fire at the foot of the mountain: the image of Grace. Thus the superior man proceeds to clarify current affairs, but dares not decide controversial issues.",
        [
            "He lends grace to his toes, leaves the carriage, and walks.",
            "Lends grace to the beard on his chin.",
            "Graced and wet as with dew. Constant perseverance brings good fortune.",
            "Grace or simplicity? A white horse comes as if on wings. He is not a robber; he wants to woo when the time comes.",
            "Grace in hills and gardens. The roll of silk is small and meager. Humiliation, but in the end good fortune.",
            "Simple grace. No blame."
        ]
    ),
    "000001": (
        23, "剥", "Bō", "Splitting Apart",
        "Disintegration, collapse of rotten structures",
        "Splitting Apart. It does not further one to go anywhere.",
        "The mountain rests on the earth: the image of Splitting Apart. Thus the high can secure their house only by giving wealth to the low.",
        [
            "The house is splitting at the foot. Destruction of the bed. Misfortune.",
            "The house is splitting at the frame. Destruction of the bed. Misfortune.",
            "He splits with them. No blame.",
            "The house is splitting up to the skin. Destruction of the bed. Misfortune.",
            "A shoal of fishes. Favor comes through the court ladies. Everything furthers.",
            "There is a large fruit still uncollected. The superior man receives a carriage. The inferior man's house splits apart."
        ]
    ),
    "100000": (
        24, "复", "Fù", "Return [The Turning Point]",
        "The turning point, return of light, recovery of energy",
        "Return. Success. Going out and coming in without error. Friends come without blame. On the seventh day comes return. It furthers to undertake something.",
        "Thunder in the middle of the earth: the image of the Turning Point. Thus the kings of old closed the passes at the winter solstice.",
        [
            "Return from a short distance. No need for remorse. Supreme good fortune.",
            "Quiet return. Good fortune.",
            "Repeated return. Danger. No blame.",
            "Walking in the midst of others, one returns alone.",
            "Noble return. No remorse.",
            "Missing the return. Misfortune. Disaster from within and without. For ten years one cannot lead."
        ]
    ),
    "100111": (
        25, "无妄", "Wú Wàng", "Innocence [The Unexpected]",
        "Natural behavior, acting without ulterior motives",
        "Innocence. Supreme success. Perseverance furthers. If someone is not as he should be, he has misfortune, and it does not further him to undertake anything.",
        "Under heaven thunder rolls: all things attain the state of innocence. Thus the kings of old gave nourishment to all things.",
        [
            "Innocent behavior brings good fortune.",
            "If one does not count on harvest while plowing, nor on the use of the ground while clearing it, it furthers one to undertake something.",
            "Undeserved misfortune. The cow that was tethered to the post is taken by the passerby. The citizen's loss.",
            "He who remains persevering remains without blame.",
            "Use no medicine for an illness incurred without one's fault. It will pass.",
            "Innocent action brings misfortune. Nothing furthers."
        ]
    ),
    "111001": (
        26, "大畜", "Dà Chù", "The Taming Power of the Great",
        "Focus, storing wisdom, preparation for large work",
        "The Taming Power of the Great. Perseverance furthers. Not eating at home brings good fortune. It furthers one to cross the great water.",
        "Heaven within the mountain: the image of the Taming Power of the Great. Thus the superior man acquaints himself with many sayings.",
        [
            "Danger is at hand. It furthers one to desist.",
            "The axletrees are taken from the wagon.",
            "A good horse that follows others. Constant perseverance in awareness of danger furthers. Practice chariot-driving daily.",
            "The headboard of a young bull. Great good fortune.",
            "The tusk of a gelded boar. Good fortune.",
            "One attains the highway of heaven. Success."
        ]
    ),
    "100001": (
        27, "颐", "Yí", "The Corners of the Mouth [Nourishment]",
        "Providing food, monitoring what enters mouth and mind",
        "The Corners of the Mouth. Perseverance brings good fortune. Pay heed to the providing of nourishment and to what a man seeks to fill his mouth.",
        "At the foot of the mountain, thunder: the image of Nourishment. Thus the superior man is careful in his words and moderate in eating and drinking.",
        [
            "You let your magic tortoise go, and look at me with hanging jaw. Misfortune.",
            "Turning to the summit for nourishment. To deviate from the path to seek nourishment from the hill brings misfortune.",
            "Turning away from nourishment. Perseverance brings misfortune. Do not act for ten years. Nothing furthers.",
            "Turning to the summit for nourishment brings good fortune. Looking down with glaring eyes like a tiger. No blame.",
            "Turning away from the path. To remain persevering brings good fortune. One should not cross the great water.",
            "The source of nourishment. Aware of danger brings good fortune. It furthers one to cross the great water."
        ]
    ),
    "011110": (
        28, "大过", "Dà Guò", "Preponderance of the Great",
        "Heavy beam bends, crisis requiring extraordinary action",
        "Preponderance of the Great. The ridgepole sags to the breaking point. It furthers one to have somewhere to go. Success.",
        "The lake rises above the trees: the image of Preponderance of the Great. Thus the superior man, when he stands alone, fears nothing.",
        [
            "To spread white reeds underneath. No blame.",
            "A dry poplar sprouts at the root. An older man takes a young wife. Everything furthers.",
            "The ridgepole sags to the breaking point. Misfortune.",
            "The ridgepole is made firm. Good fortune. If there are secondary aims, it is humiliating.",
            "A withered poplar puts forth flowers. An older woman takes a young husband. No blame, no praise.",
            "One goes through the water. It goes over one's head. Misfortune. No blame."
        ]
    ),
    "010010": (
        29, "坎", "Kǎn", "The Abyssal (Water)",
        "Double danger, maintaining trust, flowing through deep chasms",
        "The Abyssal repeated. If you are sincere, you have holding together in your heart, and whatever you do succeeds.",
        "Water flows on uninterruptedly and reaches its goal: the image of the Abyssal repeated. Thus the superior man walks in constancy.",
        [
            "Abyssal upon abyssal. Grave danger. Into the abyss one falls. Do not act.",
            "The abyss is dangerous. One should strive to attain small things only.",
            "Forward and backward, abyss upon abyss. In such danger, pause and wait, otherwise you fall into the pit. Do not act.",
            "A jug of wine, a bowl of rice, earthen vessels. Handed in through the window. No blame.",
            "The abyss is not filled to overflowing, it is filled only to the rim. No blame.",
            "Bound with cords and ropes, shut in behind thorn-hedged prison walls. For three years one does not find the way. Misfortune."
        ]
    ),
    "101101": (
        30, "离", "Lí", "The Clinging, Fire",
        "Illumination, clarity, dependency on fuel, consciousness",
        "The Clinging. Perseverance furthers. It brings success. Care of the cow brings good fortune.",
        "That which is bright rises twice: the image of Fire. Thus the great man clings to clarity and illumines the four quarters of the world.",
        [
            "The footprints run in all directions. If one is serious and attentive, no blame.",
            "Yellow light. Supreme good fortune.",
            "In the light of the setting sun, men either beat the pot and sing or sigh because of old age. Misfortune.",
            "Its coming is sudden; it burns, it dies, it is thrown away. No blame.",
            "Tears flow in torrents, sighing and mourning. Good fortune.",
            "The king uses him to march forth and chastise. He kills the leaders and spares the followers. No blame."
        ]
    ),
    "001110": (
        31, "咸", "Xián", "Influence [Wooing]",
        "Mutual attraction, courtship, receptive harmony",
        "Influence. Success. Perseverance furthers. To take a maiden to wife brings good fortune.",
        "A lake on the mountain: the image of Influence. Thus the superior man encourages people to approach him by his readiness to receive them.",
        [
            "The influence shows itself in the big toe.",
            "The influence shows itself in the calves of the legs. Misfortune. Tarrying brings good fortune.",
            "The influence shows itself in the thighs. Holds to that which follows. To continue brings humiliation.",
            "Perseverance brings good fortune. Remorse disappears. If a man is agitated, only the friends follow.",
            "The influence shows itself in the back of the neck. No remorse.",
            "The influence shows itself in the jaws, cheeks, and tongue."
        ]
    ),
    "011100": (
        32, "恒", "Héng", "Duration",
        "Persistence, stable marriage of earth/wind forces",
        "Duration. Success. No blame. Perseverance furthers. It furthers one to have somewhere to go.",
        "Thunder and wind: the image of Duration. Thus the superior man stands firm and does not change his direction.",
        [
            "Seeking duration by force brings misfortune. Nothing furthers.",
            "Remorse disappears.",
            "He who does not give duration to his character meets with disgrace. Persistent humiliation.",
            "No game in the field.",
            "Giving duration to one's character through perseverance. This is good fortune for a woman, misfortune for a man.",
            "Restlessness as a status of duration brings misfortune."
        ]
    ),
    "001111": (
        33, "遁", "Tun", "Retreat",
        "Strategic withdrawal, saving energy in times of decline",
        "Retreat. Success. In what is small, perseverance furthers.",
        "Mountain under heaven: the image of Retreat. Thus the superior man keeps the inferior man at a distance, not with anger but with dignity.",
        [
            "At the tail in retreat. This is dangerous. One must not undertake anything.",
            "He holds him fast with yellow oxhide. No one can tear him loose.",
            "A halted retreat. This is dangerous. To hold people back brings good fortune.",
            "Voluntary retreat brings good fortune to the superior man, and destruction to the inferior man.",
            "Friendly retreat. Perseverance brings good fortune.",
            "Cheerful retreat. Everything furthers."
        ]
    ),
    "111100": (
        34, "大壮", "Dà Zhuàng", "The Power of the Great",
        "Steer holds horns, avoiding head-on clashes, inner discipline",
        "The Power of the Great. Perseverance furthers.",
        "Thunder in heaven above: the image of the Power of the Great. Thus the superior man does not tread upon paths that do not accord with order.",
        [
            "Power in the toes. Continuing brings misfortune. This is true.",
            "Perseverance brings good fortune.",
            "The inferior man shows power; the superior man does not. Continuing is dangerous. A goat butts against a hedge and gets its horns entangled.",
            "Perseverance brings good fortune. Remorse disappears. The hedge opens; there is no entanglement.",
            "Loses the goat in easiness. No remorse.",
            "A goat butts against a hedge. It cannot go forward, it cannot go backward. Nothing furthers. If one notes the difficulty, good fortune comes."
        ]
    ),
    "000101": (
        35, "晋", "Jìn", "Progress",
        "Sun rising over earth, dynamic advancement and honor",
        "Progress. The powerful prince is honored with horses in large numbers. In a single day he is granted audience three times.",
        "The sun rises over the earth: the image of Progress. Thus the superior man himself brightens his bright character.",
        [
            "Progressing, but turned back. Perseverance brings good fortune. If one meets with no trust, one should remain calm.",
            "Progressing, but in sorrow. Perseverance brings good fortune. One receives great blessing from one's ancestress.",
            "All are in agreement. Remorse disappears.",
            "Progressing like a marmot. Perseverance brings danger.",
            "Remorse disappears. Take not gain and loss to heart. Undertakings bring good fortune. Everything furthers.",
            "Progressing with lowered horns. One should use them only to punish one's own city. Awareness of danger brings good fortune."
        ]
    ),
    "101000": (
        36, "明夷", "Míng Yí", "Darkening of the Light",
        "Hiding light under a basket, survival during tyranny",
        "Darkening of the Light. In adversity it furthers one to be persevering.",
        "The sun has sunk into the earth: the image of Darkening of the Light. Thus the superior man lives with the great multitude.",
        [
            "Darkening of the light during flight. He drops his wings. The superior man on his journey does not eat for three days.",
            "Darkening of the light injuring him in the left thigh. He gives aid with the strength of a horse. Good fortune.",
            "Darkening of the light during the hunt in the south. Their great leader is captured. One must not expect speed.",
            "He penetrates into the left side of the belly. One wins the heart of the darkening of the light.",
            "Darkening of the light as with Prince Chi. Perseverance furthers.",
            "Not light but darkness. First he climbed up to heaven, then he plunged into the depths of the earth."
        ]
    ),
    "101011": (
        37, "家人", "Jiā Rén", "The Family [The Clan]",
        "Internal order, domestic discipline and alignment",
        "The Family. The perseverance of the woman furthers.",
        "Wind comes forth from fire: the image of the Family. Thus the superior man has truth in his words and constancy in his life.",
        [
            "Firm seclusion within the family. Remorse disappears.",
            "She should not follow her whims. She has only to look after the food within. Perseverance brings good fortune.",
            "When tempers flare in the family, too great severity brings remorse, yet good fortune. If women and children dally, it leads to humiliation.",
            "She is the treasure of the house. Great good fortune.",
            "The king approaches his family. Fear not. Good fortune.",
            "His work is full of truth and majesty. In the end, good fortune comes."
        ]
    ),
    "110101": (
        38, "睽", "Kuí", "Opposition",
        "Different paths, finding alignment on minor matters",
        "Opposition. In small matters, good fortune.",
        "Fire above, the lake below: the image of Opposition. Thus the superior man associates with others, yet maintains his individuality.",
        [
            "Remorse disappears. If you lose your horse, do not run after it; it will return. When you see evil people, guard against blame.",
            "One meets his master in a narrow street. No blame.",
            "One sees the wagon dragged back, the oxen halted, a man's hair and nose cut off. Not a good beginning, but a good end.",
            "Isolated through opposition, one meets a companion of like mind. Fellowship in mutual trust. No blame.",
            "Remorse disappears. The companion bites his way through the wrapper. If one goes to him, how could this be a mistake?",
            "Isolated through opposition, one sees one's companion as a dirty pig, as a wagon full of devils. First he draws his bow, then he unbends it. Good fortune."
        ]
    ),
    "001010": (
        39, "蹇", "Jiǎn", "Obstruction",
        "Mountain before water, need to stop and regroup",
        "Obstruction. The southwest furthers, the northeast does not. It furthers one to see the great man. Perseverance brings good fortune.",
        "Water on the mountain: the image of Obstruction. Thus the superior man turns his attention to himself and molds his character.",
        [
            "Going leads to obstructions, coming meets with praise.",
            "The king's servant is beset by obstruction after obstruction. It is not for his own sake.",
            "Going leads to obstructions, coming leads to return.",
            "Going leads to obstructions, coming leads to union.",
            "In the midst of the greatest obstructions, friends arrive.",
            "Going leads to obstructions, coming leads to great-heartedness. Good fortune. It furthers one to see the great man."
        ]
    ),
    "010100": (
        40, "解", "Xiè", "Deliverance",
        "Release of tension, forgiveness, moving forward quickly",
        "Deliverance. The southwest furthers. If there is no longer anywhere one must go, return brings good fortune. If there is, speed brings good fortune.",
        "Thunder and rain set in: the image of Deliverance. Thus the superior man pardons mistakes and forgives misdeeds.",
        [
            "In the state of deliverance, there is no blame.",
            "One shoots three foxes in the field and receives a yellow arrow. Perseverance brings good fortune.",
            "A man carries a burden on his back and yet rides in a carriage. He thereby invites robbers. Perseverance brings humiliation.",
            "Deliver yourself from your great toe. Then the companion arrives, and him you can trust.",
            "If only the superior man can deliver himself, it brings good fortune. He thereby proves to the inferior man that he is in earnest.",
            "The prince shoots at a hawk on a high wall. He kills it. Everything furthers."
        ]
    ),
    "110001": (
        41, "损", "Sǔn", "Decrease",
        "Reducing excess, concentrating on simplicity",
        "Decrease combined with sincerity brings supreme good fortune. No blame. Perseverance furthers. It furthers to undertake something. How is this to be carried out? Two small bowls may be used for sacrifice.",
        "At the foot of the mountain, the lake: the image of Decrease. Thus the superior man curbs his anger and restrains his desires.",
        [
            "Going quickly when one's tasks are finished is without blame. But one must weigh how much one may decrease another.",
            "Perseverance furthers. To undertake something brings misfortune. Without decreasing oneself, one may increase others.",
            "If three people journey together, their number decreases by one. If one man journeys alone, he finds a companion.",
            "If a man decreases his faults, it makes others hasten to arrive and rejoice. No blame.",
            "Someone increases him. Ten pairs of tortoises cannot oppose it. Supreme good fortune.",
            "If one is increased without decreasing others, no blame. Perseverance brings good fortune. One gains servants."
        ]
    ),
    "100011": (
        42, "益", "Yì", "Increase",
        "Expanding, helping the lower classes, time for undertaking",
        "Increase. It furthers to undertake something. It furthers one to cross the great water.",
        "Wind and thunder: the image of Increase. Thus the superior man, when he sees good, imitates it; when he has faults, he rids himself of them.",
        [
            "It furthers one to accomplish great deeds. Supreme good fortune. No blame.",
            "Someone increases him. Ten pairs of tortoises cannot oppose it. Constant perseverance brings good fortune.",
            "One is enriched through unfortunate events. No blame if you are sincere and walk in the middle path.",
            "If you walk in the middle path and report to the prince, he will follow. It furthers one to be used in relocating the capital.",
            "If you have a sincere heart that wishes to benefit others, ask not. Supreme good fortune. Sincerity will be recognized as your virtue.",
            "He brings increase to no one. Someone even strikes him. He does not keep his heart constant. Misfortune."
        ]
    ),
    "111110": (
        43, "夬", "Guài", "Breakthrough [Resoluteness]",
        "Decisive resolution, clearing out remaining obstacles",
        "Breakthrough. One must resolutely make the matter known at the court of the king. It must be announced truthfully. Danger. It furthers one to undertake something.",
        "The lake has risen up to heaven: the image of Breakthrough. Thus the superior man dispenses riches to those below.",
        [
            "Mighty in the forward-striding toes. If one goes and is not equal to the task, one makes a mistake.",
            "A cry of alarm. Arms at evening and during the night. Fear not.",
            "To be powerful in the cheekbones brings misfortune. The superior man is firmly resolved. He walks alone and gets wet.",
            "There is no skin on his thighs, and treading is difficult. If he let himself be led like a sheep, remorse would disappear.",
            "In dealing with weeds, firm resolution is necessary. Walking in the middle path keeps one free from blame.",
            "No cry. In the end, misfortune comes."
        ]
    ),
    "011111": (
        44, "姤", "Gòu", "Coming to Meet",
        "Sudden temptation, dynamic female influence, caution",
        "Coming to Meet. The maiden is powerful. One should not marry such a maiden.",
        "Under heaven, the wind: the image of Coming to Meet. Thus the ruler proclaims his commands and disseminates them in the four quarters.",
        [
            "It must be checked with a brake of bronze. Perseverance brings good fortune. If one lets it take its course, one experiences misfortune.",
            "There is a fish in the tank. No blame. Does not further guests.",
            "There is no skin on his thighs, and treading is difficult. If one remains mindful of the danger, no great mistake is made.",
            "No fish in the tank. This rises from standing aloof from the people.",
            "A melon covered with willow leaves. Hidden lines. Then it falls into one's lap as if from heaven.",
            "He meets others with his horns. Humiliation. No blame."
        ]
    ),
    "000110": (
        45, "萃", "Cuì", "Gathering Together [Massing]",
        "Mass convergence, alignment of leadership and sacrifices",
        "Gathering Together. Success. The king approaches his temple. It furthers one to see the great man. This brings success. Perseverance furthers. Great sacrifices bring good fortune.",
        "Lake over earth: the image of Gathering Together. Thus the superior man renews his weapons to meet the unexpected.",
        [
            "If you are sincere, but not to the end, there will sometimes be confusion. If you cry out, one grasp of the hand can make you laugh again. No blame.",
            "Letting oneself be drawn brings good fortune and remains without blame. If one is sincere, it furthers one to bring even a small offering.",
            "Gathering together amid sighs. Nothing that would further. Going is without blame; slight humiliation.",
            "Great good fortune. No blame.",
            "If in gathering together one has position, this brings no blame. If there are those not yet sincere, let your virtue be lofty.",
            "Lamenting and sighing, tears flow. No blame."
        ]
    ),
    "011000": (
        46, "升", "Shēng", "Pushing Upward",
        "Gradual vertical progress, steady effort and growth",
        "Pushing Upward has supreme success. One must see the great man. Fear not. Departure toward the south brings good fortune.",
        "Within the earth, wood grows: the image of Pushing Upward. Thus the superior man fosters his character by small steps.",
        [
            "Pushing upward that meets with confidence brings great good fortune.",
            "If one is sincere, it furthers one to bring even a small offering. No blame.",
            "One pushes upward into an empty city.",
            "The king offers sacrifice on Mount Chi. Good fortune. No blame.",
            "Perseverance brings good fortune. One pushes upward by steps.",
            "Pushing upward in darkness. It furthers one to remain unremittingly persevering."
        ]
    ),
    "010110": (
        47, "困", "Kùn", "Oppression [Exhaustion]",
        "Exhaustion, dry well, testing of resolve and speechlessness",
        "Oppression. Success. Perseverance. The great man brings about good fortune. No blame. When one has something to say, it is not believed.",
        "There is no water in the lake: the image of Oppression. Thus the superior man stakes his life on following his will.",
        [
            "One sits oppressed under a bare tree and strays into a gloomy valley. For three years one sees nothing.",
            "One is oppressed while at meat and drink. The man with the scarlet knee bands arrives. It furthers to offer sacrifices.",
            "Oppressed by stone, and leaning on thorns. He enters his house and does not see his wife. Misfortune.",
            "He comes very quietly, oppressed in a golden carriage. Humiliation, but the end is reached.",
            "His nose and feet are cut off. Oppressed by the man with the purple knee bands. Joy comes slowly.",
            "He is oppressed by creeping vines, and moves hesitantly. If one says: 'Movement brings remorse,' and repents, good fortune comes."
        ]
    ),
    "011010": (
        48, "井", "Jǐng", "The Well",
        "Inexhaustible source of life-force, maintaining the structure",
        "The Well. The town may be changed, but the well cannot be changed. It neither decreases nor increases. They come and go, drawing from the well. If one does not draw, or breaks the jug, misfortune.",
        "Water over wood: the image of the Well. Thus the superior man encourages the people in their work and exhorts them to help one another.",
        [
            "One does not drink mud from the well. No animals go to an old well. Nothing furthers.",
            "At the well hole one shoots fishes. The jug is broken and leaks.",
            "The well is cleaned, but no one drinks from it. This is my heart's sorrow, for one might draw from it.",
            "The well is being lined. No blame.",
            "In the well is a clear, cold spring from which one drinks. Good fortune.",
            "One draws from the well without hindrance. It is dependable. Supreme good fortune."
        ]
    ),
    "101110": (
        49, "革", "Gé", "Revolution [Molting]",
        "Discarding old skins, seasonal change, timing is critical",
        "Revolution. On your own day you are believed. Supreme success, furthering through perseverance. Remorse disappears.",
        "Fire in the lake: the image of Revolution. Thus the superior man sets the calendar and makes the seasons clear.",
        [
            "Wrapped in the hide of a yellow cow.",
            "When one's own day comes, one may create revolution. Starting brings good fortune. No blame.",
            "Starting brings misfortune. Perseverance brings danger. When talk of revolution has gone the round three times, one may trust it.",
            "Remorse disappears. Belief is found. Changing the form of government brings good fortune.",
            "The great man changes like a tiger. Even before he questions the oracle, he is believed.",
            "The superior man changes like a leopard. The inferior man molts his face. Starting brings misfortune. To remain persevering brings good fortune."
        ]
    ),
    "011101": (
        50, "鼎", "Dǐng", "The Cauldron",
        "Vessel of transformation, spiritual nourishment, alchemy",
        "The Cauldron. Supreme good fortune. Success.",
        "Fire over wood: the image of the Cauldron. Thus the superior man consolidates his fate by making his position correct.",
        [
            "A cauldron upright with feet turned up. Furthers removal of waste. One takes a concubine for the sake of her son. No blame.",
            "There is food in the cauldron. My comrades are envious, but they cannot harm me. Good fortune.",
            "The handle of the cauldron is altered. One is impeded in one's life. The fat of the pheasant is not eaten. Once rain falls, remorse spent.",
            "The legs of the cauldron are broken. The prince's meal is spilled and his person soiled. Misfortune.",
            "The cauldron has yellow ears and a golden carrying bar. Perseverance furthers.",
            "The cauldron has a carrying bar of jade. Great good fortune. Everything furthers."
        ]
    ),
    "100100": (
        51, "震", "Zhèn", "The Arousing (Thunder)",
        "Startling thunder, awakening, initial fear turning to laughter",
        "The Arousing brings success. Thunder comes, boom-boom! Laughter and talk, ha-ha! The thunder terrifies for a hundred miles, but he does not let fall the sacrificial spoon.",
        "Double thunder: the image of the Arousing. Thus the superior man in fear and trembling sets his life in order and examines himself.",
        [
            "Thunder comes, boom-boom! Afterward, laughter and talk, ha-ha! Good fortune.",
            "Thunder comes with danger. A hundred thousand times one loses one's treasures. Climb the nine hills; do not go after them. After seven days you get them back.",
            "Thunder comes and makes one helpless. If the thunder stirs one to action, one remains free of fate.",
            "Thunder is bogged down in the mud.",
            "Thunder goes hither and thither. Danger. However, nothing is lost; there are things to do.",
            "Thunder brings ruin and terrified gazing around. Going ahead brings misfortune. If it has not yet reached oneself, but has reached one's neighbor, no blame."
        ]
    ),
    "001001": (
        52, "艮", "Gèn", "Keeping Still, Mountain",
        "Meditation, stopping action at the right time, spine alignment",
        "Keeping Still. Keeping his back still so that he no longer feels his body. He goes into his courtyard and does not see his people. No blame.",
        "Double mountain: the image of Keeping Still. Thus the superior man does not let his thoughts go beyond his situation.",
        [
            "Keeping his toes still. No blame. Continued perseverance furthers.",
            "Keeping his calves still. He cannot rescue him whom he follows. His heart is not glad.",
            "Keeping his hips still. Making his sacrum rigid. Dangerous. The heart suffocates.",
            "Keeping his torso still. No blame.",
            "Keeping his jaws still. His words have order. Remorse disappears.",
            "Noble keeping still. Good fortune."
        ]
    ),
    "001011": (
        53, "渐", "Jiàn", "Development [Gradual Progress]",
        "Slow progress, wild geese flying in formation",
        "Development. The maiden is given in marriage. Good fortune. Perseverance furthers.",
        "On the mountain, a tree: the image of Development. Thus the superior man abides in dignity and improves the customs.",
        [
            "The wild geese gradually draw near the shore. The young son is in danger. Gossip. No blame.",
            "The wild geese gradually draw near the cliff. Eating and drinking in peace and concord. Good fortune.",
            "The wild geese gradually draw near the plateau. The husband goes forth and does not return. The wife bears a child but cannot nurture it. Misfortune.",
            "The wild geese gradually draw near the tree. They find a flat branch. No blame.",
            "The wild geese gradually draw near the summit. The wife bears no child for three years. In the end, nothing can defeat her. Good fortune.",
            "The wild geese gradually draw near the cloud heights. Their feathers can be used for the sacred dance. Good fortune."
        ]
    ),
    "110100": (
        54, "归妹", "Guī Mèi", "The Marrying Maiden",
        "Impulsive action before correctness, lack of authority",
        "The Marrying Maiden. Undertakings bring misfortune. Nothing that would further.",
        "Thunder over the lake: the image of the Marrying Maiden. Thus the superior man understands the transitory in contrast to the eternal.",
        [
            "The marrying maiden as a concubine. A lame man who can tread. Undertakings bring good fortune.",
            "A one-eyed man who can see. The perseverance of a solitary man furthers.",
            "The marrying maiden as a slave. She marries as a concubine.",
            "The marrying maiden draws out the time. A late marriage comes in its own time.",
            "The sovereign sovereign gives his daughter in marriage. The sleeves of the princess were not so gorgeous as those of her maid. The moon is almost full. Good fortune.",
            "The woman holds the basket, but there are no fruits in it. The man slaughters the sheep, but no blood flows. Nothing furthers."
        ]
    ),
    "101100": (
        55, "丰", "Fēng", "Abundance",
        "Peak illumination, transient glory, preparing for decline",
        "Abundance has success. The king attains abundance. Be not sad. Be like the sun at midday.",
        "Thunder and lightning: the image of Abundance. Thus the superior man decides lawsuits and carries out punishments.",
        [
            "When a man meets his destined ruler, they can be together for ten days without blame. To go brings recognition.",
            "The curtain is of such fullness that the polestar can be seen at noon. Going brings distrust. If one rouses him by sincerity, good fortune comes.",
            "The underbrush is of such abundance that the small stars can be seen at noon. He breaks his right arm. No blame.",
            "The screen is of such fullness that the polestar can be seen at noon. He meets his ruler who is of like mind. Good fortune.",
            "Lines are coming. Blessing and fame draw near. Good fortune.",
            "His house is in a state of abundance. He screens off his family. He peers through the gate and no longer perceives anyone. For three years he sees nothing. Misfortune."
        ]
    ),
    "001101": (
        56, "旅", "Lǚ", "The Wanderer",
        "Moving through foreign lands, cautious behavior, temporary shelter",
        "The Wanderer. Success through smallness. Perseverance brings good fortune to the wanderer.",
        "Fire on the mountain: the image of the Wanderer. Thus the superior man is clear-minded and cautious in imposing penalties.",
        [
            "If the wanderer busies himself with trivial things, he draws down misfortune upon himself.",
            "The wanderer comes to an inn. He has his property with him. He wins the loyalty of a young servant.",
            "The wanderer's inn burns down. He loses the loyalty of his young servant. Danger.",
            "The wanderer rests in a shelter. He acquires his property and a sharp axe. Yet he feels in his heart: 'I am not at home.'",
            "He shoots a pheasant. It falls with the first arrow. In the end, he receives praise and high office.",
            "The bird's nest burns up. The wanderer first laughs, then laments and weeps. Through carelessness he loses his cow. Misfortune."
        ]
    ),
    "011011": (
        57, "巽", "Xùn", "The Gentle (Wind)",
        "Penetrating influence, flexibility, persistent action",
        "The Gentle. Success through smallness. It furthers one to have somewhere to go. It furthers one to see the great man.",
        "Wind following wind: the image of the Gentle. Thus the superior man disseminates his commands and carries out his undertakings.",
        [
            "In advancing and retreating, the perseverance of a warrior furthers.",
            "Submissiveness under the bed. Appointing priests and magicians in great numbers brings good fortune. No blame.",
            "Repeated submissiveness. Humiliation.",
            "Remorse disappears. During the hunt three kinds of game are caught.",
            "Perseverance brings good fortune. Remorse disappears. Nothing that does not further. No beginning, but an end. Before the change three days, after the change three days.",
            "Submissiveness under the bed. He loses his property and his axes. Perseverance brings misfortune."
        ]
    ),
    "110110": (
        58, "兑", "Duì", "The Joyous, Lake",
        "Joy, shared discourse, friendly persuasion, openness",
        "The Joyous. Success. Perseverance furthers.",
        "Lakes resting one on the other: the image of the Joyous. Thus the superior man joins with his friends for discussion and practice.",
        [
            "Contented joy. Good fortune.",
            "Sincere joy. Good fortune. Remorse disappears.",
            "Coming joy. Misfortune.",
            "Deliberate joy is not at peace. After weeding out mistakes, one has joy.",
            "Sincerity toward disintegrating influences is dangerous.",
            "Seductive joy."
        ]
    ),
    "010011": (
        59, "涣", "Huàn", "Dispersion [Dissolution]",
        "Dissolving blockages, crossing the great water",
        "Dispersion. Success. The king approaches his temple. It furthers one to cross the great water. Perseverance furthers.",
        "Wind drives over the water: the image of Dispersion. Thus the ancient kings made sacrifice to heaven and established temples.",
        [
            "He brings help with the strength of a horse. Good fortune.",
            "At the dissolution, he runs to his support. Remorse disappears.",
            "He dissolves his self. No remorse.",
            "He dissolves his bond with his group. Supreme good fortune. Dispersion leads in turn to accumulation.",
            "At the dissolution, he loud-cries out. Dissolution of royal treasures. No blame.",
            "He dissolves his blood. Departing, keeping at a distance, going out of harm's way. No blame."
        ]
    ),
    "110010": (
        60, "节", "Jié", "Limitation",
        "Frugality, boundary definition, keeping moderation",
        "Limitation. Success. Galling limitation must not be persevered in.",
        "Water over the lake: the image of Limitation. Thus the superior man creates number and measure, and examines virtue and conduct.",
        [
            "Not going out of the gate and courtyard. No blame.",
            "Not going out of the gate and courtyard brings misfortune.",
            "He who knows no limitation will have cause to lament. No blame.",
            "Sweet limitation. Success.",
            "Delightful limitation. Good fortune. To go brings esteem.",
            "Galling limitation. To remain persevering brings misfortune. Remorse disappears."
        ]
    ),
    "110011": (
        61, "中孚", "Zhōng Fú", "Inner Truth",
        "Pigs and fishes aligned, supreme sincerity, faith",
        "Inner Truth. Pigs and fishes. Good fortune. It furthers one to cross the great water. Perseverance furthers.",
        "Wind over the lake: the image of Inner Truth. Thus the superior man discusses litigation in order to delay execution.",
        [
            "Being prepared brings good fortune. If there are secret designs, it is disquieting.",
            "A crane calling in the shade. Its young answers it. I have a good goblet. I will share it with you.",
            "He finds a comrade. Now he beats the drum, now he stops. Now he sobs, now he sings.",
            "The moon is nearly full. The team horse goes astray. No blame.",
            "He possesses truth, which binds together. No blame.",
            "Cockcrow mounting to heaven. Perseverance brings misfortune."
        ]
    ),
    "001100": (
        62, "小过", "Hsiao Kuo", "Preponderance of the Small",
        "Keeping low, avoiding flight, attention to detail",
        "Preponderance of the Small. Success. Perseverance furthers. Small things may be done; great things should not be done. The flying bird brings the message: It is not well to strive upward, it is well to remain below.",
        "Thunder on the mountain: the image of Preponderance of the Small. Thus the superior man in his conduct is exceptionally respectful.",
        [
            "The bird meets with misfortune through flying.",
            "She passes by her ancestor and meets her ancestress. He does not reach his prince and meets the official. No blame.",
            "If one is not exceptionally cautious, someone may strike him from behind. Misfortune.",
            "No blame. One meets him without passing by. Going brings danger. One must be on one's guard. Do not act.",
            "Dense clouds, no rain from our western territory. The prince shoots and hits the other in the cave.",
            "He passes him by, not meeting him. The flying bird leaves him. Misfortune. This means disaster and injury."
        ]
    ),
    "101010": (
        63, "既济", "Jì Jì", "After Completion",
        "Boiling water on fire, perfect order fading to chaos",
        "After Completion. Success in small matters. Perseverance furthers. At the beginning good fortune, at the end disorder.",
        "Water over fire: the image of After Completion. Thus the superior man takes thought of misfortune and defends against it beforehand.",
        [
            "He drags his wheel. He gets his tail in the water. No blame.",
            "The woman loses the screen for her carriage. Do not run after it; after seven days you will get it back.",
            "The illustrious ancestor disciplines the Devil's Country. After three years he conquers it. Inferior people must not be employed.",
            "The finest clothes turn to rags. Be on guard all day long.",
            "The neighbor in the east slaughters an ox, but does not attain as much real blessing as the neighbor in the west with his small offering.",
            "He gets his head in the water. Danger."
        ]
    ),
    "010101": (
        64, "未济", "Wèi Jì", "Before Completion",
        "Fire above water, potential, the young fox wetting its tail",
        "Before Completion. Success. But if the young fox, when he has almost completed the crossing, gets his tail in the water, nothing furthers.",
        "Fire over water: the image of Before Completion. Thus the superior man is careful in separating things.",
        [
            "He gets his tail in the water. Humiliation.",
            "He drags his wheel. Perseverance brings good fortune.",
            "Before completion, attack brings misfortune. It furthers to cross the great water.",
            "Perseverance brings good fortune. Remorse disappears. Shock to discipline the Devil's Country. For three years great rewards are bestowed.",
            "Perseverance brings good fortune. No remorse. The light of the superior man is true. Good fortune.",
            "There is drinking of wine in full trust. No blame. But if one wets his head, he loses truth."
        ]
    )
}

def generate():
    output_path = Path(__file__).resolve().parent.parent / "knowledge" / "iching.json"
    
    # Format database
    db = {
        "version": "1.0",
        "source": "Classic I Ching / Wilhelm-Baynes Translation (public domain)",
        "hexagrams": []
    }
    
    for pattern, data in HEXAGRAM_DATA.items():
        num, ch, pin, eng, mean, judg, img, lines = data
        db["hexagrams"].append({
            "number": num,
            "pattern": pattern,
            "name_chinese": ch,
            "name_pinyin": pin,
            "name_english": eng,
            "meaning": mean,
            "judgment": judg,
            "images": img,
            "lines": lines
        })
    
    # Sort by hexagram number
    db["hexagrams"].sort(key=lambda x: x["number"])
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    print(f"Generated {len(db['hexagrams'])} hexagrams in {output_path}")

if __name__ == "__main__":
    generate()
