"""Explicit, idempotent fictional demo data. Password is provided by environment."""
import os
from .db import Session
from .models import *
from sqlalchemy import select
from argon2 import PasswordHasher

def seed():
    password=os.environ['DEMO_PASSWORD']
    if len(password)<12: raise ValueError('Use a demo password of at least 12 characters')
    with Session() as db:
        if db.scalar(select(School).where(School.name=='EduMate Demonstration Academy')): return
        school=School(name='EduMate Demonstration Academy'); db.add(school); db.flush()
        def user(name,email,role,cls=None):
            u=User(name=name,email=email+'@demo.edumate.test',role=role,class_name=cls,school_id=None if role=='platform_admin' else school.id,password_hash=PasswordHasher().hash(password)); db.add(u); db.flush(); return u
        user('Platform Administrator','platform','platform_admin'); user('Akosua Mensah','admin','school_admin')
        teachers=[user(n,e,'teacher') for n,e in [('Kwame Asante','maths'),('Esi Owusu','english'),('Kofi Boateng','science')]]
        students=[user(n,'student'+str(i+1),'student','Primary 5' if i<10 else 'Primary 4') for i,n in enumerate(['Ama Mensah','Kwesi Owusu','Akua Asante','Yaw Boateng','Abena Osei','Kofi Adjei','Efua Arthur','Kojo Appiah','Adwoa Quaye','Nana Baah','Afi Sarpong','Kweku Aidoo','Esi Annan','Fiifi Amoah','Afia Tetteh','Kobina Dadzie','Araba Badu','Kwabena Nti','Aba Darko','Yaa Agyeman'])]
        content=[
            ('Mathematics','Equivalent fractions','Recognise equivalent fractions','A fraction describes equal parts of a whole. In 1/2, the numerator is 1 and the denominator is 2.\n\nWorked example: Multiply both numbers by 2. 1/2 = 2/4. Both describe the same share of a whole. Imagine one orange cut into two equal pieces, then cut each piece in half.\n\nPractice: Write two fractions equivalent to 1/3.\n\nSummary: Multiply or divide numerator and denominator by the same non-zero number.', ['2/4','1/3','3/5'],'Which fraction equals 1/2?','2/4'),
            ('Mathematics','Place value','Read thousands, hundreds, tens and ones','The value of a digit depends on its position. In 4,352 the digit 4 means 4 thousands.\n\nWorked example: 4,352 = 4,000 + 300 + 50 + 2.\n\nPractice: Expand 6,281.\n\nSummary: Read place values from right to left: ones, tens, hundreds, thousands.', ['300','30','3'],'What is the value of 3 in 4,352?','300'),
            ('English Language','Nouns around us','Identify common nouns','A noun names a person, place, animal or thing. Teacher, Accra, goat and table are nouns.\n\nWorked example: The pupil opens a book. Pupil and book are nouns.\n\nPractice: Find three nouns in your classroom and use each in a sentence.\n\nSummary: Ask who or what a word names.', ['teacher','quickly','runs'],'Which word is a noun?','teacher'),
            ('English Language','Reading for meaning','Identify a main idea','Read this passage: Ama waters the school garden each morning. She removes weeds and checks the young plants. Her work keeps the garden healthy.\n\nThe main idea is what the passage is mostly about. Details support that idea.\n\nPractice: Explain which details show Ama cares for plants.\n\nSummary: Read the whole passage before choosing a main idea.', ['Caring for a garden','Buying a car','Playing football'],'What is the passage mainly about?','Caring for a garden'),
            ('Science','States of matter','Compare solids, liquids and gases','Matter takes up space. A solid keeps its shape, a liquid takes the shape of its container, and a gas spreads to fill available space.\n\nExample: Ice, liquid water and water vapour are forms of the same substance.\n\nPractice: Name two solids and two liquids in your home. Never touch hot water during experiments without adult supervision.\n\nSummary: Shape and movement help describe states of matter.', ['Liquid','Solid','Gas'],'What state is drinking water?','Liquid'),
            ('Science','Healthy plants','Describe what plants need','Most green plants need light, water, air and suitable nutrients to grow. Roots absorb water and minerals. Leaves use light to help make food.\n\nExample: Compare two plants of the same kind when one receives too little water. Ask an adult before setting up an observation.\n\nPractice: Draw a plant and label roots, stem and leaves.\n\nSummary: Plant parts work together to support growth.', ['Roots','Flowers','Fruit'],'Which part absorbs water from soil?','Roots')]
        for cls in ['Primary 4','Primary 5']:
            for t,subject in zip(teachers,['Mathematics','English Language','Science']): db.add(Teaching(teacher_id=t.id,school_id=school.id,class_name=cls,subject=subject))
            for i,(subject,title,obj,text,options,prompt,correct) in enumerate(content):
                t=teachers[['Mathematics','English Language','Science'].index(subject)]
                db.add(Lesson(school_id=school.id,author_id=t.id,class_name=cls,subject=subject,title=title,topic=title,objectives=obj,content=text,status='published'))
            for idx,subject in enumerate(['Mathematics','English Language','Science']):
                units=[c for c in content if c[0]==subject]
                questions=[]
                for j in range(5):
                    c=units[j%2]; questions.append({'type':'mcq','prompt':c[5],'options':c[4],'correct':c[6],'explanation':'Review the worked example in '+c[1]+'.'})
                db.add(Assessment(school_id=school.id,author_id=teachers[idx].id,class_name=cls,subject=subject,title=subject+' knowledge check',kind='quiz',instructions='Choose the best answer. Read each question carefully.',questions=questions,status='published',attempts_allowed=3))
            a=Assessment(school_id=school.id,author_id=teachers[0].id,class_name=cls,subject='Mathematics',title='Fractions in daily life',kind='assignment',instructions='Explain your reasoning in your own words.',questions=[{'type':'short','prompt':'Explain why 1/2 and 2/4 represent equal amounts.','options':[],'correct':None,'explanation':''}],status='published'); db.add(a); db.flush()
            pupil=students[0 if cls=='Primary 5' else 10]
            db.add(Submission(event_id=uid(),assessment_id=a.id,student_id=pupil.id,answers=['Both describe half of one whole.'],score=90,feedback='Good explanation. Add a drawing next time.',released=True))
        db.commit()
if __name__=='__main__': seed()
