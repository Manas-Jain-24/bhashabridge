"""
BhashaBridge — Gamification & Interactive Learning Engine
Powers:
1. Gamification Profile (XP, Streak, Hearts, Cultural Marathi Ranks, Badges)
2. Bridge Quest Skill Tree / Roadmap with Stars and Unlock Status
3. Word Tile Scramble (Sentence Builder with Intentional Trap Distractors)
4. Chai Tapri Blitz (60s Timed Rapid-Fire Arcade)
5. Street Scenarios Roleplay (Pune/Mumbai Cultural Conversational Sim)
"""

import json
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.entities import UserGamification, Progress, Milestone, LanguageProfile
from app.schemas.gamification import (
    GamificationProfileResponse, GamificationActionRequest,
    ScrambleQuestion, ScrambleTile, BlitzQuestion,
    StreetScenario, StreetScenarioStep, StreetScenarioChoice,
    SkillTreeNode
)

RANKS = [
    (0, 200, "शिकारू (Rookie)"),
    (201, 500, "चहा मित्र (Chaha Mitra)"),
    (501, 1000, "कडक भाऊ (Khadak Bhau)"),
    (1001, 2000, "अस्सल पुणेकर (Assal Punekar)"),
    (2001, 999999, "भाषा पंडित (Bhasha Pandit)")
]

