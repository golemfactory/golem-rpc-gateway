import json
import logging

from aiohttp import web
from sqlalchemy import func
from sqlalchemy.orm import Session

from chain_check import get_short_block_info
from db import db_engine
from model import AppInfo, SerializationMode, LocalJSONEncoder, ProviderInstance
from service import Ethnode

routes = web.RouteTableDef()
quart_app = web.Application()


@routes.get("/app/db")
async def test(request):
    res = db_engine.name
    return web.Response(text=json.dumps(res, cls=LocalJSONEncoder, mode=SerializationMode.FULL),
                        content_type="application/json")


@routes.get("/app/current")
async def test(request):
    response = {}
    response["db_engine"] = db_engine.name
    app_info = None
    try:
        with Session(db_engine) as session:
            app_info = session.query(AppInfo).order_by(AppInfo.id.desc()).first()
    except Exception as ex:
        logging.error("Error getting app info: " + str(ex))

    response["app_info"] = app_info

    return web.Response(text=json.dumps(response, cls=LocalJSONEncoder, mode=SerializationMode.FULL),
                        content_type="application/json")


@routes.get("/test")
async def test(request):
    return web.Response(text="whatever")
