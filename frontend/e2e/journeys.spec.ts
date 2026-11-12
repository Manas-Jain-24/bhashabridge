import {test,expect,type Page} from '@playwright/test';

async function register(page:Page) {
  await page.goto('/');
  await page.getByRole('button',{name:'Create an account',exact:true}).click();
  await page.getByLabel('Username',{exact:true}).fill('qa_'+crypto.randomUUID().replaceAll('-','').slice(0,20));
  await page.getByLabel('Password',{exact:true}).fill('A browser test password 123!');
  await page.getByRole('button',{name:'Create account',exact:true}).click();
  await expect(page.getByLabel('Sentence to translate')).toBeVisible();
}
async function greeting(page:Page) {
  await page.getByLabel('Translation',{exact:true}).selectOption('local');
  await page.getByLabel('Sentence to translate').fill('नमस्ते!');
  const pending=page.waitForResponse(r=>r.url().endsWith('/api/analyze'));
  await page.getByRole('button',{name:'Translate',exact:true}).click();
  const response=await pending;expect(response.ok()).toBeTruthy();
  await expect(page.getByRole('table')).toBeVisible();
  return response.json();
}

test('account, local translation, language swap and correction proposal',async({page})=>{
  await register(page);
  const data=await greeting(page);
  expect(data.context_status).toBe('reviewed');
  expect(data.vocabulary[0].target_roman).not.toBe(data.vocabulary[0].meaning);
  await page.getByRole('button',{name:'Report a translation issue'}).click();
  await page.getByLabel('What seems wrong?').fill('Browser test draft. No human review.');
  await page.getByRole('button',{name:'Submit unreviewed report'}).click();
  await page.getByLabel('Proposed native translation').fill('नमस्कार!');
  await page.getByLabel('Reason / review note').fill('An unreviewed example proposal.');
  await page.getByRole('button',{name:'Save unreviewed proposal'}).click();
  await expect(page.getByRole('heading',{name:/— proposed/})).toBeVisible();
  await expect(page.getByRole('button',{name:'Record human review'})).toHaveCount(0);
  await page.getByRole('button',{name:'Close review queue'}).click();
  await page.getByRole('button',{name:'Swap languages'}).click();
  await expect(page.getByLabel('Sentence to translate')).toHaveValue(data.translation_native);
  await expect(page.getByLabel('I speak',{exact:true})).toHaveValue('marathi');
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Sign in to BhashaBridge'})).toBeVisible();
});

test('outage, malformed response and late response cannot replace newer input',async({page})=>{
  await register(page);const baseline=await greeting(page);
  await page.route('**/api/analyze',route=>route.fulfill({status:503,json:{detail:'Service unavailable for this test.'}}));
  await page.getByLabel('Sentence to translate').fill('Failure test');
  await page.getByRole('button',{name:'Translate',exact:true}).click();
  await expect(page.getByText('Service unavailable for this test.',{exact:true})).toBeVisible();
  await page.unroute('**/api/analyze');
  await page.route('**/api/analyze',route=>route.fulfill({json:{translation_native:{invalid:true}}}));
  await page.getByRole('button',{name:'Translate',exact:true}).click();
  await expect(page.getByText('The server returned an incomplete translation. Please retry.')).toBeVisible();
  await page.unroute('**/api/analyze');
  let started!:()=>void;let release!:()=>void;
  const pending=new Promise<void>(resolve=>{started=resolve;});
  const gate=new Promise<void>(resolve=>{release=resolve;});
  await page.route('**/api/analyze',async route=>{started();await gate;try{await route.fulfill({json:{...baseline,english_meaning:'STALE_RESULT'}});}catch{}});
  await page.getByRole('button',{name:'Translate',exact:true}).click();await pending;
  await page.getByLabel('Sentence to translate').fill('Replacement input');
  await page.getByLabel('Translation',{exact:true}).selectOption('hybrid');release();
  await expect(page.getByText('STALE_RESULT',{exact:false})).toHaveCount(0);
  await page.getByLabel('Sentence to translate').fill('');
  await expect(page.getByRole('button',{name:'Translate',exact:true})).toBeDisabled();
});

