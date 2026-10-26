"""School tools: private uploads, offline sync, reports, parent links and devices."""
import csv,io,re
from typing import Literal
from datetime import date,datetime,timezone
from urllib.parse import quote
from xml.sax.saxutils import escape
from fastapi import APIRouter,Depends,UploadFile,File,Query,HTTPException,Response
from pydantic import BaseModel,Field,model_validator
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from .db import db_session
from .models import *
from .main import current,role,assigned,content_access,audit,fail,serialize,submission_view,Answers,submit,complete
from . import storage
router=APIRouter()

def defaults(db,u):
    if not u.school_id:return
    if db.scalar(select(SchoolSetting.id).where(SchoolSetting.school_id==u.school_id)):return
    classes={x for x in db.scalars(select(User.class_name).where(User.school_id==u.school_id,User.class_name.is_not(None)))} or {'Primary 4','Primary 5'}
    for kind,names in [('class',classes),('subject',{'Mathematics','English Language','Science'}),('term',{'2026/2027 • Term 1'})]:
        for name in names:db.add(SchoolSetting(school_id=u.school_id,kind=kind,name=name,details={}))
    db.flush()
def validate_scope(db,u,cls,subject=None):
    defaults(db,u)
    for kind,name in [('class',cls),('subject',subject)]:
        if name and not db.scalar(select(SchoolSetting.id).where(SchoolSetting.school_id==u.school_id,SchoolSetting.kind==kind,SchoolSetting.name==name)): fail(f'Choose a registered {kind}',422)
def setting(db,u,id,kind):
    x=db.get(SchoolSetting,id)
    if not x or x.school_id!=u.school_id or x.kind!=kind:fail('Invalid school '+kind,422)
    return x
@router.get('/setup')
def setup(u=Depends(current),db=Depends(db_session)):
    role(u,'student','teacher','school_admin','parent');defaults(db,u);db.commit()
    result={k:[serialize(x) for x in db.scalars(select(SchoolSetting).where(SchoolSetting.school_id==u.school_id,SchoolSetting.kind==k))] for k in ['class','subject','term']}
    if u.role=='teacher':
        links=list(db.scalars(select(Teaching).where(Teaching.teacher_id==u.id)))
        result['class']=[x for x in result['class'] if x['name'] in {t.class_name for t in links}]
        result['subject']=[x for x in result['subject'] if x['name'] in {t.subject for t in links}]
    return result
class SettingIn(BaseModel):
    kind: Literal['class','subject','term']
    name: str = Field(min_length=2,max_length=100)
    start_date: date|None=None
    end_date: date|None=None
    @model_validator(mode='after')
    def dates(self):
        if self.start_date and self.end_date and self.end_date<self.start_date:raise ValueError('End date must follow start date')
        return self
@router.post('/setup')
def add_setting(b:SettingIn,u=Depends(current),db=Depends(db_session)):
    role(u,'school_admin');defaults(db,u)
    name=b.name.strip()
    if len(name)<2:fail('Name is too short',422)
    if db.scalar(select(SchoolSetting.id).where(SchoolSetting.school_id==u.school_id,SchoolSetting.kind==b.kind,SchoolSetting.name==name)):fail('Already registered',409)
    x=SchoolSetting(school_id=u.school_id,kind=b.kind,name=name,details={k:str(v) for k,v in {'start_date':b.start_date,'end_date':b.end_date}.items() if v});db.add(x);audit(db,u,'create school '+b.kind);db.commit();return serialize(x)
class EnrollmentIn(BaseModel):
    student_id:str
    class_name:str=Field(min_length=2,max_length=100)
    term_id:str
@router.post('/enrollments')
def enroll(b:EnrollmentIn,u=Depends(current),db=Depends(db_session)):
    role(u,'school_admin');p=db.get(User,b.student_id)
    if not p or p.school_id!=u.school_id or p.role!='student':fail('Student not found',404)
    validate_scope(db,u,b.class_name);setting(db,u,b.term_id,'term')
    x=db.scalar(select(Enrollment).where(Enrollment.student_id==p.id,Enrollment.term_id==b.term_id))
    if x:x.class_name=b.class_name
    else:db.add(Enrollment(**b.model_dump(),school_id=u.school_id))
    p.class_name=b.class_name;audit(db,u,'enroll student');db.commit();return {'ok':True}
