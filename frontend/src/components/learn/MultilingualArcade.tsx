import { useEffect, useRef, useState } from 'react';
import { languages, languageEntries, type Language } from '../../config/languages';
import { arcadeRequest, type ArcadeStats, type GameMode, type GameSession, type Difficulty, type Practice } from '../../services/arcade';
import { FoundationsCourse } from './FoundationsCourse';
import { speech } from '../../utils/speechEngine';

const modes: {id: GameMode; title: string; description: string}[] = [
  {id:'recognize', title:'Word Match', description:'Match a Roman spelling to its native word.'},
  {id:'spell', title:'Spelling Builder', description:'Build an attested Roman spelling from letter tiles.'},
  {id:'meaning', title:'Meaning Match', description:'Match everyday words or corpus sentences to English.'},
  {id:'sprint', title:'60-second Sprint', description:'Race through word matches before time runs out.'},
];

export function MultilingualArcade({initialLanguage, onProgressChange}: {initialLanguage: Language; onProgressChange?:()=>void}) {
  const [language, setLanguage] = useState<Language>(initialLanguage);
  const [stats, setStats] = useState<ArcadeStats | null>(null);
  const [run, setRun] = useState<GameSession | null>(null);
  const [mode, setMode] = useState<GameMode>('recognize');
  const [tileIds, setTileIds] = useState<number[]>([]);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [seconds, setSeconds] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [difficulty,setDifficulty]=useState<Difficulty>('beginner');
  const [practice,setPractice]=useState<Practice>('mixed');
  const [topic,setTopic]=useState('all');
  const generation = useRef(0);
  const inFlight = useRef(false);
  const clockDeadline = useRef(0);
  const activeQuestion = useRef<GameSession['question']>(null);
  const gamePanel=useRef<HTMLDivElement>(null);

  useEffect(()=>{ if(run?.session_id) gamePanel.current?.scrollIntoView({behavior:'smooth',block:'start'}); },[run?.session_id]);

  useEffect(() => {
    const controller = new AbortController();
    ++generation.current;
    inFlight.current = false;
    setRun(null); setError(''); setFeedbackOpen(false); setBusy(false); setTileIds([]); activeQuestion.current=null;
    speech.stop();
    return () => { controller.abort(); ++generation.current; speech.stop(); };
  }, [language,difficulty,practice,topic]);

  useEffect(() => {
    const controller = new AbortController();
    setStats(null);
    arcadeRequest<ArcadeStats>('stats/' + language, undefined, controller.signal).then(value => { if (!controller.signal.aborted) setStats(value); }).catch(e => {
      if (!controller.signal.aborted) setError(e.message);
    });
    return () => controller.abort();
  }, [language, refresh]);

  useEffect(() => {
    if (!run || run.done) return;
    const id = run.session_id;
    const version = generation.current;
    const timer = setInterval(() => {
      const remaining = Math.max(0, Math.ceil((clockDeadline.current - Date.now()) / 1000));
      setSeconds(remaining);
      if (remaining === 0) {
        clearInterval(timer);
        arcadeRequest<GameSession>('session/' + id).then(value => {
          if (generation.current === version) { clockDeadline.current = Date.now() + value.remaining_seconds * 1000; setRun(value); setFeedbackOpen(false); }
        }).catch(e => { if (generation.current === version) setError(e.message); });
      }
    }, 300);
    return () => clearInterval(timer);
  }, [run?.session_id, run?.done, run?.remaining_seconds]);

  const start = async (selectedMode: GameMode, lessonId?: string) => {
    if (inFlight.current) return;
    inFlight.current = true;
    const version = ++generation.current;
    setBusy(true); setError(''); setFeedbackOpen(false); setRun(null); setTileIds([]); activeQuestion.current = null;
    try {
      const value = await arcadeRequest<GameSession>('start', {language, mode:selectedMode,difficulty,topic,practice:lessonId?'new':practice,lesson_id:lessonId});
      if (generation.current !== version) return;
      setMode(selectedMode); setRun(value); setTileIds([]);
      activeQuestion.current = value.question;
      clockDeadline.current = Date.now() + value.remaining_seconds * 1000;
      setSeconds(value.remaining_seconds);
    } catch (e: any) { if (generation.current === version) setError(e.message); }
    finally { if (generation.current === version) { setBusy(false); inFlight.current = false; } }
  };

  const answer = async (choiceId?: string) => {
    if (!run?.question || run.done || feedbackOpen || inFlight.current) return;
    const version = generation.current;
    inFlight.current = true; setBusy(true); setError('');
    try {
      const value = await arcadeRequest<GameSession>('answer', {session_id:run.session_id, question_id:run.question.id,
        ...(mode === 'spell' ? {tile_ids:tileIds} : {choice_id:choiceId})});
      if (generation.current !== version) return;
      setRun(value); setFeedbackOpen(true); setRefresh(v=>v+1); onProgressChange?.();
    } catch (e: any) { if (generation.current === version) setError(e.message); }
    finally { if (generation.current === version) { setBusy(false); inFlight.current = false; } }
  };

  const question = feedbackOpen ? activeQuestion.current : run?.question;
  const next = () => { activeQuestion.current = run?.question || null; setFeedbackOpen(false); setTileIds([]); };
  const spec = languages[language];
  const progress = run ? Math.round(100 * run.answered / run.total) : 0;
  const available=stats?.available_by_difficulty[difficulty];
  const due=stats?.review_due[difficulty];

  return <section className="space-y-5" aria-label="Multilingual language arcade">
    <div className="glass-panel rounded-3xl p-5 space-y-4">
      <div className="flex flex-wrap gap-4 items-center justify-between">
        <div><h2 className="text-2xl font-bold">Language Arcade</h2><p className="text-sm text-slate-400">Play with real corpus examples. Build script recognition one round at a time.</p></div>
        <label className="flex items-center gap-2 text-sm">Game language
          <select aria-label="Game language" className="bg-slate-900 border border-slate-700 rounded-xl p-2" value={language} onChange={e=>setLanguage(e.target.value as Language)}>
            {languageEntries.map(([id, item])=><option key={id} value={id}>{item.label} · {item.native_name}</option>)}
          </select>
        </label>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div className="rounded-xl bg-indigo-950 p-3">Level <strong>{stats?.level ?? '—'}</strong></div>
        <div className="rounded-xl bg-indigo-950 p-3"><strong>{stats?.xp ?? '—'}</strong> {spec.label} XP</div>
        <div className="rounded-xl bg-indigo-950 p-3">Best score <strong>{stats?.best_score ?? '—'}</strong></div>
        <div className="rounded-xl bg-indigo-950 p-3"><strong>{stats?.correct_first_awards ?? '—'}</strong> rewarded answers</div>
      </div>
      {!!stats?.badges.length && <p className="text-amber-200 text-sm">🏅 {stats.badges.join(' · ')}</p>}
      <p className="text-sm text-indigo-200">{stats?.mastered_items ?? 0} items with three consecutive correct answers · {Object.values(due ?? {}).reduce((a,b)=>a+b,0)} reviews due at this difficulty</p>
      <p className="text-xs text-slate-400">Beginner vocabulary is an authored draft awaiting review. Higher levels use Google Dakshina spellings and FLORES-200 sentences (CC BY-SA 4.0); they may contain names and formal vocabulary.</p>
      <div className="grid sm:grid-cols-3 gap-3 text-sm">
        <label className="space-y-1">Difficulty<select aria-label="Game difficulty" value={difficulty} onChange={e=>setDifficulty(e.target.value as Difficulty)} className="block w-full bg-slate-900 border border-slate-700 rounded-xl p-2"><option value="beginner">Beginner · everyday vocabulary</option><option value="intermediate">Intermediate · shorter corpus examples</option><option value="advanced">Advanced · full corpus</option></select></label>
        <label className="space-y-1">Practice plan<select aria-label="Practice plan" value={practice} onChange={e=>setPractice(e.target.value as Practice)} className="block w-full bg-slate-900 border border-slate-700 rounded-xl p-2"><option value="mixed">Mix random items and due reviews</option><option value="new">Fresh random round</option><option value="review">Due reviews only</option></select></label>
        {difficulty==='beginner' && <label className="space-y-1">Topic<select aria-label="Vocabulary topic" value={topic} onChange={e=>setTopic(e.target.value)} className="block w-full bg-slate-900 border border-slate-700 rounded-xl p-2">{['all','daily','places','people','objects','nature','numbers'].map(t=><option key={t} value={t}>{t==='all'?'All topics':t[0].toUpperCase()+t.slice(1)}</option>)}</select></label>}
      </div>
      <p className="text-xs text-slate-400">Mistakes are due immediately. Correct answers are scheduled for review after 1, 3, 7, 14, then 30 days. Random rounds can repeat familiar items. Mixed rounds include up to half due reviews, scoped to language, mode and difficulty.</p>
    </div>

    {error && <div role="alert" className="rounded-xl border border-rose-500 p-4 text-rose-200">{error} <button className="underline ml-2" onClick={()=>setRefresh(v=>v+1)}>Reload stats</button></div>}

    <div className="grid sm:grid-cols-2 gap-3">
      {modes.map(item=><button key={item.id} disabled={busy || !available?.[item.id] || (practice==='review' && !due?.[item.id])} onClick={()=>start(item.id)} className={`text-left rounded-2xl border p-4 disabled:opacity-40 ${run && mode===item.id ? 'border-indigo-400 bg-indigo-950' : 'border-slate-700 bg-slate-900 hover:bg-slate-800'}`}>
        <strong>{item.title}</strong><p className="text-sm text-slate-400 mt-1">{item.description}</p><p className="text-xs text-indigo-300 mt-2">{practice==='review' ? `${due?.[item.id] ?? 0} due reviews` : `${difficulty==='beginner' && topic!=='all' ? stats?.topic_counts[topic] ?? '…' : available?.[item.id]?.toLocaleString() ?? '…'} source examples`} · Start round</p>
      </button>)}
    </div>

    {busy && !run && <p role="status" className="text-indigo-300">Starting your round…</p>}

    {run && <div ref={gamePanel} className="glass-panel rounded-3xl p-5 sm:p-7 space-y-5 scroll-mt-20">
      <div className="flex justify-between flex-wrap gap-3 font-semibold"><span>{spec.label} · {run.lesson_id?'Lesson checkpoint':modes.find(m=>m.id===mode)?.title} · {run.difficulty}</span><span>♥ {run.lives} · Score {run.score} · {mode==='sprint' ? `${seconds}s` : `${run.answered}/${run.total}`}</span></div>
      <div className="h-2 rounded bg-slate-800 overflow-hidden"><div className="h-full bg-indigo-400 transition-all" style={{width:`${progress}%`}} /></div>
      {(!run.done || feedbackOpen) && question && <>
        <p className="text-sm text-slate-400">{mode==='spell' ? 'Build this word’s Roman spelling:' : mode==='meaning' ? 'Choose the matching translation:' : 'Choose the native spelling:'}</p>
        <h3 lang={mode==='spell' ? spec.iso : 'en'} className="text-xl sm:text-2xl leading-relaxed font-semibold">{question.prompt}</h3>
        {mode==='spell' ? <>
          <div aria-label="Built spelling" className="min-h-14 bg-slate-950 rounded-xl p-3 text-2xl font-mono tracking-wider">{tileIds.map(i=>question.tiles?.[i]).join('') || '…'}</div>
          <div className="flex flex-wrap gap-2">{question.tiles?.map((tile,i)=><button key={i} disabled={busy || feedbackOpen || tileIds.includes(i)} aria-label={`Tile ${i+1}: ${tile}`} onClick={()=>setTileIds(ids=>[...ids,i])} className="rounded-xl px-4 py-3 bg-indigo-700 disabled:opacity-30 font-mono font-bold">{tile}</button>)}</div>
          <div className="flex gap-3"><button disabled={busy || feedbackOpen} onClick={()=>setTileIds(ids=>ids.slice(0,-1))} className="px-4 py-2 rounded-lg bg-slate-800">Undo</button><button disabled={busy || feedbackOpen || tileIds.length !== question.tiles?.length} onClick={()=>answer()} className="px-5 py-2 rounded-lg bg-indigo-600 disabled:opacity-40">Check spelling</button></div>
        </> : <div className="grid sm:grid-cols-2 gap-3">{question.options?.map(option=><button key={option.id} disabled={busy || feedbackOpen} onClick={()=>answer(option.id)} lang={spec.iso} className="rounded-2xl border border-slate-700 p-4 text-lg leading-relaxed bg-slate-900 hover:border-indigo-400 disabled:opacity-60">{option.text}</button>)}</div>}
      </>}
      {busy && <p role="status" className="text-indigo-300">Saving your answer…</p>}
      {feedbackOpen && run.feedback && <div role="status" className={`rounded-2xl border p-4 space-y-2 ${run.feedback.correct ? 'border-emerald-500 bg-emerald-950/40' : 'border-amber-500 bg-amber-950/40'}`}>
        <strong>{run.feedback.correct ? 'Correct!' : 'Keep practising.'} +{run.feedback.xp_awarded} XP</strong>
        {run.feedback.lesson_completed && <p className="text-emerald-200">Lesson checkpoint passed! +{run.feedback.completion_xp ?? 0} completion XP</p>}
        <p lang={spec.iso} className="text-xl">{run.feedback.reference}</p>{run.feedback.roman && <p className="font-mono">{run.feedback.roman}</p>}
        {run.feedback.correct && run.feedback.xp_awarded===0 && <p className="text-xs">You already earned today’s XP for this example in this game mode.</p>}
        <div className="flex flex-wrap gap-3"><button onClick={()=>speech.speak(run.feedback!.reference,language)} className="underline text-sm">Listen</button><button onClick={next} className="bg-indigo-600 rounded-xl px-5 py-2">{run.done ? 'See round result' : 'Next question'}</button></div>
      </div>}
      {run.done && !feedbackOpen && <div className="text-center space-y-3 py-6"><div className="text-4xl">{run.correct >= Math.ceil(run.total*.8) ? '🏆' : '🌱'}</div><h3 className="text-2xl font-bold">Round complete</h3><p>{run.correct} correct out of {run.answered} answered · Score {run.score}</p><p className="text-sm text-slate-400">{run.lives===0 ? 'Three mistakes ended this round. Try a fresh set.' : seconds===0 ? 'Time is up. Your saved answers count.' : 'Your progress is saved.'}</p><button onClick={()=>start(mode,run.lesson_id)} disabled={busy} className="rounded-xl bg-indigo-600 px-6 py-3">Play again</button></div>}
    </div>}
    <FoundationsCourse language={language} completed={stats?.completed_lessons ?? []} disabled={busy || !stats} onPractice={id=>start('meaning',id)} />
  </section>;
}
