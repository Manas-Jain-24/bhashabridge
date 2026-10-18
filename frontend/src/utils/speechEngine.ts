/**
 * BhashaBridge — Client-Side Speech & Audio Voice Engine
 * Uses Web Speech API (SpeechSynthesis & SpeechRecognition) for:
 * 1. Crystal-clear Marathi / Hindi native audio pronunciation
 * 2. Real-time microphone voice input
 * 3. Interactive pronunciation practice
 */

export class SpeechEngine {
  private synth: SpeechSynthesis | null = null;
  private voices: SpeechSynthesisVoice[] = [];
  private isSpeaking: boolean = false;

  constructor() {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      this.synth = window.speechSynthesis;
      this.loadVoices();
      if (this.synth.onvoiceschanged !== undefined) {
        this.synth.onvoiceschanged = () => this.loadVoices();
      }
    }
  }

  private loadVoices() {
    if (!this.synth) return;
    this.voices = this.synth.getVoices();
  }

  /**
   * Speaks Marathi or Hindi text aloud with learner-optimized cadence.
   */
  public speak(
    text: string,
    language: 'marathi' | 'hindi' = 'marathi',
    rate: number = 0.85,
    onEnd?: () => void
  ) {
    if (!this.synth) return;

    this.synth.cancel(); // Stop any overlapping speech

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = rate; // 0.85x speed allows clear distinction of Marathi retroflex consonants
    utterance.pitch = 1.0;

    const targetLangCode = language === 'marathi' ? 'mr-IN' : 'hi-IN';
    utterance.lang = targetLangCode;

    // Look for matching Marathi or Hindi native voice
    const matchingVoice = this.voices.find(
      (v) =>
        v.lang === targetLangCode ||
        v.lang.toLowerCase().startsWith(language === 'marathi' ? 'mr' : 'hi') ||
        v.name.toLowerCase().includes(language)
    );

    if (matchingVoice) {
      utterance.voice = matchingVoice;
    }

    utterance.onstart = () => {
      this.isSpeaking = true;
    };

    utterance.onend = () => {
      this.isSpeaking = false;
      if (onEnd) onEnd();
    };

    utterance.onerror = () => {
      this.isSpeaking = false;
      if (onEnd) onEnd();
    };

    this.synth.speak(utterance);
  }

  public stop() {
    if (this.synth) {
      this.synth.cancel();
      this.isSpeaking = false;
    }
  }

  public getIsSpeaking(): boolean {
    return this.isSpeaking;
  }

  /**
   * Checks if browser supports Speech Recognition
   */
  public isRecognitionSupported(): boolean {
    if (typeof window === 'undefined') return false;
    return !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);
  }

  /**
   * Starts listening to user microphone for Marathi or Hindi speech.
   */
  public startListening({
    language = 'mr-IN',
    onInterim,
    onFinal,
    onError,
    onEnd,
  }: {
    language?: 'mr-IN' | 'hi-IN';
    onInterim?: (text: string) => void;
    onFinal: (text: string) => void;
    onError?: (err: string) => void;
    onEnd?: () => void;
  }): { stop: () => void } | null {
    if (typeof window === 'undefined') return null;

    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRec) {
      if (onError) onError('Speech recognition is not supported in this browser.');
      return null;
    }

    try {
      const recognizer = new SpeechRec();
      recognizer.lang = language;
      recognizer.continuous = false;
      recognizer.interimResults = true;

      recognizer.onresult = (event: any) => {
        let interimText = '';
        let finalText = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalText += event.results[i][0].transcript;
          } else {
            interimText += event.results[i][0].transcript;
          }
        }

        if (interimText && onInterim) {
          onInterim(interimText);
        }

        if (finalText) {
          onFinal(finalText);
        }
      };

      recognizer.onerror = (event: any) => {
        if (onError) onError(event.error || 'Speech capture failed');
      };

      recognizer.onend = () => {
        if (onEnd) onEnd();
      };

      recognizer.start();

      return {
        stop: () => recognizer.stop(),
      };
    } catch (e: any) {
      if (onError) onError(e?.message || 'Failed to start microphone');
      return null;
    }
  }
}

export const speech = new SpeechEngine();