@router.get('/enrollments')
def enrollments(u=Depends(current),db=Depends(db_session)):
    role(u,'school_admin');return [serialize(x) for x in db.scalars(select(Enrollment).where(Enrollment.school_id==u.school_id))]
class CurriculumIn(BaseModel):
    term_id:str|None=None
    week:int|None=Field(default=None,ge=1,le=52)
    strand:str=Field(default='',max_length=200)
    sub_strand:str=Field(default='',max_length=200)
    review_status:Literal['pending','reviewed']='pending'
    practice_prompt:str=Field(default='',max_length=2000)
    practice_options:list[str]=Field(default_factory=list,max_length=6)
    practice_correct:str=Field(default='',max_length=1000)
    practice_explanation:str=Field(default='',max_length=2000)
def curriculum_view(db,l):
    x=db.get(Curriculum,l.id);d=serialize(x) if x else {'term_id':None,'week':None,'strand':'','sub_strand':'','review_status':'pending'}
    q=db.get(PracticeQuestion,l.id)
    d['practice']=serialize(q) if q else None
    return d
@router.get('/lessons/{id}/curriculum')
def curriculum(id:str,u=Depends(current),db=Depends(db_session)):
    l=db.get(Lesson,id);content_access(db,u,l);return curriculum_view(db,l)
@router.put('/lessons/{id}/curriculum')
def save_curriculum(id:str,b:CurriculumIn,u=Depends(current),db=Depends(db_session)):
    role(u,'teacher','school_admin');l=db.get(Lesson,id);content_access(db,u,l)
    if u.role=='teacher' and l.author_id!=u.id:fail()
    if b.term_id:setting(db,u,b.term_id,'term')
    if b.review_status=='reviewed' and u.role!='school_admin':fail('A school administrator must record educator review')
    x=db.get(Curriculum,id)
    if not x:x=Curriculum(lesson_id=id);db.add(x)
    for k in ['term_id','week','strand','sub_strand','review_status']:setattr(x,k,getattr(b,k))
    x.reviewer_id=u.id if b.review_status=='reviewed' else None
    if b.practice_prompt:
        if len(b.practice_options)<2 or len(set(b.practice_options))!=len(b.practice_options) or b.practice_correct not in b.practice_options:fail('Practice needs distinct options and a correct answer',422)
        q=db.get(PracticeQuestion,id)
        if not q:q=PracticeQuestion(lesson_id=id);db.add(q)
        q.prompt=b.practice_prompt;q.options=b.practice_options;q.correct=b.practice_correct;q.explanation=b.practice_explanation
    audit(db,u,'update curriculum');db.commit();return curriculum_view(db,l)

def asset_access(db,u,a):
    if not a or a.school_id!=u.school_id:fail('File not found',404)
    if a.lesson_id:content_access(db,u,db.get(Lesson,a.lesson_id))
    elif a.assessment_id:
        content_access(db,u,db.get(Assessment,a.assessment_id))
        if u.role=='student' and a.student_work and a.uploader_id!=u.id:fail('File not found',404)
    else:fail('File not found',404)
def file_view(x):return {k:getattr(x,k) for k in ['id','name','content_type','size','lesson_id','assessment_id','uploader_id','student_work','created_at']}
@router.post('/files')
async def upload(file:UploadFile=File(...),lesson_id:str|None=None,assessment_id:str|None=None,u=Depends(current),db=Depends(db_session)):
    if bool(lesson_id)==bool(assessment_id):fail('Select one lesson or assessment',422)
    role(u,'teacher','school_admin','student')
    if lesson_id:
        role(u,'teacher','school_admin');l=db.get(Lesson,lesson_id);content_access(db,u,l)
        if u.role=='teacher' and l.author_id!=u.id:fail()
    if assessment_id:content_access(db,u,db.get(Assessment,assessment_id))
    data=await file.read(storage.MAX_BYTES+1);name=re.sub(r'[^\w.() -]','_',file.filename or 'resource')[:180]
    mime=storage.validate_file(name,data);id=uid();key=f'{u.school_id}/{id}/{name}'
    storage.put(key,data,mime)
    a=FileAsset(id=id,school_id=u.school_id,uploader_id=u.id,lesson_id=lesson_id,assessment_id=assessment_id,student_work=u.role=='student',name=name,object_key=key,content_type=mime,size=len(data));db.add(a);audit(db,u,'upload resource');db.commit();return file_view(a)
