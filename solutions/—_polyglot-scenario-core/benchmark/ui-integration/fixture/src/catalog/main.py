from fastapi import FastAPI,Depends
from sqlmodel import SQLModel,Field,Session,create_engine
from uuid import UUID,uuid4
app=FastAPI()
class Upload(SQLModel):
    title:str
    quantity:int
class Item(SQLModel,table=True):
    __tablename__="artifact_rows"
    id:UUID=Field(default_factory=uuid4,primary_key=True)
    title:str
    quantity:int
def database():return Session(create_engine("postgresql://worker:pass@db/inventory"))
@app.post("/items")
def add_item(upload:Upload,session:Session=Depends(database)):
    item=Item(title=upload.title,quantity=upload.quantity)
    session.add(item)
    session.commit()
    return item
def lookup(session,id):return session.get(Item,id)
@app.get("/items/{id}")
def read_item(id:UUID,session:Session=Depends(database)):return lookup(session,id)