SCRAMBLE_BANK: List[Dict[str, Any]] = [
    {
        "id": "scramble_1",
        "prompt_hindi": "मुझे कल कॉलेज जाना है।",
        "prompt_roman": "Mujhe kal college jaana hai.",
        "english_meaning": "I have to go to college tomorrow.",
        "target_sentence_devanagari": "मला उद्या कॉलेजला जायचं आहे",
        "target_sentence_roman": "Mala udya college-la jaycha aahe",
        "target_tokens": ["मला", "उद्या", "कॉलेजला", "जायचं", "आहे"],
        "target_tokens_roman": ["Mala", "udya", "college-la", "jaycha", "aahe"],
        "distractors": [
            {"token": "काल", "roman": "kaal", "trap_explanation": "‘काल’ म्हणजे कालचा दिवस (Yesterday)! Tomorrow साठी ‘उद्या’ वापरा."},
            {"token": "मी", "roman": "mi", "trap_explanation": "Obligation / Want रचनेत Subject ‘मला’ (Dative) लागतो, ‘मी’ नाही."},
            {"token": "पाहिजे", "roman": "pahije", "trap_explanation": "‘पाहिजे’ म्हणजे Need/Want. ‘जाणे’ क्रियापदासाठी ‘जायचं आहे’ हवे."}
        ],
        "grammar_tip": "Marathi dative obligation: 'मला' + Action + 'आहे'. And remember: 'उद्या' is tomorrow, 'काल' is yesterday!",
        "topic": "college",
        "level": 2
    },
    {
        "id": "scramble_2",
        "prompt_hindi": "मैं अभी घर जा रहा हूँ।",
        "prompt_roman": "Main abhi ghar jaa raha hoon.",
        "english_meaning": "I am going home right now.",
        "target_sentence_devanagari": "मी आता घरी जात आहे",
        "target_sentence_roman": "Mi aata ghari jaat aahe",
        "target_tokens": ["मी", "आता", "घरी", "जात", "आहे"],
        "target_tokens_roman": ["Mi", "aata", "ghari", "jaat", "aahe"],
        "distractors": [
            {"token": "घर", "roman": "ghar", "trap_explanation": "मराठीत 'घराकडे जाणे' यासाठी Locative रूप 'घरी' (ghari) वापरले जाते."},
            {"token": "घरला", "roman": "gharla", "trap_explanation": "‘घरला’ अशुद्ध वाटते; अस्सल मराठीत 'घरी' वापरतात."},
            {"token": "मला", "roman": "mala", "trap_explanation": "Continuous Action (मी जात आहे) मध्ये कर्ता 'मी' असतो, 'मला' नाही."}
        ],
        "grammar_tip": "Locative inflection: In Marathi, 'to home' is simply 'घरी' (ghari), not bare 'घर'.",
        "topic": "daily_routine",
        "level": 2
    },
    {
        "id": "scramble_3",
        "prompt_hindi": "मुझे ठंडा पानी चाहिए।",
        "prompt_roman": "Mujhe thanda paani chahiye.",
        "english_meaning": "I need cold water.",
        "target_sentence_devanagari": "मला थंड पाणी पाहिजे",
        "target_sentence_roman": "Mala thand paani pahije",
        "target_tokens": ["मला", "थंड", "पाणी", "पाहिजे"],
        "target_tokens_roman": ["Mala", "thand", "paani", "pahije"],
        "distractors": [
            {"token": "मी", "roman": "mi", "trap_explanation": "Wants and needs in Marathi always take dative 'मला' (to me), not 'मी'."},
            {"token": "पाहिजेत", "roman": "pahijet", "trap_explanation": "'पाहिजेत' plural साठी वापरतात (उदा. पुस्तके पाहिजेत). 'पाणी' singular neuter आहे."},
            {"token": "आहे", "roman": "aahe", "trap_explanation": "Here you are expressing desire/need ('चाहिए'), so 'पाहिजे' is required."}
        ],
        "grammar_tip": "Expressing wants: 'मला' + [Noun] + 'पाहिजे' corresponds to Hindi 'मुझे [चीज] चाहिए'.",
        "topic": "requests",
        "level": 1
    },
    {
        "id": "scramble_4",
        "prompt_hindi": "मुझे मराठी बोलना पसंद है।",
        "prompt_roman": "Mujhe Marathi bolna pasand hai.",
        "english_meaning": "I like speaking Marathi.",
        "target_sentence_devanagari": "मला मराठी बोलायला आवडतं",
        "target_sentence_roman": "Mala Marathi bolayala aavadta",
        "target_tokens": ["मला", "मराठी", "बोलायला", "आवडतं"],
        "target_tokens_roman": ["Mala", "Marathi", "bolayala", "aavadta"],
        "distractors": [
            {"token": "आवडतो", "roman": "aavadto", "trap_explanation": "Infinitive action clauses take neuter singular agreement: 'आवडतं' (aavadta)."},
            {"token": "बोलतो", "roman": "bolto", "trap_explanation": "'बोलतो' म्हणजे 'मी बोलतो' (I speak). 'Speaking' साठी dative infinitive 'बोलायला' हवे."},
            {"token": "मी", "roman": "mi", "trap_explanation": "'आवडणे' क्रियापदाचा भोक्ता नेहमी Dative 'मला' असतो."}
        ],
        "grammar_tip": "Preference with verbs: 'मला' + [Verb + -ायला] + 'आवडतं' (e.g., मला शिकायला आवडतं = I like learning).",
        "topic": "learning",
        "level": 3
    },
    {
        "id": "scramble_5",
        "prompt_hindi": "आप सब कैसे हैं?",
        "prompt_roman": "Aap sab kaise hain?",
        "english_meaning": "How are you all (respectful/plural)?",
        "target_sentence_devanagari": "तुम्ही सगळे कसे आहात",
        "target_sentence_roman": "Tumhi sagle kase aahat",
        "target_tokens": ["तुम्ही", "सगळे", "कसे", "आहात"],
        "target_tokens_roman": ["Tumhi", "sagle", "kase", "aahat"],
        "distractors": [
            {"token": "तू", "roman": "tu", "trap_explanation": "'तू' हे एकवचनी आणि अनौपचारिक आहे. आदरार्थी 'तुम्ही' वापरा."},
            {"token": "कसा", "roman": "kasa", "trap_explanation": "'कसा' हे पुल्लिंगी एकवचन आहे. 'तुम्ही' सोबत 'कसे' लागते."},
            {"token": "आहेस", "roman": "aahes", "trap_explanation": "'आहेस' हे 'तू' सोबत येते (तू कसा आहेस). 'तुम्ही' सोबत 'आहात' लागते."}
        ],
        "grammar_tip": "Honorific agreement: 'तुम्ही' always pairs with plural verb ending '-आहात' (Tumhi aahat).",
        "topic": "greetings",
        "level": 1
    },
    {
        "id": "scramble_6",
        "prompt_hindi": "भाई, एक कड़क चाय दीजिए।",
        "prompt_roman": "Bhai, ek kadak chai dijiye.",
        "english_meaning": "Brother, please give one strong tea.",
        "target_sentence_devanagari": "भाऊ एक कडक चहा द्या",
        "target_sentence_roman": "Bhau ek kadak chaha dya",
        "target_tokens": ["भाऊ", "एक", "कडक", "चहा", "द्या"],
        "target_tokens_roman": ["Bhau", "ek", "kadak", "chaha", "dya"],
        "distractors": [
            {"token": "दे", "roman": "de", "trap_explanation": "'दे' हे एकेरी किंवा मुलांशी बोलताना वापरतात. टपरीवर किंवा आदरार्थी 'द्या' (dya) म्हणावे."},
            {"token": "दोन", "roman": "don", "trap_explanation": "'दोन' म्हणजे 2 (Two). इथे 'एक' विचारले आहे."},
            {"token": "चाय", "roman": "chai", "trap_explanation": "हिंदी 'चाय' ऐवजी मराठीत 'चहा' (chaha) म्हणा."}
        ],
        "grammar_tip": "Polite imperative: In Marathi, give politely is 'द्या' (dya), whereas informal is 'दे' (de).",
        "topic": "street_food",
        "level": 1
    },
    {
        "id": "scramble_7",
        "prompt_hindi": "क्या यह बस स्वारगेट जाएगी?",
        "prompt_roman": "Kya yeh bus Swargate jaayegi?",
        "english_meaning": "Will this bus go to Swargate?",
        "target_sentence_devanagari": "ही बस स्वारगेटला जाईल का",
        "target_sentence_roman": "Hee bus Swargate-la jaail kaa",
        "target_tokens": ["ही", "बस", "स्वारगेटला", "जाईल", "का"],
        "target_tokens_roman": ["Hee", "bus", "Swargate-la", "jaail", "kaa"],
        "distractors": [
            {"token": "हा", "roman": "haa", "trap_explanation": "Marathi 'बस' (bus) is feminine, so 'ही बस' (hee bus), not masculine 'हा'."},
            {"token": "जातो", "roman": "jaato", "trap_explanation": "'जातो' is present tense masculine. For future 'will go', use 'जाईल' (jaail)."},
            {"token": "काय", "roman": "kaay", "trap_explanation": "Yes/No questions in Marathi end with 'का' (kaa), whereas 'काय' means 'What'."}
        ],
        "grammar_tip": "Yes/No Question marker: In Marathi, place 'का' (kaa) at the very end of the sentence to form a yes/no query.",
        "topic": "travel",
        "level": 3
    },
    {
        "id": "scramble_8",
        "prompt_hindi": "तुम्हें क्या हुआ?",
        "prompt_roman": "Tumhein kya hua?",
        "english_meaning": "What happened to you?",
        "target_sentence_devanagari": "तुला काय झालं",
        "target_sentence_roman": "Tula kaay zhaala",
        "target_tokens": ["तुला", "काय", "झालं"],
        "target_tokens_roman": ["Tula", "kaay", "zhaala"],
        "distractors": [
            {"token": "तू", "roman": "tu", "trap_explanation": "Experiencer needs dative 'तुला' (to you), not subject 'तू'."},
            {"token": "झाली", "roman": "zhaali", "trap_explanation": "'झाली' is feminine. General interrogative 'काय' takes neuter singular 'झालं'."},
            {"token": "झाला", "roman": "zhaala_m", "trap_explanation": "'झाला' is masculine. Neuter 'झालं' is standard for 'what happened'."}
        ],
        "grammar_tip": "Neuter past: 'काय झालं?' (What happened?) is the universal neuter form in Marathi.",
        "topic": "conversation",
        "level": 2
    }
]

