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
    time_buckets_seconds: dict = field(default_factory=dict)
    time_buckets_minutes: dict = field(default_factory=dict)
    time_buckets_hours: dict = field(default_factory=dict)
    time_buckets_days: dict = field(default_factory=dict)

    # @todo do not cleanup every call, it's inefficient
    # move it to some kind of watcher or add time difference to the cleanup
    def cleanup_history(self, time_buckets, last_valid_time):
        keys_to_delete = []
        for network_name in time_buckets:
            time_bucket = time_buckets[network_name]
            for time_str in time_bucket:
                if time_str < last_valid_time:
                    keys_to_delete.append(time_str)

        for key in keys_to_delete:
            del time_bucket[key]

    def get_or_add_time_bucket(self, time_buckets, network_name, time_str: datetime):
        if network_name not in time_buckets:
            time_buckets[network_name] = {}
        time_bucket = time_buckets[network_name]

        if time_str not in time_bucket:
            time_bucket[time_str] = ClientNetworkInfo()
        return time_bucket[time_str]

    def add_request(self, network_name, request_type):
        current_time = datetime.now(timezone.utc)

        day_format = "%Y-%m-%dT00:00:00"
        hour_format = "%Y-%m-%dT%H:00:00"
        minute_format = "%Y-%m-%dT%H:%M:00"
        second_format = "%Y-%m-%dT%H:%M:%S"

        SECONDS_BEFORE = 600
        MINUTES_BEFORE = 600
        HOURS_BEFORE = 600
        DAYS_BEFORE = 600

        self.cleanup_history(self.time_buckets_seconds, (current_time - timedelta(seconds=SECONDS_BEFORE)).strftime(second_format))
        self.cleanup_history(self.time_buckets_minutes, (current_time - timedelta(minutes=MINUTES_BEFORE)).strftime(minute_format))
        self.cleanup_history(self.time_buckets_hours, (current_time - timedelta(hours=HOURS_BEFORE)).strftime(hour_format))
        self.cleanup_history(self.time_buckets_days, (current_time - timedelta(days=DAYS_BEFORE)).strftime(day_format))

        days = current_time.strftime(day_format)
        hours = current_time.strftime(hour_format)
        minutes = current_time.strftime(minute_format)
        seconds = current_time.strftime(second_format)

        cl_infos = []
        if network_name not in self.networks:
            cl_info = ClientNetworkInfo()
            self.networks[network_name] = cl_info
        else:
            cl_info = self.networks[network_name]

        cl_infos.append(cl_info)

        cl_infos.append(self.get_or_add_time_bucket(self.time_buckets_seconds, network_name, seconds))
        cl_infos.append(self.get_or_add_time_bucket(self.time_buckets_minutes, network_name, minutes))
        cl_infos.append(self.get_or_add_time_bucket(self.time_buckets_hours, network_name, hours))
        cl_infos.append(self.get_or_add_time_bucket(self.time_buckets_days, network_name, days))

        for cl_info in cl_infos:
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
