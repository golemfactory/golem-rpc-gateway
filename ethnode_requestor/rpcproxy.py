from datetime import datetime
import aiohttp
import logging
import json
import time
import asyncio
from aiohttp import ClientTimeout

from model import DaoRequest


class RpcProxyException(Exception):
    pass


PROXY_TIMEOUT = 15


class RpcProxy:
    @staticmethod
    async def proxy_call(address, data):
        r = DaoRequest()
        r.status = "started"
        r.address = address
        r.code = 0
        r.date = datetime.utcnow()
        try:
            r.payload = data.decode()
            jsonrpc = json.loads(r.payload)
        except Exception as ex:
            r.input_error = f"Failed to parse json {ex}"
            return r
        try:
            r.status = "sending"

            def check_rpc_entry(entr):
                if "jsonrpc" not in entr:
                    raise RpcProxyException("No jsonrpc field")
                if "method" not in entr:
                    raise RpcProxyException("No method field")
                if "params" not in entr:
                    raise RpcProxyException("No params field")
                if "id" not in entr:
                    raise RpcProxyException("No id field")

            if isinstance(jsonrpc, list):
                for entry in jsonrpc:
                    check_rpc_entry(entry)
            elif isinstance(jsonrpc, dict):
                check_rpc_entry(jsonrpc)
            else:
                raise RpcProxyException("Invalid jsonrpc request")

            async with aiohttp.ClientSession(timeout=ClientTimeout(PROXY_TIMEOUT)) as session:
                headers = {"Content-Type": "application/json"}
                request_time_start = time.time()
                async with session.post(address, headers=headers, json=jsonrpc) as resp:
                    request_time_end = time.time()
                    r.response_time = request_time_end - request_time_start
                    r.status = "received"
                    response_binary_data = await resp.read()
                    r.status = "read"
                    r.response = response_binary_data.decode()
                    r.code = resp.status
                    if resp.status == 504:
                        r.error = "External server timed out"
                        r.timeout = True
                        return r
                    _rpc_result = json.loads(r.response)
                    r.status = "parsed"
                    # todo further parsing
                    r.result_valid = True
                    r.status = "ok"

        except RpcProxyException as ex:
            r.input_error = f"{ex}"
            r.error = f"{ex}"
        except asyncio.TimeoutError as ex:
            r.timeout = True
            r.error = "Internal timeout"
        except Exception as ex:
            r.error = f"Unknown error: {ex}"

        return r
