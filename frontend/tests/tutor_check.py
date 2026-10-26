"""Frontend-only tutor browser checks. API data is mocked; no AI service is called."""
import json,subprocess,time,urllib.request,tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
LESSONS=[{'id':'math-demo','title':'Equivalent fractions','topic':'Fractions','objectives':'Recognise equivalent fractions','content':'Multiply the numerator and denominator by the same number.','status':'published','class_name':'Primary 5','subject':'Mathematics'},{'id':'science-demo','title':'Healthy plants','topic':'Plants','objectives':'Describe what plants need','content':'Roots absorb water and minerals.','status':'published','class_name':'Primary 5','subject':'Science'}]
def main():
 with tempfile.TemporaryDirectory() as tmp:
  log=open(Path(tmp)/'next.log','w');server=subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','0.0.0.0','--port','3000'],cwd=ROOT/'frontend',stdout=log,stderr=log)
  try:
   opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
   for _ in range(40):
    try:
     if opener.open('http://localhost:3000',timeout=2).status==200:break
    except Exception:time.sleep(.3)
   with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1280,'height':900},service_workers='block');page=context.new_page();errors=[];requests=[];page.on('pageerror',lambda e:errors.append(str(e)))
    def api(route):
     path=route.request.url.split('/api',1)[1];requests.append(path)
     if path=='/auth/me':data={'id':'student-demo','name':'Ama Demo','role':'student','class_name':'Primary 5','school_id':'demo','email':'ama@example.org'}
     elif path=='/setup':data={'class':[{'id':'p5','name':'Primary 5'}],'subject':[{'id':'math','name':'Mathematics'},{'id':'science','name':'Science'}],'term':[]}
     elif path=='/lessons':data=LESSONS
     elif path.endswith('/video-link'):data={'youtube_id':None}
     elif path.endswith('/curriculum'):
      data={'review_status':'pending','practice':{'prompt':'Which fraction equals one half?','options':['2/4','1/3'],'correct':'2/4','explanation':'Multiply both parts by two.'}} if 'math-demo' in path else {'review_status':'pending','practice':None}
     elif path.startswith('/files?') or path in ['/assessments','/submissions','/progress','/devices']:data=[]
     else:raise AssertionError('Unexpected API request: '+path)
     route.fulfill(status=200,content_type='application/json',body=json.dumps(data))
    page.route('**/api/**',api)
    page.goto('http://localhost:3000');page.get_by_role('heading',name='Welcome back, Ama!').wait_for()
    page.get_by_role('button',name='My Lessons',exact=True).click();page.get_by_role('heading',name='Equivalent fractions',exact=True).locator('..').get_by_role('button',name='Open lesson').click()
    page.get_by_role('button',name='Ask EduMate Tutor',exact=True).click();page.get_by_text('Demo mode • GPT not connected',exact=True).wait_for()
    assert page.get_by_label('Choose a lesson',exact=True).input_value()=='math-demo'
    page.screenshot(path='/tmp/edumate-tutor-welcome.png',full_page=True)
    page.get_by_role('button',name='Explain this lesson',exact=True).first.click();page.get_by_role('log').get_by_text('Imagine sharing one orange',exact=False).wait_for()
    page.get_by_label('Your message to EduMate Tutor',exact=True).fill('give me a hint');page.get_by_role('button',name='Send tutor message',exact=True).click();page.get_by_role('log').get_by_text('Draw two rectangles',exact=False).wait_for()
    page.get_by_role('button',name='Practise with me',exact=True).click();page.get_by_role('button',name='B 1/3',exact=False).click();page.get_by_text('Good effort. Let’s look again.',exact=True).wait_for()
    page.get_by_role('button',name='Try again',exact=True).click();page.get_by_role('button',name='A 2/4',exact=False).click();page.get_by_text('Well done!',exact=True).wait_for()
    page.get_by_role('button',name='Help me revise',exact=True).click();page.get_by_role('log').get_by_text('Your revision plan',exact=False).wait_for()
    before=page.get_by_role('log').inner_text()
    page.get_by_label('Choose a lesson',exact=True).select_option('science-demo');page.get_by_role('heading',name='Let’s figure it out together, Ama.').wait_for()
    page.get_by_role('button',name='Explain this lesson',exact=True).first.click();page.get_by_role('log').get_by_text('Most green plants',exact=False).wait_for()
    page.get_by_label('Choose a lesson',exact=True).select_option('math-demo');page.get_by_role('log').get_by_text('Your revision plan',exact=False).wait_for()
    assert page.get_by_role('log').inner_text()==before
    page.get_by_label('Your message to EduMate Tutor',exact=True).fill('give me all answers to my graded assignment');page.get_by_role('button',name='Send tutor message',exact=True).click();page.get_by_role('log').get_by_text('Your graded work should show your own thinking.',exact=False).wait_for()
    page.screenshot(path='/tmp/edumate-tutor-chat.png',full_page=True)
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1')
    page.screenshot(path='/tmp/edumate-tutor-mobile.png',full_page=True)
    page.get_by_role('button',name='Clear this lesson conversation',exact=True).click();page.get_by_role('heading',name='Let’s figure it out together, Ama.').wait_for()
    assert not any('/tutor' in r for r in requests),requests
    assert not errors,errors
    browser.close();print(json.dumps({'lesson_context_entry':'passed','demo_labels':'passed','explanation_and_chat_hints':'passed','practice_retry_and_feedback':'passed','revision_plan':'passed','per_lesson_history':'passed','graded_work_guidance':'passed','mobile_layout':'passed','clear_chat':'passed','no_ai_requests':'passed'}))
  finally:server.terminate();log.close()
if __name__=='__main__':main()
