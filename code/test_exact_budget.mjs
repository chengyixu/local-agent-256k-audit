import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';

const modulePath = new URL('./exact_budget.mjs', import.meta.url);
async function implementation() {
  assert.ok(existsSync(modulePath), 'Missing exact-budget implementation');
  return import(modulePath.href);
}
const profile = {provider:'ccs-local-ornith15-normal-pi', id:'local-ornith15-35b-262k', baseUrl:'http://127.0.0.1:7870/v1',contextWindow:262144,maxTokens:4096};
const model = {...profile, api:'openai-completions'};
const payload = {model:profile.id,messages:[{role:'user',content:'unchanged source'}],tools:[{type:'function',function:{name:'read'}}],max_completion_tokens:1,stream:true};
function transport(count) {
  const calls=[];
  const fetchImpl=async (url,options) => {
    calls.push({url,options});
    const body = url.endsWith('/apply-template') ? {prompt:'rendered exactly'} : {tokens:Array(count).fill(9)};
    return {ok:true,status:200,json:async()=>body};
  };
  return {calls,fetchImpl};
}
test('recover budget at recorded258228 input without altering messages or tools',async()=>{
  const {prepareExactBudget}=await implementation();const t=transport(258228);
  const r=await prepareExactBudget({model,payload,profiles:[profile],apiKey:'test-only',fetchImpl:t.fetchImpl});
  assert.equal(r.payload.max_completion_tokens,3852); // 262144 - 258228 - 64
  assert.deepEqual(r.payload.messages,payload.messages);assert.deepEqual(r.payload.tools,payload.tools);
  assert.equal(payload.max_completion_tokens,1);
  assert.deepEqual(t.calls.map(c=>c.url),['http://127.0.0.1:7870/apply-template','http://127.0.0.1:7870/tokenize']);
  assert.equal(t.calls[0].options.redirect,'error');
  assert.equal(r.audit.input_tokens,258228);assert.equal(r.audit.margin_tokens,64);
});
test('explicit output schema is counted in the same payload without changing source or tools',async()=>{
  const {prepareExactBudget}=await implementation();const t=transport(256150);
  const responseFormat={type:'json_schema',json_schema:{name:'audit',strict:true,schema:{type:'object',properties:{answer:{type:'string'}},required:['answer'],additionalProperties:false}}};
  const r=await prepareExactBudget({model,payload,profiles:[profile],apiKey:'test-only',fetchImpl:t.fetchImpl,responseFormat});
  assert.deepEqual(r.payload.response_format,responseFormat);
  assert.deepEqual(JSON.parse(t.calls[0].options.body).response_format,responseFormat);
  assert.deepEqual(r.payload.messages,payload.messages);assert.deepEqual(r.payload.tools,payload.tools);
  assert.equal(payload.response_format,undefined);
});
test('profile-scoped default can be disabled and does not enable unregistered profiles',async()=>{
  const {budgetEnabled}=await implementation();
  assert.equal(typeof budgetEnabled,'function');
  assert.equal(budgetEnabled({defaultEnabled:true},undefined),true);
  assert.equal(budgetEnabled({defaultEnabled:true},'0'),false);
  assert.equal(budgetEnabled({defaultEnabled:false},undefined),false);
  assert.equal(budgetEnabled({defaultEnabled:false},'1'),true);
  assert.equal(budgetEnabled(undefined,'1'),false);
});
test('initial256150 input keeps4096 ceiling; never inflates capacity',async()=>{
  const {prepareExactBudget}=await implementation();const t=transport(256150);
  const r=await prepareExactBudget({model,payload,profiles:[profile],apiKey:'test-only',fetchImpl:t.fetchImpl});
  assert.equal(r.payload.max_completion_tokens,4096);assert.ok(256150+4096+64<=262144);
});
test('do not touch cloud, wrong model identity, or redirected local endpoints',async()=>{
  const {prepareExactBudget}=await implementation();
  for(const changed of [{...model,provider:'cloud'},{...model,id:'other'},{...model,baseUrl:'https://remote.invalid/v1'}]){
    const r=await prepareExactBudget({model:changed,payload,profiles:[profile],apiKey:'secret',fetchImpl:()=>{throw Error('must not fetch')}});
    assert.equal(r,null);
  }
});
test('matching a malicious manifest still cannot send credentials off-loopback',async()=>{
  const {prepareExactBudget}=await implementation();
  const bad={...profile,baseUrl:'http://127.0.0.1:7870/v1?redirect=cloud'};
  await assert.rejects(prepareExactBudget({model:{...model,...bad},payload,profiles:[bad],apiKey:'secret',fetchImpl:()=>{throw Error('must not fetch')}}),/loopback/);
});
test('experimental hook aborts and returns invalid ceiling when preflight fails',async()=>{
  const before=process.env.LOCAL_EXACT_BUDGET;
  const oldFetch=globalThis.fetch;
  process.env.LOCAL_EXACT_BUDGET='1';
  try {
    const {default:extension}=await import('./extensions/local-exact-budget.ts');
    let handler;let aborted=false;
    extension({on:(name,fn)=>{assert.equal(name,'before_provider_request');handler=fn;}});
    globalThis.fetch=async()=>({ok:false,status:503});
    const result=await handler({payload},{model,modelRegistry:{getApiKeyAndHeaders:async()=>({apiKey:'test-only'})},abort:()=>{aborted=true;}});
    assert.equal(result.max_completion_tokens,0);
    assert.equal(aborted,true);
    assert.deepEqual(result.messages,payload.messages);
  } finally {
    globalThis.fetch=oldFetch;
    if(before===undefined)delete process.env.LOCAL_EXACT_BUDGET;else process.env.LOCAL_EXACT_BUDGET=before;
  }
});
test('counting failure and exhausted context fail rather than estimate or truncate',async()=>{
  const {prepareExactBudget}=await implementation();
  await assert.rejects(prepareExactBudget({model,payload,profiles:[profile],apiKey:'test',fetchImpl:async()=>({ok:false,status:503})}),/503/);
  const t=transport(262080);
  await assert.rejects(prepareExactBudget({model,payload,profiles:[profile],apiKey:'test',fetchImpl:t.fetchImpl}),/remaining/);
  const malformed={fetchImpl:async url=>({ok:true,status:200,json:async()=>url.endsWith('apply-template')?{prompt:'x'}:{tokens:[1,'bad']}})};
  await assert.rejects(prepareExactBudget({model,payload,profiles:[profile],apiKey:'test',...malformed}),/token/);
});
