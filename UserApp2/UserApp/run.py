from fastapi import FastAPI, Request, Response, HTTPException, Depends, Form, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from .schemas.schema import UserSchema, RegisterSchema
from fastapi.templating import Jinja2Templates
import hashlib
from pydantic import EmailStr
from sqlalchemy import create_engine, Column, Integer, String,MetaData, select, LargeBinary, ForeignKey
from databases import Database
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker,relationship

from PIL import Image
from io import BytesIO
import base64




DATABASE_URL = "postgresql://username:password@db:5432/database"

database = Database(DATABASE_URL)
metadata = MetaData()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
# class User(Base):
#     __tablename__ = "Users"
#     user_id = Column(Integer, primary_key=True, index=True)
#     fullname = Column(String, index=True)
#     email = Column(String, index=True)
#     password = Column(String)
#     phone = Column(String)
#     images = relationship("Profile", back_populates="user", cascade="all, delete-orphan")
# class Profile(Base):
#     __tablename__ = "Profile"
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
#     profile = Column(LargeBinary)
#     user = relationship("User", back_populates="images")
class User(Base):
    __tablename__ = "Users"
    user_id = Column(Integer, primary_key=True, index=True)
    fullname = Column(String, index=True)
    email = Column(String, index=True)
    password = Column(String)
    phone = Column(String)
    profiles = relationship("Profile", back_populates="user", cascade="all, delete-orphan")

class Profile(Base):
    __tablename__ = "Profile"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("Users.user_id"), nullable=False)
    image = Column(LargeBinary)
    user = relationship("User", back_populates="profiles")


    
Base.metadata.create_all(bind=engine)

app = FastAPI()
@app.on_event("startup")
async def startup_db_client():
    await database.connect()


@app.on_event("shutdown")
async def shutdown_db_client():
    await database.disconnect()


app.mount("/static", StaticFiles(directory="UserApp/static"), name="static")
templates = Jinja2Templates(directory="UserApp/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request : Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register(request : Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("view_user/{user_id}", response_class=HTMLResponse)
async def view_user(request : Request, user_id: int):
    query = User.__table__.select().where(User.id == user_id)
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return templates.TemplateResponse("view_user.html", {"request": request, "user": user})

@app.get("/view_users", response_class=HTMLResponse)
async def view_users(request : Request):
    try:
        query = """
        SELECT "Users"."user_id", "Users"."fullname", "Users"."email","Users"."phone", "Profile"."image"
        FROM "Users"
        LEFT JOIN "Profile" ON "Users"."user_id" = "Profile"."user_id"
        """
        
        # Execute the query 
        profiles_result = await database.fetch_all(query)
        print(profiles_result)
        profiles = []
        for profile in profiles_result:
            profile.image = base64.b64encode(profile.image).decode("utf-8")
            profiles.append(profile)
        return templates.TemplateResponse("users.html", {"request": request, "users": profiles})
    except Exception as e:
        import traceback
        traceback.print_exc()

@app.post("/register_user")
async def register_user(request:Request,
    fullname: str = Form(...),
    email: EmailStr = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    profile: UploadFile = File(...)
):
    h = hashlib.new('sha256')
    h.update(email.encode())
    user_id = h.hexdigest()
    query = select(User).where(User.user_id == user_id)
    result = await database.fetch_one(query)
    if result:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "alert": "User already exists in the database"},
        )

    query = User.__table__.insert().values(
        user_id=user_id, fullname=fullname, email=email, password=password, phone=phone
    )
    await database.execute(query)
    
    query = Profile.__table__.insert().values(
        user_id=user_id, image=await profile.read()
    )
    await database.execute(query)

    return templates.TemplateResponse(
            "register.html",
            {"request": request, "alert": "User added to the database"},
        )

