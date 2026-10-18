"""
BhashaBridge — Contrastive Grammar Rule Engine (M4 Enhanced)
Encodes explicit grammatical differences, structural contrasts, and
curated beginner-friendly parallel examples between Hindi and Marathi.
"""

from typing import Dict, List, Optional
from app.schemas.analyze import GrammarPoint, ExampleItem

class ContrastiveGrammarRule:
    def __init__(
        self,
        rule_id: str,
        title: str,
        concept: str,
        source_pattern: str,
        target_pattern: str,
        explanation: str,
        triggers: List[str],
        contrast_insight: Optional[str] = None,
        examples: Optional[List[ExampleItem]] = None
    ):
        self.rule_id = rule_id
        self.title = title
        self.concept = concept
        self.source_pattern = source_pattern
        self.target_pattern = target_pattern
        self.explanation = explanation
        self.triggers = [t.lower() for t in triggers]
        self.contrast_insight = contrast_insight or explanation
        self.examples = examples or []

    def matches(self, text: str) -> bool:
        lower_text = text.lower()
        return any(t in lower_text for t in self.triggers)

    def to_grammar_point(self) -> GrammarPoint:
        return GrammarPoint(
            title=self.title,
            concept=self.concept,
            source_pattern=self.source_pattern,
            target_pattern=self.target_pattern,
            explanation=self.explanation
        )

