from fastapi import FastAPI, HTTPException, Depends
from fastapi.routing import APIRouter
from sqlmodel import Field, Session, SQLModel, create_engine, select
from contextlib import asynccontextmanager
from typing import Annotated
from pydantic import BaseModel

# ------------------- Database Setup ------------------- #
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

# ------------------- Lifespan ------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

# ------------------- Models ------------------- #
class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    age: int | None = Field(default=None, index=True)
    secret_name: str

class Item(BaseModel):
    id: int | None = None
    name: str
    price: float

# ------------------- Routers ------------------- #

class RootRouter:
    router = APIRouter()

    @router.get("/")
    def hello():
        return {"message": "Hello World"}

class FruitRouter:
    router = APIRouter()
    fake_fruits_db = []

    @router.get("/fruits/")
    def read_fruits(skip: int = 0, limit: int = 3):
        return FruitRouter.fake_fruits_db[skip: skip + limit]

    @router.get("/fruit/{id}")
    def read_fruit_by_id(id: int):
        for fruit in FruitRouter.fake_fruits_db:
            if fruit["id"] == id:
                return fruit
        raise HTTPException(status_code=404, detail="Item not found")

    @router.post("/fruit/{name}")
    def add_fruit(name: str):
        fruit_id = len(FruitRouter.fake_fruits_db) + 1
        fruit = {"id": fruit_id, "name": name}
        FruitRouter.fake_fruits_db.append(fruit)
        return fruit

class ItemRouter:
    router = APIRouter()
    fake_items_db = []

    @router.get("/items/")
    def read_items():
        return ItemRouter.fake_items_db

    @router.post("/items/")
    def create_item(item: Item):
        id = len(ItemRouter.fake_items_db) + 1
        new_item = item.dict()
        new_item["id"] = id
        ItemRouter.fake_items_db.append(new_item)
        return new_item

    @router.put("/items/{item_id}")
    def update_item(item_id: int, item: Item):
        for index, existing_item in enumerate(ItemRouter.fake_items_db):
            if existing_item["id"] == item_id:
                updated_item = item.dict()
                updated_item["id"] = item_id
                ItemRouter.fake_items_db[index] = updated_item
                return updated_item
        raise HTTPException(status_code=404, detail="Item not found")

class HeroRouter:
    router = APIRouter()

    @router.post("/heroes/")
    def create_hero(hero: Hero, session: SessionDep) -> Hero:
        session.add(hero)
        session.commit()
        session.refresh(hero)
        return hero

    @router.get("/heroes/")
    def read_heroes(session: SessionDep) -> list[Hero]:
        heroes = session.exec(select(Hero)).all()
        return heroes

    @router.get("/heroes/{hero_id}")
    def read_hero(hero_id: int, session: SessionDep) -> Hero:
        hero = session.get(Hero, hero_id)
        if not hero:
            raise HTTPException(status_code=404, detail="Hero not found")
        return hero

    @router.put("/heroes/{hero_id}")
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

    @router.delete("/heroes/{hero_id}")
    def delete_hero(hero_id: int, session: SessionDep):
        hero = session.get(Hero, hero_id)
        if not hero:
            raise HTTPException(status_code=404, detail="Hero not found")
        session.delete(hero)
        session.commit()
        return {"ok": True}

# ------------------- Register Routers ------------------- #
app.include_router(RootRouter.router)
app.include_router(FruitRouter.router)
app.include_router(ItemRouter.router)
app.include_router(HeroRouter.router)
