import os,tempfile
from pathlib import Path
TEST_DATABASE=Path(tempfile.gettempdir())/('edumate-test-'+str(os.getpid())+'.db')
os.environ['DATABASE_URL']='sqlite:///'+str(TEST_DATABASE)
os.environ['JWT_SECRET']='test-only-secret-at-least-32-characters-long'
os.environ['COOKIE_SECURE']='false'
os.environ['DEMO_PASSWORD']='temporary-test-password'
import pytest
from fastapi.testclient import TestClient
from app.db import Base,engine,Session
from app.main import app
from app.seed import seed
from app.models import School,User,Lesson,Teaching
from argon2 import PasswordHasher
from sqlalchemy import select
@pytest.fixture(scope='module',autouse=True)
def setup():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine); seed()
    yield
    Base.metadata.drop_all(engine)
def client(email):
    c=TestClient(app)
    r=c.post('/auth/login',json={'email':email+'@demo.edumate.test','password':os.environ['DEMO_PASSWORD']})
    assert r.status_code==200,r.text
    return c

def test_full_teaching_workflow():
    teacher=client('maths'); student=client('student2')
    lesson={'class_name':'Primary 5','subject':'Mathematics','title':'New fractions lesson','topic':'Fractions','objectives':'Understand equal shares','content':'Split a whole into equal shares. One of two equal parts is one half.','status':'draft'}
    r=teacher.post('/lessons',json=lesson); assert r.status_code==200,r.text
    lid=r.json()['id']
    assert lid not in [x['id'] for x in student.get('/lessons').json()]
    lesson['status']='published'; assert teacher.put('/lessons/'+lid,json=lesson).status_code==200
    assert lid in [x['id'] for x in student.get('/lessons').json()]
    assert student.post('/lessons/'+lid+'/complete').status_code==200
    assert student.post('/lessons/'+lid+'/complete').status_code==200
    assert student.get('/progress').json().count(lid)==1
    a={'class_name':'Primary 5','subject':'Mathematics','title':'Explain fractions','kind':'assignment','instructions':'Write a short explanation','status':'published','questions':[{'type':'essay','prompt':'Explain one half.'}]}
    r=teacher.post('/assessments',json=a); assert r.status_code==200,r.text
    aid=r.json()['id']; event='unique-workflow-event-0001'
    r=student.post('/assessments/'+aid+'/submit',json={'event_id':event,'answers':['One of two equal parts.']}); assert r.status_code==200,r.text
    sid=r.json()['id']; assert r.json()['score'] is None
    assert student.post('/assessments/'+aid+'/submit',json={'event_id':event,'answers':['Retry']}).json()['id']==sid
    assert teacher.put('/submissions/'+sid+'/grade',json={'score':85,'feedback':'Clear explanation','released':False}).status_code==200
    assert next(x for x in student.get('/submissions').json() if x['id']==sid)['score'] is None
    assert teacher.put('/submissions/'+sid+'/grade',json={'score':85,'feedback':'Clear explanation','released':True}).status_code==200
    assert next(x for x in student.get('/submissions').json() if x['id']==sid)['score']==85

def test_quiz_answers_hidden_and_score_saved():
    c=client('student3'); q=next(x for x in c.get('/assessments').json() if x['kind']=='quiz')
    assert all('correct' not in x and 'explanation' not in x for x in q['questions'])
    r=c.post('/assessments/'+q['id']+'/submit',json={'event_id':'unique-quiz-event-0001','answers':[x['options'][0] for x in q['questions']]})
    assert r.status_code==200,r.text
    assert r.json()['score']==100
    assert any(x['id']==r.json()['id'] for x in c.get('/submissions').json())

def test_cross_school_and_role_permissions():
    c=client('student4'); teacher=client('maths'); platform=client('platform')
    assert c.post('/lessons',json={'class_name':'Primary 5','subject':'Mathematics','title':'Unauthorized lesson','topic':'x','objectives':'x','content':'This cannot be created.'}).status_code==403
    assert platform.get('/users').status_code==403
    assert platform.get('/lessons').status_code==403
    assert c.get('/demo-requests').status_code==403
    with Session() as db:
        school=School(name='Another School'); db.add(school);db.flush()
        other=User(name='Other student',email='other@example.org',role='student',class_name='Primary 5',school_id=school.id,password_hash=PasswordHasher().hash('other-password-123'));db.add(other);db.commit()
    outsider=TestClient(app);assert outsider.post('/auth/login',json={'email':'other@example.org','password':'other-password-123'}).status_code==200
    assert outsider.get('/lessons').json()==[]
    lid=c.get('/lessons').json()[0]['id']
    assert outsider.post('/lessons/'+lid+'/complete').status_code==404
    # Mathematics teacher cannot publish Science lessons.
    assert teacher.post('/lessons',json={'class_name':'Primary 5','subject':'Science','title':'Wrong subject','topic':'x','objectives':'x','content':'This is not assigned.'}).status_code==403

def test_rotation_and_csrf():
    c=client('english'); old=c.cookies.get('refresh')
    assert c.post('/auth/refresh',headers={'Cookie':'refresh='+old}).status_code==200
    assert c.post('/auth/refresh',headers={'Cookie':'refresh='+old}).status_code==401
    assert c.post('/auth/logout',headers={'Origin':'https://attacker.example'}).status_code==403

def test_demo_request_persisted():
    c=TestClient(app)
    r=c.post('/demo-requests',json={'school_name':'Fictional Private School','contact':'Demo Person','email':'contact@example.org','phone':'0240000000','location':'Accra','students':100,'preferred_date':'2027-01-10','message':'Please demonstrate.'})
    assert r.status_code==200
    assert any(x['school_name']=='Fictional Private School' for x in client('platform').get('/demo-requests').json())
