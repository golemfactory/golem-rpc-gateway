import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from dataclasses_json import dataclass_json
from enum import Enum


class RequestType(Enum):
    Succeeded = 1
    Backup = 2
    Failed = 3


@dataclass_json
@dataclass
class ClientNetworkInfo:
    request_count: int = field(default=0)
    request_failed_count: int = field(default=0)
    request_backup_count: int = field(default=0)


@dataclass_json
@dataclass
class ClientInfo:
    api_key: str
    networks: dict = field(default_factory=dict)

    def add_request(self, network_name, request_type):
        if network_name not in self.networks:
            cl_info = ClientNetworkInfo()
            self.networks[network_name] = cl_info
        else:
            cl_info = self.networks[network_name]

        if request_type == RequestType.Succeeded:
            cl_info.request_count += 1
        elif request_type == RequestType.Failed:
            cl_info.request_failed_count += 1
        elif request_type == RequestType.Backup:
            cl_info.request_backup_count += 1
        else:
            raise Exception(f"Unknown request type: {request_type}")


@dataclass_json
@dataclass
class ClientCollection:
    clients: dict = field(default_factory=dict)

    def add_client(self, api_key: str):
        if api_key not in self.clients:
            self.clients[api_key] = ClientInfo(api_key)
        else:
            raise Exception(f"Client with api key {api_key} already exists")

    def get_client(self, api_key: str):
        return self.clients.get(api_key)



if __name__ == "__main__":
    c = ClientInfo(networks={})
    c.networks["polygon"] = ClientNetworkInfo(request_count=10, request_failed_count=2, request_backup_count=3)

    print(c.to_json())
