from __future__ import annotations
from typing import Optional
import hashlib, re
from typing import Literal
from pydantic import BaseModel, Field, model_validator
class Option(BaseModel):
    id: str = Field(min_length=1, max_length=20)
    text: str = Field(min_length=1)
    explanation: str = Field(min_length=5)
class QuestionInput(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    domain_id: int = Field(ge=1,le=10)
    objective_id: str
    text: str = Field(min_length=15)
    type: Literal['single','multiple']
    options: list[Option] = Field(min_length=4,max_length=10)
    correct: list[str] = Field(min_length=1)
    explanation: str = Field(min_length=15)
    difficulty: Literal['easy','medium','hard']
    commands: list[str] = []
    reference: str = ''
    review_status: Literal['verified','needs_review'] = 'needs_review'
    @model_validator(mode='after')
    def validate_answers(self):
        ids=[o.id for o in self.options]
        if len(ids)!=len(set(ids)): raise ValueError('Option IDs must be unique')
        if len(self.correct)!=len(set(self.correct)) or not set(self.correct)<=set(ids): raise ValueError('Invalid correct answer IDs')
        if self.type=='single' and len(self.correct)!=1: raise ValueError('Single-choice requires exactly one correct answer')
        if self.type=='multiple' and len(self.correct)<2: raise ValueError('Multiple-response requires at least two correct answers')
        if not self.objective_id.startswith(f'{self.domain_id}.'): raise ValueError('Domain and objective do not match')
        if self.reference and not self.reference.startswith(('https://docs.splunk.com/','https://help.splunk.com/','https://www.splunk.com/')): raise ValueError('Use an official Splunk documentation URL')
        return self
class StartExam(BaseModel):
    mode: Literal['mock','quick','topic','wrong']='quick'
    count: int = Field(default=10,ge=1,le=300)
    timed: bool = False
    duration: Optional[int] = Field(default=None,ge=1,le=240)
    feedback: Literal['immediate','end']='end'
    difficulty: Literal['all','easy','medium','hard']='all'
    domains: list[int]=[]
    objectives: list[str]=[]
    unanswered: bool=False
    weak: bool=False
class AnswerInput(BaseModel):
    selected: list[str]
    flagged: Optional[bool]=None
    current_index: Optional[int]=None
class RevisionInput(BaseModel):
    bookmarked: Optional[bool]=None
    note: Optional[str]=Field(default=None,max_length=20000)
class SettingsInput(BaseModel):
    duration: int = Field(default=57,ge=1,le=240)
    count: int = Field(default=20,ge=1,le=300)
    target: int = Field(default=80,ge=1,le=100)
    theme: Literal['dark','light']='dark'
    randomize: bool=True
    feedback: Literal['immediate','end']='immediate'
def fingerprint(text):
    return hashlib.sha256(re.sub(r'\W+', ' ', text.lower()).strip().encode()).hexdigest()