@router.get('/files')
def files(lesson_id:str|None=None,assessment_id:str|None=None,u=Depends(current),db=Depends(db_session)):
    if bool(lesson_id)==bool(assessment_id):fail('Select a lesson or assessment',422)
    obj=db.get(Lesson,lesson_id) if lesson_id else db.get(Assessment,assessment_id);content_access(db,u,obj)
    rows=db.scalars(select(FileAsset).where(FileAsset.school_id==u.school_id,FileAsset.lesson_id==lesson_id) if lesson_id else select(FileAsset).where(FileAsset.school_id==u.school_id,FileAsset.assessment_id==assessment_id))
    return [file_view(x) for x in rows if u.role!='student' or not x.student_work or x.uploader_id==u.id]
@router.get('/files/{id}/download')
def download(id:str,u=Depends(current),db=Depends(db_session)):
    a=db.get(FileAsset,id);asset_access(db,u,a)
    return Response(storage.read(a.object_key),media_type=a.content_type,headers={'Content-Disposition':"attachment; filename*=UTF-8''"+quote(a.name),'X-Content-Type-Options':'nosniff'})
def validate_attachments(db,u,assessment_id,ids):
    if len(set(ids))!=len(ids):fail('Duplicate attachment',422)
    for id in ids:
        a=db.get(FileAsset,id)
        if not a or a.school_id!=u.school_id or a.assessment_id!=assessment_id or not a.student_work or a.uploader_id!=u.id:fail('Invalid submission attachment',422)
class DraftIn(BaseModel):
    answers:list[str]=Field(default_factory=list,max_length=50)
    file_ids:list[str]=Field(default_factory=list,max_length=10)
    version:int=Field(default=0,ge=0)
@router.get('/assessments/{id}/draft')
def draft(id:str,u=Depends(current),db=Depends(db_session)):
    role(u,'student');content_access(db,u,db.get(Assessment,id));d=db.scalar(select(AssignmentDraft).where(AssignmentDraft.student_id==u.id,AssignmentDraft.assessment_id==id));return serialize(d) if d else {'answers':[],'file_ids':[],'version':0}
@router.put('/assessments/{id}/draft')
def save_draft(id:str,b:DraftIn,u=Depends(current),db=Depends(db_session)):
    role(u,'student');a=db.get(Assessment,id);content_access(db,u,a)
    db.scalar(select(User).where(User.id==u.id).with_for_update())
    if len(b.answers)>len(a.questions) or any(len(s)>20000 for s in b.answers):fail('Invalid draft answers',422)
    validate_attachments(db,u,id,b.file_ids)
    d=db.scalar(select(AssignmentDraft).where(AssignmentDraft.student_id==u.id,AssignmentDraft.assessment_id==id).with_for_update())
    if (d.version if d else 0)!=b.version:fail('Draft changed on another device. Your local copy is preserved; reopen online to compare.',409)
    if not d:d=AssignmentDraft(student_id=u.id,assessment_id=id);db.add(d)
    d.answers=b.answers;d.file_ids=b.file_ids;d.version=b.version+1;d.updated_at=now();db.commit();return serialize(d)
@router.get('/submissions/{id}/files')
def submission_files(id:str,u=Depends(current),db=Depends(db_session)):
    s=db.get(Submission,id)
    if not s:fail('Not found',404)
    content_access(db,u,db.get(Assessment,s.assessment_id))
    if u.role=='student' and s.student_id!=u.id:fail()
    return [file_view(db.get(FileAsset,x.file_id)) for x in db.scalars(select(SubmissionFile).where(SubmissionFile.submission_id==id))]
class PracticeIn(BaseModel):
    event_id:str=Field(min_length=16,max_length=100)
    answer:str=Field(max_length=2000)
