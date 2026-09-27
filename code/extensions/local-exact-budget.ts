import { readFileSync } from 'node:fs';
import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { prepareExactBudget, budgetEnabled } from '../exact_budget.mjs';

// Profile-scoped admission. LOCAL_EXACT_BUDGET=0 opts out; cloud is untouched.
export default function(pi: ExtensionAPI) {
  if (process.env.LOCAL_EXACT_BUDGET === '0') return;
  const profiles=JSON.parse(readFileSync(new URL('../deployment-state/exact-budget-profiles.json',import.meta.url),'utf8'));
  pi.on('before_provider_request',async (event,ctx)=>{
    const model=ctx.model;
    if(!model) return;
    const profile=profiles.find((p:any)=>p.provider===model.provider && p.id===model.id && p.baseUrl===model.baseUrl);
    if(!budgetEnabled(profile,process.env.LOCAL_EXACT_BUDGET)) return;
    try {
      const auth=await ctx.modelRegistry.getApiKeyAndHeaders(model);
      const responseFormat=process.env.LOCAL_JSON_SCHEMA_FILE
        ? {type:'json_schema',json_schema:{name:'local_task_result',strict:true,
            schema:JSON.parse(readFileSync(process.env.LOCAL_JSON_SCHEMA_FILE,'utf8'))}}
        : undefined;
      const result=await prepareExactBudget({model,payload:event.payload,profiles,apiKey:auth.apiKey,signal:ctx.signal,responseFormat});
      if(!result) return;
      // Only counts/timings. Never log prompts, keys, model text, or tool arguments.
      process.stderr.write('LOCAL_EXACT_BUDGET '+JSON.stringify({...result.audit,structured_output:responseFormat!==undefined})+'\n');
      return result.payload;
    } catch(error) {
      process.stderr.write('LOCAL_EXACT_BUDGET_FAILED '+(error instanceof Error ? error.message : 'preflight failed')+'\n');
      // Pi swallows errors in this transforming hook. Abort and return an explicitly
      // invalid ceiling so it cannot silently fall back to sending an uncounted request.
      ctx.abort();
      return {...(event.payload as object),max_completion_tokens:0};
    }
  });
}
