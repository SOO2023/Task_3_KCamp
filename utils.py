import string
import random
from PIL import Image
import os
from fastapi import UploadFile, Query
from fastapi.exceptions import HTTPException
from pandasql import sqldf
from databases import product_db
from math import ceil
from passlib.hash import pbkdf2_sha256
from email.mime.text import MIMEText
from dotenv import load_dotenv
from mailersend import emails

load_dotenv()

productsqldf = lambda q: sqldf(q, globals())
product_db = product_db.copy()


class IDGen:
    def __init__(self):
        self.all = (
            list(string.ascii_lowercase)
            + list(string.ascii_uppercase)
            + list(string.digits)
        )
        self.numbers = list(string.digits)
        random.shuffle(self.all)
        random.shuffle(self.numbers)

    def id_gen(self):
        sample = random.choices(population=self.all, k=20)
        return "".join(sample)

    def otp_gen(self, k=6):
        sample = random.choices(population=self.numbers, k=k)
        return "".join(sample)

    def simple_id_gen(self):
        i = 0
        while True:
            i += 1
            yield str(i)


# ------------------------------------------------------------------------------------------------
# Functions for task 2
# ------------------------------------------------------------------------------------------------
def image_saver(byte_file, extention) -> str:
    current_dir = os.getcwd()
    image = Image.open(byte_file)
    new_image_name = IDGen().id_gen() + "." + extention
    saved_image_dir = os.path.join(current_dir, "image")

    if os.path.exists(saved_image_dir):
        image_path = os.path.join(saved_image_dir, new_image_name)
        image.save(image_path)
    else:
        os.mkdir(saved_image_dir)
        image_path = os.path.join(saved_image_dir, new_image_name)
        image.save(image_path)
    return image_path


def image_validator(avatar: UploadFile):
    file_extention = avatar.filename.split(".")[-1]
    # validating if size of file is not greater than 300kb or if it is an image
    required_size = 300_000
    if int(avatar.size) > required_size or file_extention.lower() not in [
        "png",
        "jpg",
        "jpeg",
    ]:
        raise HTTPException(
            status_code=400,
            detail={
                "msg": "Check if the uploaded file is not greater than the minimum size or supports the required file extention.",
                "expected_size": f"{required_size/1000:.0f}kb",
                "uploaded_file_size": f"{int(avatar.size)/1000:.0f}kb",
                "required_extention": ["png", "jpg", "jpeg"],
                "uploaded_extention": file_extention,
                "file_name": f"{avatar.filename}",
            },
        )
    return {"file": avatar.file, "extention": file_extention}


# ------------------------------------------------------------------------------------------------
# Functions for task 3
# ------------------------------------------------------------------------------------------------
def price_range_fun(
    min_price: float = Query(gt=0, description="minimum price of item"),
    max_price: float = Query(description="maximum price of item", gt=0),
):
    if min_price >= max_price:
        raise HTTPException(
            status_code=400, detail="max price should be greater than minimum price"
        )
    return {"min": min_price, "max": max_price}


def query_to_list(category, min_price, max_price, page, size):
    offset = (page - 1) * size
    q1 = f"""
    SELECT * 
    FROM product_db
    WHERE category = "{category}" AND price BETWEEN {min_price} AND {max_price}
    """
    q2 = f"""
    SELECT * 
    FROM product_db
    WHERE category = "{category}" AND price BETWEEN {min_price} AND {max_price}
    LIMIT {size} OFFSET {offset};
    """
    total_results = productsqldf(q1).shape[0]
    total_pages = ceil(total_results / size)
    df = productsqldf(q2)

    if total_results == 0:
        total_results = None

    if total_pages > 0:
        if page > total_pages:
            raise HTTPException(
                status_code=400,
                detail={
                    "msg": f"No such page. Page number should no be more than {total_pages}",
                    "page_entered": page,
                },
            )
    else:
        total_pages = None
        if page > 1:
            raise HTTPException(status_code=400, detail="No such page.")

    df_dict = df.T.to_dict()
    df_list = [df_dict[key] for key in df_dict]
    return {
        "total_results": total_results,
        "total_pages": total_pages,
        "items_list": df_list,
    }


# ------------------------------------------------------------------------------------------------
# Functions for task 4
# ------------------------------------------------------------------------------------------------
def otp_generator():
    return IDGen().otp_gen()


def password_hasher(password: str):
    return pbkdf2_sha256.hash(password)


def send_email_otp(email: str, otp: str):
    api_key = os.getenv("API_KEY")
    mailer = emails.NewEmail(api_key)
    mail_body = {}
    name = email.split("@")[0]
    mail_from = {
        "name": "No Reply",
        "email": os.getenv("EMAIL"),
    }

    recipients = [
        {
            "name": name,
            "email": email,
        }
    ]

    html = f"""
            <!DOCTYPE html>
            <html>
            <body>

            <p>Hello <strong>{name}!</strong></p>
            <p>Kindly find your OTP below to activate your account:</p>
            <h2>{otp}</h2>

            </body>
            </html>
    """

    mailer.set_mail_from(mail_from, mail_body)
    mailer.set_mail_to(recipients, mail_body)
    mailer.set_subject("Activate your account", mail_body)
    mailer.set_html_content(html, mail_body)

    # using print() will also return status code and data
    mailer.send(mail_body)
