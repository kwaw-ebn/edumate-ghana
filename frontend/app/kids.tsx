'use client';
import {useState} from 'react';
type Row=Record<string,any>;
const activities=[
 {title:'Colours',icon:'🎨',prompt:'Which colour is the sun?',choices:['🔵 Blue','🟡 Yellow','🟢 Green'],answer:'🟡 Yellow',idea:'Find something yellow in the classroom.'},
 {title:'Numbers',icon:'🔢',prompt:'How many stars can you see? ⭐ ⭐ ⭐',choices:['1','2','3'],answer:'3',idea:'Count three classroom objects together.'},
 {title:'Animals',icon:'🐓',prompt:'Which animal says “meow”?',choices:['🐱 Cat','🐐 Goat','🐟 Fish'],answer:'🐱 Cat',idea:'Talk about animals you see in your community.'},
 {title:'Healthy habits',icon:'🧼',prompt:'What do we use to wash our hands?',choices:['🧼 Soap','📚 Book','🧸 Toy'],answer:'🧼 Soap',idea:'Practise handwashing with a teacher or parent.'}
];
export default function Kids({lessons,onOpen}:{lessons:Row[],onOpen:(l:Row)=>void}){
 const [chosen,setChosen]=useState<number|null>(null),[feedback,setFeedback]=useState('');
 const early=lessons.filter(l=>/^(nursery|pre[ -]?school|kg\s*[12]|kindergarten)/i.test(l.class_name||''));
 return <div className="kids"><div className="kids-hero"><div><span className="eyebrow">TEACHER-GUIDED EARLY LEARNING</span><h1>Little learners, big discoveries!</h1><p>Explore stories, songs, videos and play together.</p></div><span className="kids-sun" aria-hidden="true">☀️</span></div>
 <p className="kids-note">For use with a teacher or parent. Example activities are demonstrations and are not recorded as pupil progress.</p>
 <h2>Play and practise</h2><div className="kids-grid">{activities.map((a,i)=><button key={a.title} className="kids-tile" onClick={()=>{setChosen(i);setFeedback('');}}><span aria-hidden="true">{a.icon}</span><strong>{a.title}</strong><small>Try an activity</small></button>)}</div>
 {chosen!==null&&<section className="card kids-activity" aria-live="polite"><h2>{activities[chosen].icon} {activities[chosen].title}</h2><p>{activities[chosen].prompt}</p><div className="kids-choices">{activities[chosen].choices.map(x=><button key={x} className="outline" onClick={()=>setFeedback(x===activities[chosen].answer?'Well done! '+activities[chosen].idea:'Let’s try another answer together.')}>{x}</button>)}</div>{feedback&&<p role="status">{feedback}</p>}<button className="text-button" onClick={()=>setChosen(null)}>Close activity</button></section>}
 <h2>Our preschool lessons</h2><p>Open a school lesson to watch its reviewed videos and save available resources for offline use.</p>{early.length?<div className="kids-grid">{early.map(l=><button className="kids-tile" key={l.id} onClick={()=>onOpen(l)}><span aria-hidden="true">📖</span><strong>{l.title}</strong><small>{l.class_name} · {l.subject}</small></button>)}</div>:<div className="card"><p>No preschool lessons are available to this account yet. A school administrator can add Nursery, KG 1 and KG 2 under School setup, assign teachers, and enrol learners. Teachers can then create lessons for their assigned classes.</p></div>}
 <p className="fine">The sample activities are not curriculum approval. Teachers should review all content. To use school lessons and videos offline, first download them while connected and open Offline learning.</p></div>
}
