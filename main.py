from fastapi import FastAPI, Form, Response, Request, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from pydantic import EmailStr
from utils import (
    IDGen,
    image_saver,
    image_validator,
    price_range_fun,
    query_to_list,
    password_hasher,
    otp_generator,
    send_email_otp,
)
from model import (
    FormData,
    UserResponse,
    QueryModel,
    UserRegistrationModel,
    VerifiedModel,
    Category,
    AddItemModel,
)
from databases import stock_db

app = FastAPI()


# changing validation error status code to 400
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


# -------------------------------------------------------------------------------------------------------------------------------------------
# TASK 1 - SIMPLE BLOG POST CREATION
# -------------------------------------------------------------------------------------------------------------------------------------------
post_db = []


@app.post(
    "/upload-post",
    response_model=FormData,
    response_description="Post Created",
    tags=["user post"],
)
def upload_post(
    id: str = Depends(IDGen().id_gen),
    title: str = Form(),
    content: str = Form(),
    author: str | None = Form(None),
):
    user_post = {"post_id": id, "title": title, "content": content, "author": author}

    # save post in in-memory storage
    post_db.append(user_post)
    return JSONResponse(content=user_post, status_code=201)


# -------------------------------------------------------------------------------------------------------------------------------------------
# TASK 2 - USER PROFILE UPDATE WITH IMAGE UPLOAD
# -------------------------------------------------------------------------------------------------------------------------------------------
@app.post("/user-information", response_model=UserResponse, tags=["user profile"])
def user_info(
    name: str = Form(min_length=2, max_length=30),
    *,
    email: EmailStr = Form(),
    file_dict: dict = Depends(image_validator),
):
    # saving image in image folder
    image_path = image_saver(file_dict["file"], file_dict["extention"])
    return {"name": name, "email": email, "avatar_path": image_path}


# -------------------------------------------------------------------------------------------------------------------------------------------
# TASK 3 - PRODUCT SEARCH WITH PAGINATION AND FILTERING
# -------------------------------------------------------------------------------------------------------------------------------------------
@app.get("/items", response_model=QueryModel, tags=["query-items"])
def get_query_items(
    category: Category = Query(Category.Books, description="Category of items."),
    price_range: dict = Depends(price_range_fun),
    page: int = Query(1, gt=0, description="Navigate the pages of search results."),
    size: int = Query(
        10, gt=0, description="Number of items to be displayed per page."
    ),
):
    min_price = price_range["min"]
    max_price = price_range["max"]

    query_dict = query_to_list(category.value, min_price, max_price, page, size)

    return {
        "items": query_dict["items_list"],
        "total_items": query_dict["total_results"],
        "current_page": page,
        "page_size": size,
        "total_pages": query_dict["total_pages"],
    }


# -------------------------------------------------------------------------------------------------------------------------------------------
# TASK 4 - SECURE REGISTRATION WITH OTP VERIFICATION
# -------------------------------------------------------------------------------------------------------------------------------------------
user_registration_db = {
    "users": [],
    "otp": {},
}
simple_id_gen = IDGen().simple_id_gen()


@app.post("/register", response_model=UserRegistrationModel, tags=["registration"])
def user_registration(
    email: EmailStr = Form(),
    password: str = Form(min_length=8),
    phone: str | None = Form(None),
):
    id = next(simple_id_gen)
    user = {
        "id": id,
        "email": email,
        "password": password_hasher(password),
        "phone": phone,
        "is_active": False,
    }

    otp = otp_generator()

    try:
        send_email_otp(email, otp)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    else:
        user_registration_db["users"].append(user)
        user_registration_db["otp"][id] = otp

    return {
        "user_id": id,
        "msg": "Registration successful. Check your email to verify OTP.",
    }


@app.post("/verify-user", response_model=VerifiedModel, tags=["registration"])
def user_verification(
    user_id: str = Form(), otp: str = Form(min_length=6, max_length=6)
):
    if user_registration_db["otp"][user_id] != otp:
        raise HTTPException(
            status_code=400,
            detail={
                "msg": "The OTP entered is not correct. Check your email for OTP.",
                "otp_entered": otp,
            },
        )
    for user in user_registration_db["users"]:
        if user["id"] == user_id:
            user["is_active"] = True

    del user_registration_db["otp"][user_id]
    return JSONResponse(
        content={"message": "Your account is activated successfully."}, status_code=200
    )


# -------------------------------------------------------------------------------------------------------------------------------------------
# TASK 5 - E-COMMERCE SHOPPING CART MANAGEMENT
# -------------------------------------------------------------------------------------------------------------------------------------------
stock_db = stock_db.copy()
cart_db = {}


@app.post(
    "/items",
    tags=["items"],
    response_model=AddItemModel,
    response_description="Item added successfully.",
)
def add_item(product_id: int = Form(gt=0), quantity: int = Form(gt=0)):
    # does the product id exist?
    if not stock_db.get(product_id):
        raise HTTPException(
            status_code=400,
            detail={
                "msg": "Invalid product id",
                "product_id": product_id,
            },
        )
    # is the quantity more than the available quantity?
    if stock_db[product_id]["quantity"] < quantity:
        raise HTTPException(
            status_code=400,
            detail={
                "msg": "Quantity selected is more than the available quantity",
                "product_id": product_id,
                "available_quantity": stock_db[product_id]["quantity"],
                "selected_quantity": quantity,
            },
        )
    # is product available?
    if stock_db[product_id]["available"] == "no":
        raise HTTPException(
            status_code=400,
            detail={
                "msg": "Product is not available",
                "product_id": product_id,
                "available_statis": "no",
            },
        )
    stock_db[product_id]["quantity"] -= quantity
    added_item = {"item": f"product{product_id}", "quantity": quantity}
    if cart_db.get(product_id):
        cart_db[product_id]["quantity"] += quantity
    else:
        cart_db[product_id] = added_item

    return {"message": "Item added successfully.", "cart_items": cart_db}


@app.delete(
    "/items", response_description="Item was successfully deleted.", tags=["items"]
)
def delete_item(product_id: int):
    if not cart_db.get(product_id):
        raise HTTPException(
            status_code=400,
            detail={
                "msg": f"The product with id {product_id} is not in your cart.",
                "product_id": product_id,
            },
        )
    del cart_db[product_id]
    return Response(status_code=200)


@app.put("/item", response_model=AddItemModel, tags=["items"])
def update_item(product_id: int = Form(gt=0), quantity: int = Form(gt=0)):
    if not cart_db.get(product_id):
        raise HTTPException(
            status_code=400,
            detail={
                "msg": "Product id not in cart",
                "product_id": product_id,
            },
        )
    previous_quantity = cart_db[product_id]["quantity"]
    stock_db[product_id]["quantity"] += previous_quantity

    if stock_db[product_id]["quantity"] < quantity:
        stock_db[product_id]["quantity"] -= previous_quantity
        raise HTTPException(
            status_code=400,
            detail={
                "msg": "Quantity selected is more than the available quantity",
                "product_id": product_id,
                "available_quantity": stock_db[product_id]["quantity"],
                "selected_quantity": quantity,
            },
        )
    stock_db[product_id]["quantity"] -= quantity
    updated_item = {"item": f"product{product_id}", "quantity": quantity}
    cart_db[product_id] = updated_item

    return {"message": "Item was updated successfully.", "cart_items": cart_db}
