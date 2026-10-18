"""
BhashaBridge — Learner Traps & Cultural Context Detector (M4)
Identifies recurring learner pitfalls, false friends, and contextual nuances
between Hindi and Marathi speakers as specified in Section 9 of the product spec.
"""

from typing import List, Dict

COMMON_TRAPS_DATABASE = [
    {
        "id": "trap_kal_yesterday",
        "triggers": ["कल", "kal", "उद्या", "udya", "काल", "kaal"],
        "mistake": "Confusing 'काल' (yesterday) with 'उद्या' (tomorrow). In Hindi, 'कल' means both yesterday and tomorrow, but in Marathi 'काल' strictly means yesterday.",
        "tip": "Always use 'उद्या' (udya) when referring to future actions."
    },
    {
        "id": "trap_nominative_obligation",
        "triggers": ["जाना है", "jaana hai", "जायचं", "jaycha", "करायचं", "karaycha"],
        "mistake": "Using nominative 'मी' (I) instead of dative 'मला' (to me) in obligation sentences (e.g. saying 'मी जायचं आहे' instead of correct 'मला जायचं आहे').",
        "tip": "Obligation with '-चं आहे' always takes the dative subject 'मला'."
    },
    {
        "id": "trap_omitting_la_postposition",
        "triggers": ["college", "कॉलेज", "office", "ऑफिस", "शाळा", "दुकान"],
        "mistake": "Omitting the dative destination suffix '-ला' in Marathi (e.g., saying 'कॉलेज जायचं' instead of 'कॉलेजला जायचं').",
        "tip": "Marathi attaches '-ला' directly to the destination noun when indicating travel toward it."
    },
    {
        "id": "trap_masculine_language_agreement",
        "triggers": ["मराठी", "marathi", "शिकायचा", "seekhna"],
        "mistake": "Using masculine verb ending 'शिकायचा आहे' for Marathi language instead of feminine 'शिकायची आहे'.",
        "tip": "Language names (मराठी, हिंदी) are feminine; verbs agreeing with them must take feminine endings."
    },
    {
        "id": "trap_water_gender",
        "triggers": ["पाणी", "paani", "पानी"],
        "mistake": "Treating 'पाणी' (water) as masculine like Hindi ('पानी ठंडा है'). In Marathi, 'पाणी' is neuter and requires neuter adjectives ('पाणी थंड / गार आहे').",
        "tip": "Use neuter forms like 'थोडं पाणी' (thoda paani) rather than 'थोडा पाणी'."
    },
    {
        "id": "trap_farewell_inauspicious",
        "triggers": ["अलविदा", "जातो", "yeet", "bye"],
        "mistake": "Saying 'मी जातो' (I am going) when taking leave. In Maharashtrian etiquette, saying 'I go' is considered inauspicious; customary departure is 'मी येतो' (male) or 'मी येते' (female), meaning 'I will return'.",
        "tip": "Always bid farewell by saying 'येतो / येते' (I will come back)."
    },
    {
        "id": "trap_continuous_raha_calque",
        "triggers": ["रहा", "raha", "जा रहा", "जात आहे", "जात"],
        "mistake": "Attempting to literally translate Hindi 'रहा' into Marathi (e.g., saying 'मी राहतो आहे' instead of 'मी जात आहे').",
        "tip": "In Marathi, simply add suffix '-त' (-t) to the verb root plus 'आहे': 'जा' + 'त' = 'जात आहे' (jaat aahe)."
    }
]

def detect_learner_traps(source_text: str, target_text: str) -> List[str]:
    combined = f"{source_text.lower()} {target_text.lower()}"
    traps = []

    for item in COMMON_TRAPS_DATABASE:
        if any(t in combined for t in item["triggers"]):
            traps.append(f"{item['mistake']} 💡 Tip: {item['tip']}")

    if not traps:
        traps.append("Avoid literal word-by-word substitution; Marathi postpositions attach directly to nouns rather than standing as separate words.")

    return traps

def analyze_formality_and_context(source_text: str, target_text: str) -> Dict[str, str]:
    combined = f"{source_text.lower()} {target_text.lower()}"

    if any(w in combined for t, w in enumerate(["आप", "तुम्ही", "aap", "tumhi", "आहात", "करा", "बसा"])):
        return {
            "level": "Formal / Respectful",
            "usage": "Used when addressing elders, professors, clients, strangers, or in professional workplaces.",
            "pronoun": "तुम्ही (tumhi)"
        }
    elif any(w in combined for t, w in enumerate(["तू", "तु", "tu", "तुम", "आहेस", "नकोस", "यार"])):
        return {
            "level": "Informal / Familiar",
            "usage": "Used among close peers, college friends, siblings, or younger children.",
            "pronoun": "तू (tu)"
        }
    else:
        return {
            "level": "Neutral / Standard",
            "usage": "Standard communicative tone appropriate in everyday contexts.",
            "pronoun": "General"
        }
