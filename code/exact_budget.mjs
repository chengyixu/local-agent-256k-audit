// Exact local-tokenizer admission. No message/tool edits and no cloud fallback.
export function budgetEnabled(profile, override) {
  return Boolean(profile && override!=='0' && (override==='1' || profile.defaultEnabled===true));
}
export async function prepareExactBudget({model,payload,profiles,apiKey,signal,fetchImpl=fetch,responseFormat}) {
  const profile=profiles.find(p=>p.provider===model?.provider && p.id===model.id && p.baseUrl===model.baseUrl);
  if(!profile || model.api!=='openai-completions' || payload?.model!==model.id) return null;
  const url=new URL(profile.baseUrl);
  if(url.protocol!=='http:' || url.hostname!=='127.0.0.1' || !['7870','7871'].includes(url.port)
     || url.pathname!=='/v1' || url.username || url.password || url.search || url.hash)
    throw new Error('Exact-budget endpoint must be the declared loopback service');
  if(!Number.isSafeInteger(profile.contextWindow) || profile.contextWindow!==model.contextWindow
     || !Number.isSafeInteger(profile.maxTokens) || profile.maxTokens<=0 || !apiKey)
    throw new Error('Invalid exact-budget profile or authentication');
  if(responseFormat!==undefined) payload={...payload,response_format:responseFormat};
  const started=performance.now();
  const bounded=signal ? AbortSignal.any([signal,AbortSignal.timeout(30000)]) : AbortSignal.timeout(30000);
  async function post(path,body) {
    const response=await fetchImpl(url.origin+path,{method:'POST',redirect:'error',signal:bounded,
      headers:{'Content-Type':'application/json',Authorization:'Bearer '+apiKey},body:JSON.stringify(body)});
    if(!response.ok) throw new Error('Local token preflight HTTP'+response.status);
    return response.json();
  }
  const rendered=await post('/apply-template',payload);
  if(typeof rendered.prompt!=='string') throw new Error('Missing rendered prompt');
  const tokenized=await post('/tokenize',{content:rendered.prompt});
  if(!Array.isArray(tokenized.tokens) || !tokenized.tokens.every(n=>Number.isSafeInteger(n)&&n>=0))
    throw new Error('Invalid tokenizer response');
  const input=tokenized.tokens.length,margin=64;
  const ceiling=Math.min(profile.maxTokens,profile.contextWindow-input-margin);
  if(ceiling<1) throw new Error('No remaining context after exact tokenizer admission');
  return {payload:{...payload,max_completion_tokens:ceiling},audit:{input_tokens:input,
    previous_output_ceiling:payload.max_completion_tokens??payload.max_tokens??null,
    output_ceiling:ceiling,context_window:profile.contextWindow,margin_tokens:margin,
    preflight_ms:performance.now()-started}};
}
