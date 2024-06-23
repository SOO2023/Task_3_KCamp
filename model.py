from pydantic import BaseModel, EmailStr
from enum import Enum


# model for task 1
# --------------------------------------------------------
class FormData(BaseModel):
    post_id: str
    title: str
    content: str
    author: str


# model for task 2
# --------------------------------------------------------
class UserResponse(BaseModel):
    name: str
    email: EmailStr
    avatar_path: str


# model for task 3
# --------------------------------------------------------
class Category(Enum):
    Electronics = "Electronics"
    Home_Appliances = "Home Appliances"
    Tools = "Tools"
    Books = "Books"
    Clothing = "Clothing"


class QueryModel(BaseModel):
    total_items: int | None = None
    current_page: int
    page_size: int
    total_pages: int | None = None
    items: list[dict]


# model for task 4
# --------------------------------------------------------
class UserRegistrationModel(BaseModel):
    user_id: str
    msg: str


class VerifiedModel(BaseModel):
    message: str


# model for task 5
# --------------------------------------------------------
class AddItemModel(BaseModel):
    message: str
    cart_items: dict
