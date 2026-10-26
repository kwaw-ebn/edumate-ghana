import assert from 'node:assert/strict';
import {waitForLoginService} from '../app/server-readiness.ts';
let clock=0;let calls=[];let updates=[];
await waitForLoginService(message=>updates.push(message),{
 now:()=>clock,sleep:async ms=>{clock+=ms},pollMs:10,maxWaitMs:100,isOnline:()=>true,
 fetcher:async (url,init)=>{calls.push([url,init.method]);return {ok:calls.length===3,status:calls.length===3?200:502};}
});
assert.equal(calls.length,3);assert.ok(calls.every(([url,method])=>url==='/api/health'&&method==='GET'));
assert.match(updates[0],/wake up/);
clock=0;calls=[];
await assert.rejects(()=>waitForLoginService(()=>{},{now:()=>clock,sleep:async ms=>{clock+=ms},pollMs:10,maxWaitMs:30,isOnline:()=>true,fetcher:async()=>{calls.push(1);return {ok:false,status:503};}}),/longer than expected/);
assert.equal(calls.length,3);
await assert.rejects(()=>waitForLoginService(()=>{},{isOnline:()=>false,fetcher:async()=>{throw Error('must not request');}}),/offline/);
calls=[];
await assert.rejects(()=>waitForLoginService(()=>{},{isOnline:()=>true,fetcher:async()=>{calls.push(1);return {ok:false,status:403};}}),/could not reach/);
assert.equal(calls.length,1);
console.log('Login readiness checks passed: wake-up retries, bounded wait, offline and non-transient errors.');
