import uuid
from fastapi import FastAPI, Depends
from sqlmodel import SQLModel, Field, Session, create_engine
app=FastAPI()
class Item(SQLModel,table=True):
    id:str=Field(default_factory=uuid.uuid4,primary_key=True)
    quantity:int
def db():return Session(create_engine("sqlite://"))
@app.post("/items")
def create(value:Item,session:Session=Depends(db)):
    session.add(value)
    session.commit()
    return value
@app.get("/items/{id}")
def read(id:str,session:Session=Depends(db)):
    return lookup(session,id)

def lookup(session,id):return session.get(Item,id)