# Comprehensive library of Hindi-Marathi contrastive rules with parallel examples
GRAMMAR_RULES: List[ContrastiveGrammarRule] = [
    ContrastiveGrammarRule(
        rule_id="temporal_kal_udya",
        title="Temporal Distinction ('कल' vs 'उद्या')",
        concept="temporal_distinction",
        source_pattern="कल (kal)",
        target_pattern="उद्या (udya) / काल (kaal)",
        explanation="Hindi 'कल' is ambiguous and denotes either yesterday or tomorrow depending solely on verb tense. Marathi strictly requires 'उद्या' (udya) for tomorrow and 'काल' (kaal) for yesterday.",
        triggers=["कल", "kal", "उद्या", "udya", "काल", "kaal"],
        contrast_insight="Temporal Clarity: Hindi 'कल' relies entirely on tense context; Marathi never confuses them: 'उद्या' (future) vs 'काल' (past).",
        examples=[
            ExampleItem(
                source_sentence="मैं कल कॉलेज जाऊँगा।",
                target_sentence="मी उद्या कॉलेजला जाईन।",
                target_roman="Mi udya college-la jaain.",
                english_translation="I will go to college tomorrow."
            ),
            ExampleItem(
                source_sentence="कल बहुत बारिश हुई थी।",
                target_sentence="काल खूप पाऊस पडला होता।",
                target_roman="Kaal khoop paaus padla hota.",
                english_translation="It rained a lot yesterday."
            ),
            ExampleItem(
                source_sentence="हम कल मिलेंगे।",
                target_sentence="आपण उद्या भेटू।",
                target_roman="Aapan udya bhetu.",
                english_translation="We will meet tomorrow."
            )
        ]
    ),
    ContrastiveGrammarRule(
        rule_id="dative_want_need",
        title="Expressing Want/Need ('चाहिए' vs 'पाहिजे')",
        concept="dative_want_modal",
        source_pattern="मुझे ... चाहिए (chahiye)",
        target_pattern="मला ... पाहिजे / हवं (pahije)",
        explanation="Both Hindi and Marathi express desire with dative subjects ('मुझे' / 'मला'), but Marathi uses 'पाहिजे' (pahije) or 'हवं' (hava) and inflects to 'पाहिजेत' for plural items.",
        triggers=["चाहिए", "chahiye", "पाहिजे", "pahije", "हवं", "hava", "हवे"],
        contrast_insight="Subject Case & Modal Agreement: 'मला' (to me) + object + 'पाहिजे'. Plural objects take 'पाहिजेत' (उदा. 'पुस्तके पाहिजेत').",
        examples=[
            ExampleItem(
                source_sentence="मुझे एक कप चाय चाहिए।",
                target_sentence="मला एक कप चहा पाहिजे।",
                target_roman="Mala ek cup chaha pahije.",
                english_translation="I want a cup of tea."
            ),
            ExampleItem(
                source_sentence="मुझे दो किताबें चाहिए।",
                target_sentence="मला दोन पुस्तके पाहिजेत।",
                target_roman="Mala don pustake pahijet.",
                english_translation="I want two books (plural agreement)."
            ),
            ExampleItem(
                source_sentence="तुम्हें क्या चाहिए?",
                target_sentence="तुला काय पाहिजे?",
                target_roman="Tula kay pahije?",
                english_translation="What do you want?"
            )
        ]
    ),
    ContrastiveGrammarRule(
        rule_id="dative_obligation",
        title="Dative Obligation ('-ना है' vs '-चं आहे')",
        concept="obligation_construction",
        source_pattern="मुझे ... जाना है (jaana hai)",
        target_pattern="मला ... जायचं आहे (jaycha aahe)",
        explanation="Expressing obligation ('have to / must') in Marathi pairs the dative subject 'मला' (to me) with a neuter potential participle ending in '-चं' ('जायचं', 'करायचं', 'शिकायचं') and present auxiliary 'आहे'.",
        triggers=["जाना है", "jaana hai", "जायचं", "jaycha", "करायचं", "karaycha", "करना है", "karna hai", "सीखनी है", "shikaychi"],
        contrast_insight="Obligation Modal Suffix: Hindi uses bare infinitive + auxiliary ('जाना है'), whereas Marathi uses neuter potential participle '-चं' + 'आहे' ('जायचं आहे').",
        examples=[
            ExampleItem(
                source_sentence="मुझे घर जाना है।",
                target_sentence="मला घरी जायचं आहे।",
                target_roman="Mala ghari jaycha aahe.",
                english_translation="I have to go home."
            ),
            ExampleItem(
                source_sentence="मुझे पानी पीना है।",
                target_sentence="मला पाणी प्यायचं आहे।",
                target_roman="Mala paani pyaycha aahe.",
                english_translation="I want to drink water."
            ),
            ExampleItem(
                source_sentence="मुझे आज काम करना है।",
                target_sentence="मला आज काम करायचं आहे।",
                target_roman="Mala aaj kaam karaycha aahe.",
                english_translation="I have to do work today."
            )
        ]
    ),
    ContrastiveGrammarRule(
        rule_id="dative_destination_la",
        title="Dative Destination Suffix ('-ला')",
        concept="dative_postposition_la",
        source_pattern="कॉलेज जाना / घर जाना",
        target_pattern="कॉलेजला / ऑफिसला (-la)",
        explanation="Marathi attaches the dative postposition '-ला' (-la) directly to destination nouns (e.g. 'कॉलेजला', 'ऑफिसला') to indicate direction or recipient. Colloquial Hindi often leaves destinations unmarked.",
        triggers=["college", "कॉलेज", "office", "ऑफिस", "स्टेशन", "station", "शाळा", "दुकान", "बाजार"],
        contrast_insight="Synthetic Destination Marker: Marathi explicitly suffixes '-ला' to destination nouns ('कॉलेज' -> 'कॉलेजला'), while Hindi leaves it bare.",
        examples=[
            ExampleItem(
                source_sentence="मुझे ऑफिस जाना है।",
                target_sentence="मला ऑफिसला जायचं आहे।",
                target_roman="Mala officela jaycha aahe.",
                english_translation="I have to go to the office."
            ),
            ExampleItem(
                source_sentence="वह स्टेशन जा रहा है।",
                target_sentence="तो स्टेशनला जात आहे।",
                target_roman="To stationla jaat aahe.",
                english_translation="He is going to the station."
            ),
            ExampleItem(
                source_sentence="हम बाज़ार जा रहे हैं।",
                target_sentence="आम्ही बाजारात जात आहोत।",
                target_roman="Aamhi bajaarat jaat aahot.",
                english_translation="We are going to the market."
            )
        ]
    ),
    ContrastiveGrammarRule(
        rule_id="neuter_gender_nouns",
        title="Neuter Gender Category in Marathi",
        concept="neuter_grammatical_gender",
        source_pattern="पानी (M) / किताब (F)",
        target_pattern="पाणी (N) / पुस्तक (N)",
        explanation="Unlike Hindi which only has Masculine and Feminine genders, Marathi preserves the ancestral Indo-Aryan Neuter gender. Common nouns like 'पाणी' (water), 'पुस्तक' (book), and 'जेवण' (meal) are neuter and take neuter verb/adjective agreements (e.g., 'थोडं पाणी', 'चांगलं पुस्तक').",
        triggers=["पाणी", "paani", "पानी", "पुस्तक", "pustak", "किताब", "जेवण", "jevan", "नाव", "naav", "नाम"],
        contrast_insight="Three-Gender System: Marathi features a 3rd grammatical gender (नपुंसकलिंग / Neuter). Modifiers take neuter endings ('माझं नाव', 'थोडं पाणी').",
        examples=[
            ExampleItem(
                source_sentence="मुझे ठंडा पानी चाहिए।",
                target_sentence="मला थंड पाणी पाहिजे।",
                target_roman="Mala thand paani pahije.",
                english_translation="I want cold water (water is neuter)."
            ),
            ExampleItem(
                source_sentence="यह मेरी किताब है।",
                target_sentence="हे माझं पुस्तक आहे।",
                target_roman="He mazha pustak aahe.",
                english_translation="This is my book (book is neuter: 'हे' / 'माझं')."
            ),
            ExampleItem(
                source_sentence="तुम्हारा नाम क्या है?",
                target_sentence="तुझं नाव काय आहे?",
                target_roman="Tuzha naav kay aahe?",
                english_translation="What is your name? ('नाव' is neuter: 'तुझं')."
            )
        ]
    ),
    ContrastiveGrammarRule(
        rule_id="locative_inflection",
        title="Direct Locative Suffix ('-त' / '-ी')",
        concept="locative_synthetic_case",
        source_pattern="पुणे में / घर पर / नाश्ते में",
        target_pattern="पुण्यात / घरी / नाश्त्यात",
        explanation="Marathi frequently uses synthetic case suffixes '-त' (in) and '-ी' (at/home) directly attached to an inflected oblique noun root (e.g. 'पुण्यात' = in Pune, 'घरी' = at home), whereas Hindi uses independent postpositions ('में', 'पर').",
        triggers=["घरी", "ghari", "पुण्यात", "punyat", "नाश्त्यात", "nashtyaat", "बाजारात", "bajarat", "घर पर", "में"],
        contrast_insight="Locative Suffixation: Hindi uses analytic postpositions ('घर पर', 'पुणे में'), while Marathi fuses suffixes directly into nouns ('घरी', 'पुण्यात').",
        examples=[
            ExampleItem(
                source_sentence="मैं घर पर हूँ।",
                target_sentence="मी घरी आहे।",
                target_roman="Mi ghari aahe.",
                english_translation="I am at home."
            ),
            ExampleItem(
                source_sentence="वह पुणे में रहता है।",
                target_sentence="तो पुण्यात राहतो।",
                target_roman="To Punyat rahato.",
                english_translation="He lives in Pune."
            ),
            ExampleItem(
                source_sentence="चाय में चीनी कम है।",
                target_sentence="चहात साखर कमी आहे।",
                target_roman="Chahaat saakhar kami aahe.",
                english_translation="There is less sugar in the tea."
            )
        ]
    ),
    ContrastiveGrammarRule(
        rule_id="inclusive_exclusive_we",
        title="Inclusive vs Exclusive 'We' ('आम्ही' vs 'आपण')",
        concept="clusivity_pronoun",
        source_pattern="हम (hum)",
        target_pattern="आम्ही (exclusive) / आपण (inclusive)",
        explanation="Marathi strictly distinguishes 'आम्ही' (we excluding the listener) from 'आपण' (we including the listener). Hindi uses 'हम' for both, often leading to communicative ambiguity.",
        triggers=["हम", "hum", "आम्ही", "aamhi", "आपण", "aapan"],
        contrast_insight="Clusivity Distinction: Marathi has two words for 'we': 'आपण' (includes the listener) and 'आम्ही' (excludes the listener).",
        examples=[
            ExampleItem(
                source_sentence="हम खाना खाने जा रहे हैं (आप भी चलिए)।",
                target_sentence="आपण जेवायला जाऊया।",
                target_roman="Aapan jevayala jaauya.",
                english_translation="Let's go eat (inclusive 'आपण' includes you)."
            ),
            ExampleItem(
                source_sentence="हम कल निकल रहे हैं (तुम्हें छोड़कर)।",
                target_sentence="आम्ही उद्या निघत आहोत।",
                target_roman="Aamhi udya nighat aahot.",
                english_translation="We are leaving tomorrow (exclusive 'आम्ही' excludes you)."
            )
        ]
    ),
    ContrastiveGrammarRule(
        rule_id="feminine_language_agreement",
        title="Language Name Gender Agreement",
        concept="language_gender_agreement",
        source_pattern="मराठी सीखनी (seekhni)",
        target_pattern="मराठी शिकायची (shikaychi)",
        explanation="In both Hindi and Marathi, names of spoken languages (मराठी, हिंदी, इंग्रजी) are grammatically feminine. Verbs agreeing with language names reflect feminine inflection ('सीखनी है' / 'शिकायची आहे').",
        triggers=["मराठी", "marathi", "हिंदी", "hindi", "इंग्रजी", "english", "seekhni", "shikaychi"],
        contrast_insight="Feminine Language Agreement: Languages are grammatically feminine, so modal verbs inflect to feminine: 'शिकायची आहे', 'बोलायची आहे'.",
        examples=[
            ExampleItem(
                source_sentence="मुझे मराठी सीखनी है।",
                target_sentence="मला मराठी शिकायची आहे।",
                target_roman="Mala Marathi shikaychi aahe.",
                english_translation="I want to learn Marathi."
            ),
            ExampleItem(
                source_sentence="उसे अच्छी हिंदी आती है।",
                target_sentence="त्याला चांगली हिंदी येते।",
                target_roman="Tyala chaangli Hindi yete.",
                english_translation="He knows good Hindi."
            )
        ]
    ),
    ContrastiveGrammarRule(
        rule_id="habitual_present_agreement",
        title="Habitual Present Verb Inflection",
        concept="habitual_verb_inflection",
        source_pattern="जाता हूँ / खाती हूँ",
        target_pattern="जातो (M) / जाते (F)",
        explanation="Marathi 1st person habitual present is expressed by suffixing '-तो' (masculine) or '-ते' (feminine) directly to the verb root ('मी जातो' = I go [M], 'मी जाते' = I go [F]), omitting the auxiliary.",
        triggers=["जाता हूँ", "jaata hoon", "उठता हूँ", "uthta hoon", "खाता हूँ", "khaata hoon", "जातो", "जाते", "खातो"],
        contrast_insight="Auxiliary-Free Habitual Tense: Hindi says 'जाता हूँ' (root + ta + hoon); Marathi says 'जातो' (M) or 'जाते' (F) without 'आहे'.",
        examples=[
            ExampleItem(
                source_sentence="मैं रोज़ सुबह उठता हूँ।",
                target_sentence="मी रोज सकाळी उठतो।",
                target_roman="Mi roj sakaali uthto.",
                english_translation="I wake up every morning (masculine speaker)."
            ),
            ExampleItem(
                source_sentence="मैं कॉलेज जाती हूँ।",
                target_sentence="मी कॉलेजला जाते।",
                target_roman="Mi college-la jaate.",
                english_translation="I go to college (feminine speaker)."
            )
        ]
    ),
    ContrastiveGrammarRule(
        rule_id="present_continuous_aspect",
        title="Present Continuous Aspect ('-रहा हूँ' vs '-त आहे')",
        concept="continuous_aspect",
        source_pattern="जा रहा हूँ / आ रहा हूँ (-raha hoon)",
        target_pattern="जात आहे / येत आहे (-t aahe)",
        explanation="Hindi forms continuous aspect using the separate auxiliary participle 'रहा हूँ / रहे हैं' ('मैं जा रहा हूँ' = I am going). Marathi directly suffixes imperfective '-त' (-t) to the verb root plus 'आहे' ('मी जात आहे'). Notice Marathi has no separate word for 'रहा'; the '-त' suffix fulfills that role.",
        triggers=["रहा", "raha", "रही", "rahi", "रहे", "rahe", "जात आहे", "jaat aahe", "येत आहे", "करत आहे", "खात आहे"],
        contrast_insight="Aspect Suffix vs Particle: Marathi has no separate word for Hindi 'रहा'; instead, it attaches the suffix '-त' directly to the verb stem ('जात आहे').",
        examples=[
            ExampleItem(
                source_sentence="मैं चाय पी रहा हूँ।",
                target_sentence="मी चहा पीत आहे।",
                target_roman="Mi chaha peet aahe.",
                english_translation="I am drinking tea."
            ),
            ExampleItem(
                source_sentence="वह क्या कर रहा है?",
                target_sentence="तो काय करत आहे?",
                target_roman="To kay karat aahe?",
                english_translation="What is he doing?"
            ),
            ExampleItem(
                source_sentence="हम फिल्म देख रहे हैं।",
                target_sentence="आम्ही चित्रपट बघत आहोत।",
                target_roman="Aamhi chitrapat baghat aahot.",
                english_translation="We are watching a movie."
            )
        ]
    ),
    ContrastiveGrammarRule(
        rule_id="spatial_deixis_yaha_vaha",
        title="Place Adverbs ('यहाँ / वहाँ' vs 'इथे / तिथे')",
        concept="spatial_deixis",
        source_pattern="यहाँ (yahan) / वहाँ (vahan)",
        target_pattern="इथे (ithe) / तिथे (tithe)",
        explanation="Spatial adverbs exhibit direct sound correspondences: Hindi 'यहाँ' corresponds to Marathi 'इथे', and Hindi 'वहाँ' corresponds to Marathi 'तिथे'.",
        triggers=["यहाँ", "yaha", "yahan", "वहाँ", "vaha", "vahan", "इथे", "ithe", "तिथे", "tithe", "teethe"],
        contrast_insight="Phonetic Shift in Location Adverbs: Hindi 'यहाँ' corresponds to Marathi 'इथे', and 'वहाँ' corresponds to 'तिथे'.",
        examples=[
            ExampleItem(
                source_sentence="यहाँ बैठो।",
                target_sentence="इथे बसा।",
                target_roman="Ithe basa.",
                english_translation="Sit here."
            ),
            ExampleItem(
                source_sentence="वहाँ कौन है?",
                target_sentence="तिथे कोण आहे?",
                target_roman="Tithe kon aahe?",
                english_translation="Who is there?"
            )
        ]
    ),
    ContrastiveGrammarRule(
        rule_id="yes_no_question_tag_ka",
        title="Yes/No Question Marker ('क्या ... ?' vs '... का?')",
        concept="polar_question_syntax",
        source_pattern="क्या ... ? (Kya ... ?)",
        target_pattern="... का? (... ka?)",
        explanation="In Hindi, yes/no questions start with 'क्या' ('क्या सब ठीक है?'). In Marathi, speakers place the question particle 'का' (ka) at the end of the sentence ('सगळं ठीक आहे का?').",
        triggers=["क्या", "kya", "का?", "ka?", "का"],
        contrast_insight="Question Word Order: Hindi begins yes/no questions with 'क्या', while Marathi appends 'का' (ka) to the end.",
        examples=[
            ExampleItem(
                source_sentence="क्या सब ठीक है?",
                target_sentence="सगळं ठीक आहे का?",
                target_roman="Sagla theek aahe ka?",
                english_translation="Is everything fine?"
            ),
            ExampleItem(
                source_sentence="क्या तुम तैयार हो?",
                target_sentence="तू तयार आहेस का?",
                target_roman="Tu tayaar aahes ka?",
                english_translation="Are you ready?"
            )
        ]
    )
]