@router.post('/lessons/{id}/practice')
def practice(id:str,b:PracticeIn,u=Depends(current),db=Depends(db_session)):
    role(u,'student');content_access(db,u,db.get(Lesson,id));q=db.get(PracticeQuestion,id)
    if not q:fail('This lesson has no practice question',404)
    old=db.get(SyncEvent,b.event_id)
    if old:
        if old.student_id!=u.id or old.kind!='practice:'+id:fail('Event identifier belongs to another action',409)
        return old.result
    if b.answer not in q.options:fail('Choose a practice option',422)
    result={'correct':b.answer==q.correct,'explanation':q.explanation,'practice_only':True}
    db.add(PracticeAttempt(student_id=u.id,lesson_id=id,answer=b.answer,correct=result['correct']));db.add(SyncEvent(event_id=b.event_id,student_id=u.id,kind='practice:'+id,result=result));db.commit();return result
@router.get('/lessons/{id}/offline-package')
def offline_package(id:str,u=Depends(current),db=Depends(db_session)):
    role(u,'student');l=db.get(Lesson,id);content_access(db,u,l)
    # Only ungraded practice exposes answer keys; assessment keys are never in downloads.
    return {'lesson':serialize(l),'curriculum':curriculum_view(db,l),'files':files(lesson_id=id,assessment_id=None,u=u,db=db)}
class SyncIn(BaseModel):
    events:list[dict]=Field(max_length=50)
    device_id:str|None=None
@router.post('/sync')
def sync(b:SyncIn,u=Depends(current),db=Depends(db_session)):
    role(u,'student');results=[]
    for e in b.events:
        try:
            kind=e.get('kind');id=e.get('target');event=e.get('event_id','')
            if not isinstance(event,str) or not 16<=len(event)<=100:fail('Invalid event id',422)
            if kind=='complete':
                previous=db.get(SyncEvent,event)
                if previous:
                    if previous.student_id!=u.id or previous.kind!='complete:'+id:fail('Event identifier belongs to another action',409)
                    r=previous.result
                else:
                    r=complete(id,u,db);db.add(SyncEvent(event_id=event,student_id=u.id,kind='complete:'+id,result=r));db.commit()
            elif kind=='practice':r=practice(id,PracticeIn(event_id=event,answer=e.get('answer','')),u,db)
            elif kind=='submit':r=submit(id,Answers(event_id=event,answers=e.get('answers',[]),file_ids=e.get('file_ids',[])),u,db)
            else:fail('Unsupported synchronization event',422)
            results.append({'event_id':event,'ok':True,'result':r})
        except (HTTPException,ValueError,TypeError) as ex:
            db.rollback();results.append({'event_id':e.get('event_id'),'ok':False,'status':getattr(ex,'status_code',422),'error':getattr(ex,'detail','Invalid synchronization event')})
    if b.device_id:
        d=db.get(Device,b.device_id)
        if d and d.school_id==u.school_id and d.active and d.student_id==u.id:d.last_sync=now();db.commit()
    return {'events':results}

class DeviceIn(BaseModel):
    label:str=Field(min_length=2,max_length=100)
    serial:str=Field(min_length=2,max_length=100)
    student_id:str|None=None
    active:bool=True
@router.get('/devices')
def devices(u=Depends(current),db=Depends(db_session)):
    role(u,'school_admin','student')
    return [serialize(x) for x in db.scalars(select(Device).where(Device.school_id==u.school_id)) if u.role=='school_admin' or x.student_id==u.id]
@router.post('/devices')
def device(b:DeviceIn,u=Depends(current),db=Depends(db_session)):
    role(u,'school_admin')
    if b.student_id:
        s=db.get(User,b.student_id)
        if not s or s.school_id!=u.school_id or s.role!='student':fail('Choose a student from this school',422)
    if db.scalar(select(Device.id).where(Device.school_id==u.school_id,Device.serial==b.serial)):fail('Serial already registered',409)
    x=Device(**b.model_dump(),school_id=u.school_id);db.add(x);audit(db,u,'register tablet');db.commit();return serialize(x)
