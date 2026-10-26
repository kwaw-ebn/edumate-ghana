"""Authorization, files, offline idempotence, reports, setup and parent privacy."""
from test_workflow import client,setup
from app.db import Session
from app.models import *
from app.main import app
from app import storage
from fastapi.testclient import TestClient
from sqlalchemy import select
import pytest,io,zipfile
from uuid import uuid4

@pytest.fixture
def object_store(monkeypatch):
    objects={}
    monkeypatch.setattr(storage,'put',lambda key,data,mime:objects.update({key:data}))
    monkeypatch.setattr(storage,'read',lambda key:objects[key])
    return objects

def lesson(c):return next(x for x in c.get('/lessons').json() if x['class_name']=='Primary 5' and x['subject']=='Mathematics')
def assignment(c):return next(x for x in c.get('/assessments').json() if x['class_name']=='Primary 5' and x['kind']=='assignment')

def test_custom_school_setup_enrollment_and_curriculum():
    admin=client('admin');teacher=client('maths')
    cls=admin.post('/setup',json={'kind':'class','name':'Primary 6'});assert cls.status_code==200,cls.text
    sub=admin.post('/setup',json={'kind':'subject','name':'Computing'});assert sub.status_code==200
    term=admin.post('/setup',json={'kind':'term','name':'2027 Term 2','start_date':'2027-01-10','end_date':'2027-04-10'}).json()
    assert admin.post('/setup',json={'kind':'term','name':'Bad dates','start_date':'2027-06-10','end_date':'2027-01-10'}).status_code==422
    u=admin.post('/users',json={'name':'New Learner','email':'newlearner@example.org','password':'long-test-password','role':'student','class_name':'Primary 6'});assert u.status_code==200,u.text
    assert admin.post('/enrollments',json={'student_id':u.json()['id'],'class_name':'Primary 6','term_id':term['id']}).status_code==200
    assert admin.post('/users',json={'name':'Invalid Class','email':'invalid@example.org','password':'long-test-password','role':'student','class_name':'Unregistered'}).status_code==422
    l=lesson(teacher)
    curriculum={'term_id':term['id'],'week':4,'strand':'Number','sub_strand':'Fractions','practice_prompt':'Which equals one half?','practice_options':['2/4','1/3'],'practice_correct':'2/4','practice_explanation':'Multiply numerator and denominator by two.'}
    r=teacher.put('/lessons/'+l['id']+'/curriculum',json=curriculum);assert r.status_code==200,r.text
    assert teacher.put('/lessons/'+l['id']+'/curriculum',json={**curriculum,'review_status':'reviewed'}).status_code==403
    assert admin.put('/lessons/'+l['id']+'/curriculum',json={**curriculum,'review_status':'reviewed'}).status_code==200
    assert client('student2').get('/lessons/'+l['id']+'/offline-package').json()['curriculum']['practice']['correct']=='2/4'

def test_private_upload_draft_attachment_and_grading(object_store):
    t=client('maths');s=client('student7');other=client('student8');l=lesson(t)
    pdf=b'%PDF-1.4\nFictional demo worksheet'
    r=t.post('/files?lesson_id='+l['id'],files={'file':('worksheet.pdf',pdf,'application/pdf')});assert r.status_code==200,r.text
    fid=r.json()['id'];assert object_store
    assert s.get('/files/'+fid+'/download').content==pdf
    assert s.post('/files?lesson_id='+l['id'],files={'file':('x.pdf',pdf)}).status_code==403
    assert t.post('/files?lesson_id='+l['id'],files={'file':('bad.pdf',b'<script>bad</script>')}).status_code==422
    a=assignment(s);r=s.post('/files?assessment_id='+a['id'],files={'file':('homework.jpg',b'\xff\xd8\xffdemo','image/jpeg')});assert r.status_code==200,r.text
    work=r.json()['id'];assert other.get('/files/'+work+'/download').status_code==404
    assert other.put('/assessments/'+a['id']+'/draft',json={'answers':['copied'],'file_ids':[work],'version':0}).status_code==422
    d=s.put('/assessments/'+a['id']+'/draft',json={'answers':['See handwritten work.'],'file_ids':[work],'version':0});assert d.status_code==200,d.text
    assert s.get('/assessments/'+a['id']+'/draft').json()['file_ids']==[work]
    assert s.put('/assessments/'+a['id']+'/draft',json={'answers':['stale overwrite'],'version':0}).status_code==409
    r=s.post('/assessments/'+a['id']+'/submit',json={'event_id':str(uuid4()),'answers':['See handwritten work.'],'file_ids':[work]});assert r.status_code==200,r.text
    sid=r.json()['id'];assert t.get('/submissions/'+sid+'/files').json()[0]['id']==work
    assert other.get('/submissions/'+sid+'/files').status_code==403

