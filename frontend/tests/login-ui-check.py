"""Exercise the sign-in UI while a mocked sleeping API wakes up."""
import json,subprocess,time,tempfile,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
def main():
 with tempfile.TemporaryDirectory() as tmp:
  log=open(Path(tmp)/'server.log','w');server=subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','0.0.0.0','--port','3000'],cwd=ROOT/'frontend',stdout=log,stderr=log)
  try:
   opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
   for _ in range(50):
    try:
     if opener.open('http://localhost:3000',timeout=2).status==200:break
    except Exception:time.sleep(.3)
   with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1100,'height':800},service_workers='block');page=context.new_page();errors=[];health=0;logins=[];page.on('pageerror',lambda e:errors.append(str(e)))
    def route_api(route):
     nonlocal health
     path=route.request.url.split('/api',1)[1]
     if path=='/auth/me':route.fulfill(status=401,content_type='application/json',body='{"detail":"Please sign in"}');return
     if path=='/health':
      health+=1
      if health<3:route.fulfill(status=502,content_type='text/html',body='<h1>Service unavailable</h1>');return
      data={'status':'ok'}
     elif path=='/auth/login':
      logins.append(route.request.post_data_json);data={'id':'demo-admin','name':'Demo Admin','role':'platform_admin','school_id':None,'class_name':None,'email':'platform@demo.edumate.test'}
     elif path in ['/schools','/demo-requests']:data=[]
     else:raise AssertionError('Unexpected request '+path)
     route.fulfill(status=200,content_type='application/json',body=json.dumps(data))
    page.route('**/api/**',route_api)
    page.goto('http://localhost:3000');page.get_by_role('button',name='Sign in',exact=False).first.click()
    page.get_by_label('Email address',exact=True).last.fill('platform@demo.edumate.test');page.get_by_label('Password',exact=True).fill('test-password-only')
    page.get_by_role('button',name='Sign in securely').click()
    page.get_by_text('The school server may take a minute or longer to wake up.',exact=False).wait_for()
    assert page.get_by_role('button',name='Connecting…').is_disabled()
    assert page.get_by_label('Email address',exact=True).last.input_value()=='platform@demo.edumate.test'
    assert page.get_by_label('Password',exact=True).input_value()=='test-password-only'
    page.get_by_role('heading',name='Platform overview').wait_for(timeout=25000)
    assert health==3,health
    assert len(logins)==1 and logins[0]['email']=='platform@demo.edumate.test'
    assert not errors,errors
    browser.close();print('Browser login check passed: progress message, retained input, server retries and one login request.')
  finally:server.terminate();log.close()
if __name__=='__main__':main()
