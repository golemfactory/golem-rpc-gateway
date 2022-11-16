import os
import requests
import json
import logging

import aiohttp
from aiohttp import web
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.orm import Session

import db
import model
from chain_check import get_short_block_info
from db import db_engine
from db_tools import list_all_instances
from model import AppInfo, SerializationMode, LocalJSONEncoder, ProviderInstance
from service import Ethnode

routes = web.RouteTableDef()
aiohttp_app = web.Application()


@routes.get("/app/db/{admin_token}")
async def test(request):
    if request.match_info["admin_token"] != os.getenv("ADMIN_TOKEN", "admin"):
        return web.Response(text="Wrong admin token")
    res = db_engine.name
    return web.Response(text=json.dumps(res, cls=LocalJSONEncoder, mode=SerializationMode.FULL),
                        content_type="application/json")


@routes.get("/app/current/{admin_token}")
async def test(request):
    if request.match_info["admin_token"] != os.getenv("ADMIN_TOKEN", "admin"):
        return web.Response(text="Wrong admin token")
    response = {}
    response["db_engine"] = db_engine.name
    app_info = None
    try:
        async with db.async_session() as session:
            result = await session.execute(
                select(model.AppInfo)
                    .order_by(model.AppInfo.id.desc()))

            app_info = result.scalars().first()
    except Exception as ex:
        logging.error("Error getting app info: " + str(ex))

    response["app_info"] = app_info

    return web.Response(text=json.dumps(response, cls=LocalJSONEncoder, mode=SerializationMode.FULL),
                        content_type="application/json")


@routes.get("/providers/{admin_token}")
async def test(request):
    if request.match_info["admin_token"] != os.getenv("ADMIN_TOKEN", "admin"):
        return web.Response(text="Wrong admin token")
    response = {"app_info": await list_all_instances()}

    return web.Response(text=json.dumps(response, cls=LocalJSONEncoder, mode=SerializationMode.FULL),
                        content_type="application/json")


@routes.get("/yagna/{admin_token}")
async def test(request):
    if request.match_info["admin_token"] != os.getenv("ADMIN_TOKEN", "admin"):
        return web.Response(text="Wrong admin token")
    # todo: probably cache this request
    url = os.getenv("YAGNA_MONITOR_URL") or 'http://127.0.0.1:3333'
    resp = requests.get(url=url)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=2) as result:
            if result.status == 200:
                return web.Response(text=await result.text(), content_type="application/json")

    return web.Response(text="Failed to get yagna info")


@routes.get("/test_client_endpoint/{admin_token}")
async def test(request):
    if request.match_info["admin_token"] != os.getenv("ADMIN_TOKEN", "admin"):
        return web.Response(text="Wrong admin token")
    base_url = os.getenv("GATEWAY_BASE_URL") or 'http://127.0.0.1:8545'
    allowed_endpoint = os.getenv("ALLOWED_ENDPOINT") or 'mumbai'

    return web.Response(text=f"{base_url}/rpc/{allowed_endpoint}/MAaCpE421MddDmzMLcAp")

@routes.get("/test")
async def test(request):
    return web.Response(text="whatever")