BLITZ_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "b1",
        "question": "मराठीत 'उद्या' म्हणजे 'Yesterday' असा अर्थ होतो.",
        "question_roman": "Marathi-t 'udya' mhanje 'Yesterday' asa arth hoto.",
        "type": "true_false",
        "is_true": False,
        "explanation": "चूक! 'उद्या' (udya) म्हणजे Tomorrow! 'Yesterday' साठी 'काल' (kaal) वापरतात.",
        "concept": "temporal_vocabulary",
        "points": 100
    },
    {
        "id": "b2",
        "question": "'मला पाणी पाहिजे' म्हणजे 'I want water'.",
        "question_roman": "'Mala paani pahije' means 'I want water'.",
        "type": "true_false",
        "is_true": True,
        "explanation": "बरोबर! 'मला' (dative) + 'पाहिजे' म्हणजे 'मला हवे आहे / I want'.",
        "concept": "requests",
        "points": 100
    },
    {
        "id": "b3",
        "question": "'मी घर जात आहे' हे व्याकरणदृष्ट्या १००% बरोबर आहे.",
        "question_roman": "'Mi ghar jaat aahe' is 100% grammatically correct.",
        "type": "true_false",
        "is_true": False,
        "explanation": "चूक! मराठीत 'घराकडे जाणे' यासाठी Locative रूप 'घरी' लागते: 'मी घरी जात आहे'.",
        "concept": "locative_case",
        "points": 100
    },
    {
        "id": "b4",
        "question": "'काय चाललंय?' (Kaay chaallay?) चा अर्थ 'What is up?' असा होतो.",
        "question_roman": "'Kaay chaallay?' means 'What's up? / How are things going?'.",
        "type": "true_false",
        "is_true": True,
        "explanation": "बरोबर! हा पुण्यात आणि मुंबईत मित्रांमध्ये वापरला जाणारा लोकप्रिय कट्टा प्रश्न आहे.",
        "concept": "colloquial_slang",
        "points": 100
    },
    {
        "id": "b5",
        "question": "Choose the correct Marathi word for 'Yesterday':",
        "question_roman": "Choose the correct Marathi word for 'Yesterday':",
        "type": "multiple_choice",
        "options": ["काल (Kaal)", "उद्या (Udya)", "परवा (Parwa)"],
        "correct_index": 0,
        "explanation": "'काल' = Yesterday, 'उद्या' = Tomorrow, 'परवा' = Day after tomorrow / Day before yesterday.",
        "concept": "time_words",
        "points": 120
    },
    {
        "id": "b6",
        "question": "मराठीत आदरार्थी 'तुम्ही' सोबत क्रियापद शेवटी '-आहात' येते.",
        "question_roman": "In Marathi, honorific 'Tumhi' pairs with verb ending '-aahat'.",
        "type": "true_false",
        "is_true": True,
        "explanation": "बरोबर! उदा. 'तुम्ही कसे आहात?' (How are you?).",
        "concept": "honorific_agreement",
        "points": 100
    },
    {
        "id": "b7",
        "question": "How do you politely say 'Give one cutting tea' at a Tapri?",
        "question_roman": "How do you politely say 'Give one cutting tea' at a Tapri?",
        "type": "multiple_choice",
        "options": ["एक कटिंग चहा द्या (Dya)", "एक कटिंग चाय दे (De)", "एक कटिंग चहा कर (Kar)"],
        "correct_index": 0,
        "explanation": "'द्या' (dya) हे योग्य आदरार्थी रूप आहे आणि 'चहा' हा शुद्ध मराठी शब्द आहे.",
        "concept": "polite_ordering",
        "points": 120
    },
    {
        "id": "b8",
        "question": "मराठी वर्णमालेतील 'ळ' हे अक्षर हिंदीमध्ये सर्रास वापरले जाते.",
        "question_roman": "The letter 'ळ' is commonly used in standard Hindi.",
        "type": "true_false",
        "is_true": False,
        "explanation": "चूक! 'ळ' (retroflex lateral approximant) हे मराठीचे वैशिष्ट्यपूर्ण अक्षर आहे; हिंदीत ते नाही.",
        "concept": "script_phonology",
        "points": 100
    },
    {
        "id": "b9",
        "question": "'कडक!' हा शब्द मराठीत अप्रतिम किंवा जबरदस्त गोष्टीसाठी वापरतात.",
        "question_roman": "'Kadak!' is used in Marathi slang when something is awesome or superb.",
        "type": "true_false",
        "is_true": True,
        "explanation": "एकदम बरोबर! 'कडक काम केलंस!' म्हणजे भन्नाट काम केलंस!",
        "concept": "slang",
        "points": 100
    },
    {
        "id": "b10",
        "question": "Choose the correct Marathi translation of 'I am hungry':",
        "question_roman": "Choose the correct Marathi translation of 'I am hungry':",
        "type": "multiple_choice",
        "options": ["मला भूक लागली आहे", "मी भुकेला आहे", "माझे भूक आहे"],
        "correct_index": 0,
        "explanation": "मराठीत 'भूक लागणे' ही रचना असते: 'मला भूक लागली आहे' (literally: To me hunger has attached).",
        "concept": "dative_sensations",
        "points": 130
    },
    {
        "id": "b11",
        "question": "मराठीत 'किती झाले?' म्हणजे 'How much does it cost / What is the bill?'.",
        "question_roman": "'Kiti zhaale?' means 'How much is the total / What is the bill?'.",
        "type": "true_false",
        "is_true": True,
        "explanation": "बरोबर! दुकानात किंवा रिक्षात पैसे विचारताना 'किती झाले?' म्हणतात.",
        "concept": "shopping_money",
        "points": 100
    },
    {
        "id": "b12",
        "question": "हिंदीतील 'मुझे जाना पड़ेगा' चे मराठी रूप:",
        "question_roman": "Marathi equivalent of Hindi 'Mujhe jaana padega':",
        "type": "multiple_choice",
        "options": ["मला जावं लागेल", "मी जायचे पडेल", "मला जाणे होईल"],
        "correct_index": 0,
        "explanation": "भविष्यातील सक्तीसाठी '-वं लागेल' प्रत्यय लागतो: 'मला जावं लागेल' (Mala jaava laagel).",
        "concept": "necessity_modal",
        "points": 140
    }
]

