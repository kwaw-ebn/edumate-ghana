import hashlib, os, secrets, time
from collections import defaultdict, deque
from datetime import datetime
from typing import Literal
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import select, func
from .db import db_session
from .models import *

SECRET = os.getenv('JWT_SECRET')
if not SECRET or len(SECRET) < 32: raise RuntimeError('JWT_SECRET must contain at least 32 characters')
SECURE = os.getenv('COOKIE_SECURE', 'true') == 'true'
ph = PasswordHasher()
app = FastAPI(title='EduMate Ghana API', version='0.2.0')
rate = defaultdict(deque)
def limit(key, count=15):
    q = rate[key]; t = time.time()
    while q and q[0] < t - 60: q.popleft()
    if len(q) >= count: raise HTTPException(429, 'Too many requests. Try again shortly.')
    q.append(t)
def fail(detail='Access denied', code=403): raise HTTPException(code, detail)
@app.middleware('http')
async def protection(request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        if origin and origin != os.getenv('APP_ORIGIN', 'http://localhost:3000'):
            return Response('Invalid origin', status_code=403)
        if request.headers.get('sec-fetch-site') == 'cross-site': return Response(status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    return response

def current(request: Request, db=Depends(db_session)):
    try:
        payload = jwt.decode(request.cookies.get('access', ''), SECRET, algorithms=['HS256'])
        user = db.get(User, payload['sub'])
    except (jwt.InvalidTokenError, KeyError): fail('Please sign in', 401)
    if not user or not user.active: fail('Please sign in', 401)
    if user.school_id and not db.get(School, user.school_id).active: fail('School account inactive')
    return user

def role(u, *roles):
    if u.role not in roles: fail()
def assigned(db, u, class_name, subject):
    validate_scope(db,u,class_name,subject)
    if u.role == 'school_admin': return
    role(u, 'teacher')
    if not db.scalar(select(Teaching).where(Teaching.teacher_id == u.id, Teaching.class_name == class_name, Teaching.subject == subject)): fail('Class or subject not assigned')
def content_access(db, u, obj):
    if not obj or obj.school_id != u.school_id: fail('Not found', 404)
    if u.role == 'student':
        if obj.class_name != u.class_name or obj.status != 'published': fail('Not found', 404)
    else: assigned(db, u, obj.class_name, obj.subject)
def audit(db, u, action): db.add(Audit(user_id=u.id, action=action))
def public_user(u): return {k:getattr(u,k) for k in ('id','name','email','role','class_name','school_id')}
def serialize(obj): return {c.name:getattr(obj,c.name) for c in obj.__table__.columns}
def assessment_view(a, u):
    d = serialize(a)
    if u.role == 'student': d['questions'] = [{k:v for k,v in q.items() if k not in ('correct','explanation')} for q in a.questions]
    return d

def session_cookies(response, db, u):
    token = jwt.encode({'sub':u.id,'exp':int(time.time())+900}, SECRET, algorithm='HS256')
    refresh = secrets.token_urlsafe(48)
    db.add(Refresh(id=hashlib.sha256(refresh.encode()).hexdigest(),user_id=u.id,expires=int(time.time())+604800))
    response.set_cookie('access', token, httponly=True, secure=SECURE, samesite='lax', max_age=900, path='/')
    response.set_cookie('refresh', refresh, httponly=True, secure=SECURE, samesite='lax', max_age=604800, path='/api/auth')
class Login(BaseModel):
    # Login accepts seeded .test identifiers; registration still validates real email syntax.
    email: str = Field(min_length=3,max_length=254,pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(max_length=256)
@app.get('/health')
def health(db=Depends(db_session)):
    db.execute(select(1)); return {'status':'ok'}
@app.post('/auth/login')
def login(body: Login, request: Request, response: Response, db=Depends(db_session)):
    limit(('login-account',body.email.lower()))
    limit(('login-ip',request.client.host),120)
    u = db.scalar(select(User).where(User.email == body.email.lower()))
    try: valid = ph.verify(u.password_hash if u else ph.hash('dummy-invalid-password'), body.password)
    except VerificationError: valid = False
    if not u or not valid or not u.active: fail('Invalid email or password',401)
    if u.school_id and not db.get(School,u.school_id).active: fail('School account inactive')
    session_cookies(response,db,u); audit(db,u,'login'); db.commit(); return public_user(u)
@app.post('/auth/refresh')
def refresh(request: Request, response: Response, db=Depends(db_session)):
    digest=hashlib.sha256(request.cookies.get('refresh','').encode()).hexdigest()
    r=db.scalar(select(Refresh).where(Refresh.id==digest).with_for_update())
    if not r or r.expires < time.time(): fail('Please sign in',401)
    u=db.get(User,r.user_id)
    if not u.active or (u.school_id and not db.get(School,u.school_id).active): fail('Account inactive',401)
    db.delete(r); session_cookies(response,db,u); db.commit(); return public_user(u)
@app.post('/auth/logout')
def logout(request: Request, response: Response, db=Depends(db_session)):
    r=db.get(Refresh,hashlib.sha256(request.cookies.get('refresh','').encode()).hexdigest())
    if r: db.delete(r); db.commit()
    response.delete_cookie('access',path='/'); response.delete_cookie('refresh',path='/api/auth'); return {'ok':True}
@app.get('/auth/me')
def me(u=Depends(current)): return public_user(u)

class LessonIn(BaseModel):
    class_name: str = Field(min_length=2,max_length=100)
    subject: str = Field(min_length=2,max_length=100)
    title: str = Field(min_length=3,max_length=200)
    topic: str = Field(max_length=200)
    objectives: str = Field(max_length=4000)
    content: str = Field(min_length=10,max_length=50000)
    status: Literal['draft','published','archived'] = 'draft'
@app.get('/lessons')
def lessons(u=Depends(current),db=Depends(db_session)):
    role(u,'student','teacher','school_admin')
    rows=db.scalars(select(Lesson).where(Lesson.school_id==u.school_id)).all()
    if u.role=='student': rows=[x for x in rows if x.class_name==u.class_name and x.status=='published']
    if u.role=='teacher':
        pairs={(x.class_name,x.subject) for x in db.scalars(select(Teaching).where(Teaching.teacher_id==u.id))}
        rows=[x for x in rows if (x.class_name,x.subject) in pairs]
    return [serialize(x) for x in rows]
@app.post('/lessons')
def create_lesson(b:LessonIn,u=Depends(current),db=Depends(db_session)):
    assigned(db,u,b.class_name,b.subject)
    x=Lesson(**b.model_dump(),school_id=u.school_id,author_id=u.id); db.add(x); audit(db,u,'create lesson'); db.commit(); return serialize(x)
@app.put('/lessons/{id}')
def edit_lesson(id:str,b:LessonIn,u=Depends(current),db=Depends(db_session)):
    x=db.get(Lesson,id); content_access(db,u,x); assigned(db,u,b.class_name,b.subject)
    if u.role=='teacher' and x.author_id!=u.id: fail()
    for k,v in b.model_dump().items(): setattr(x,k,v)
    audit(db,u,'update lesson'); db.commit(); return serialize(x)
@app.post('/lessons/{id}/complete')
def complete(id:str,u=Depends(current),db=Depends(db_session)):
    role(u,'student'); content_access(db,u,db.get(Lesson,id))
    if not db.scalar(select(Progress).where(Progress.student_id==u.id,Progress.lesson_id==id)):
        db.add(Progress(student_id=u.id,lesson_id=id)); db.commit()
    return {'ok':True}
@app.get('/progress')
def progress(u=Depends(current),db=Depends(db_session)):
    role(u,'student'); return [x.lesson_id for x in db.scalars(select(Progress).where(Progress.student_id==u.id))]
class Question(BaseModel):
    type: Literal['mcq','true_false','short','essay']
    prompt: str = Field(min_length=1,max_length=2000)
    options: list[str] = Field(default_factory=list,max_length=8)
    correct: str | None = Field(default=None,max_length=2000)
    explanation: str = Field(default='',max_length=2000)
class AssessmentIn(BaseModel):
    class_name: str = Field(min_length=2,max_length=100)
    subject: str = Field(min_length=2,max_length=100)
    title: str = Field(min_length=3,max_length=200)
    kind: Literal['quiz','assignment']
    instructions: str = Field(max_length=5000)
    questions: list[Question] = Field(min_length=1,max_length=50)
    status: Literal['draft','published','archived'] = 'draft'
    due_at: str | None = None
    max_score: int = Field(default=100,ge=1,le=1000)
    attempts_allowed: int = Field(default=1,ge=1,le=10)
@app.get('/assessments')
def assessments(u=Depends(current),db=Depends(db_session)):
    role(u,'student','teacher','school_admin')
    result=[]
    for a in db.scalars(select(Assessment).where(Assessment.school_id==u.school_id)):
        try: content_access(db,u,a)
        except HTTPException: continue
        result.append(assessment_view(a,u))
    return result
@app.post('/assessments')
def create_assessment(b:AssessmentIn,u=Depends(current),db=Depends(db_session)):
    assigned(db,u,b.class_name,b.subject)
    if b.due_at:
        try:
            if datetime.fromisoformat(b.due_at).tzinfo is None: raise ValueError()
        except ValueError: fail('Deadline must be an ISO date with timezone',422)
    for q in b.questions:
        if q.type in ('mcq','true_false') and (len(q.options)<2 or q.correct not in q.options): fail('Objective questions need options and a valid answer',422)
        if b.kind=='quiz' and q.type not in ('mcq','true_false'): fail('Quizzes support objective questions',422)
    a=Assessment(**b.model_dump(),school_id=u.school_id,author_id=u.id); db.add(a); audit(db,u,'create assessment'); db.commit(); return serialize(a)
class Answers(BaseModel):
    event_id: str = Field(min_length=16,max_length=100)
    answers: list[str] = Field(max_length=50)
    file_ids: list[str] = Field(default_factory=list,max_length=10)
@app.post('/assessments/{id}/submit')
def submit(id:str,b:Answers,u=Depends(current),db=Depends(db_session)):
    role(u,'student'); a=db.get(Assessment,id); content_access(db,u,a)
    # Lock this student's row to serialize concurrent retries and attempt limits.
    db.scalar(select(User).where(User.id==u.id).with_for_update())
    existing=db.scalar(select(Submission).where(Submission.event_id==b.event_id))
    if existing:
        if existing.student_id!=u.id or existing.assessment_id!=id: fail()
        return submission_view(existing)
    count=db.scalar(select(func.count()).select_from(Submission).where(Submission.assessment_id==id,Submission.student_id==u.id))
    if count>=a.attempts_allowed: fail('Attempt limit reached',409)
    validate_attachments(db,u,id,b.file_ids)
    if len(b.answers)!=len(a.questions) or any(len(v)>20000 for v in b.answers): fail('Answer every question',422)
    objective=all(q['type'] in ('mcq','true_false') for q in a.questions)
    score=sum(ans==q['correct'] for ans,q in zip(b.answers,a.questions))/len(a.questions)*a.max_score if objective else None
    s=Submission(event_id=b.event_id,assessment_id=id,student_id=u.id,answers=b.answers,score=score,released=objective)
    db.add(s); db.flush()
    for file_id in b.file_ids: db.add(SubmissionFile(submission_id=s.id,file_id=file_id))
    audit(db,u,'submit assessment'); db.commit(); return submission_view(s)
def submission_view(s):
    d=serialize(s)
    if not s.released: d['score']=None; d['feedback']=''
    return d
@app.get('/submissions')
def submissions(u=Depends(current),db=Depends(db_session)):
    role(u,'student','teacher','school_admin'); result=[]
    for s,a in db.execute(select(Submission,Assessment).join(Assessment,Submission.assessment_id==Assessment.id).where(Assessment.school_id==u.school_id)):
        if u.role=='student' and s.student_id!=u.id: continue
        if u.role=='teacher':
            try: assigned(db,u,a.class_name,a.subject)
            except HTTPException: continue
        d=submission_view(s) if u.role=='student' else serialize(s)
        d['title']=a.title; d['max_score']=a.max_score; d['student_name']=db.get(User,s.student_id).name
        d['late']=bool(a.due_at and datetime.fromisoformat(s.submitted_at)>datetime.fromisoformat(a.due_at))
        if u.role=='student' and s.released: d['review']=a.questions
        result.append(d)
    return result
class Grade(BaseModel):
    score: float = Field(ge=0)
    feedback: str = Field(max_length=5000)
    released: bool = True
@app.put('/submissions/{id}/grade')
def grade(id:str,b:Grade,u=Depends(current),db=Depends(db_session)):
    role(u,'teacher','school_admin'); s=db.get(Submission,id)
    if not s: fail('Not found',404)
    a=db.get(Assessment,s.assessment_id); content_access(db,u,a)
    if b.score>a.max_score: fail('Score exceeds maximum',422)
    for k,v in b.model_dump().items(): setattr(s,k,v)
    audit(db,u,'grade submission'); db.commit(); return serialize(s)
@app.get('/users')
def users(u=Depends(current),db=Depends(db_session)):
    role(u,'teacher','school_admin')
    rows=db.scalars(select(User).where(User.school_id==u.school_id)).all()
    if u.role=='teacher':
        classes={x.class_name for x in db.scalars(select(Teaching).where(Teaching.teacher_id==u.id))}
        rows=[x for x in rows if x.role=='student' and x.class_name in classes]
    return [public_user(x)|{'active':x.active} for x in rows]
class UserIn(BaseModel):
    name: str = Field(min_length=2,max_length=100)
    email: EmailStr
    password: str = Field(min_length=12,max_length=128)
    role: Literal['student','teacher','parent']
    class_name: str | None = Field(default=None,min_length=2,max_length=100)
@app.post('/users')
def add_user(b:UserIn,u=Depends(current),db=Depends(db_session)):
    role(u,'school_admin')
    if b.role=='student' and not b.class_name: fail('Student class required',422)
    if b.class_name: validate_scope(db,u,b.class_name)
    if db.scalar(select(User).where(User.email==b.email.lower())): fail('Email already registered',409)
    d=b.model_dump(exclude={'password'}); d['email']=d['email'].lower()
    x=User(**d,school_id=u.school_id,password_hash=ph.hash(b.password)); db.add(x); audit(db,u,'register user'); db.commit(); return public_user(x)
@app.patch('/users/{id}/active')
def toggle_user(id:str,u=Depends(current),db=Depends(db_session)):
    role(u,'school_admin'); x=db.get(User,id)
    if not x or x.school_id!=u.school_id or x.role not in ('student','teacher','parent'): fail()
    x.active=not x.active; audit(db,u,'toggle user active'); db.commit(); return public_user(x)|{'active':x.active}
class TeachingIn(BaseModel):
    teacher_id: str
    class_name: str = Field(min_length=2,max_length=100)
    subject: str = Field(min_length=2,max_length=100)
@app.post('/teaching')
def assign(b:TeachingIn,u=Depends(current),db=Depends(db_session)):
    role(u,'school_admin'); t=db.get(User,b.teacher_id)
    if not t or t.role!='teacher' or t.school_id!=u.school_id: fail()
    existing=db.scalar(select(Teaching).where(Teaching.teacher_id==t.id,Teaching.class_name==b.class_name,Teaching.subject==b.subject))
    if not existing: db.add(Teaching(**b.model_dump(),school_id=u.school_id)); audit(db,u,'assign teacher'); db.commit()
    return {'ok':True}
@app.get('/schools')
def schools(u=Depends(current),db=Depends(db_session)):
    role(u,'platform_admin'); return [serialize(s) for s in db.scalars(select(School))]
class SchoolIn(BaseModel):
    name: str = Field(min_length=3,max_length=200)
@app.post('/schools')
def school(b:SchoolIn,u=Depends(current),db=Depends(db_session)):
    role(u,'platform_admin'); s=School(name=b.name); db.add(s); audit(db,u,'register school'); db.commit(); return serialize(s)
@app.get('/audit')
def logs(u=Depends(current),db=Depends(db_session)):
    role(u,'platform_admin'); return [serialize(x) for x in db.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(100))]
class DemoIn(BaseModel):
    school_name: str = Field(min_length=3,max_length=200)
    contact: str = Field(min_length=2,max_length=100)
    email: EmailStr
    phone: str = Field(min_length=8,max_length=30)
    location: str = Field(min_length=2,max_length=200)
    students: int = Field(ge=1,le=100000)
    preferred_date: str = Field(max_length=40)
    message: str = Field(default='',max_length=3000)
    website: str = ''
@app.post('/demo-requests')
def request_demo(b:DemoIn,request:Request,db=Depends(db_session)):
    limit(('demo',request.client.host),5)
    if not b.website: db.add(DemoRequest(**b.model_dump(exclude={'website'}))); db.commit()
    return {'ok':True}
@app.get('/demo-requests')
def requests(u=Depends(current),db=Depends(db_session)):
    role(u,'platform_admin'); return [serialize(x) for x in db.scalars(select(DemoRequest))]

from .expansion import router as expansion_router, validate_scope, validate_attachments
app.include_router(expansion_router)
