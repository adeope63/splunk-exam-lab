"""Validate and combine the manually authored base bank and playlist adaptations.
The reviewed JSON files are the canonical content; regeneration never recreates
legacy template questions or overwrites the individual editorial choices.
"""
import json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.schemas import QuestionInput,fingerprint

def generate():
    base=json.loads((ROOT/'question_bank/authored_questions.json').read_text())
    playlist=json.loads((ROOT/'question_bank/playlist_questions.json').read_text())
    questions=base+playlist
    objectives={o['id'] for d in json.loads((ROOT/'references/blueprint.json').read_text()) for o in d['objectives']}
    ids=set(); stems=set()
    for raw in questions:
        q=QuestionInput.model_validate(raw)
        assert q.id not in ids,q.id
        assert q.objective_id in objectives,q.id
        assert q.type=='single' and len(q.options)==4,q.id
        assert len({o.text.strip().lower() for o in q.options})==4,q.id
        assert all(o.explanation.startswith('Correct. ' if o.id in q.correct else 'Incorrect. ') for o in q.options),q.id
        fp=fingerprint(q.text);assert fp not in stems,q.id
        ids.add(q.id);stems.add(fp)
    assert len(base)==300 and len(playlist)==58
    assert {q['objective_id'] for q in base}==objectives
    counts=Counter(q['domain_id'] for q in questions)
    assert Counter(q['domain_id'] for q in base)=={1:15,2:30,3:45,4:30,5:30,6:30,7:30,8:30,9:30,10:30}
    validation={'count':len(questions),'original_reviewed':len(base),'playlist_adaptations':len(playlist),'exam_eligible':sum(q['review_status']=='verified' and q.get('objective_alignment')!='supplemental' for q in questions),'supplemental':sum(q.get('objective_alignment')=='supplemental' for q in questions),'distribution':dict(counts),'objective_coverage':len(objectives),'structural_validation':'passed','duplicate_stems':0,'style':'Direct single-answer questions, four parallel choices, specific distractor rationales','base_answer_distribution':dict(sorted(Counter(q['correct'][0] for q in base).items())),'review_method':'Individual editorial review of 358 records against primary Splunk references. Replaced 200 repeated reasoning/multiple-response templates with direct questions; revised weak distractors. Related concepts remain across questions. No live Splunk execution or independent SME review.'}
    (ROOT/'question_bank/questions.json').write_text(json.dumps(questions,indent=2,ensure_ascii=False)+'\n')
    (ROOT/'question_bank/validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(f'Validated {len(questions)} questions; {len(objectives)} objectives; answer positions {validation["base_answer_distribution"]}')
if __name__=='__main__':generate()