STREET_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "fc_road_auto",
        "title": "FC Road Autowala Bargain",
        "marathi_title": "एफसी रोड रिक्षावाल्याशी चर्चा",
        "location": "FC Road, Deccan, Pune",
        "badge_id": "auto_king",
        "badge_name": "FC Road Auto King",
        "badge_icon": "🚗",
        "description": "Negotiate a fair ride from Ferguson College Road to Swargate without getting rejected!",
        "steps": [
            {
                "step_number": 1,
                "speaker": "काका (Autowala)",
                "avatar": "🛺",
                "dialogue_devanagari": "कुठे जायचंय साहेब? स्वारगेट? तिकडे खूप ट्रॅफिक आहे, मीटरने नाही परवडणार. १०० रुपये फिक्स होतील!",
                "dialogue_roman": "Kuthe jaychay saheb? Swargate? Tikde khoop traffic aahe, meter-ne naahi parvadnaar. 100 rupaye fix hotil!",
                "english_meaning": "Where do you want to go, sir? Swargate? Heavy traffic there, meter won't do. Fixed 100 rupees!",
                "choices": [
                    {
                        "id": "c1_a",
                        "text_devanagari": "अहो काका, नेहमीचाच रस्ता आहे! मीटरनेच चला ना, सुट्टे पैसे देतो.",
                        "text_roman": "Aho kaka, nehmichach rasta aahe! Meter-nech chala na, sutte paise deto.",
                        "english": "Uncle, it's the everyday route! Let's go by meter, I'll give exact change.",
                        "is_best": True,
                        "is_hindi_slip": False,
                        "reaction_devanagari": "बरं बरं, बसा! सुट्टे पैसे आहेत तर काही हरकत नाही.",
                        "reaction_roman": "Bara bara, basa! Sutte paise aahet tar kahi harkat naahi.",
                        "xp_reward": 50,
                        "feedback": "Perfect! Respectful 'अहो काका' and mentioning 'सुट्टे पैसे' (exact change) won him over immediately."
                    },
                    {
                        "id": "c1_b",
                        "text_devanagari": "भैय्या १०० रुपये ज्यादा है, ५० ले लो ना प्लीज!",
                        "text_roman": "Bhaiyya 100 rupaye zyaada hai, 50 le lo na please!",
                        "english": "Brother 100 is too much, take 50 please!",
                        "is_best": False,
                        "is_hindi_slip": True,
                        "reaction_devanagari": "अरे भाऊ, पुण्यात मराठीत बोला की! आणि ५० रुपयात कोण जातं तिकडे?",
                        "reaction_roman": "Are bhau, Punyat Marathi-t bola kee! Aani 50 rupayat kon jaata tikde?",
                        "xp_reward": 10,
                        "feedback": "Hindi slip detected! Calling him 'भैय्या' in Pune reduces trust. Use 'काका' or 'भाऊ' in Marathi."
                    },
                    {
                        "id": "c1_c",
                        "text_devanagari": "नाही पाहिजे तुझी रिक्षा, मी चालत जाईन!",
                        "text_roman": "Naahi pahije tuzhi rickshaw, mi chaalat jaain!",
                        "english": "Don't want your auto, I will walk!",
                        "is_best": False,
                        "is_hindi_slip": False,
                        "reaction_devanagari": "जा मग! आम्हाला काय!",
                        "reaction_roman": "Jaa mag! Aamhala kaay!",
                        "xp_reward": 5,
                        "feedback": "A bit too rude ('तुझी' instead of respectful 'तुमची'). Autowala drove off!"
                    }
                ]
            },
            {
                "step_number": 2,
                "speaker": "काका (Autowala)",
                "avatar": "🛺",
                "dialogue_devanagari": "पुण्यात नवीन दिसताय? कुठून आलात? कॉलेजचे विद्यार्थी आहात का?",
                "dialogue_roman": "Punyat naveen distaay? Kuthun aalaat? College-che vidyarthi aahat kaa?",
                "english_meaning": "You seem new to Pune? Where did you come from? Are you college students?",
                "choices": [
                    {
                        "id": "c2_a",
                        "text_devanagari": "हो काका, मी पुण्यात शिकायला आलोय. मराठी शिकण्याचा प्रयत्न करतोय!",
                        "text_roman": "Ho kaka, mi Punyat shikayala aaloy. Marathi shiknyacha prayatna kartoy!",
                        "english": "Yes uncle, I came to Pune to study. Trying to learn Marathi right now!",
                        "is_best": True,
                        "is_hindi_slip": False,
                        "reaction_devanagari": "फार छान वाटलं ऐकून! अशीच मराठी बोला, लगेच शिकाल!",
                        "reaction_roman": "Faar chhaan vaatla aikun! Ashich Marathi bola, lagech shikaal!",
                        "xp_reward": 60,
                        "feedback": "Outstanding! Punes locals deeply appreciate honest efforts to speak the language."
                    },
                    {
                        "id": "c2_b",
                        "text_devanagari": "हा भाई, दिल्ली से आया हूँ, बीटेक कर रहा हूँ.",
                        "text_roman": "Haa bhai, Delhi se aaya hoon, B.Tech kar raha hoon.",
                        "english": "Yes bro, came from Delhi, doing B.Tech.",
                        "is_best": False,
                        "is_hindi_slip": True,
                        "reaction_devanagari": "अच्छा ठीक आहे, स्वारगेट आलं बघा. ४० रुपये झाले मीटरने.",
                        "reaction_roman": "Achha theek aahe, Swargate aala bagha. 40 rupaye zhaale meter-ne.",
                        "xp_reward": 20,
                        "feedback": "Switched back to Hindi! Try to maintain Marathi for maximum street credibility."
                    }
                ]
            }
        ]
    },
    {
        "id": "goodluck_chai",
        "title": "Goodluck Cafe Tapri Chaha",
        "marathi_title": "चहा टपरी आणि बन मस्का कट्टा",
        "location": "Goodluck Chowk, FC Road",
        "badge_id": "tapri_regular",
        "badge_name": "Tapri Regular",
        "badge_icon": "☕",
        "description": "Order like a true local at Pune's legendary evening tea gathering.",
        "steps": [
            {
                "step_number": 1,
                "speaker": "भाऊ (Chaiwala)",
                "avatar": "🍵",
                "dialogue_devanagari": "बोला साहेब! काय देऊ आज? कडक चहा की स्पेशल आलं चहा?",
                "dialogue_roman": "Bola saheb! Kaay deu aaj? Kadak chaha kee special aala chaha?",
                "english_meaning": "Tell me sir! What should I give today? Strong tea or special ginger tea?",
                "choices": [
                    {
                        "id": "gc1_a",
                        "text_devanagari": "भाऊ, एक स्पेशल कटिंग चहा आणि एक मस्का पाव द्या!",
                        "text_roman": "Bhau, ek special cutting chaha aani ek maska pav dya!",
                        "english": "Brother, please give one special cutting tea and one bun maska!",
                        "is_best": True,
                        "is_hindi_slip": False,
                        "reaction_devanagari": "एकदम कडक! दोनच मिनिटात गरम गरम आणतो!",
                        "reaction_roman": "Ekdam kadak! Donach minitaat garam garam aanto!",
                        "xp_reward": 50,
                        "feedback": "Classic tapri phrasing! 'भाऊ', 'कटिंग चहा', and polite 'द्या'."
                    },
                    {
                        "id": "gc1_b",
                        "text_devanagari": "एक चाय और समोसा दे दो जल्दी.",
                        "text_roman": "Ek chai aur samosa de do jaldi.",
                        "english": "Give one tea and samosa fast.",
                        "is_best": False,
                        "is_hindi_slip": True,
                        "reaction_devanagari": "साहेब, समोसा संपलाय, पॅटीस मिळेल.",
                        "reaction_roman": "Saheb, samosa samplay, pattice milel.",
                        "xp_reward": 15,
                        "feedback": "Pure Hindi. In Marathi, say 'भाऊ, चहा द्या'."
                    }
                ]
            },
            {
                "step_number": 2,
                "speaker": "भाऊ (Chaiwala)",
                "avatar": "🍵",
                "dialogue_devanagari": "हा घ्या गरमागरम चहा! अजून काही पाहिजे का?",
                "dialogue_roman": "Haa ghya garmagaram chaha! Azoon kahi pahije kaa?",
                "english_meaning": "Here is piping hot tea! Do you need anything else?",
                "choices": [
                    {
                        "id": "gc2_a",
                        "text_devanagari": "नाही, पुरेसं आहे. भाऊ, किती झाले एकूण? ऑनलाईन चालतं का?",
                        "text_roman": "Naahi, puresa aahe. Bhau, kiti zhaale ekun? Online chaalta kaa?",
                        "english": "No, that's enough. Brother, how much is the total? Do you accept online?",
                        "is_best": True,
                        "is_hindi_slip": False,
                        "reaction_devanagari": "फक्त ३० रुपये झाले. हा समोर क्यूआर कोड आहे, स्कॅन करा!",
                        "reaction_roman": "Phakta 30 rupaye zhaale. Haa samor QR code aahe, scan kara!",
                        "xp_reward": 50,
                        "feedback": "Super fluent! 'किती झाले एकूण?' is how real locals ask the bill."
                    }
                ]
            }
        ]
    },
    {
        "id": "campus_katta",
        "title": "College Canteen Katta",
        "marathi_title": "कॉलेज कट्टा आणि मैत्री",
        "location": "COEP / Fergusson Canteen",
        "badge_id": "canteen_boss",
        "badge_name": "Campus Katta Boss",
        "badge_icon": "🎓",
        "description": "Engage in genuine campus banter with local batchmates between lectures.",
        "steps": [
            {
                "step_number": 1,
                "speaker": "रोहित (Batchmate)",
                "avatar": "🎒",
                "dialogue_devanagari": "अरे मानस! काय चाललंय? कालचा प्रोफेसर कुलकर्णींचा लेक्चर समजला का तुला?",
                "dialogue_roman": "Are Manas! Kaay chaallay? Kaalcha Professor Kulkarni-ncha lecture samajla kaa tula?",
                "english_meaning": "Hey Manas! What's up? Did you understand yesterday's Prof Kulkarni lecture?",
                "choices": [
                    {
                        "id": "ck1_a",
                        "text_devanagari": "अरे अजिबात नाही! खूप अवघड होतं यार, नोट्स शेअर करशील का?",
                        "text_roman": "Are ajibaat naahi! Khoop avghad hota yaar, notes share karshil kaa?",
                        "english": "Not at all! It was very difficult man, will you share notes?",
                        "is_best": True,
                        "is_hindi_slip": False,
                        "reaction_devanagari": "हो नक्कीच! माझ्याकडे सगळे नोट्स आहेत, लेक्चर संपल्यावर पाठवतो.",
                        "reaction_roman": "Ho nakkich! Mazyakade sagle notes aahet, lecture samplayvar pathavto.",
                        "xp_reward": 50,
                        "feedback": "Natural college Marathi! 'अजिबात नाही' (not at all) and 'अवघड' (difficult) are spot on."
                    },
                    {
                        "id": "ck1_b",
                        "text_devanagari": "कुछ समझ नहीं आया भाई, बहुत टफ था.",
                        "text_roman": "Kuch samajh nahi aaya bhai, bahut tough tha.",
                        "english": "Didn't understand anything bro, was very tough.",
                        "is_best": False,
                        "is_hindi_slip": True,
                        "reaction_devanagari": "अरे तू मराठी शिकतोयस ना? मराठीत बोल!",
                        "reaction_roman": "Are tu Marathi shiktoys na? Marathi-t bol!",
                        "xp_reward": 10,
                        "feedback": "Your friend teased you for slipping into Hindi! Try 'खूप अवघड होतं'."
                    }
                ]
            }
        ]
    }
]

