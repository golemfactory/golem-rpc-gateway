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

from strategy import BadNodeFilter
from time_range import NodeRunningTimeRange


@dataclass
class EthnodePayload(Payload):
    runtime: str = constraint(inf.INF_RUNTIME_NAME)


class Ethnode(Service):
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
                    result = requests.get(url)
                    if result.status_code == 200:
                        self.addresses.append(url)
                except requests.ConnectionError:
                    # print(colors.red(f"Connection error: {url}"))
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
