import json
from pathlib import Path
from typing import Any, Dict, List
from app.services.base import BaseExplanationService
from app.schemas.analyze import VocabularyItem, GrammarPoint, ExampleItem
from app.services.explanation.grammar_rules import find_matching_grammar_rules
from app.services.explanation.bilingual_aligner import align_sentence_vocabulary
from app.services.explanation.learner_traps import detect_learner_traps, analyze_formality_and_context

class HybridExplanationEngine(BaseExplanationService):
    """
    Hybrid linguistic explanation engine combining bilingual dictionary alignment,
    contrastive grammar rules, curated learning datasets, and contextual examples.
    """

    def __init__(self):
        self._dataset_cache = []
        dataset_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "processed" / "learning" / "bhashabridge_learning.json"
        if dataset_path.exists():
            try:
                with open(dataset_path, "r", encoding="utf-8") as f:
                    self._dataset_cache = json.load(f)
            except Exception:
                self._dataset_cache = []

    # Knowledge base for specific phrase mappings and grammar explanations
    EXPLANATION_KB = {
        "college_obligation": {
            "triggers": ["college", "कॉलेज", "जाना", "जायचं", "कल", "उद्या"],
            "summary": "Expressing obligation ('have to go') and specific time referencing between Hindi and Marathi.",
            "vocabulary": [
                VocabularyItem(source_word="मुझे", target_word="मला", target_roman="Mala", meaning="to me / I (dative subject)", part_of_speech="pronoun", is_construction_based=True),
                VocabularyItem(source_word="कल", target_word="उद्या", target_roman="udya", meaning="tomorrow (specifically future)", part_of_speech="adverb", is_construction_based=False),
                VocabularyItem(source_word="कॉलेज", target_word="कॉलेजला", target_roman="college-la", meaning="to college (with dative postposition -ला)", part_of_speech="noun + postposition", is_construction_based=True),
                VocabularyItem(source_word="जाना है", target_word="जायचं आहे", target_roman="jaycha aahe", meaning="have to go / must go", part_of_speech="verb phrase", is_construction_based=True)
            ],
            "grammar_points": [
                GrammarPoint(
                    title="Temporal Distinction ('कल' vs 'उद्या')",
                    concept="future_temporal_marker",
                    source_pattern="कल (kal)",
                    target_pattern="उद्या (udya)",
                    explanation="Hindi 'कल' can denote either yesterday or tomorrow based on verb tense. Marathi strictly uses 'उद्या' (udya) for tomorrow and 'काल' (kaal) for yesterday."
                ),
                GrammarPoint(
                    title="Dative Postposition ('-ला')",
                    concept="locative_dative_postposition",
                    source_pattern="कॉलेज जाना (college jaana)",
                    target_pattern="कॉलेजला जायचं (college-la jaycha)",
                    explanation="Marathi attaches the dative suffix '-ला' (-la) directly to the destination noun when indicating direction or goal, whereas colloquial Hindi often leaves destination unmarked."
                ),
                GrammarPoint(
                    title="Obligation Construction ('-ना है' vs '-चं आहे')",
                    concept="obligation_modal",
                    source_pattern="जाना है (jaana hai)",
                    target_pattern="जायचं आहे (jaycha aahe)",
                    explanation="Expressing necessity in Marathi requires neuter potential participle ending in '-चं' ('जायचं', 'करायचं') paired with 'आहे', preceded by the dative subject 'मला'."
                )
            ],
            "differences": [
                "Hindi uses unmarked noun 'कॉलेज' while Marathi attaches suffix '-ला' ('कॉलेजला').",
                "Hindi relies on context for 'कल' (yesterday/tomorrow); Marathi demands unambiguous 'उद्या' for tomorrow.",
                "Subject takes dative case in both languages ('मुझे' in Hindi, 'मला' in Marathi)."
            ],
            "common_mistakes": [
                "Using Marathi 'काल' (which means yesterday) instead of 'उद्या' for tomorrow.",
                "Omitting the postposition suffix '-ला' on the destination noun in Marathi."
            ],
            "examples": [
                ExampleItem(
                    source_sentence="मुझे कल ऑफिस जाना है।",
                    target_sentence="मला उद्या ऑफिसला जायचं आहे।",
                    target_roman="Mala udya officela jaycha aahe.",
                    english_translation="I have to go to the office tomorrow."
                ),
                ExampleItem(
                    source_sentence="मुझे आज घर जाना है।",
                    target_sentence="मला आज घरी जायचं आहे।",
                    target_roman="Mala aaj ghari jaycha aahe.",
                    english_translation="I have to go home today."
                )
            ]
        },
        "learning_marathi": {
            "triggers": ["seekhni", "shikaychi", "मराठी", "सीखनी"],
            "summary": "Expressing desire/intention to learn a language and feminine noun-verb agreement.",
            "vocabulary": [
                VocabularyItem(source_word="मुझे", target_word="मला", target_roman="Mala", meaning="to me / I", part_of_speech="pronoun", is_construction_based=True),
                VocabularyItem(source_word="मराठी", target_word="मराठी", target_roman="Marathi", meaning="Marathi language", part_of_speech="noun", is_construction_based=False),
                VocabularyItem(source_word="सीखनी", target_word="शिकायची", target_roman="shikaychi", meaning="to learn (feminine agreement)", part_of_speech="verb", is_construction_based=True),
                VocabularyItem(source_word="है", target_word="आहे", target_roman="aahe", meaning="is / present auxiliary", part_of_speech="auxiliary verb", is_construction_based=False)
            ],
            "grammar_points": [
                GrammarPoint(
                    title="Gender Agreement with Languages",
                    concept="feminine_agreement",
                    source_pattern="सीखनी है (seekhni hai)",
                    target_pattern="शिकायची आहे (shikaychi aahe)",
                    explanation="In both Hindi and Marathi, names of languages are grammatically feminine. Hence, 'सीखना' becomes 'सीखनी' in Hindi and 'शिकायचे' becomes feminine 'शिकायची' in Marathi."
                ),
                GrammarPoint(
                    title="Cognate Root with Sound Shift (s -> sh)",
                    concept="phonological_cognate",
                    source_pattern="सीख- (seekh-)",
                    target_pattern="शिक- (shik-)",
                    explanation="The verb root corresponds systematically: Hindi 'सीख' (seekh) corresponds to Marathi 'शिक' (shik)."
                )
            ],
            "differences": [
                "Both languages use dative subject ('मुझे' / 'मला') for expressing intent/obligation.",
                "Verb endings agree with the feminine grammatical gender of the language name ('सीखनी' / 'शिकायची')."
            ],
            "common_mistakes": [
                "Using masculine verb form 'शिकायचा आहे' instead of feminine 'शिकायची आहे' when referring to Marathi.",
                "Saying nominative 'मी मराठी शिकायची आहे' instead of dative 'मला मराठी शिकायची आहे'."
            ],
            "examples": [
                ExampleItem(
                    source_sentence="मुझे हिंदी सीखनी है।",
                    target_sentence="मला हिंदी शिकायची आहे।",
                    target_roman="Mala Hindi shikaychi aahe.",
                    english_translation="I want to learn Hindi."
                ),
                ExampleItem(
                    source_sentence="मुझे गिटार सीखना है।",
                    target_sentence="मला गिटार शिकायचं आहे।",
                    target_roman="Mala guitar shikaycha aahe.",
                    english_translation="I want to learn guitar (masculine/neuter)."
                )
            ]
        }
    }

    def explain(
        self,
        source_text: str,
        source_language: str = "hindi",
        target_text: str = "marathi",
        target_language: str = "marathi"
    ) -> Dict[str, Any]:
        combined_text = f"{source_text.lower()} {target_text.lower()}"

        # 1. Match best KB entry if present
        for key, entry in self.EXPLANATION_KB.items():
            if any(t.lower() in combined_text for t in entry["triggers"]):
                return {
                    "summary": entry["summary"],
                    "word_explanations": [v.model_dump() for v in entry["vocabulary"]],
                    "grammar_points": [g.model_dump() for g in entry["grammar_points"]],
                    "differences": entry["differences"],
                    "common_mistakes": entry["common_mistakes"],
                    "examples": [e.model_dump() for e in entry["examples"]]
                }

        # 2. Check educational dataset cache
        clean_src = source_text.strip(".,!?:;\"'()[]{}।")
        for item in self._dataset_cache:
            if clean_src in item["hindi_devanagari"] or clean_src in item["marathi_devanagari"] or clean_src in item["hindi_roman"] or clean_src in item["marathi_roman"]:
                vocab_list = [
                    {
                        "source_word": v["hindi"],
                        "target_word": v["marathi"],
                        "target_roman": v.get("meaning", ""),
                        "meaning": v["meaning"],
                        "part_of_speech": "aligned_term",
                        "is_construction_based": True
                    } for v in item.get("vocabulary", [])
                ]
                return {
                    "summary": f"{item['topic'].capitalize()}: {item.get('context_note', '')}",
                    "word_explanations": vocab_list,
                    "grammar_points": [
                        {
                            "title": f"Grammar Note ({item['topic'].capitalize()})",
                            "concept": item["topic"],
                            "source_pattern": item["hindi_devanagari"],
                            "target_pattern": item["marathi_devanagari"],
                            "explanation": item["grammar_note"]
                        }
                    ],
                    "differences": [item.get("context_note", "Standard structural divergence.")],
                    "common_mistakes": item.get("common_mistakes", []),
                    "examples": [
                        {
                            "source_sentence": item["hindi_devanagari"],
                            "target_sentence": item["marathi_devanagari"],
                            "target_roman": item["marathi_roman"],
                            "english_translation": item["english_meaning"]
                        }
                    ]
                }

        # 3. Dynamic Deep Linguistic Breakdown via M4 Modules
        aligned_vocab = align_sentence_vocabulary(source_text, target_text, source_lang=source_language)
        matched_grammar = find_matching_grammar_rules(source_text, target_text)
        traps = detect_learner_traps(source_text, target_text)
        formality_info = analyze_formality_and_context(source_text, target_text)

        summary = f"{formality_info['level']} construction between {source_language.capitalize()} and {target_language.capitalize()}. {formality_info['usage']}"

        differences = [
            f"Register & Tone: {formality_info['level']} ({formality_info['usage']})",
            "Morphology: Marathi attaches postpositions directly as suffixes (synthetic), whereas Hindi uses independent postpositions (analytic)."
        ]

        return {
            "summary": summary,
            "word_explanations": [v.model_dump() for v in aligned_vocab],
            "grammar_points": [g.model_dump() for g in matched_grammar],
            "differences": differences,
            "common_mistakes": traps,
            "examples": []
        }

explanation_engine = HybridExplanationEngine()
