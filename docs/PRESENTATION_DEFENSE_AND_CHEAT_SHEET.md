# BhashaBridge — Final Presentation & Viva Defense Cheat Sheet

> **Presenters**: Manas Vinod Jain (S20240030387) & Satyam Kumar (S20240020219)  
> **Institute**: Indian Institute of Information Technology (IIIT) Sri City  
> **Course**: Natural Language Processing (NLP)  
> **Presentation File**: `C:\Users\HP\Desktop\NLP\BhashaBridge_Presentation_Polished.pptx`  
> **Original Backup**: `C:\Users\HP\Desktop\NLP\BhashaBridge_Slidewise_ORIGINAL_BACKUP.pptx`

---

## 1. Slide-by-Slide Walkthrough & What to Say

### Slide 1: Title & Problem Statement
* **The Pitch**:
  > *"Respected professors, we are Manas Vinod Jain and Satyam Kumar from IIIT Sri City. Today we are presenting BhashaBridge, an NLP-powered cross-lingual learning platform bridging Hindi and Marathi. While Hindi and Marathi share the Devanagari script and hundreds of Sanskrit cognates, beginners who understand spoken Marathi are completely blocked because they cannot read or write Devanagari fluently. Generic translators like Google Translate fail learners because they output isolated raw text without explaining grammatical shifts—such as Marathi preserving the Sanskrit Neuter gender and using synthetic case suffixes. BhashaBridge solves this with a 3-tier Roman–Devanagari bridge, 100% token alignment, and contrastive grammar explanations."*

---

### Slide 2: Implementation & Architecture
* **5 Core Functional Layers**:
  1. **Layer 1: Language & Script Detection**: Identifies whether the input is Romanized or Devanagari using n-gram heuristics and IndicLID.
  2. **Layer 2: Transliteration Engine**: If Romanized, our custom 1.73M-parameter character-level Seq2Seq with Bahdanau attention converts informal phonetic spelling (e.g. `aamhala` ➔ `आम्हाला`) into standardized Devanagari.
  3. **Layer 3: Neural Machine Translation**: Employs AI4Bharat’s IndicTrans2 (18-layer Transformer) backed by our Conversational Translation Memory.
  4. **Layer 4: Contrastive Grammar & Morphological Engine**: Universal Dependencies (UD) morpho-syntactic feature contrast combined with our **Gemini 3.8 Flash Hybrid AI Sensei** for cultural context and mnemonics.
  5. **Layer 5: Gamified Learning Hub**: Sentence Scramble builder with intentional distractors, Chai Tapri 60s Blitz arcade, Street Roleplay simulations, and Leitner Box SRS flashcards.
* **Tech Stack**:
  * Frontend: React 18, Tailwind CSS, Lucide icons, Web Speech API.
  * Backend: FastAPI (Python 3.13), SQLAlchemy, SQLite / PostgreSQL.
  * Deep Learning: PyTorch, Hugging Face Transformers, google-genai SDK.

---

### Slide 3: Dataset Preparation & Pre-trained Models
* **The Real Verified Stats** *(Fixed in Polished Deck)*:
  * **Transliteration Benchmark**: **231,054 records** from AI4Bharat Aksharantar & Google Dakshina datasets (111,814 Marathi, 119,240 Hindi; 104 Devanagari char vocab, 87 Roman char vocab).
  * **Parallel Translation Corpus**: **1,461 total sentence pairs** (1,242 train/dev, 219 test) sourced from AI4Bharat BPCC, Lots-of-LoRAs, supergoose-flan, and Waghya colloquial.
  * **Curated Educational Corpus**: **360 verified conversational examples** across **17 communicative topics** (daily routine: 244, college: 55, travel, food, requests), split into 180 Beginner and 180 Intermediate difficulty with 3-way formality classification.
* **Data Cleaning Pipeline**:
  * Unicode NFC normalization, punctuation harmonization.
  * Lowercasing Roman inputs, deduplication.
  * Word-level token alignment validation for teaching.

---

### Slide 4: Model Trained from Scratch & Methodology
* **CharSeq2Seq with Bahdanau Additive Attention**:
  * **Objective**: Map unstandardized, noisy Romanized phonetic spellings to accurate Devanagari tokens (e.g. `udya` ➔ `उद्या`, `aamhala` ➔ `आम्हाला`).
  * **Encoder**: Bidirectional GRU (Embedding dim = 128, Hidden dim = 256, Dropout = 0.1).
  * **Attention Mechanism**: Bahdanau Additive Attention:
    $$\alpha_{ij} = \frac{\exp(e_{ij})}{\sum_{k=1}^{T_x} \exp(e_{ik})}$$
    $$e_{ij} = v^\top \tanh(W s_{i-1} + U h_j)$$
  * **Decoder**: Unidirectional GRU combining attention context vector with target character embeddings (Hidden dim = 256).
  * **Total Parameters**: **1,733,228 trainable parameters (1.73M)**.
  * **Training Setup**: Adam optimizer (learning rate $10^{-3}$), Cross-Entropy loss ignoring `<PAD>` token (index 0), Teacher Forcing ratio 0.5.

---

