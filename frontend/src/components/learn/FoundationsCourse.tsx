import { useEffect, useState } from 'react';
import { type Language, languages } from '../../config/languages';
import { arcadeRequest } from '../../services/arcade';
import { speech } from '../../utils/speechEngine';

interface Unit { id: string; title: string; review_status: string; source_url?: string; note: string; items: {native:string; roman:string; english:string}[]; }
interface Course { title: string; review_note: string; units: Unit[]; }

export function FoundationsCourse({language, completed, disabled, onPractice}: {
  language: Language; completed: string[]; disabled: boolean; onPractice: (id:string)=>void;
}) {
  const [course,setCourse]=useState<Course|null>(null);
  const [active,setActive]=useState('');
  const [roman,setRoman]=useState(true);
  const [error,setError]=useState('');
  useEffect(()=>{
    const controller=new AbortController();
    setCourse(null); setActive(''); setError('');
    arcadeRequest<Course>('lessons/'+language,undefined,controller.signal).then(value=>{
      if(!controller.signal.aborted) { setCourse(value); setActive(value.units[0]?.id || ''); }
    }).catch(e=>{if(!controller.signal.aborted) setError(e.message);});
    return ()=>controller.abort();
  },[language]);
  const unit=course?.units.find(u=>u.id===active);
  if(error) return <p role="alert">Could not load starter lessons: {error}</p>;
  if(!course?.units.length) return null;
  return <section className="glass-panel rounded-3xl p-5 space-y-4" aria-label="Starter lessons">
    <div className="flex flex-wrap justify-between gap-3"><div><h3 className="text-xl font-bold">{course.title}</h3><p className="text-sm text-slate-400">{completed.length}/{course.units.length} checkpoints passed · 24 everyday phrases</p></div><label className="flex gap-2 items-center text-sm"><input type="checkbox" checked={roman} onChange={e=>setRoman(e.target.checked)} />Show Roman guide</label></div>
    <p className="text-xs text-amber-200">{course.review_note}</p>
    <div className="grid sm:grid-cols-3 gap-2">{course.units.map(item=><button key={item.id} onClick={()=>{speech.stop(); setActive(item.id);}} aria-pressed={active===item.id} className={`text-left rounded-xl border p-3 text-sm ${active===item.id?'border-indigo-400 bg-indigo-950':'border-slate-700 bg-slate-900'}`}>{completed.includes(item.id)?'✓ ':''}{item.title}<span className="block text-xs text-slate-400 mt-1">{item.review_status==='source_checked'?'Source-checked phrases':'Draft · review pending'}</span></button>)}</div>
    {unit && <div className="space-y-3">
      <p className="text-sm text-slate-300">{unit.note}</p>
      {unit.source_url && <a className="text-xs underline text-indigo-300" href={unit.source_url} target="_blank" rel="noreferrer">Check the Bhasha Sangam source</a>}
      <div className="grid sm:grid-cols-2 gap-3">{unit.items.map(item=><article key={item.native} className="bg-slate-950 rounded-2xl p-4 space-y-1"><p lang={languages[language].iso} className="text-xl leading-relaxed">{item.native}</p>{roman && <p className="font-mono text-indigo-300 text-sm">{item.roman}</p>}<p className="text-sm text-slate-300">{item.english}</p><button className="text-xs underline text-indigo-300" onClick={()=>speech.speak(item.native,language)}>Listen to phrase</button></article>)}</div>
      <button onClick={()=>onPractice(unit.id)} disabled={disabled} className="rounded-xl bg-indigo-600 px-5 py-3 disabled:opacity-40">Practise this lesson</button><p className="text-xs text-slate-400">Pass at least 80% to save the checkpoint. First completion earns 10 bonus XP. Roman spellings are learning aids.</p>
    </div>}
  </section>;
}