def find_matching_grammar_rules(source_text: str, target_text: str) -> List[GrammarPoint]:
    """Finds all applicable contrastive grammar points for a given sentence pair (backwards-compatible)."""
    rules = get_matching_rules(source_text, target_text)
    return [r.to_grammar_point() for r in rules]

def get_matching_rules(source_text: str, target_text: str) -> List[ContrastiveGrammarRule]:
    """Finds all applicable ContrastiveGrammarRule objects with examples and contrast insights."""
    combined = f"{source_text} {target_text}"
    matched: List[ContrastiveGrammarRule] = []
    seen = set()

    for rule in GRAMMAR_RULES:
        if rule.matches(combined) and rule.rule_id not in seen:
            seen.add(rule.rule_id)
            matched.append(rule)

    # Fallback default rule if none matched
    if not matched:
        matched.append(ContrastiveGrammarRule(
            rule_id="sov_syntax",
            title="SOV Word Order & Postposition Structure",
            concept="sov_syntax",
            source_pattern="Subject + Object + Verb",
            target_pattern="Subject + Object + Verb",
            explanation="Both Hindi and Marathi share core Subject-Object-Verb (SOV) sentence order and postpositional phrasing.",
            triggers=[],
            contrast_insight="Sentence Structure: Both languages follow Subject-Object-Verb order, but Marathi suffixes postpositions directly to nouns.",
            examples=[
                ExampleItem(
                    source_sentence="मैं चाय पीता हूँ।",
                    target_sentence="मी चहा पितो।",
                    target_roman="Mi chaha peeto.",
                    english_translation="I drink tea (SOV structure)."
                )
            ]
        ))

    return matched
