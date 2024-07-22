from tempfile import SpooledTemporaryFile

from pydantic import BaseModel
from rich.spinner import Spinner


class UserSchema(BaseModel):
    fullname: str
    email: str
    phone: str
    # profile_picture : SpooledTemporaryFile
    # disabled: bool = None

class RegisterSchema(UserSchema):
    password: str