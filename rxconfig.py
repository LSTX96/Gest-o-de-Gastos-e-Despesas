import os
import reflex as rx
from dotenv import load_dotenv

load_dotenv()

config = rx.Config(
    app_name="rps_passivo",
    db_url=os.environ.get("DATABASE_URL"),
)