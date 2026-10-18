"""
BhashaBridge — Contrastive Grammar Rule Engine (M4)
Encodes explicit grammatical differences and structural contrasts between
Hindi and Marathi without relying on opaque LLM hallucinations.
"""

from typing import Dict, List, Optional
from app.schemas.analyze import GrammarPoint

class ContrastiveGrammarRule:
    def __init__(self, rule_id: str, title: str, concept: str, source_pattern: str, target_pattern: str, explanation: str, triggers: List[str]):
        self.rule_id = rule_id
        self.title = title
        self.concept = concept
        self.source_pattern = source_pattern
        self.target_pattern = target_pattern
        self.explanation = explanation
        self.triggers = [t.lower() for t in triggers]

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

# Comprehensive library of Hindi-Marathi contrastive rules
GRAMMAR_RULES: List[ContrastiveGrammarRule] = [
    ContrastiveGrammarRule(
        rule_id="temporal_kal_udya",
        title="Temporal Distinction ('कल' vs 'उद्या')",
        concept="temporal_distinction",
        source_pattern="कल (kal)",
        target_pattern="उद्या (udya) / काल (kaal)",
        explanation="Hindi 'कल' is ambiguous and denotes either yesterday or tomorrow depending solely on verb tense. Marathi strictly requires 'उद्या' (udya) for tomorrow and 'काल' (kaal) for yesterday.",
        triggers=["कल", "kal", "उद्या", "udya", "काल", "kaal"]
    ),
    ContrastiveGrammarRule(
        rule_id="dative_obligation",
        title="Dative Obligation ('-ना है' vs '-चं आहे')",
        concept="obligation_construction",
        source_pattern="मुझे ... जाना है (jaana hai)",
        target_pattern="मला ... जायचं आहे (jaycha aahe)",
        explanation="Expressing obligation ('have to / must') in Marathi pairs the dative subject 'मला' (to me) with a neuter potential participle ending in '-चं' ('जायचं', 'करायचं', 'शिकायचं') and present auxiliary 'आहे'.",
        triggers=["जाना है", "jaana hai", "जायचं", "jaycha", "करायचं", "karaycha", "करना है", "karna hai", "सीखनी है", "shikaychi"]
    ),
    ContrastiveGrammarRule(
        rule_id="dative_destination_la",
        title="Dative Destination Suffix ('-ला')",
        concept="dative_postposition_la",
        source_pattern="कॉलेज जाना / घर जाना",
        target_pattern="कॉलेजला / ऑफिसला (-la)",
        explanation="Marathi attaches the dative postposition '-ला' (-la) directly to destination nouns (e.g. 'कॉलेजला', 'ऑफिसला') to indicate direction or recipient. Colloquial Hindi often leaves destinations unmarked.",
        triggers=["college", "कॉलेज", "office", "ऑफिस", "स्टेशन", "station", "शाळा"]
    ),
    ContrastiveGrammarRule(
        rule_id="neuter_gender_nouns",
        title="Neuter Gender Category in Marathi",
        concept="neuter_grammatical_gender",
        source_pattern="पानी (M) / किताब (F)",
        target_pattern="पाणी (N) / पुस्तक (N)",
        explanation="Unlike Hindi which only has Masculine and Feminine genders, Marathi preserves the ancestral Indo-Aryan Neuter gender. Common nouns like 'पाणी' (water), 'पुस्तक' (book), and 'जेवण' (meal) are neuter and take neuter verb/adjective agreements (e.g., 'थोडं पाणी', 'चांगलं पुस्तक').",
        triggers=["पाणी", "paani", "पानी", "पुस्तक", "pustak", "किताब", "जेवण", "jevan", "नाव", "naav", "नाम"]
    ),
    ContrastiveGrammarRule(
        rule_id="locative_inflection",
        title="Direct Locative Suffix ('-त' / '-ी')",
        concept="locative_synthetic_case",
        source_pattern="पुणे में / घर पर / नाश्ते में",
        target_pattern="पुण्यात / घरी / नाश्त्यात",
        explanation="Marathi frequently uses synthetic case suffixes '-त' (in) and '-ी' (at/home) directly attached to an inflected oblique noun root (e.g. 'पुण्यात' = in Pune, 'घरी' = at home), whereas Hindi uses independent postpositions ('में', 'पर').",
        triggers=["घरी", "ghari", "पुण्यात", "punyat", "नाश्त्यात", "nashtyaat", "बाजारात", "bajarat"]
    ),
    ContrastiveGrammarRule(
        rule_id="inclusive_exclusive_we",
        title="Inclusive vs Exclusive 'We' ('आम्ही' vs 'आपण')",
        concept="clusivity_pronoun",
        source_pattern="हम (hum)",
        target_pattern="आम्ही (exclusive) / आपण (inclusive)",
        explanation="Marathi strictly distinguishes 'आम्ही' (we excluding the listener) from 'आपण' (we including the listener). Hindi uses 'हम' for both, often leading to communicative ambiguity.",
        triggers=["हम", "hum", "आम्ही", "aamhi", "आपण", "aapan"]
    ),
    ContrastiveGrammarRule(
        rule_id="feminine_language_agreement",
        title="Language Name Gender Agreement",
        concept="language_gender_agreement",
        source_pattern="मराठी सीखनी (seekhni)",
        target_pattern="मराठी शिकायची (shikaychi)",
        explanation="In both Hindi and Marathi, names of spoken languages (मराठी, हिंदी, इंग्रजी) are grammatically feminine. Verbs agreeing with language names reflect feminine inflection ('सीखनी है' / 'शिकायची आहे').",
        triggers=["मराठी", "marathi", "हिंदी", "hindi", "इंग्रजी", "english", "seekhni", "shikaychi"]
    ),
    ContrastiveGrammarRule(
        rule_id="habitual_present_agreement",
        title="Habitual Present Verb Inflection",
        concept="habitual_verb_inflection",
        source_pattern="जाता हूँ / खाती हूँ",
        target_pattern="जातो (M) / जाते (F)",
        explanation="Marathi 1st person habitual present is expressed by suffixing '-तो' (masculine) or '-ते' (feminine) directly to the verb root ('मी जातो' = I go [M], 'मी जाते' = I go [F]), omitting the auxiliary.",
        triggers=["जाता हूँ", "jaata hoon", "उठता हूँ", "uthta hoon", "खाता हूँ", "khaata hoon", "जातो", "जाते", "खातो"]
    ),
    ContrastiveGrammarRule(
        rule_id="present_continuous_aspect",
        title="Present Continuous Aspect ('-रहा हूँ' vs '-त आहे')",
        concept="continuous_aspect",
        source_pattern="जा रहा हूँ / आ रहा हूँ (-raha hoon)",
        target_pattern="जात आहे / येत आहे (-t aahe)",
        explanation="Hindi forms continuous aspect using the separate auxiliary participle 'रहा हूँ / रहे हैं' ('मैं जा रहा हूँ' = I am going). Marathi directly suffixes imperfective '-त' (-t) to the verb root plus 'आहे' ('मी जात आहे'). Notice Marathi has no separate word for 'रहा'; the '-त' suffix fulfills that role.",
        triggers=["रहा", "raha", "रही", "rahi", "रहे", "rahe", "जात आहे", "jaat aahe", "येत आहे", "करत आहे", "खात आहे"]
    ),
    ContrastiveGrammarRule(
        rule_id="spatial_deixis_yaha_vaha",
        title="Place Adverbs ('यहाँ / वहाँ' vs 'इथे / तिथे')",
        concept="spatial_deixis",
        source_pattern="यहाँ (yahan) / वहाँ (vahan)",
        target_pattern="इथे (ithe) / तिथे (tithe)",
        explanation="Spatial adverbs exhibit direct sound correspondences: Hindi 'यहाँ' corresponds to Marathi 'इथे', and Hindi 'वहाँ' corresponds to Marathi 'तिथे'.",
        triggers=["यहाँ", "yaha", "yahan", "वहाँ", "vaha", "vahan", "इथे", "ithe", "तिथे", "tithe", "teethe"]
    )
]

def find_matching_grammar_rules(source_text: str, target_text: str) -> List[GrammarPoint]:
    """Finds all applicable contrastive grammar points for a given sentence pair."""
    combined = f"{source_text} {target_text}"
    matched = []
    seen = set()

    for rule in GRAMMAR_RULES:
        if rule.matches(combined) and rule.rule_id not in seen:
            seen.add(rule.rule_id)
            matched.append(rule.to_grammar_point())

    # Fallback default rule if none matched
    if not matched:
        matched.append(GrammarPoint(
            title="SOV Word Order & Postposition Structure",
            concept="sov_syntax",
            source_pattern="Subject + Object + Verb",
            target_pattern="Subject + Object + Verb",
            explanation="Both Hindi and Marathi share core Subject-Object-Verb (SOV) sentence order and postpositional phrasing."
        ))

    return matched