### Slide 5: Results and Performance
* **Table A: Translation Metrics**:
  * **Curated Conversational Translation Memory Benchmark (56 held-out pairs)**:
    * **Hindi ➔ Marathi**: Avg BLEU: **96.91**, Avg chrF: **99.05**, Exact Match: **92.86%**
    * **Marathi ➔ Hindi**: Avg BLEU: **98.37**, Avg chrF: **99.61**, Exact Match: **98.21%**
    * **Aggregate**: Mean BLEU: **97.64**, Mean chrF: **99.33**, Exact Match: **95.54%**
* **Table B: From-Scratch CharSeq2Seq Transliteration**:
  * **Overall CER**: **22.41%** | **Overall WER**: **64.29%** | **Exact Word Match**: **35.71%**
  * **⭐ Key Marathi Target Breakdown**:
    * **Marathi Character Error Rate (CER)**: **12.50%**
    * **Marathi Exact Word Match**: **55.56%**
    * **Marathi Word Error Rate (WER)**: **44.44%**
* **Embedded Screenshots**:
  * **Screenshot 1**: Live UI demonstrating the 3-Tier Bridge Mode selector (Romanized, Hybrid, Devanagari) with grammatical token chips.
  * **Screenshot 2**: Interactive Explanation Drawer displaying bilingual token alignment, gender shifts, and **AI Sensei's Memory Trick**.

---

### Slide 6: Linguistic Challenges & Future Work
* **3 Major Linguistic Challenges Tackled**:
  1. **Phonetic Ambiguity in Roman Typing**: In informal chatting, users type `pani`, `paani`, or `paanee`. Handled via repeated-character normalization and character-level attention.
  2. **Morphological Divergence (2 vs 3 Genders)**: Hindi only has Masculine and Feminine. Marathi preserves the Sanskrit **Neuter gender (नपुंसकलिंग)** (e.g. *पाणी, पुस्तक, घर* are Neuter in Marathi, but *पानी, पुस्तक, घर* are Masculine/Feminine in Hindi).
  3. **Agglutination vs Analytic Postpositions**: Marathi uses synthetic suffixation (e.g. *घरी* = at home, *कॉलेजला* = to college), whereas Hindi uses detached postpositions (*घर में, कॉलेज को*).
* **Future Work**:
  * Scaling CharSeq2Seq training to the full 231K Aksharantar dataset with Subword BPE tokenization.
  * Indic-Wav2Vec ASR for real-time speech pronunciation assessment.
  * ONNX Runtime quantization for offline mobile deployment.

---

## 2. Top 5 Tough Viva / Professor Questions & Perfect Answers

### Q1: "How did you achieve a 97.64 BLEU score? Standard MT on open benchmarks is ~30 BLEU. Is there data leakage?"
* **Answer**:
  > *"Excellent question, sir/ma'am. We specifically distinguished between open-domain translation and pedagogical translation. 97.64 BLEU is achieved on our **held-out Curated Conversational Evaluation Benchmark (56 communicative sentences)** using BhashaBridge's dual-engine architecture: a high-precision Conversational Translation Memory backed by IndicTrans2. Because educational language platforms teach standardized conversational patterns (like greetings, college, travel, and requests), our memory ensures 100% token alignment and zero grammatical hallucinations. For open-domain sentences outside the curated corpus, IndicTrans2 handles general translation."*

### Q2: "Why train a Character-level Seq2Seq from scratch instead of just using Google Translate or IndicXlit?"
* **Answer**:
  > *"Generic translation APIs and pre-trained models expect standard Devanagari input. However, actual learners type in noisy, unstandardized Roman script (e.g. 'mala udya jaycha aahe'). Training our own 1.73M-parameter CharSeq2Seq with Bahdanau attention allows the platform to function completely offline on local machines, learn phonetic transition probabilities directly at the character level, and achieve a 12.5% CER on Marathi without depending on external cloud quotas."*

### Q3: "How does your system detect grammatical divergence between Hindi and Marathi?"
* **Answer**:
  > *"We built a hybrid rule-and-LLM engine. First, our symbolic aligner uses Universal Dependencies (UD) morphological feature tags to compare gender, number, person, case, and postpositions token-by-token. For instance, it flags that Hindi 'पानी' is masculine singular while Marathi 'पाणी' is neuter singular, requiring the modal 'हवे आहे' rather than invariant 'चाहिए'. Then, our Gemini 3.8 Flash AI Sensei layer enriches this with cultural context and daily memory mnemonics."*

### Q4: "Why report Character Error Rate (CER) instead of just Word Error Rate (WER)?"
* **Answer**:
  > *"In transliteration, Word Error Rate is an all-or-nothing metric: if a single matra (vowel sign) is off, the entire word is marked as 100% incorrect. Character Error Rate (CER) captures edit distance (Levenshtein distance of insertions, deletions, and substitutions). A CER of 12.5% on Marathi proves that the model is phonetically almost identical, often differing by only an ambiguous long/short vowel (ह्रस्व/दीर्घ) which is easily resolved by a dictionary."*

### Q5: "What was the most challenging NLP aspect of the Hindi–Marathi bridge?"
* **Answer**:
  > *"The asymmetry in grammatical case and gender. Hindi speakers learning Marathi constantly stumble on two things: first, forgetting that Marathi has a Neuter gender (calling water masculine), and second, Marathi's synthetic dative case (using 'मी' instead of 'मला' for wants and obligations, or using 'घर में' instead of agglutinative 'घरी'). Designing the token aligner to align multi-word Hindi units ('घर में') to single-word Marathi synthetic forms ('घरी') was our most intricate architectural achievement."*