SKILL_TREE_NODES: List[Dict[str, Any]] = [
    {
        "id": 1,
        "level": 0,
        "title": "Script & Sounds Bridge",
        "marathi_title": "वर्णमाला आणि उच्चार",
        "icon": "🔤",
        "status": "completed",
        "stars": 3,
        "exercises_count": 10,
        "completed_count": 10,
        "description": "Master distinct Marathi consonants like 'ळ', vowel sounds, and Roman transliteration mapping.",
        "key_concepts": ["ळ phonetics", "Roman vowels", "Devanagari mapping"]
    },
    {
        "id": 2,
        "level": 1,
        "title": "Street Survival & Requests",
        "marathi_title": "रोजची विचारपूस आणि मागण्या",
        "icon": "☕",
        "status": "completed",
        "stars": 3,
        "exercises_count": 10,
        "completed_count": 10,
        "description": "Everyday polite requests: 'पाणी द्या' (give water), 'किती झाले?' (how much), and tea ordering.",
        "key_concepts": ["पाहिजे (want)", "द्या vs दे", "किती झाले?"]
    },
    {
        "id": 3,
        "level": 2,
        "title": "Daily Routine & Time Traps",
        "marathi_title": "दिनक्रम आणि काळ",
        "icon": "⏰",
        "status": "in_progress",
        "stars": 2,
        "exercises_count": 10,
        "completed_count": 7,
        "description": "Conquer false friends: 'काल' (yesterday) vs 'उद्या' (tomorrow), and locative 'घरी' (at home).",
        "key_concepts": ["काल vs उद्या trap", "घरी locative", "आता (now)"]
    },
    {
        "id": 4,
        "level": 3,
        "title": "Dative Desires & Obligation",
        "marathi_title": "इच्छा आणि कर्तव्य",
        "icon": "🎯",
        "status": "locked",
        "stars": 0,
        "exercises_count": 12,
        "completed_count": 0,
        "description": "Subject dative 'मला' paired with obligation verbs: 'मला जायचं आहे', 'मला शिकायचं आहे'.",
        "key_concepts": ["मला subject", "-ायचं आहे", "आवडतं (likes)"]
    },
    {
        "id": 5,
        "level": 4,
        "title": "Colloquial Slang & Nuances",
        "marathi_title": "कट्टा आणि स्थानिक भाषा",
        "icon": "🗣️",
        "status": "locked",
        "stars": 0,
        "exercises_count": 15,
        "completed_count": 0,
        "description": "Authentic Pune/Mumbai expressions: 'कडक', 'काय चाललंय', 'भारी', 'भाऊ', and humor.",
        "key_concepts": ["काय चाललंय", "कडक / भारी", "अजिबात नाही"]
    },
    {
        "id": 6,
        "level": 5,
        "title": "Script Fluency & Native Dialogue",
        "marathi_title": "अस्खलित देवनागरी संभाषण",
        "icon": "🏆",
        "status": "locked",
        "stars": 0,
        "exercises_count": 20,
        "completed_count": 0,
        "description": "Full Devanagari immersion with rapid conversational flow and zero English scaffolding.",
        "key_concepts": ["Pure Devanagari", "Complex subordinate clauses", "Native speed"]
    }
]

