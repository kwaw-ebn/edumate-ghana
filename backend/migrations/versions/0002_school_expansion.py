"""Add school setup, files, curriculum, drafts, devices and parent records."""
from alembic import op
import sqlalchemy as sa
from app.db import Base
from app import models
from uuid import uuid4
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None
TABLES=['school_settings','enrollments','lesson_curriculum','file_assets','submission_files','assignment_drafts','parent_links','devices','sync_events','practice_attempts','lesson_practice_questions']
def upgrade():
    bind=op.get_bind()
    for name in TABLES: Base.metadata.tables[name].create(bind,checkfirst=True)
    settings=Base.metadata.tables['school_settings']
    for school in bind.execute(sa.text('SELECT id FROM schools')):
        school_id=school[0]
        classes={r[0] for r in bind.execute(sa.text('SELECT DISTINCT class_name FROM users WHERE school_id=:s AND class_name IS NOT NULL'),{'s':school_id})}
        subjects={r[0] for r in bind.execute(sa.text('SELECT DISTINCT subject FROM lessons WHERE school_id=:s'),{'s':school_id})}
        for kind,names in [('class',classes or {'Primary 4','Primary 5'}),('subject',subjects or {'Mathematics','English Language','Science'}),('term',{'2026/2027 • Term 1'})]:
            for name in names:
                if not bind.execute(sa.select(settings.c.id).where(settings.c.school_id==school_id,settings.c.kind==kind,settings.c.name==name)).first():
                    bind.execute(settings.insert().values(id=str(uuid4()),school_id=school_id,kind=kind,name=name,details={}))
    practice=Base.metadata.tables['lesson_practice_questions']
    examples={
        'Equivalent fractions':('Which fraction equals one half?',['2/4','1/3','3/5'],'2/4','Multiply both numbers in 1/2 by two.'),
        'Place value':('What is the value of 3 in 4,352?',['300','30','3'],'300','The digit 3 is in the hundreds place.'),
        'Nouns around us':('Which word names a person?',['Teacher','Quickly','Runs'],'Teacher','Teacher names a person and is a noun.'),
        'Reading for meaning':('The main idea tells us what a passage is…',['Mostly about','Printed on','Numbered with'],'Mostly about','Supporting details explain the main idea.'),
        'States of matter':('Which state describes drinking water?',['Liquid','Solid','Gas'],'Liquid','A liquid takes the shape of its container.'),
        'Healthy plants':('Which plant part absorbs water from soil?',['Roots','Flowers','Fruit'],'Roots','Roots absorb water and minerals from the soil.')}
    for row in bind.execute(sa.text('SELECT id,title FROM lessons')):
        if row[1] in examples and not bind.execute(sa.select(practice.c.lesson_id).where(practice.c.lesson_id==row[0])).first():
            prompt,options,correct,explanation=examples[row[1]]
            bind.execute(practice.insert().values(lesson_id=row[0],prompt=prompt,options=options,correct=correct,explanation=explanation))
def downgrade():
    # Intentionally retain user-created records; rollback requires an explicit retention decision.
    raise RuntimeError('Data-preserving migration; do not drop school records automatically')
