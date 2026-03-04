from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from database import get_latest, init_db

app = FastAPI()

templates = Jinja2Templates(directory="templates")

init_db()


@app.get("/")
def home(request: Request):

    data = get_latest()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "data": data
        }
    )