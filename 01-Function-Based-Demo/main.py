from fastapi import FastAPI
from fastapi import HTTPException


def lifespan(app: FastAPI):
    create_db_and_tables()  # This replaces the old startup event
    yield  # we can also do cleanup here after shutdown if needed

app = FastAPI(lifespan=lifespan) # Creates an instance of fastapi


@app.get("/")
def hello():
    return {"message": "Hello World"}

fake_fruits_db = []

# -----------  Query Parameter --------------- #
@app.get("/fruits/")
def read_fruits(skip: int = 0, limit: int = 3):
    return fake_fruits_db[skip : skip + limit]

@app.get("/fruit/{id}")
def read_fruit_by_id(id: int):
    for fruit in fake_fruits_db:
        if fruit["id"] == id:
            return fruit
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/fruit/{name}")
def add_fruit(name: str):
    fruit_id = len(fake_fruits_db) + 1  
    fruit = {"id": fruit_id, "name": name} 
    fake_fruits_db.append(fruit)
    print(fake_fruits_db)
    return fruit


# ----------- Request Body --------- #
from pydantic import BaseModel

fake_items_db = []

class Item(BaseModel):
    id: int  = None  # Will be assigned automatically
    name: str
    price: float

@app.get("/items/")
def read_items(): 
    return fake_items_db

@app.post("/items/")
def create_item(item: Item):
    id = len(fake_items_db) + 1
    print(item)
    new_item = item.dict()
    print(new_item)
    new_item["id"] = id
    fake_items_db.append(new_item)
    return new_item

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    for index, existing_item in enumerate(fake_items_db):
        if existing_item["id"] == item_id:
            updated_item = item.dict()
            updated_item["id"] = item_id
            fake_items_db[index] = updated_item
            return updated_item
    raise HTTPException(status_code=404, detail="Item not found")



# ---------- Connect with sqlite server ------- #
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select

class Hero(SQLModel, table=True):  # table=True, tells SQLModel that this is a table model, it should represent a table in the SQL database
    id: int | None = Field(default=None, primary_key=True)  # Field(primary_key=True), tells SQLModel that the id is the primary key in the SQL database
    name: str = Field(index=True)
    age: int | None = Field(default=None, index=True)
    secret_name: str


sqlite_file_name = "database.db" 
sqlite_url = f"sqlite:///{sqlite_file_name}"

connection_string = (
    "mssql+pyodbc://username:password@localhost/DatabaseName"
    "?driver=ODBC+Driver+17+for+SQL+Server"
)


connect_args = {"check_same_thread": False}  # Using check_same_thread=False allows FastAPI to use the same SQLite database in different threads.
engine = create_engine(sqlite_url, connect_args=connect_args)  # create a database engine


def create_db_and_tables(): 
    SQLModel.metadata.create_all(engine) # to create the tables for all the table models.


def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]  # Create session dependency


@app.post("/heroes/")
def create_hero(hero: Hero, session: SessionDep) -> Hero:
    session.add(hero)
    session.commit()
    session.refresh(hero)
    return hero

@app.get("/heroes/")
def read_heroes(session: SessionDep) -> list[Hero]:
    print(session)
    heroes = session.exec(select(Hero)).all()
    return heroes

@app.get("/heroes/{hero_id}")
def read_hero(hero_id: int, session: SessionDep) -> Hero:
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    return hero

@app.put("/heroes/{hero_id}")
def update_hero(new_hero: Hero, hero_id: int, session: SessionDep):
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    hero.name = new_hero.name
    hero.secret_name = new_hero.secret_name
    hero.age = new_hero.age

    session.add(hero)
    session.commit()
    session.refresh(hero)

    return hero

@app.delete("/heroes/{hero_id}")
def delete_hero(hero_id: int, session: SessionDep):
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    session.delete(hero)
    session.commit()
    return {"ok": True}