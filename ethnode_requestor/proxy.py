import asyncio
import json

import aiohttp
from aiohttp import web
from datetime import datetime, timedelta, timezone
import random

from yapapi.services import Cluster

from http_server import quart_app, routes
from service import Ethnode
from client_info import ClientInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

INSTANCES_RETRY_INTERVAL_SEC = 1
INSTANCES_RETRY_TIMEOUT_SEC = 30

MAX_RETRIES = 3

from logging import getLogger

logger = getLogger("yapapi...ethnode_requestor.proxy")

allowed_endpoints = ["rinkeby", "polygon"]


env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape()
)


class EthnodeProxy:
    def __init__(self, cluster: Cluster[Ethnode], port: int, proxy_only_mode):
        self._request_count = 0
        self._request_lock = asyncio.Lock()
        self._cluster = cluster
        self._port = port
        self._app_task: asyncio.Task = None
        self._proxy_only_mode = proxy_only_mode
        # self._site: Optional[web.TCPSite] = None
        self._clients = dict()

        api_key = "MAaCpE421MddDmzMLcAp"
        self._clients[api_key] = ClientInfo(api_key)

    async def get_instance(self) -> Ethnode:
        timeout = datetime.now(timezone.utc) + timedelta(seconds=INSTANCES_RETRY_TIMEOUT_SEC)
        while datetime.now(timezone.utc) < timeout:
            instances = [i for i in self._cluster.instances if i.is_ready]
            if instances:
                async with self._request_lock:
                    self._request_count += 1
                    return instances[self._request_count % len(instances)]

            logger.warning("Waiting for any available instances...")
            await asyncio.sleep(INSTANCES_RETRY_INTERVAL_SEC)

        raise TimeoutError(
            f"Could not find an available instance after {INSTANCES_RETRY_TIMEOUT_SEC}s."
        )

    async def _proxy_rpc(self, request: web.Request) -> web.Response:
        token = request.match_info["token"]
        network = request.match_info["network"]
        logger.debug(
            f"Received a local HTTP request: {request.method} {request.path_qs}, "
            f"headers={request.headers}"
        )
        logger.warning(
            f"Request: network={network} token={token}"
        )
        if not network in allowed_endpoints:
            return web.Response(text="network should be one of " + str(allowed_endpoints))

        client = self._clients.get(token)


        if not self._proxy_only_mode:
            if client:
                client.add_request(network)
                retry = 0
                while retry <= MAX_RETRIES:
                    instance = None if self._proxy_only_mode else await self.get_instance()

                    try:
                        return await self._handle_request(instance, request)
                    except aiohttp.ClientConnectionError as e:
                        retry += 1
                        logger.warning(
                            "Retrying %s / %s, because of %s: %s on",
                            retry,
                            MAX_RETRIES,
                            type(e).__name__,
                            e,
                        )
                        # fail the provider and restart the instance on a connection failure
                        instance.fail(blacklist_node=False)
            else:
                return web.Response(text="client not found, probably wrong token")
        else:
            if client:
                client.add_request(network)
                retry = 0
                while retry <= MAX_RETRIES:

                    try:
                        if network == "polygon":
                            return await self._handle_request2("https://bor.golem.network", request)
                        elif network == "rinkeby":
                            return await self._handle_request2("http://1.geth.testnet.golem.network:55555", request)
                        else:
                            raise Exception("unknown network")

                    except aiohttp.ClientConnectionError as e:
                        retry += 1
                        logger.warning(
                            "Retrying %s / %s, because of %s: %s on",
                            retry,
                            MAX_RETRIES,
                            type(e).__name__,
                            e,
                        )
                        # fail the provider and restart the instance on a connection failure

                return web.Response(text="Cannot connect to endpoint")
            else:
                return web.Response(text="client not found, probably wrong token")

    @staticmethod
    async def _handle_request2(address: str, request: web.Request) -> web.Response:
        logger.debug(f"Using: {address}")
        async with aiohttp.ClientSession() as session:
            async with session.request(
                    request.method, address, headers=request.headers, data=request.content
            ) as resp:
                headers = {
                    k: v
                    for k, v in resp.headers.items()
                    if k
                       not in (
                           "Content-Encoding",
                           "Content-Length",
                           "Transfer-Encoding",
                       )
                }
                response_kwargs = {
                    "reason": resp.reason,
                    "status": resp.status,
                    "body": await resp.read(),
                    "headers": headers,
                }
                logger.debug(f"response: {response_kwargs}")
                return web.Response(**response_kwargs)

    @staticmethod
    async def _handle_request(instance: Ethnode, request: web.Request) -> web.Response:
        address = instance.addresses[random.randint(0, len(instance.addresses) - 1)]
        logger.debug(f"Using: {instance} / {address}")
        async with aiohttp.ClientSession() as session:
            async with session.request(
                request.method, address, headers=request.headers, data=request.content
            ) as resp:
                headers = {
                    k: v
                    for k, v in resp.headers.items()
                    if k
                    not in (
                        "Content-Encoding",
                        "Content-Length",
                        "Transfer-Encoding",
                    )
                }
                response_kwargs = {
                    "reason": resp.reason,
                    "status": resp.status,
                    "body": await resp.read(),
                    "headers": headers,
                }
                logger.debug(f"response: {response_kwargs}")
                return web.Response(**response_kwargs)

    async def _hello(self, request: web.Request) -> web.Response:
        # test response
        return web.Response(text="whatever" + str(self._clients))

    async def _clients_endpoint(self, request: web.Request) -> web.Response:
        # test response
        return web.Response(text=json.dumps(self._clients), content_type="application/json")

    async def _instances_endpoint(self, request: web.Request) -> web.Response:
        # test response
        return web.Response(text=json.dumps(self.get_cluster_info()), content_type="application/json")

    def get_cluster_info(self):
        cv = cluster_view = {}
        if self._cluster:
            cv["exists"] = True
            cv["runtime"] = self._cluster.payload.runtime
            cv["instances"] = {}
            for idx, instance in enumerate(self._cluster.instances):
                cv["instances"][instance.uuid] = instance.to_dict()
        else:
            cv["exists"] = False
        return cv


    async def _main_endpoint(self, request: web.Request) -> web.Response:
        t = "empty"
        template = env.get_template("index.html")
        page = template.render(hello="template_test")
        return web.Response(text=page, content_type="text/html")

    async def run(self):
        """
        run a local HTTP server, listening on the specified port and passing subsequent requests to
        the :meth:`~HttpProxyService.handle_request` of the specified cluster in a round-robin
        fashion
        """

        quart_app.router.add_route("*", "/", handler=self._main_endpoint)
        quart_app.router.add_route("*", "/rpc/{network}/{token}", handler=self._proxy_rpc)
        quart_app.router.add_route("*", "/hello", handler=self._hello)
        quart_app.router.add_route("*", "/clients", handler=self._clients_endpoint)
        quart_app.router.add_route("*", "/instances", handler=self._instances_endpoint)
        quart_app.add_routes(routes)
        self._app_task = asyncio.create_task(
            web._run_app(quart_app, port=self._port, handle_signals=False, print=None)  # noqa
        )

        # runner = web.ServerRunner(web.Server(self._request_handler))  # type: ignore
        # await runner.setup()
        # self._site = web.TCPSite(runner, port=self._port)
        # await self._site.start()

    async def stop(self):
        assert self._app_task, "Not started, call `run` first."
        self._app_task.cancel()
        await asyncio.gather(*[self._app_task])