@router.put('/devices/{id}')
def edit_device(id:str,b:DeviceIn,u=Depends(current),db=Depends(db_session)):
    role(u,'school_admin');x=db.get(Device,id)
    if not x or x.school_id!=u.school_id:fail('Device not found',404)
    if b.student_id:
        s=db.get(User,b.student_id)
        if not s or s.school_id!=u.school_id or s.role!='student':fail('Choose a student from this school',422)
    duplicate=db.scalar(select(Device.id).where(Device.school_id==u.school_id,Device.serial==b.serial,Device.id!=id))
    if duplicate:fail('Serial already registered',409)
    for k,v in b.model_dump().items():setattr(x,k,v)
    audit(db,u,'update tablet');db.commit();return serialize(x)
@router.post('/devices/{id}/heartbeat')
def heartbeat(id:str,u=Depends(current),db=Depends(db_session)):
    role(u,'student');x=db.get(Device,id)
    if not x or x.school_id!=u.school_id or x.student_id!=u.id or not x.active:fail('This tablet record is inactive or not assigned to you')
    x.last_sync=now();db.commit();return {'ok':True,'last_sync':x.last_sync}
class ParentLinkIn(BaseModel):
    parent_id:str
    student_id:str
@router.post('/parent-links')
def link_parent(b:ParentLinkIn,u=Depends(current),db=Depends(db_session)):
    role(u,'school_admin');p=db.get(User,b.parent_id);s=db.get(User,b.student_id)
    if not p or not s or p.role!='parent' or s.role!='student' or p.school_id!=u.school_id or s.school_id!=u.school_id:fail('Choose a parent and student in this school',422)
    if not db.scalar(select(ParentLink.id).where(ParentLink.parent_id==p.id,ParentLink.student_id==s.id)):db.add(ParentLink(**b.model_dump(),school_id=u.school_id))
    audit(db,u,'link parent and learner');db.commit();return {'ok':True}
def learner_summary(db,student):
    work=list(db.scalars(select(Assessment).where(Assessment.school_id==student.school_id,Assessment.class_name==student.class_name,Assessment.status=='published')))
    submissions=list(db.scalars(select(Submission).where(Submission.student_id==student.id)))
    visible={a.id:a for a in work};released=[s for s in submissions if s.released and s.score is not None]
    # Historical released results remain visible after class transfers.
    results=[]
    for s in released:
        a=db.get(Assessment,s.assessment_id)
        if a.school_id==student.school_id:results.append({'title':a.title,'subject':a.subject,'score':s.score,'max_score':a.max_score,'feedback':s.feedback,'submitted_at':s.submitted_at})
    published=list(db.scalars(select(Lesson.id).where(Lesson.school_id==student.school_id,Lesson.class_name==student.class_name,Lesson.status=='published')))
    done=set(db.scalars(select(Progress.lesson_id).where(Progress.student_id==student.id)))
    submitted={s.assessment_id for s in submissions}
    return {'student_id':student.id,'name':student.name,'class_name':student.class_name,'lessons_completed':len(done.intersection(published)),'lessons_available':len(published),'average_score':round(sum(r['score']/r['max_score']*100 for r in results)/len(results),1) if results else None,'assignments_due':[{'title':a.title,'subject':a.subject,'due_at':a.due_at} for a in work if a.kind=='assignment' and a.id not in submitted],'results':results}
@router.get('/parent-summaries')
def parent_summaries(u=Depends(current),db=Depends(db_session)):
    role(u,'parent','school_admin')
    links=db.scalars(select(ParentLink).where(ParentLink.school_id==u.school_id))
    return [learner_summary(db,db.get(User,x.student_id))|{'parent_id':x.parent_id} for x in links if u.role=='school_admin' or x.parent_id==u.id]

