import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from app.services.base import BaseExplanationService
from app.schemas.analyze import VocabularyItem, GrammarPoint, ExampleItem
from app.services.explanation.grammar_rules import get_matching_rules, find_matching_grammar_rules, ContrastiveGrammarRule
from app.services.explanation.bilingual_aligner import align_sentence_vocabulary
from app.services.explanation.learner_traps import detect_learner_traps, analyze_formality_and_context
from app.services.explanation.legacy_backup.engine_legacy import HybridExplanationEngine as LegacyExplanationEngine

logger = logging.getLogger(__name__)

class HybridExplanationEngine(BaseExplanationService):
    """
    Enhanced Hybrid Linguistic Explanation Engine with:
    - Explicit 'Why sentences differ' contrastive analysis
    - Curated parallel minimal-pair examples
    - Smart dataset retrieval across 360+ verified learning scenarios
    - Fail-safe runtime fallback to preserved legacy engine
    """

    def __init__(self):
        # 1. Preserved legacy fallback instance
        self._legacy_engine = LegacyExplanationEngine()

        # 2. Curated educational dataset & external open-source parallel index
        self._dataset_cache: List[Dict[str, Any]] = []
        self._external_cache: List[Dict[str, Any]] = []
        data_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "processed" / "learning"
        dataset_path = data_dir / "bhashabridge_learning.json"
        if dataset_path.exists():
            try:
                with open(dataset_path, "r", encoding="utf-8") as f:
                    self._dataset_cache = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load educational dataset cache: {e}")
                self._dataset_cache = []

        external_path = data_dir / "external_parallel_learning_index.json"
        if external_path.exists():
            try:
                with open(external_path, "r", encoding="utf-8") as ef:
                    self._external_cache = json.load(ef)
                logger.info(f"Loaded {len(self._external_cache)} external parallel sentences into explanation cache.")
            except Exception as e:
                logger.warning(f"Could not load external parallel index: {e}")
                self._external_cache = []

    # Knowledge base for specific flagship phrase mappings
    EXPLANATION_KB = {
        "college_obligation": {
            "triggers": ["college", "कॉलेज"],
            "summary": "Expressing obligation ('have to go') and specific time referencing between Hindi and Marathi.",
            "vocabulary": [
                VocabularyItem(source_word="मुझे", target_word="मला", target_roman="Mala", meaning="to me / I (dative subject)", part_of_speech="pronoun", is_construction_based=True, morph_analysis="Case=Dat | Suffix=-ला | Experiencer Subject", gender_contrast=None, root_lemma="मी ➔ मला"),
                VocabularyItem(source_word="कल", target_word="उद्या", target_roman="udya", meaning="tomorrow (specifically future)", part_of_speech="adverb", is_construction_based=False, morph_analysis="Tense=Fut | Unambiguous future marker", gender_contrast=None, root_lemma="उद्या (tomorrow) vs काल (yesterday)"),
                VocabularyItem(source_word="कॉलेज", target_word="कॉलेजला", target_roman="college-la", meaning="to college (with dative postposition -ला)", part_of_speech="noun + postposition", is_construction_based=True, morph_analysis="Case=Dat (Goal) | Suffix=-ला attached directly", gender_contrast=None, root_lemma="कॉलेज + -ला"),
                VocabularyItem(source_word="जाना है", target_word="जायचं आहे", target_roman="jaycha aahe", meaning="have to go / must go", part_of_speech="verb phrase", is_construction_based=True, morph_analysis="Mood=Obligation | Participle=-चं | Aux=आहे", gender_contrast=None, root_lemma="जा- + -चं आहे")
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
                "Vibhakti Suffixation: Hindi uses bare 'कॉलेज' while Marathi attaches dative suffix '-ला' ('कॉलेजला').",
                "Temporal Precision: Hindi relies on context for 'कल'; Marathi demands unambiguous 'उद्या' for tomorrow and 'काल' for yesterday.",
                "Subject Case: Both languages use dative subject ('मुझे' in Hindi, 'मला' in Marathi) for expressing obligation."
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
                ),
                ExampleItem(
                    source_sentence="उसे कल पुणे जाना है।",
                    target_sentence="त्याला उद्या पुण्याला जायचं आहे।",
                    target_roman="Tyala udya Punyala jaycha aahe.",
                    english_translation="He has to go to Pune tomorrow."
                )
            ]
        },
        "learning_marathi": {
            "triggers": ["seekhni", "shikaychi", "सीखनी", "शिकायची"],
            "summary": "Expressing desire/intention to learn a language and feminine noun-verb agreement.",
            "vocabulary": [
                VocabularyItem(source_word="मुझे", target_word="मला", target_roman="Mala", meaning="to me / I", part_of_speech="pronoun", is_construction_based=True, morph_analysis="Case=Dat | Suffix=-ला | Experiencer Subject", gender_contrast=None, root_lemma="मी ➔ मला"),
                VocabularyItem(source_word="मराठी", target_word="मराठी", target_roman="Marathi", meaning="Marathi language", part_of_speech="noun", is_construction_based=False, morph_analysis="Gender=Fem | Proper Noun", gender_contrast="Language names are feminine in both languages", root_lemma="मराठी"),
                VocabularyItem(source_word="सीखनी", target_word="शिकायची", target_roman="shikaychi", meaning="to learn (feminine agreement)", part_of_speech="verb", is_construction_based=True, morph_analysis="Mood=Desiderative | Gender=Fem (-ची participle)", gender_contrast="Verb agrees with feminine noun 'मराठी'", root_lemma="शिक- + -ची आहे"),
                VocabularyItem(source_word="है", target_word="आहे", target_roman="aahe", meaning="is / present auxiliary", part_of_speech="auxiliary verb", is_construction_based=False, morph_analysis="Tense=Pres | Person=3 | Fin", gender_contrast=None, root_lemma="असणे")
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
                "Gender Concord: Both languages treat language names as feminine; verbs inflect to feminine ('सीखनी है' / 'शिकायची आहे').",
                "Phonetic Shift: Regular sibilant correspondence where Hindi /s/ aligns with Marathi /sh/ ('सीख' -> 'शिक').",
                "Dative Subject: Intent to learn uses dative experiencer ('मुझे' -> 'मला')."
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
                ),
                ExampleItem(
                    source_sentence="तुम्हाला कोणती भाषा शिकायची आहे?",
                    target_sentence="तुम्हें कौन सी भाषा सीखनी है?",
                    target_roman="Tumhala konti bhasha shikaychi aahe?",
                    english_translation="Which language do you want to learn?"
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
        """
        Public entrypoint with automatic fallback to preserved legacy engine if needed.
        """
        try:
            return self._explain_enhanced(
                source_text=source_text,
                source_language=source_language,
                target_text=target_text,
                target_language=target_language
            )
        except Exception as e:
            logger.warning(f"Enhanced explanation failed ({e}); falling back to preserved legacy engine.")
            return self._legacy_engine.explain(
                source_text=source_text,
                source_language=source_language,
                target_text=target_text,
                target_language=target_language
            )

    def _explain_enhanced(
        self,
        source_text: str,
        source_language: str,
        target_text: str,
        target_language: str
    ) -> Dict[str, Any]:
        combined_text = f"{source_text.lower()} {target_text.lower()}"

        # 1. Check flagship Knowledge Base entry
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

        # 2. Check exact/substring match in educational dataset
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
                        "is_construction_based": True,
                        "morph_analysis": v.get("morph_analysis") or v.get("bridge_note") or f"Case=Aligned | Term={v['marathi']}",
                        "gender_contrast": v.get("gender_contrast") or v.get("gender_info"),
                        "root_lemma": v.get("root_lemma") or v.get("marathi")
                    } for v in item.get("vocabulary", [])
                ]

                # Pull sibling examples from same topic in dataset
                topic_examples = self._get_topic_examples(item["topic"], exclude_id=item.get("id"), limit=3)
                if not topic_examples:
                    topic_examples = [
                        {
                            "source_sentence": item["hindi_devanagari"],
                            "target_sentence": item["marathi_devanagari"],
                            "target_roman": item["marathi_roman"],
                            "english_translation": item["english_meaning"]
                        }
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
                    "differences": [
                        item.get("context_note", "Standard structural divergence."),
                        f"Tone: {item.get('formality', 'natural')} conversation in Marathi."
                    ],
                    "common_mistakes": item.get("common_mistakes", []),
                    "examples": topic_examples
                }

        # 3. Dynamic Deep Contrast Breakdown with Smart Example Retrieval
        aligned_vocab = align_sentence_vocabulary(source_text, target_text, source_lang=source_language)
        matched_rules = get_matching_rules(source_text, target_text)
        traps = detect_learner_traps(source_text, target_text)
        formality_info = analyze_formality_and_context(source_text, target_text)

        # Build precise "Why sentences differ" structural explanations
        differences = self._build_dynamic_differences(
            source_text=source_text,
            target_text=target_text,
            matched_rules=matched_rules,
            formality_info=formality_info,
            aligned_vocab=aligned_vocab
        )

        # Retrieve relevant similar examples from rule banks + dataset
        examples = self._find_similar_examples(
            source_text=source_text,
            target_text=target_text,
            matched_rules=matched_rules,
            limit=3
        )

        summary = f"{formality_info['level']} construction between {source_language.capitalize()} and {target_language.capitalize()}. {formality_info['usage']}"

        return {
            "summary": summary,
            "word_explanations": [v.model_dump() for v in aligned_vocab],
            "grammar_points": [r.to_grammar_point().model_dump() for r in matched_rules],
            "differences": differences,
            "common_mistakes": traps,
            "examples": [e.model_dump() for e in examples]
        }

    def _build_dynamic_differences(
        self,
        source_text: str,
        target_text: str,
        matched_rules: List[ContrastiveGrammarRule],
        formality_info: Dict[str, str],
        aligned_vocab: List[VocabularyItem]
    ) -> List[str]:
        """Constructs detailed pedagogical differences explaining why this sentence changed."""
        diffs = []

        # 1. Insights from matched contrastive rules
        for rule in matched_rules:
            if rule.rule_id != "sov_syntax" and rule.contrast_insight:
                diffs.append(rule.contrast_insight)

        # 2. Case marker & synthetic vs analytic postpositions
        construction_words = [v for v in aligned_vocab if v.is_construction_based]
        if construction_words:
            first_c = construction_words[0]
            diffs.append(
                f"Synthetic Suffixation: In '{first_c.source_word}' → '{first_c.target_word}', Marathi attaches grammatical markers directly as word suffixes, unlike Hindi analytic postpositions."
            )

        # 3. Tone & Formality
        diffs.append(f"Register & Tone: {formality_info['level']} ({formality_info['usage']})")

        # 4. Fallback if short
        if len(diffs) < 2:
            diffs.append("Word Order: Both languages follow Subject-Object-Verb (SOV) order, but Marathi maintains strict gender-number agreement with neuter nouns.")

        return diffs[:4]

    def _find_similar_examples(
        self,
        source_text: str,
        target_text: str,
        matched_rules: List[ContrastiveGrammarRule],
        limit: int = 3
    ) -> List[ExampleItem]:
        """Finds parallel, beginner-friendly examples to help learners grasp the sentence structure."""
        collected_examples: List[ExampleItem] = []
        seen_targets = {target_text.strip(".,!?:;\"'()[]{}।")}

        # 1. Collect from matched contrast rules (highest relevance)
        for rule in matched_rules:
            for ex in rule.examples:
                clean_target = ex.target_sentence.strip(".,!?:;\"'()[]{}।")
                if clean_target not in seen_targets:
                    seen_targets.add(clean_target)
                    collected_examples.append(ex)
                    if len(collected_examples) >= limit:
                        return collected_examples

        # 2. Semantic token overlap search in the 360-sentence dataset
        dataset_matches = self._search_dataset_by_tokens(source_text, target_text, exclude_targets=seen_targets, limit=limit - len(collected_examples))
        collected_examples.extend(dataset_matches)

        return collected_examples[:limit]

    def _search_dataset_by_tokens(
        self,
        source_text: str,
        target_text: str,
        exclude_targets: Set[str],
        limit: int = 2
    ) -> List[ExampleItem]:
        """Scores sentences in curated and external parallel datasets by shared tokens/keywords."""
        if (not self._dataset_cache and not self._external_cache) or limit <= 0:
            return []

        # Extract tokens (ignoring single-letter punctuation)
        words = set(re.findall(r"[\w]+", f"{source_text} {target_text}"))
        stopwords = {"है", "हूँ", "हो", "आहे", "आहेस", "आहोत", "आहेत", "का", "एक", "मी", "main", "to", "hi"}
        significant_words = {w for w in words if len(w) > 1 and w not in stopwords}

        scored_candidates = []
        
        # 1. Search curated educational dataset first (high priority)
        for item in self._dataset_cache:
            clean_mr = item["marathi_devanagari"].strip(".,!?:;\"'()[]{}।")
            if clean_mr in exclude_targets:
                continue

            item_text = f"{item['hindi_devanagari']} {item['marathi_devanagari']} {item.get('hindi_roman', '')} {item.get('marathi_roman', '')}".lower()
            score = sum(1 for w in significant_words if w.lower() in item_text)
            if score > 0:
                scored_candidates.append((score + 2, item))  # +2 boost for curated educational items

        # 2. Search external parallel corpora if we need more examples
        for item in self._external_cache:
            mr_text = item.get("marathi", "").strip()
            clean_mr = mr_text.strip(".,!?:;\"'()[]{}।")
            if not clean_mr or clean_mr in exclude_targets:
                continue

            hi_text = item.get("hindi", "").strip()
            item_text = f"{hi_text} {mr_text}".lower()
            score = sum(1 for w in significant_words if w.lower() in item_text)
            if score > 0:
                scored_candidates.append((score, {
                    "hindi_devanagari": hi_text,
                    "marathi_devanagari": mr_text,
                    "marathi_roman": "",
                    "english_meaning": item.get("english") or "Parallel contextual example"
                }))

        # Sort by highest keyword overlap
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        results = []
        for _, item in scored_candidates[:limit]:
            results.append(ExampleItem(
                source_sentence=item["hindi_devanagari"],
                target_sentence=item["marathi_devanagari"],
                target_roman=item.get("marathi_roman", ""),
                english_translation=item.get("english_meaning", "")
            ))

        return results

    def _get_topic_examples(self, topic: str, exclude_id: Optional[str] = None, limit: int = 3) -> List[Dict[str, str]]:
        """Pulls sibling examples from the same topic in the educational corpus."""
        examples = []
        for item in self._dataset_cache:
            if item.get("topic") == topic and item.get("id") != exclude_id:
                examples.append({
                    "source_sentence": item["hindi_devanagari"],
                    "target_sentence": item["marathi_devanagari"],
                    "target_roman": item["marathi_roman"],
                    "english_translation": item["english_meaning"]
                })
                if len(examples) >= limit:
                    break
        return examples

explanation_engine = HybridExplanationEngine()
