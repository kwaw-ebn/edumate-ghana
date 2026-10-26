const CACHE='edumate-offline-v4';
const FILES=['/offline.html','/offline.css','/offline-app.js','/offline-core.js','/manifest.webmanifest','/icon.svg'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(FILES)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>{
 event.waitUntil((async()=>{
  const keys=await caches.keys();
  await Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)));
  await self.clients.claim();
 })());
});
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(u.origin!==self.location.origin)return;if(FILES.includes(u.pathname)){e.respondWith(caches.match(e.request).then(c=>c||fetch(e.request)));return;}if(e.request.mode==='navigate')e.respondWith(fetch(e.request).catch(()=>caches.match('/offline.html')));});
