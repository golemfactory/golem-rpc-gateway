import os
import asyncio
import json

import aiohttp
from aiohttp import web
from datetime import datetime, timedelta, timezone
import random
import typing

from yapapi.services import Cluster
from yapapi.agreements_pool import AgreementsPool

from chain_check import get_short_block_info
from http_server import quart_app, routes
from service import Ethnode

from jinja2 import Environment, FileSystemLoader, select_autoescape
from client_info import ClientInfo, ClientCollection, RequestType

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
    def __init__(self, port: int, proxy_only_mode):
        self._request_count = 0
        self._request_lock = asyncio.Lock()
        self._cluster: Cluster = None
        self._port = port
        self._app_task: asyncio.Task = None
        self._proxy_only_mode = proxy_only_mode
        # self._site: Optional[web.TCPSite] = None
        self._clients = ClientCollection()

        api_key = "MAaCpE421MddDmzMLcAp"
        self._clients.add_client(api_key)

    def set_cluster(self, cluster: Cluster[Ethnode]):
        self._cluster = cluster

    async def get_instance(self) -> Ethnode:
        instances = [i for i in self._cluster.instances if i.is_ready]
        if not instances:
            return None

        async with self._request_lock:
            self._request_count += 1
            return instances[self._request_count % len(instances)]

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

        client = self._clients.get_client(token)

        if not self._proxy_only_mode:
            if client:
                retry = 0
                while retry <= MAX_RETRIES:
                    instance = None if self._proxy_only_mode else await self.get_instance()
                    if not instance:
                        try:
                            if network == "polygon":
                                res = await self._handle_request2("https://bor.golem.network", request)

                            elif network == "rinkeby":
                                res = await self._handle_request2("http://1.geth.testnet.golem.network:55555", request)
                            else:
                                raise Exception("unknown network")

                            client.add_request(network, RequestType.Backup)
                            return res
                        except Exception as ex:
                            logger.error(f"Failed to proxy request {ex}")
                            client.add_request(network, RequestType.Failed)
                    try:
                        res = await self._handle_request(instance, request)
                        client.add_request(network, RequestType.Succeeded)
                        return res
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
        return web.Response(text=self._clients.to_json(), content_type="application/json")

    async def _instances_endpoint(self, request: web.Request) -> web.Response:
        # test response
        return web.Response(text=json.dumps(await self.get_cluster_info()), content_type="application/json")

    async def _offers_endpoint(self, request: web.Request) -> web.Response:

        def convert_timestamps(d: dict):
            for k, v in d.items():
                if isinstance(v, datetime):
                    d[k] = v.timestamp()
                elif isinstance(v, dict):
                    convert_timestamps(v)
            return d

        agreements_pool: AgreementsPool = self._cluster.service_runner._job.agreements_pool  # noqa

        output = {
            "offers": [
                convert_timestamps(o.proposal._proposal.proposal.to_dict())  # noqa
                for o in agreements_pool._offer_buffer.values()  # noqa
            ],
            "agreements": [
                convert_timestamps(a.agreement_details.raw_details.to_dict())  # noqa
                for a in agreements_pool._agreements.values()  # noqa
            ]
        }

        return web.Response(text=json.dumps(output), content_type="application/json")

    async def get_cluster_info(self):
        cv = cluster_view = {}
        if self._cluster:
            cv["exists"] = True
            cv["runtime"] = self._cluster.payload.runtime
            cv["instances"] = {}
            for idx, instance in enumerate(self._cluster.instances):
                cv["instances"][instance.uuid] = instance.to_dict()
                inst = cv["instances"][instance.uuid]

                inst["block_info"] = {}
                try:
                    if len(instance.addresses) > 0:
                        address = instance.addresses[0]
                        if address:
                            inst["block_info"] = await get_short_block_info(address)
                except Exception as ex:
                    inst["block_info"]["error"] = "Failed to obtain block info"
                    logger.warning(f"Failed to obtain block info {ex}")
        else:
            cv["exists"] = False
        return cv


    async def _main_endpoint(self, request: web.Request) -> web.Response:
        t = "empty"
        template = env.get_template("index.html")
        base_url = os.getenv("GATEWAY_BASE_URL") or 'http://127.0.0.1:8545'
        page = template.render(hello="template_test", base_url=base_url)
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
        quart_app.router.add_route("*", "/offers", handler=self._offers_endpoint)
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
