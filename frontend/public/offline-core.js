// Shared by the online React app and the offline fallback. Never stores auth tokens.
const DB='edumate-offline-v2';
function database(){return new Promise((resolve,reject)=>{const r=indexedDB.open(DB,1);r.onupgradeneeded=()=>r.result.createObjectStore('records',{keyPath:'key'});r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
export async function write(kind,owner,id,data){const db=await database();return new Promise((resolve,reject)=>{const t=db.transaction('records','readwrite');t.objectStore('records').put({key:kind+':'+owner+':'+id,kind,owner,id,data});t.oncomplete=()=>{db.close();resolve(data);};t.onerror=()=>{db.close();reject(t.error);};});}
export async function read(kind,owner,id){const db=await database();return new Promise((resolve,reject)=>{const r=db.transaction('records').objectStore('records').get(kind+':'+owner+':'+id);r.onsuccess=()=>{db.close();resolve(r.result?.data||null);};r.onerror=()=>reject(r.error);});}
export async function list(kind,owner){const db=await database();return new Promise((resolve,reject)=>{const r=db.transaction('records').objectStore('records').getAll();r.onsuccess=()=>{db.close();resolve(r.result.filter(x=>x.kind===kind&&x.owner===owner).map(x=>({id:x.id,...x.data})));};r.onerror=()=>reject(r.error);});}
export async function remove(kind,owner,id){const db=await database();return new Promise((resolve,reject)=>{const t=db.transaction('records','readwrite');t.objectStore('records').delete(kind+':'+owner+':'+id);t.oncomplete=()=>{db.close();resolve();};t.onerror=()=>reject(t.error);});}
export function activate(user){localStorage.setItem('edumate-active-user',JSON.stringify({id:user.id,name:user.name,role:user.role}));}
export function active(){try{return JSON.parse(localStorage.getItem('edumate-active-user')||'null');}catch{return null;}}
export async function queue(owner,kind,target,data={}){const event={event_id:crypto.randomUUID(),kind,target,...data};await write('event',owner,event.event_id,event);return event;}
let syncing=false;
export async function synchronize(user,request){if(syncing||!navigator.onLine||user.role!=='student')return {sent:0,pending:(await list('event',user.id)).length};syncing=true;let sent=0;try{
 // Upload local photos/documents before synchronizing draft references or submissions.
 for(const f of await list('upload',user.id)){
  try{const form=new FormData();form.append('file',f.blob,f.name);const r=await request('/files?assessment_id='+encodeURIComponent(f.assessment_id),'POST',form);await write('file-map',user.id,f.id,{server_id:r.id});await remove('upload',user.id,f.id);}catch(e){await write('sync-error',user.id,f.id,{error:e.message});}
 }
 const mapped=async ids=>{const out=[];for(const id of ids||[]){if(!id.startsWith('local-'))out.push(id);else{const m=await read('file-map',user.id,id);if(!m)return null;out.push(m.server_id);}}return out;};
 for(const d of await list('draft',user.id)){
  if(!d.dirty)continue;const ids=await mapped(d.file_ids);if(!ids)continue;
  try{const saved=await request('/assessments/'+d.id+'/draft','PUT',{answers:d.answers,file_ids:ids,version:d.version||0});await write('draft',user.id,d.id,{...d,file_ids:ids,version:saved.version,dirty:false,conflict:false});}
  catch(e){await write('draft',user.id,d.id,{...d,conflict:true,sync_error:e.message});}
 }
 const events=await list('event',user.id);
 for(const event of events){
  const ids=await mapped(event.file_ids);if(event.kind==='submit'&&!ids)continue;
  try{const response=await request('/sync','POST',{events:[{...event,file_ids:ids||[]}],device_id:localStorage.getItem('edumate-device-'+user.id)});const r=response.events[0];if(r.ok){await remove('event',user.id,event.event_id);await write('receipt',user.id,event.event_id,{...r,kind:event.kind,target:event.target});sent++;}else{await write('event',user.id,event.event_id,{...event,sync_error:r.error,status:r.status});}}
  catch(e){if(/sign in/i.test(e.message))break;await write('event',user.id,event.event_id,{...event,sync_error:e.message});}
 }
 const device=localStorage.getItem('edumate-device-'+user.id);if(device)await request('/devices/'+device+'/heartbeat','POST').catch(()=>{});
 return {sent,pending:(await list('event',user.id)).length};
 }finally{syncing=false;}}
