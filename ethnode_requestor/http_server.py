from aiohttp import web

routes = web.RouteTableDef()
app = web.Application()

import proxy



@routes.get("/test")
async def test(request):
    return web.Response(text="whatever")
