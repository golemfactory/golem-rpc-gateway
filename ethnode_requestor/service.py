import asyncio
from datetime import datetime, timezone, timedelta
import colors
from dataclasses import dataclass
import json
import random
import requests
import string
from typing import Optional, List
import uuid

from yapapi.props import constraint, inf
from yapapi.payload import Payload
from yapapi.services import Service, ServiceState

from chain_check import get_short_block_info
from strategy import BadNodeFilter
from time_range import NodeRunningTimeRange


@dataclass
class EthnodePayload(Payload):
    runtime: str = constraint(inf.INF_RUNTIME_NAME)


class Ethnode(Service):
    uuid: str
    username: str
    password: str
    failed: bool = False
    stopped: bool = False
    addresses: List[str]
    _node_running_time_range: NodeRunningTimeRange
    node_expiry: datetime

    @staticmethod
    def generate_username() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def generate_password(length: int) -> str:
        return "".join([random.choice(string.ascii_letters + string.digits) for _ in range(length)])

    def __init__(
            self,
            node_running_time_range: NodeRunningTimeRange,
            username: Optional[str] = None,
            password: Optional[str] = None,
    ):
        super().__init__()
        self.uuid = str(uuid.uuid4())
        self.username = username or self.generate_username()
        self.password = password or self.generate_password(16)
        self.addresses = list()
        self._node_running_time_range = node_running_time_range
        self.set_expiry()

    def set_expiry(self):
        self.node_expiry = self._node_running_time_range.get_expiry()

    def fail(self, blacklist_node: bool = True):
        if blacklist_node:
            BadNodeFilter.blacklist_node(self.provider_id)
        self.failed = True

    async def start(self):
        if self.stopped:
            return

        async for s in super().start():
            yield s

        script = self._ctx.new_script()

        user_future = script.run("user", "add", self.username, self.password)
        service_future = script.run("service", "info")

        yield script

        try:
            user = json.loads((await user_future).stdout)
            assert "createdAt" in user, colors.red("Could not create a user")
            service = json.loads((await service_future).stdout)
        except Exception as e:
            print(
                colors.red(f"{type(e).__name__ + ': ' + str(e)}, blacklisting {self.provider_name}")
            )
            self.fail()
            return

        for name in service["serverName"]:
            for port in service["portHttp"]:
                url = f"http://{self.username}:{self.password}@{name}:{port}/"
                try:
                    await get_short_block_info(url)
                    self.addresses.append(url)
                except requests.ConnectionError as conn_err:
                    print("Error when connecting to service: " + str(conn_err))
                    # print(colors.red(f"Connection error: {url}"))
                    pass
                except Exception as other_ex:
                    print("Other error when connecting to service: " + str(other_ex))
                    pass

        if not self.addresses:
            print(colors.red(f"No suitable addresses found, blacklisting {self.provider_name}"))
            self.fail()
            return

        addr_str = "\n".join(self.addresses)
        print(f"Good addresses: \n{colors.green(addr_str)}\non {self.provider_name}")

    @property
    def is_ready(self) -> bool:
        return self.state == ServiceState.running and not self.failed

    @property
    def is_expired(self) -> bool:
        return self.node_expiry < datetime.now(timezone.utc)

    async def run(self):
        while not self.stopped and not self.failed and not self.is_expired:
            await asyncio.sleep(1)

        return
        yield

    def stop(self):
        self.stopped = True

    async def reset(self):
        if self.failed:
            print(colors.red(f"Activity failed: {self}, restarting..."))
        elif self.is_expired:
            print(colors.red(f"Node expired: {self}, restarting..."))

        self.set_expiry()
        self._ctx = None
        self.failed = False
        self.addresses = list()

    def to_dict(self):
        cv_inst = {}
        cv_inst["uuid"] = self.uuid
        cv_inst["addresses"] = self.addresses
        cv_inst["username"] = self.username
        cv_inst["is_ready"] = self.is_ready
        cv_inst["state"] = self.state.identifier
        cv_inst["node_expiry"] = self.node_expiry.strftime("%Y-%m-%d_%H:%M:%S")
        today = datetime.now(timezone.utc)
        cv_inst["expires_in_secs"] = (self.node_expiry - today).total_seconds()
        cv_inst["provider_id"] = self.provider_id
        cv_inst["provider_name"] = self.provider_name
        cv_inst["stopped"] = self.stopped
        return cv_inst
