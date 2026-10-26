"""Browser smoke test for the preschool workspace, with fictional data."""
import json, subprocess, tempfile, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
def main():
 with tempfile.TemporaryDirectory() as tmp:
  log=open(Path(tmp)/'next.log','w');server=subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3109'],cwd=ROOT/'frontend',stdout=log,stderr=log)
  try:
   opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
   for _ in range(50):
    try:
     if opener.open('http://127.0.0.1:3109',timeout=2).status==200:break
    except Exception:time.sleep(.3)
   with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':900,'height':900},service_workers='block');errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    def api(route):
     path=route.request.url.split('/api',1)[1]
     if path=='/auth/me':data={'id':'kid-demo','name':'Demo Pupil','role':'student','class_name':'KG 1','school_id':'demo'}
     elif path=='/setup':data={'class':[{'id':'kg','name':'KG 1'}],'subject':[{'id':'math','name':'Mathematics'}],'term':[]}
     elif path=='/lessons':data=[{'id':'kg-colours','title':'Our colours','subject':'Mathematics','class_name':'KG 1','status':'published','objectives':'Recognise colours','content':'Discover colours together.'}]
     elif path.endswith('/curriculum'):data={'review_status':'reviewed','practice':None}
     elif path.endswith('/video-link'):data={'youtube_id':None}
     elif path.startswith('/files?') or path in ('/assessments','/submissions','/progress','/devices'):data=[]
     else:raise AssertionError(path)
     route.fulfill(status=200,content_type='application/json',body=json.dumps(data))
    page.route('**/api/**',api);page.goto('http://127.0.0.1:3109');page.get_by_role('button',name='EduMate Kids').click();page.get_by_role('heading',name='Little learners, big discoveries!').wait_for()
    page.get_by_role('button',name='Colours Try an activity').click();page.get_by_role('button',name='🟡 Yellow').click();page.get_by_text('Well done! Find something yellow in the classroom.').wait_for()
    page.get_by_role('button',name='Our colours KG 1 · Mathematics').click();page.get_by_text('Discover colours together.').wait_for();page.get_by_role('heading',name='Online video').wait_for()
    assert not errors,errors;browser.close()
   print('Preschool activity, class lesson and video section: passed')
  finally:server.terminate();server.wait(timeout=10);log.close()
if __name__=='__main__':main()
