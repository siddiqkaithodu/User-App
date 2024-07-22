from fastapi import FastAPI, Request, Response, HTTPException, Depends, Form, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from .schemas.schema import UserSchema, RegisterSchema
from fastapi.templating import Jinja2Templates
import hashlib
from pydantic import EmailStr
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import create_engine, Column, Integer, String, MetaData, select
from databases import Database
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from PIL import Image
from io import BytesIO
import base64

mongo_client = AsyncIOMotorClient("mongodb://username:password@mongodb:27017")

db = mongo_client["database"]
collection = db["Profile"]


DATABASE_URL = "postgresql://username:password@db:5432/database"

database = Database(DATABASE_URL)
metadata = MetaData()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
class User(Base):
    __tablename__ = "Users"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    fullname = Column(String, index=True)
    email = Column(String, index=True)
    password = Column(String)
    phone = Column(String)
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
        query = User.__table__.select()
        users_result = await database.fetch_all(query)

        
        user_ids = [user.user_id for user in users_result]
        profiles_result = await collection.find({"user_id": {"$in": user_ids}}).to_list(
            length=len(user_ids)
        )

        
        user_data = {user["user_id"]: dict(user) for user in users_result}
        for profile in profiles_result:
            image_data = profile["profile"]
            base64_image = base64.b64encode(image_data).decode("utf-8")
            user_data[profile["user_id"]]["profile"] = base64_image
        return templates.TemplateResponse("users.html", {"request": request, "users": user_data.values()})
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

    # Save to MongoDB
    contents = await profile.read()
    user_data = {"profile": contents, "user_id": user_id}
    await collection.insert_one(user_data)
    return templates.TemplateResponse(
            "register.html",
            {"request": request, "alert": "User added to the database"},
        )