class GamificationService:
    """Service handling state, scores, scramble questions, blitz arcade, and scenarios."""

    def get_or_create_profile(self, db: Session, user_id: int = 1) -> UserGamification:
        profile = db.query(UserGamification).filter(UserGamification.user_id == user_id).first()
        if not profile:
            profile = UserGamification(
                user_id=user_id,
                xp=320,
                streak_days=5,
                hearts=3,
                max_hearts=3,
                rank_title="चहा मित्र (Chaha Mitra)",
                unlocked_badges_json=json.dumps(["first_step", "tapri_regular"], ensure_ascii=False),
                blitz_high_score=140,
                completed_scrambles=3,
                completed_scenarios_json=json.dumps(["goodluck_chai"], ensure_ascii=False)
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        return profile

    def get_profile_dto(self, db: Session, user_id: int = 1) -> GamificationProfileResponse:
        profile = self.get_or_create_profile(db, user_id)
        
        # Determine rank title and level based on XP
        user_xp = profile.xp or 0
        current_rank = "शिकारू (Rookie)"
        level = 1
        next_xp = 500
        
        for min_xp, max_xp, title in RANKS:
            if min_xp <= user_xp <= max_xp:
                current_rank = title
                next_xp = max_xp + 1
                break
        
        if user_xp < 200:
            level = 1
        elif user_xp < 500:
            level = 2
        elif user_xp < 1000:
            level = 3
        elif user_xp < 2000:
            level = 4
        else:
            level = 5

        badges = []
        if profile.unlocked_badges_json:
            try:
                badges = json.loads(profile.unlocked_badges_json)
            except Exception:
                badges = ["first_step"]

        scenarios = []
        if profile.completed_scenarios_json:
            try:
                scenarios = json.loads(profile.completed_scenarios_json)
            except Exception:
                scenarios = []

        return GamificationProfileResponse(
            xp=user_xp,
            level=level,
            streak_days=profile.streak_days or 5,
            hearts=profile.hearts if profile.hearts is not None else 3,
            max_hearts=profile.max_hearts or 3,
            rank_title=current_rank,
            unlocked_badges=badges,
            blitz_high_score=profile.blitz_high_score or 0,
            completed_scrambles=profile.completed_scrambles or 0,
            completed_scenarios=scenarios,
            next_level_xp=next_xp
        )

    def process_action(self, db: Session, req: GamificationActionRequest, user_id: int = 1) -> GamificationProfileResponse:
        profile = self.get_or_create_profile(db, user_id)

        if req.action_type == "xp_gain":
            profile.xp = (profile.xp or 0) + (req.xp_amount or 10)
        elif req.action_type == "heart_lost":
            profile.hearts = max(0, (profile.hearts or 3) - 1)
        elif req.action_type == "heart_refill":
            profile.hearts = profile.max_hearts or 3
        elif req.action_type == "unlock_badge" and req.badge_id:
            try:
                current_badges = json.loads(profile.unlocked_badges_json or "[]")
            except Exception:
                current_badges = []
            if req.badge_id not in current_badges:
                current_badges.append(req.badge_id)
                profile.unlocked_badges_json = json.dumps(current_badges, ensure_ascii=False)
                profile.xp = (profile.xp or 0) + 50  # Badge bonus
        elif req.action_type == "blitz_score":
            score = req.score or 0
            if score > (profile.blitz_high_score or 0):
                profile.blitz_high_score = score
            profile.xp = (profile.xp or 0) + max(10, score // 5)
        elif req.action_type == "complete_scramble":
            profile.completed_scrambles = (profile.completed_scrambles or 0) + 1
            profile.xp = (profile.xp or 0) + (req.xp_amount or 25)
        elif req.action_type == "complete_scenario" and req.scenario_id:
            try:
                scenarios = json.loads(profile.completed_scenarios_json or "[]")
            except Exception:
                scenarios = []
            if req.scenario_id not in scenarios:
                scenarios.append(req.scenario_id)
                profile.completed_scenarios_json = json.dumps(scenarios, ensure_ascii=False)
            profile.xp = (profile.xp or 0) + (req.xp_amount or 75)

        profile.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(profile)
        return self.get_profile_dto(db, user_id)

    def get_skill_tree(self, db: Session, user_id: int = 1) -> List[SkillTreeNode]:
        return [SkillTreeNode(**node) for node in SKILL_TREE_NODES]

    def get_scramble_questions(self) -> List[ScrambleQuestion]:
        results = []
        for item in SCRAMBLE_BANK:
            # Build tiles list: target tokens + distractors
            tiles: List[ScrambleTile] = []
            for idx, token in enumerate(item["target_tokens"]):
                roman = item["target_tokens_roman"][idx] if idx < len(item["target_tokens_roman"]) else token
                tiles.append(ScrambleTile(
                    id=f"{item['id']}_t_{idx}",
                    token=token,
                    roman=roman,
                    is_distractor=False,
                    trap_explanation=None
                ))

            for idx, dist in enumerate(item["distractors"]):
                tiles.append(ScrambleTile(
                    id=f"{item['id']}_d_{idx}",
                    token=dist["token"],
                    roman=dist["roman"],
                    is_distractor=True,
                    trap_explanation=dist["trap_explanation"]
                ))

            # Shuffle tiles deterministically seeded by id for replayability or random
            shuffled_tiles = list(tiles)
            random.seed(42 + len(item["id"]))
            random.shuffle(shuffled_tiles)

            results.append(ScrambleQuestion(
                id=item["id"],
                prompt_hindi=item["prompt_hindi"],
                prompt_roman=item["prompt_roman"],
                english_meaning=item["english_meaning"],
                target_sentence_devanagari=item["target_sentence_devanagari"],
                target_sentence_roman=item["target_sentence_roman"],
                target_tokens=item["target_tokens"],
                tiles=shuffled_tiles,
                grammar_tip=item["grammar_tip"],
                topic=item["topic"],
                level=item["level"]
            ))
        return results

    def get_blitz_questions(self) -> List[BlitzQuestion]:
        return [BlitzQuestion(**q) for q in BLITZ_QUESTIONS]

    def get_street_scenarios(self) -> List[StreetScenario]:
        return [StreetScenario(**s) for s in STREET_SCENARIOS]


gamification_service = GamificationService()
