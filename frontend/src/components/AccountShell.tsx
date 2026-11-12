import {useState, useEffect, type ReactNode, createContext} from 'react';
import {apiJson} from '../services/http';

export type Account = {id:number; username:string; role:string};
export const AccountContext = createContext<Account | null>(null);
const field = 'block w-full rounded-lg bg-slate-900 border border-slate-600 p-3 text-white';

export function AccountShell({children}:{children:ReactNode}) {
  const [account,setAccount] = useState<Account|null>(null);
  const [loading,setLoading] = useState(true);
  const [mode,setMode] = useState<'login'|'register'>('login');
  const [registration,setRegistration] = useState(false);
  const [error,setError] = useState('');
  const [busy,setBusy] = useState(false);
  const [username,setUsername] = useState('');
  const [password,setPassword] = useState('');
  const [managing,setManaging] = useState(false);
  const [deletePassword,setDeletePassword] = useState('');
  const load = async () => {
    setLoading(true); setError('');
    try {
      const config = await apiJson<{mode:string;registration:boolean}>('/api/auth/config');
      setRegistration(config.registration);
      try { setAccount(await apiJson<Account>('/api/auth/me')); }
      catch (failure) { setAccount(null); if (config.mode==='local') throw failure; }
    } catch (failure) { setError((failure as Error).message); }
    finally { setLoading(false); }
  };
  useEffect(()=>{
    void load();
    const expired=()=>{setAccount(null);setMode('login');setPassword('');setError('Your session expired. Sign in again.');};
    window.addEventListener('bhashabridge:session-expired',expired);
    const audio=(event:Event)=>setError((event as CustomEvent<string>).detail);
    window.addEventListener('bhashabridge:speech-error',audio);
    return ()=>{window.removeEventListener('bhashabridge:session-expired',expired);window.removeEventListener('bhashabridge:speech-error',audio);};
  },[]);
  const submit=async(event:React.FormEvent)=>{
    event.preventDefault();setBusy(true);setError('');
    try {setAccount(await apiJson<Account>('/api/auth/'+mode,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password})}));setPassword('');}
    catch(failure){setError((failure as Error).message);}finally{setBusy(false);}
  };
  const signOut=async()=>{
    setBusy(true);
    try {await apiJson('/api/auth/logout',{method:'POST'});setAccount(null);setMode('login');setPassword('');setManaging(false);await load();}
    catch(failure){setError((failure as Error).message);}finally{setBusy(false);}
  };
  const exportData=async()=>{
    try {const data=await apiJson('/api/auth/export');const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
      const a=document.createElement('a');a.href=url;a.download='bhashabridge-account.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
    catch(failure){setError((failure as Error).message);}
  };
  const deleteAccount=async(event:React.FormEvent)=>{
    event.preventDefault();setBusy(true);setError('');
    try {await apiJson('/api/auth/account',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:deletePassword})});setDeletePassword('');setMode('login');setAccount(null);setManaging(false);}
    catch(failure){setError((failure as Error).message);}finally{setBusy(false);}
  };
  if(loading)return <main className="p-8 text-slate-100" role="status">Loading your workspace…</main>;
  if(!account)return <main className="max-w-md mx-auto p-8 space-y-5 text-slate-100">
    <h1 className="text-2xl font-bold">{mode==='login'?'Sign in to BhashaBridge':'Create your learner account'}</h1>
    <form onSubmit={submit} className="space-y-4">
      <label className="block">Username<input className={field} autoComplete="username" pattern="[a-zA-Z0-9_]{3,40}" required value={username} onChange={e=>setUsername(e.target.value)} /></label>
      <label className="block">Password<input className={field} type="password" autoComplete={mode==='login'?'current-password':'new-password'} minLength={12} maxLength={128} required value={password} onChange={e=>setPassword(e.target.value)} /></label>
      <p className="text-sm text-slate-400">Use 3–40 letters, numbers or underscores for your username and at least 12 characters for your password.</p>
      <button disabled={busy} className="rounded-lg bg-indigo-600 p-3 w-full">{busy?'Please wait…':mode==='login'?'Sign in':'Create account'}</button>
    </form>
    {registration&&<button onClick={()=>{setMode(mode==='login'?'register':'login');setError('');}} className="underline">{mode==='login'?'Create an account':'Already have an account? Sign in'}</button>}
    {error&&<p role="alert" className="text-rose-300">{error} <button onClick={()=>void load()} className="underline">Retry connection</button></p>}
  </main>;
  return <AccountContext.Provider value={account}><div className="bg-slate-950 text-slate-200 px-4 py-2 text-sm border-b border-slate-800 flex flex-wrap gap-4 items-center">
    <span>{account.role==='local'?'Local workspace':account.username}</span>
    {account.role!=='local'&&<><button onClick={()=>setManaging(!managing)} className="underline">Account settings</button><button disabled={busy} onClick={signOut} className="underline">Sign out</button></>}
    {error&&<span role="alert" className="text-rose-300">{error}</span>}
  </div>
    {managing&&<section className="bg-slate-900 text-white p-5 space-y-4" aria-label="Account settings">
      <button onClick={exportData} className="underline">Export my learning data</button>
      <form onSubmit={deleteAccount} className="max-w-md space-y-2">
        <p>Delete your account and learning history. This cannot be undone. Review audit records authored for other users retain an anonymous actor identifier.</p>
        <label>Confirm your password<input type="password" required className={field} value={deletePassword} onChange={e=>setDeletePassword(e.target.value)}/></label>
        <button disabled={busy} className="p-2 bg-rose-800 rounded">Permanently delete my account</button>
      </form>
    </section>}
    <div key={account.id}>{children}</div>
  </AccountContext.Provider>;
}
