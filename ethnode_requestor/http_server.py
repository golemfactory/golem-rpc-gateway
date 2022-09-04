import json

from aiohttp import web
from sqlalchemy import func
from sqlalchemy.orm import Session

from db import db_engine
from model import AppInfo, SerializationMode, LocalJSONEncoder

routes = web.RouteTableDef()
quart_app = web.Application()


@routes.get("/app/current")
async def test(request):
    with Session(db_engine) as session:
        res = session.query(AppInfo).order_by(AppInfo.id.desc()).first()
    return web.Response(text=json.dumps(res, cls=LocalJSONEncoder, mode=SerializationMode.FULL))


@routes.get("/test")
async def test(request):
    return web.Response(text="whatever")