test('mobile preview, long URL wrapping, missing English and clipboard failure',async({page,context})=>{
  await page.setViewportSize({width:390,height:844});await register(page);const baseline=await greeting(page);
  await page.getByLabel('Sentence to translate').fill('Main kal ghar jaunga lekin mere paas samay kam hai aur mujhe apna kaam poora karna hai');
  await expect(page.getByText('Spelling estimate:',{exact:true})).toBeVisible();
  const geometry=await page.evaluate(()=>({bottom:document.querySelector('#main-sentence-input')!.getBoundingClientRect().bottom,
    top:[...document.querySelectorAll('span')].find(e=>e.textContent==='Spelling estimate:')!.parentElement!.getBoundingClientRect().top}));
  expect(geometry.top).toBeGreaterThanOrEqual(geometry.bottom);
  await page.route('**/api/analyze',route=>route.fulfill({json:{...baseline,model_source:'indictrans2-320m-neural',context_status:'unavailable',
    quality_note:'Gemini assistance is unavailable. Showing the local translation without contextual interpretation.',
    translation_native:'नमस्कार https://example.org/'+('longsegment'.repeat(35)),english_meaning:'',english_meaning_source:'unavailable'}}));
  await page.getByLabel('Translation',{exact:true}).selectOption('hybrid');
  await page.getByRole('button',{name:'Translate',exact:true}).click();
  await expect(page.getByRole('status').filter({hasText:'Gemini assistance is unavailable'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Copy English meaning',exact:true})).toBeDisabled();
  await page.evaluate(()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:()=>Promise.reject(new Error('denied'))}}));
  await page.getByRole('button',{name:'Copy translation',exact:true}).click();
  await expect(page.getByText('Copy was blocked by the browser. Select the translation text to copy it.')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
});

test('dialog traps keyboard focus and restores it when closed',async({page})=>{
  await register(page);await greeting(page);
  const opener=page.getByRole('button',{name:'Why is this sentence different?',exact:true});
  await opener.click();const dialog=page.getByRole('dialog');await expect(dialog).toBeVisible();
  const first=dialog.locator('button').first();await first.focus();await page.keyboard.press('Shift+Tab');
  expect(await dialog.evaluate(el=>el.contains(document.activeElement))).toBeTruthy();
  await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);await expect(opener).toBeFocused();
});

test('Bengali learning round completes with server-owned score',async({page})=>{
  await register(page);await page.getByRole('button',{name:'Learn & Play Hub',exact:true}).click();
  await page.getByLabel('Game language').selectOption('bengali');
  const start=page.getByRole('button',{name:/Word Match.*Start round/});await expect(start).toBeEnabled({timeout:30000});
  const response=page.waitForResponse(r=>r.url().endsWith('/api/arcade/start'));await start.click();
  let run=await(await response).json();
  for(let i=0;i<10&&!run.done;i++) {
    const option=run.question.options[0];
    const reply=page.waitForResponse(r=>r.url().endsWith('/api/arcade/answer'));
    await page.getByRole('button',{name:option.text,exact:true}).click();
    run=await(await reply).json();
    if(!run.done) await page.getByRole('button',{name:/Next/}).click();
  }
  expect(run.done).toBeTruthy();expect(run.score).toBeGreaterThanOrEqual(0);
  await page.getByRole('button',{name:'See round result'}).click();
  await expect(page.getByText(/Round complete/)).toBeVisible();
});

test('missing speech voice gives a usable fallback',async({page})=>{
  await page.addInitScript(()=>Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{getVoices:()=>[],cancel:()=>{},speak:()=>{throw new Error('No voice should be invoked');},onvoiceschanged:null}}));
  await register(page);await greeting(page);
  await page.getByRole('button',{name:'Listen in Marathi',exact:true}).click();
  await expect(page.getByRole('alert').filter({hasText:'Audio is unavailable'})).toBeVisible();
});
