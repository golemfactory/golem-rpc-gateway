import os
import asyncio
import json
import sys
import traceback

import aiohttp
from aiohttp import web
from datetime import datetime, timedelta, timezone
import random
import typing

from yapapi.services import Cluster
from yapapi.agreements_pool import AgreementsPool

from chain_check import get_short_block_info
from db_tools import insert_request
from http_server import aiohttp_app, routes
from model import DaoRequest
from rpcproxy import RpcProxy
from service import Ethnode

from jinja2 import Environment, FileSystemLoader, select_autoescape
from client_info import ClientInfo, ClientCollection, RequestType

INSTANCES_RETRY_INTERVAL_SEC = 1
INSTANCES_RETRY_TIMEOUT_SEC = 30

MAX_RETRIES = 3

from logging import getLogger

logger = getLogger("yapapi...ethnode_requestor.proxy")

#allowed_endpoints = ["rinkeby", "polygon", "mumbai"]

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape()
)

allowed_endpoint = os.getenv("ALLOWED_ENDPOINT") or 'mumbai'
polygon_backup_rpc_url = os.getenv("POLYGON_BACKUP_RPC") or "https://bor.golem.network"
mumbai_backup_rpc_url = os.getenv("MUMBAI_BACKUP_RPC") or "https://rpc-mumbai.maticvigil.com"
rinkeby_rpc_url = os.getenv("RINKEBY_BACKUP_RPC") or "http://1.geth.testnet.golem.network:55555"


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
        additional_headers = {"Access-Control-Allow-Origin": "*"}
        try:
            token = request.match_info["token"]
            network = request.match_info["network"]
            logger.debug(
                f"Received a local HTTP request: {request.method} {request.path_qs}, "
                f"headers={request.headers}"
            )
            logger.warning(
                f"Request: network={network} token={token}"
            )
            if network != allowed_endpoint:
                return web.Response(text="Only network supported for now is " + str(network))



            client = self._clients.get_client(token)
            client_id = 1  # todo: fix after adding clients to db

            try:
                data = await request.content.read()
            except Exception as ex:
                logger.warning(f"Error reading request content: {ex}")
                return web.Response(text="Cannot get data from the request", status=400, headers=additional_headers)

            compare_request = None
            if client:
                retry = 0
                for retry in range(MAX_RETRIES):
                    instance = await self.get_instance()
                    if not instance:
                        break

                    provider_id = instance.provider_db_id

                    res = await self._handle_instance_request(instance, data)

                    res.provider_instance = provider_id
                    # todo add client to database
                    res.client_id = client_id
                    res.backup = False


                    # if res.code == 401:
                    #    retry += 1
                    #    logger.warning("Retrying %s / %s, because of 401", retry, MAX_RETRIES)
                    #    instance.fail(blacklist_node=False)
                    #    continue
                    # if res.code >= 400:
                    #    retry += 1
                    #    logger.warning("Retrying %s / %s, because of %s", retry, MAX_RETRIES, res.status)
                    #    instance.fail(blacklist_node=False)
                    #    continue

                    await insert_request(res)
                    if res.timeout:
                        instance.fail(blacklist_node=False)
                        continue

                    if res.input_error:
                        return web.Response(text=res.input_error, status=400, headers=additional_headers)

                    if res.result_valid:
                        compare_request = res
                        client.add_request(network, RequestType.Succeeded)
                        break

                    if res.code > 200:
                        client.add_request(network, RequestType.Failed)
                        instance.fail(blacklist_node=False)

                    # continue trying on other error

                if network == "polygon":
                    res = await self._handle_request(polygon_backup_rpc_url, data)
                elif network == "mumbai":
                    res = await self._handle_request(mumbai_backup_rpc_url, data)
                elif network == "rinkeby":
                    res = await self._handle_request(rinkeby_rpc_url, data)
                else:
                    raise Exception("unknown network")

                # todo add client to database
                res.client_id = client_id
                res.backup = True

                if compare_request:
                    # TODO: compare results
                    if not compare_request.result_valid and not res.result_valid:
                        res.compare_result = "both_failed"
                    elif not compare_request.result_valid and res.result_valid:
                        res.compare_result = "backup_succeeded"
                    elif compare_request.result_valid and not res.result_valid:
                        res.compare_result = "backup_failed"
                    else:
                        try:
                            left = json.loads(compare_request.response)
                            right = json.loads(res.response)
                            if "error" in right and "error" in left:
                                res.compare_result = "both_returned_error"
                            elif "error" in right:
                                res.compare_result = "backup_returned_error"
                            elif "error" in left:
                                res.compare_result = "backup_returned_result"
                            elif left["result"] == right["result"]:
                                res.compare_result = "both_succeeded_same_result"
                            else:
                                res.compare_result = "both_succeeded_different_result"
                        except Exception as _ex:
                            pass
                            res.compare_result = "both_succeeded_comparison_failed"

                if res.input_error:
                    return web.Response(text=res.input_error, status=400, headers=additional_headers)

                if res.timeout:
                    return web.Response(text="Call timed out", status=504, headers=additional_headers)

                await insert_request(res)
                if res.result_valid:
                    client.add_request(network, RequestType.Succeeded)
                    return web.Response(content_type="Application/json", headers=additional_headers, text=res.response)

                client.add_request(network, RequestType.Failed)
                return web.Response(text="Backup request failed with status " + str(res.code), status=400, headers=additional_headers)
            else:
                return web.Response(text="client not found, probably wrong token", headers=additional_headers)
        except Exception as ex:
            logger.error(f"Unrecoverable error {ex}")
            traceback.print_exception(*sys.exc_info())
            return web.Response(text="unrecoverable error", headers=additional_headers)

    async def _handle_instance_request(self, instance: Ethnode, data) -> DaoRequest:
        address = instance.addresses[random.randint(0, len(instance.addresses) - 1)]
        logger.debug(f"Using: {instance} / {address}")
        return await self._handle_request(address, data)

    @staticmethod
    async def _handle_request(address: str, data) -> DaoRequest:
        proxy = RpcProxy()
        r = await proxy.proxy_call(address, data)
        return r

    async def _hello(self, request: web.Request) -> web.Response:
        # test response
        if request.match_info["admin_token"] != os.getenv("ADMIN_TOKEN", "admin"):
            return web.Response(text="Wrong admin token")
        return web.Response(text="whatever" + str(self._clients))

    async def _clients_endpoint(self, request: web.Request) -> web.Response:
        # test response
        if request.match_info["admin_token"] != os.getenv("ADMIN_TOKEN", "admin"):
            return web.Response(text=json.dumps({"token":"invalid"}, content_type="application/json"))
        return web.Response(text=json.dumps({"token":"OK"}, content_type="application/json"))

    async def _instances_endpoint(self, request: web.Request) -> web.Response:
        # test response
        if request.match_info["admin_token"] != os.getenv("ADMIN_TOKEN", "admin"):
            return web.Response(text="Wrong admin token")
        return web.Response(text=json.dumps(await self.get_cluster_info()), content_type="application/json")

    async def _offers_endpoint(self, request: web.Request) -> web.Response:
        if request.match_info["admin_token"] != os.getenv("ADMIN_TOKEN", "admin"):
            return web.Response(text="Wrong admin token")

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
        if request.match_info["admin_token"] != os.getenv("ADMIN_TOKEN", "admin"):
            return web.Response(text="Wrong admin token")
        template = env.get_template("index.html")
        base_url = os.getenv("GATEWAY_BASE_URL") or 'http://127.0.0.1:8545'
        admin_token = os.getenv("ADMIN_TOKEN", "admin")
        page = template.render(hello="template_test", base_url=base_url, admin_token=admin_token)
        return web.Response(text=page, content_type="text/html")

    async def run(self):
        """
        run a local HTTP server, listening on the specified port and passing subsequent requests to
        the :meth:`~HttpProxyService.handle_request` of the specified cluster in a round-robin
        fashion
        """

        aiohttp_app.router.add_route("*", "/info/{admin_token}", handler=self._main_endpoint)
        aiohttp_app.router.add_route("*", "/rpc/{network}/{token}", handler=self._proxy_rpc)
        aiohttp_app.router.add_route("*", "/hello/{admin_token}", handler=self._hello)
        aiohttp_app.router.add_route("*", "/clients/{admin_token}", handler=self._clients_endpoint)
        aiohttp_app.router.add_route("*", "/instances/{admin_token}", handler=self._instances_endpoint)
        aiohttp_app.router.add_route("*", "/offers/{admin_token}", handler=self._offers_endpoint)
        aiohttp_app.add_routes(routes)
        self._app_task = asyncio.create_task(
            web._run_app(aiohttp_app, port=self._port, handle_signals=False, print=None)  # noqa
        )

        # runner = web.ServerRunner(web.Server(self._request_handler))  # type: ignore
        # await runner.setup()
        # self._site = web.TCPSite(runner, port=self._port)
        # await self._site.start()

    async def stop(self):
        assert self._app_task, "Not started, call `run` first."
        self._app_task.cancel()
        await asyncio.gather(*[self._app_task])
