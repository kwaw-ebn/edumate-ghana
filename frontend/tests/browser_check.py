"""Run after npm run build. Covers a real disconnected browser and sync retry.
Requires Python playwright + Chromium. Uses disposable SQLite and fake local object storage.
"""
import os,sys,time,tempfile,subprocess,json,io
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
PASSWORD='temporary-browser-check-password'

def main():
 with tempfile.TemporaryDirectory(prefix='edumate-browser-') as tmp:
  env={**os.environ,'DATABASE_URL':'sqlite:///'+tmp+'/browser.db','JWT_SECRET':'browser-check-secret-at-least-thirty-two-characters','COOKIE_SECURE':'false','DEMO_PASSWORD':PASSWORD,'APP_ORIGIN':'http://localhost:3000'}
  subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT/'backend',env=env,check=True)
  subprocess.run([sys.executable,'-m','app.seed'],cwd=ROOT/'backend',env=env,check=True)
  runner=Path(tmp)/'runner.py'
  runner.write_text("import sys\nsys.path.insert(0,"+repr(str(ROOT/'backend'))+")\nfrom app.main import app\nfrom app import storage\nimport uvicorn\nobjects={}\nstorage.put=lambda key,data,mime:objects.update({key:data})\nstorage.read=lambda key:objects[key]\nuvicorn.run(app,host='127.0.0.1',port=8000)\n")
  log=open(Path(tmp)/'servers.log','w')
  backend=subprocess.Popen([sys.executable,str(runner)],cwd=ROOT/'backend',env=env,stdout=log,stderr=log)
  frontend=subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','0.0.0.0','--port','3000'],cwd=ROOT/'frontend',stdout=log,stderr=log)
  try:
   with httpx.Client(base_url='http://localhost:3000',trust_env=False) as c:
    for _ in range(60):
     try:
      if c.get('/api/health').status_code==200:break
     except httpx.HTTPError:pass
     time.sleep(.5)
    r=c.post('/api/auth/login',json={'email':'maths@demo.edumate.test','password':PASSWORD});assert r.status_code==200,r.text
    lessons=c.get('/api/lessons').json();lesson=next(x for x in lessons if x['class_name']=='Primary 5')
    r=c.put('/api/lessons/'+lesson['id']+'/curriculum',json={'practice_prompt':'Which fraction equals one half?','practice_options':['2/4','1/3'],'practice_correct':'2/4','practice_explanation':'Equal shares.'});assert r.status_code==200,r.text
    r=c.post('/api/files?lesson_id='+lesson['id'],files={'file':('demo.pdf',b'%PDF-1.4\nDemo worksheet','application/pdf')});assert r.status_code==200,r.text
   with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1100,'height':820})
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://localhost:3000');page.get_by_role('button',name='Sign in',exact=False).first.click()
    page.get_by_label('Email address',exact=True).last.fill('student11@demo.edumate.test')
    # This pupil is Primary 4; switch to a Primary 5 account for this lesson.
    page.get_by_label('Email address',exact=True).last.fill('student6@demo.edumate.test')
    page.get_by_label('Password',exact=True).fill(PASSWORD);page.get_by_role('button',name='Sign in securely').click()
    page.get_by_role('heading',name='Welcome back, Kofi!').wait_for()
    page.get_by_role('button',name='My Lessons',exact=True).click()
    page.get_by_role('heading',name=lesson['title'],exact=True).first.locator('..').get_by_role('button',name='Open lesson').click()
    page.get_by_role('button',name='Save for offline reading').click()
    page.get_by_text('Lesson and attached resources saved for offline learning.').wait_for()
    page.get_by_role('button',name='Assignments',exact=True).click()
    page.get_by_role('button',name='Start assignment').first.click()
    page.get_by_role('button',name='Download assessment for offline work').click()
    page.get_by_text('Assessment saved for offline work.').wait_for()
    page.locator('textarea').first.fill('This answer should survive a refresh.')
    page.get_by_text('Draft saved online.',exact=True).wait_for()
    page.get_by_role('button',name='Assignments',exact=True).click();page.get_by_role('button',name='Start assignment').first.click()
    page.wait_for_function("document.querySelector('textarea')?.value === 'This answer should survive a refresh.'")
    page.get_by_role('button',name='Offline learning',exact=True).click()
    page.evaluate('navigator.serviceWorker.ready')
    page.wait_for_function('!!navigator.serviceWorker.controller')
    page.screenshot(path='/tmp/edumate-online-tablet.png',full_page=True)
    frontend.terminate();frontend.wait(timeout=10)
    context.set_offline(True)
    # A disconnected navigation must return the cached offline shell, CSS and JS.
    page.goto('http://localhost:3000/disconnected-test')
    page.get_by_role('heading',name='EduMate Ghana',exact=True).wait_for()
    page.get_by_role('button',name=lesson['title'],exact=True).click()
    page.get_by_text('Which fraction equals one half?',exact=True).wait_for()
    page.get_by_role('button',name='2/4',exact=True).click()
    page.get_by_role('button',name='Mark lesson complete').click()
    page.get_by_role('button',name='Fractions in daily life',exact=True).click()
    page.locator('textarea').first.fill('Offline answer with a handwritten-work attachment.')
    page.locator('input[type=file]').set_input_files({'name':'handwritten.jpg','mimeType':'image/jpeg','buffer':b'\xff\xd8\xffdemo'})
    page.get_by_text('Attached: handwritten.jpg').wait_for()
    page.get_by_role('button',name='Queue final submission').click()
    page.wait_for_function("document.querySelector('#status').textContent.includes('Final submission queued')")
    page.reload();page.get_by_role('button',name='Fractions in daily life',exact=True).click()
    assert page.locator('textarea').first.input_value()=='Offline answer with a handwritten-work attachment.'
    page.screenshot(path='/tmp/edumate-offline-tablet.png',full_page=True)
    # Expire cookies: a failed sync must retain all pending work.
    context.clear_cookies()
    frontend=subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','0.0.0.0','--port','3000'],cwd=ROOT/'frontend',stdout=log,stderr=log)
    time.sleep(1)
    context.set_offline(False);page.get_by_role('button',name='Synchronize now').click()
    page.wait_for_function("document.querySelector('#status').textContent.includes('remain queued')")
    pending=page.evaluate("import('/offline-core.js').then(async m=>(await m.list('event',m.active().id)).length)")
    assert pending==3,pending
    # Restore a valid session, upload the queued photo and synchronize once.
    r=context.request.post('http://localhost:3000/api/auth/login',data={'email':'student6@demo.edumate.test','password':PASSWORD});assert r.ok,r.text()
    page.get_by_role('button',name='Synchronize now').click()
    page.wait_for_function("document.querySelector('#status').textContent.includes('0 remain queued')",timeout=30000)
    r=context.request.get('http://localhost:3000/api/submissions');assert r.ok
    work=r.json();assert len(work)==1 and work[0]['answers'][0].startswith('Offline answer')
    assert len(context.request.get('http://localhost:3000/api/submissions/'+work[0]['id']+'/files').json())==1
    page.get_by_role('button',name='Synchronize now').click()
    assert len(context.request.get('http://localhost:3000/api/submissions').json())==1
    assert errors==[],errors
    page.screenshot(path='/tmp/edumate-synchronized.png',full_page=True)
    browser.close()
   print(json.dumps({'tablet_ui':'passed','online_draft_restore':'passed','disconnected_shell_lesson_practice':'passed','offline_photo_and_draft_reload':'passed','expired_session_retains_work':'passed','reconnect_upload_and_sync':'passed','duplicate_sync':'passed'}))
  finally:
   frontend.terminate();backend.terminate();log.close()
if __name__=='__main__':main()