@router.get('/reports')
def reports(class_name:str|None=None,subject:str|None=None,u=Depends(current),db=Depends(db_session)):
    role(u,'teacher','school_admin')
    pairs=None
    if u.role=='teacher':pairs={(x.class_name,x.subject) for x in db.scalars(select(Teaching).where(Teaching.teacher_id==u.id))}
    all_students=list(db.scalars(select(User).where(User.school_id==u.school_id,User.role=='student')))
    if class_name:all_students=[s for s in all_students if s.class_name==class_name]
    if pairs is not None:all_students=[s for s in all_students if any(c==s.class_name and (not subject or sub==subject) for c,sub in pairs)]
    lessons=[x for x in db.scalars(select(Lesson).where(Lesson.school_id==u.school_id,Lesson.status=='published')) if (not subject or x.subject==subject) and (pairs is None or (x.class_name,x.subject) in pairs)]
    assessments=[x for x in db.scalars(select(Assessment).where(Assessment.school_id==u.school_id,Assessment.status=='published')) if (not subject or x.subject==subject) and (pairs is None or (x.class_name,x.subject) in pairs)]
    ids={s.id for s in all_students};assessment_ids={a.id for a in assessments};rows=[]
    attempts=[s for s in db.scalars(select(Submission).where(Submission.student_id.in_(ids))) if s.assessment_id in assessment_ids] if ids else []
    progress=list(db.scalars(select(Progress).where(Progress.student_id.in_(ids)))) if ids else []
    for s in all_students:
        eligible={a.id:a for a in assessments if a.class_name==s.class_name};mine=[x for x in attempts if x.student_id==s.id and x.assessment_id in eligible];marked=[x for x in mine if x.released and x.score is not None]
        average=round(sum(x.score/eligible[x.assessment_id].max_score*100 for x in marked)/len(marked),1) if marked else None
        lesson_ids={x.id for x in lessons if x.class_name==s.class_name};completed=len({x.lesson_id for x in progress if x.student_id==s.id}.intersection(lesson_ids))
        work={a.id for a in eligible.values() if a.kind=='assignment'};submitted={x.assessment_id for x in mine}.intersection(work)
        rate=round(len(submitted)/len(work)*100,1) if work else None
        rows.append({'student_id':s.id,'name':s.name,'class_name':s.class_name,'average_score':average,'lessons_completed':completed,'lessons_available':len(lesson_ids),'assignments_submitted':len(submitted),'assignments_available':len(work),'completion_rate':rate,'needs_support':bool((average is not None and average<50) or (rate is not None and rate<50))})
    marked=[x for x in rows if x['average_score'] is not None]
    return {'students':rows,'class_average':round(sum(x['average_score'] for x in marked)/len(marked),1) if marked else None,'support_count':sum(x['needs_support'] for x in rows),'support_rule':'Released score below 50% or assignment completion below 50%. This is a follow-up flag, not a diagnosis.','class_name':class_name,'subject':subject,'generated_at':now()}
@router.get('/reports/export')
def export(format:Literal['csv','pdf']='csv',class_name:str|None=None,subject:str|None=None,u=Depends(current),db=Depends(db_session)):
    report=reports(class_name,subject,u,db);rows=report['students'];headers=['Name','Class','Average %','Lessons completed','Lessons available','Assignments submitted','Assignments available','Completion %','Support flag']
    data=[[x['name'],x['class_name'],x['average_score'],x['lessons_completed'],x['lessons_available'],x['assignments_submitted'],x['assignments_available'],x['completion_rate'],'Follow up' if x['needs_support'] else ''] for x in rows]
    if format=='csv':
        buf=io.StringIO();w=csv.writer(buf);w.writerow(headers)
        for row in data:w.writerow([("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v) for v in row])
        return Response(buf.getvalue().encode('utf-8-sig'),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="edumate-performance.csv"'})
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4,landscape
    buf=io.BytesIO();styles=getSampleStyleSheet();doc=SimpleDocTemplate(buf,pagesize=landscape(A4),leftMargin=25,rightMargin=25,topMargin=25,bottomMargin=25)
    small=styles['BodyText'];small.fontSize=8;small.leading=11
    table=Table([[Paragraph(escape(str(v if v is not None else '—')),small) for v in row] for row in [headers]+data],colWidths=[125,65,65,70,70,75,75,65,65],repeatRows=1)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf2fb')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#dbe3ed')),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    doc.build([Paragraph('EduMate Ghana — School Performance',styles['Title']),Paragraph(escape(f"Class: {class_name or 'All authorized classes'} | Subject: {subject or 'All authorized subjects'}"),styles['Normal']),Spacer(1,15),table,Spacer(1,15),Paragraph(escape(report['support_rule']),small)])
    audit(db,u,'export performance '+format);db.commit();return Response(buf.getvalue(),media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="edumate-performance.pdf"'})
