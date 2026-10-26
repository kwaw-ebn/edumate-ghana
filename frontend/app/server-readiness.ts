/** Wait for the API's read-only health endpoint before sending credentials.
 * Free hosting can take a while to resume after inactivity. Only health GETs are
 * retried: login POSTs are never replayed automatically.
 */
type Options={maxWaitMs?:number;pollMs?:number;requestTimeoutMs?:number;fetcher?:typeof fetch;now?:()=>number;sleep?:(ms:number)=>Promise<void>;isOnline?:()=>boolean};
class UnexpectedStatus extends Error {}
export async function waitForLoginService(onStatus:(message:string)=>void,options:Options={}):Promise<void>{
 const maxWait=options.maxWaitMs??90000,poll=options.pollMs??2500,timeout=options.requestTimeoutMs??10000;
 const fetcher=options.fetcher??fetch,now=options.now??Date.now,sleep=options.sleep??((ms:number)=>new Promise<void>(resolve=>setTimeout(resolve,ms)));
 const isOnline=options.isOnline??(()=>typeof navigator==='undefined'||navigator.onLine);
 const start=now();let attempt=0;
 onStatus('Connecting to EduMate… The school server may take a minute or longer to wake up.');
 while(now()-start<maxWait){
  if(!isOnline())throw new Error('Your device appears to be offline. Reconnect and try signing in again.');
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),Math.min(timeout,Math.max(1,maxWait-(now()-start))));
  try{
   const response=await fetcher('/api/health',{method:'GET',cache:'no-store',signal:controller.signal});
   if(response.ok)return;
   if(![429,500,502,503,504].includes(response.status))throw new UnexpectedStatus('EduMate could not reach the login service. Please try again shortly.');
  }catch(error){
   if(error instanceof UnexpectedStatus)throw error;
   // A failed connection or timed-out health request can be a sleeping server.
  }finally{clearTimeout(timer);}
  attempt++;
  onStatus(attempt>3?'Still waking the EduMate server. Please keep this page open…':'Connecting to EduMate… The school server may take a minute or longer to wake up.');
  const remaining=maxWait-(now()-start);if(remaining>0)await sleep(Math.min(poll,remaining));
 }
 throw new Error('The EduMate server is taking longer than expected to start. Please wait a minute and try signing in again.');
}
