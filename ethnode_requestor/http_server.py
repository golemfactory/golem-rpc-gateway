from aiohttp import web

routes = web.RouteTableDef()
quart_app = web.Application()




@routes.get("/test")
async def test(request):
    return web.Response(text="whatever")