def test_offline_sync_idempotence_and_permission_recheck():
    s=client('student9');t=client('maths');l=lesson(t)
    t.put('/lessons/'+l['id']+'/curriculum',json={'practice_prompt':'Half equals?','practice_options':['2/4','1/3'],'practice_correct':'2/4'})
    event={'event_id':str(uuid4()),'kind':'practice','target':l['id'],'answer':'2/4'}
    for _ in range(2):
        r=s.post('/sync',json={'events':[event]});assert r.status_code==200,r.text;assert r.json()['events'][0]['result']['correct']
    with Session() as db:assert len(list(db.scalars(select(PracticeAttempt).where(PracticeAttempt.student_id==s.get('/auth/me').json()['id']))))==1
    a=assignment(s);submit={'event_id':str(uuid4()),'kind':'submit','target':a['id'],'answers':['Equal parts.']}
    first=s.post('/sync',json={'events':[submit]}).json()['events'][0];assert first['ok']
    second=s.post('/sync',json={'events':[submit]}).json()['events'][0];assert second['result']['id']==first['result']['id']
    # Student class is changed before a queued event is replayed: server rejects stale permission.
    with Session() as db:
        pupil=db.get(User,s.get('/auth/me').json()['id']);pupil.class_name='Primary 4';db.commit()
    denied=s.post('/sync',json={'events':[{'event_id':str(uuid4()),'kind':'complete','target':l['id']}]}).json()['events'][0]
    assert not denied['ok'] and denied['status']==404

def test_parent_privacy_reports_and_device_records():
    admin=client('admin');teacher=client('maths');s=client('student10');sid=s.get('/auth/me').json()['id']
    p=admin.post('/users',json={'name':'Demo Parent','email':'parent@example.org','password':'long-parent-password','role':'parent'});assert p.status_code==200,p.text
    parent=TestClient(app);assert parent.post('/auth/login',json={'email':'parent@example.org','password':'long-parent-password'}).status_code==200
    assert parent.get('/parent-summaries').json()==[]
    assert admin.post('/parent-links',json={'parent_id':p.json()['id'],'student_id':sid}).status_code==200
    summaries=parent.get('/parent-summaries').json();assert len(summaries)==1 and summaries[0]['student_id']==sid
    assert parent.get('/users').status_code==403 and parent.get('/lessons').status_code==403
    assert s.get('/reports').status_code==403
    csv=teacher.get('/reports/export?format=csv');assert csv.status_code==200 and b'Completion %' in csv.content
    pdf=admin.get('/reports/export?format=pdf');assert pdf.status_code==200 and pdf.content.startswith(b'%PDF-')
    device=admin.post('/devices',json={'label':'Tablet 01','serial':'EDU-001','student_id':sid});assert device.status_code==200,device.text
    did=device.json()['id'];assert s.post('/devices/'+did+'/heartbeat').status_code==200
    assert client('student1').post('/devices/'+did+'/heartbeat').status_code==403
    assert admin.put('/devices/'+did,json={'label':'Tablet 01','serial':'EDU-001','student_id':sid,'active':False}).status_code==200
    assert s.post('/devices/'+did+'/heartbeat').status_code==403

def test_document_type_detection():
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:z.writestr('[Content_Types].xml','xml');z.writestr('ppt/presentation.xml','xml')
    assert storage.validate_file('slides.pptx',out.getvalue()).endswith('presentation')
    with pytest.raises(Exception):storage.validate_file('slides.docx',out.getvalue())

def test_lesson_video_review_permissions_and_offline(object_store):
    t=client('maths');admin=client('admin');s=client('student3');l=lesson(t)
    video=b'\x00\x00\x00\x18ftypisom'+b'\x00'*16
    r=t.post('/files?lesson_id='+l['id'],files={'file':('lesson.mp4',video,'video/mp4')});assert r.status_code==200,r.text
    fid=r.json()['id']
    assert s.get('/files/'+fid+'/download').status_code==404
    assert all(x['id']!=fid for x in s.get('/lessons/'+l['id']+'/offline-package').json()['files'])
    assert s.post('/files?lesson_id='+l['id'],files={'file':('lesson.mp4',video)}).status_code==403
    assert t.post('/files?lesson_id='+l['id'],files={'file':('fake.mp4',b'not a video')}).status_code==422
    assert admin.put('/lessons/'+l['id']+'/curriculum',json={'review_status':'reviewed'}).status_code==200
    r=s.get('/files/'+fid+'/download');assert r.status_code==200 and r.content==video and r.headers['content-type']=='video/mp4'
    assert any(x['id']==fid for x in s.get('/lessons/'+l['id']+'/offline-package').json()['files'])
    assert t.put('/lessons/'+l['id']+'/video-link',json={'url':'https://evil.test/watch?v=abcdefghijk','rights_confirmed':True}).status_code==422
    assert t.put('/lessons/'+l['id']+'/video-link',json={'url':'https://youtu.be/abcdefghijk','rights_confirmed':False}).status_code==422
    assert t.put('/lessons/'+l['id']+'/video-link',json={'url':'https://youtu.be/abcdefghijk','rights_confirmed':True}).status_code==200
    assert s.get('/lessons/'+l['id']+'/video-link').json()['youtube_id'] is None
    assert admin.put('/lessons/'+l['id']+'/curriculum',json={'review_status':'reviewed'}).status_code==200
    assert s.get('/lessons/'+l['id']+'/video-link').json()['youtube_id']=='abcdefghijk'
    assert s.put('/lessons/'+l['id']+'/video-link',json={'url':''}).status_code==403
