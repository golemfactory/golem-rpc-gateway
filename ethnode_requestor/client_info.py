import json

d
class ClientNetworkInfo(dict):
    def __init__(
            self
    ):
        dict.__init__(self, request_count=0, request_failed_count=0, request_backup_count=0)

    def add_request(self):
        self["request_count"] = self["request_count"] + 1

    def add_failed_request(self):
        self["request_failed_count"] = self["request_failed_count"] + 1

    def add_backup_request(self):
        self["request_backup_count"] = self["request_backup_count"] + 1

class ClientInfo(dict):
    def __init__(
            self,
            api_key: str
    ):
        dict.__init__(self, api_key=api_key, networks=dict())

    def add_request(self, network_name):
        if network_name not in self["networks"]:
            self["networks"][network_name] = ClientNetworkInfo()

        self["networks"][network_name].add_request()

    def add_failed_request(self, network_name):
        if network_name not in self["networks"]:
            self["networks"][network_name] = ClientNetworkInfo()

        self["networks"][network_name].add_failed_request()

    def add_backup_request(self, network_name):
        if network_name not in self["networks"]:
            self["networks"][network_name] = ClientNetworkInfo()

        self["networks"][network_name].add_backup_request()
