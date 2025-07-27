from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from urllib.parse import quote_plus

app = FastAPI()
@app.get("/")
def read_root():   
    return {"message": "Welcome to the FastAPI application!"}

# Setup local sql server database with SQL Server authentoication
username = "localdbadmin"
password = quote_plus("admin123")  # Important to escape special characters
server = "localhost"  # Use 'localhost' for localdb
database = "FastApiTest"  # Name of your database

DATABASE_URL = (
    f"mssql+pyodbc://{username}:{password}@{server}/{database}"
    f"?driver={quote_plus('ODBC Driver 17 for SQL Server')}"
)

engine = create_engine(DATABASE_URL, echo=True) # Create the SQLAlchemy engine

sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) # Create a session factory

# Create a base class for declarative models
Base = declarative_base()

class ProductDB(Base):  # Model for the products table
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)

# Create the database tables
Base.metadata.create_all(bind=engine)

class ProductCreate(BaseModel): # Model for creating a product
    name: str
    price: float

class Product(ProductCreate): # Inherits from ProductCreate to include the fields for response
    id: int

    class Config:
        orm_mode = True


# Dependency to get the database session
def get_db():  
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()
        

@app.get("/products", response_model=list[Product])
def get_products(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    products = db.query(ProductDB).order_by(ProductDB.id).offset(skip).limit(limit).all()
    return products

@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/products", response_model=Product)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = ProductDB(name=product.name, price=product.price)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.put("/products/{product_id}", response_model=Product)
def update_product(product_id: int, product: ProductCreate, db: Session = Depends(get_db)):
    db_product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db_product.name = product.name
    db_product.price = product.price
    db.commit()
    db.refresh(db_product)
    return db_product

@app.delete("/products/{product_id}", response_model=Product)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(db_product)
    db.commit()
    return db_product