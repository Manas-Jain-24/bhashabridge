import {useState, useEffect, useContext} from 'react';
import {AccountContext} from './AccountShell';
import {apiJson} from '../services/http';
import {useDialog} from '../utils/useDialog';
type Draft = {source_language:string;target_language:string;source_text:string;observed_target:string};
type Report = Draft & {id:string;status:string;version:number;category:string;note:string;proposed_target?:string;proposed_roman?:string;proposed_english?:string;provenance:string;license:string};
export function CorrectionQueue({initial,onClose}:{initial:Draft|null;onClose:()=>void}) {
  const account=useContext(AccountContext);
  const dialog=useDialog(true);
  const [reports,setReports]=useState<Report[]>([]);
  const [offset,setOffset]=useState(0);
  const [selected,setSelected]=useState<Report|null>(null);
  const [category,setCategory]=useState('intent');
  const [note,setNote]=useState('');
  const [target,setTarget]=useState('');
  const [roman,setRoman]=useState('');
  const [english,setEnglish]=useState('');
  const [provenance,setProvenance]=useState('');
  const [license,setLicense]=useState('');
  const [attested,setAttested]=useState(false);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [history,setHistory]=useState<{action:string;actor_id:number;created_at:string}[]>([]);
  const load=async()=>setReports(await apiJson<Report[]>('/api/corrections?limit=50&offset='+offset));
  useEffect(()=>{let active=true;void apiJson<Report[]>('/api/corrections?limit=50&offset='+offset).then(rows=>{if(active)setReports(rows);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[offset]);
  useEffect(()=>{const key=(e:KeyboardEvent)=>{if(e.key==='Escape')onClose();};document.addEventListener('keydown',key);return()=>document.removeEventListener('keydown',key);},[]);
  const act=async(operation:()=>Promise<unknown>)=>{setBusy(true);setError('');try{await operation();await load();}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
  const create=async(e:React.FormEvent)=>{e.preventDefault();if(!initial)return;await act(async()=>{
    const row=await apiJson<Report>('/api/corrections',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...initial,category,note,provenance:'Learner report from translation screen; unreviewed',license:'User contribution; permission required before redistribution'})});
    setSelected(row);setTarget('');setRoman('');setEnglish('');setProvenance(row.provenance);setLicense(row.license);setHistory([]);
  });};
  const choose=async(row:Report)=>{setSelected(row);setTarget(row.proposed_target||'');setRoman(row.proposed_roman||'');setEnglish(row.proposed_english||'');setProvenance(row.provenance);setLicense(row.license);setNote(row.note);setAttested(false);setHistory([]);
    try{setHistory(await apiJson('/api/corrections/'+row.id+'/history'));}catch(e){setError((e as Error).message);}};
  const proposal=async(e:React.FormEvent)=>{e.preventDefault();if(!selected)return;await act(async()=>{const row=await apiJson<Report>('/api/corrections/'+selected.id+'/proposal',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({version:selected.version,target,roman,english,note,provenance,license})});await choose(row);});};
  const decision=(status:string)=>{if(!selected)return;void act(async()=>{setSelected(await apiJson<Report>('/api/corrections/'+selected.id+'/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({version:selected.version,status,human_attestation:attested,note})}));setAttested(false);setHistory([]);});};
  const field='w-full bg-slate-950 border border-slate-600 rounded-lg p-2 text-white';
  return <div ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-label="Correction review queue" className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/95 text-slate-100 p-4 sm:p-10">
    <div className="max-w-4xl mx-auto space-y-5 [overflow-wrap:anywhere]">
      <div className="flex justify-between gap-4"><h2 className="text-2xl font-bold">Correction review queue</h2><button onClick={onClose} className="underline">Close review queue</button></div>
      <p className="text-amber-200">Reports and proposals are unreviewed. They do not change translations or train a model. Only an assigned human reviewer can record a review decision.</p>
      {error&&<p role="alert" className="text-rose-300">{error}</p>}
      {initial&&!selected&&<form onSubmit={create} className="space-y-3 rounded-xl border border-slate-700 p-4">
        <p>{initial.source_text}</p><p>{initial.observed_target}</p>
        <label className="block">Issue category<select className={field} value={category} onChange={e=>setCategory(e.target.value)}>{['spelling','negation','tense','intent','entity','fluency','roman','english','explanation','other'].map(value=><option key={value}>{value}</option>)}</select></label>
        <label className="block">What seems wrong?<textarea className={field} maxLength={2000} value={note} onChange={e=>setNote(e.target.value)}/></label>
        <button disabled={busy} className="bg-indigo-600 p-2 rounded">Submit unreviewed report</button>
      </form>}
      <ul className="space-y-2" aria-label="Your correction reports">{reports.map(row=><li key={row.id}><button className="w-full text-left border border-slate-700 rounded-lg p-3" onClick={()=>void choose(row)}>{row.source_language} → {row.target_language}: {row.source_text} <strong>({row.status})</strong></button></li>)}</ul>
      <nav aria-label="Correction pages" className="flex gap-4 items-center"><button disabled={busy||offset===0} onClick={()=>{setSelected(null);setOffset(Math.max(0,offset-50));}} className="underline disabled:opacity-40">Previous reports</button><span>Page {offset/50+1}</span><button disabled={busy||reports.length<50} onClick={()=>{setSelected(null);setOffset(offset+50);}} className="underline disabled:opacity-40">Next reports</button></nav>
      {!reports.length&&<p>No reports yet. Use “Report a translation issue” below a translation.</p>}
      {selected&&<section className="rounded-xl border border-slate-700 p-4 space-y-3">
        <h3 className="font-bold">{selected.source_text} — {selected.status}</h3><p>Observed: {selected.observed_target}</p>
        <p className="text-xs text-slate-400">Source: {selected.provenance}. Rights: {selected.license}.</p>
        <form onSubmit={proposal} className="space-y-3">
          <label className="block">Proposed native translation<textarea className={field} required maxLength={4000} value={target} onChange={e=>setTarget(e.target.value)}/></label>
          <label className="block">Proposed Roman spelling<input className={field} maxLength={4000} value={roman} onChange={e=>setRoman(e.target.value)}/></label>
          <label className="block">Proposed English meaning<input className={field} maxLength={1000} value={english} onChange={e=>setEnglish(e.target.value)}/></label>
          <label className="block">Source / provenance<input className={field} required maxLength={1000} value={provenance} onChange={e=>setProvenance(e.target.value)}/></label>
          <label className="block">License or permission<input className={field} required maxLength={120} value={license} onChange={e=>setLicense(e.target.value)}/></label>
          <p className="text-xs text-slate-400">Record actual rights and source information. Changing a proposal or its provenance requires a new review.</p>
          <label className="block">Reason / review note<textarea className={field} required maxLength={2000} value={note} onChange={e=>setNote(e.target.value)}/></label>
          <button disabled={busy} className="bg-indigo-600 p-2 rounded">Save unreviewed proposal</button>
        </form>
        {account?.role==='reviewer'&&selected.status==='proposed'&&<div className="space-y-3">
          <label className="flex gap-2"><input type="checkbox" checked={attested} onChange={e=>setAttested(e.target.checked)}/>I personally reviewed both languages and the proposed supporting text.</label>
          <button disabled={busy||!attested||!note.trim()} onClick={()=>decision('reviewed')} className="p-2 bg-emerald-800 rounded mr-3">Record human review</button>
          <button disabled={busy||!attested||!note.trim()} onClick={()=>decision('rejected')} className="p-2 bg-rose-800 rounded">Reject proposal</button>
        </div>}
        <ol aria-label="Review history">{history.map((event,index)=><li key={index}>{event.created_at}: {event.action} by account {event.actor_id}</li>)}</ol>
      </section>}
    </div>
  </div>;
}
