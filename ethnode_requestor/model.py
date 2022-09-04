from datetime import datetime
import json
from enum import Enum

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import declarative_base


BaseClass = declarative_base()


class SerializationMode(Enum):
    FULL = 1
    MINIMAL = 2


class AppInfo(BaseClass):
    __tablename__ = "app"
    id = Column(Integer, primary_key=True)
    args = Column(String, nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    version = Column(String,  nullable=False, default="dev")

    def to_json(self, mode=SerializationMode.FULL):
        if mode == SerializationMode.FULL:
            return {c.name: getattr(self, c.name) for c in self.__table__.columns}
        elif mode == SerializationMode.MINIMAL:
            return {
                "version": self.version
            }
        else:
            raise Exception(f"Unknown mode {mode}")


class EthnodeInstance(BaseClass):
    __tablename__ = "ethnode"
    id = Column(Integer, primary_key=True)
    app = Column(Integer, ForeignKey("app.id"), nullable=False)
    uuid = Column(String, nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    username = Column(String)


class ProviderInstance(BaseClass):
    __tablename__ = "provider"
    id = Column(Integer, primary_key=True)
    status = Column(String, default="unknown")
    ethnode = Column(Integer, ForeignKey("ethnode.id"), nullable=False)
    addresses = Column(String)
    node_expiry = Column(DateTime)
    provider_id = Column(String)
    provider_name = Column(String)


# class PathInfoEntry(BaseClass):
#     __tablename__ = "path_info_entry"
#     id = Column(Integer, primary_key=True)
#     path_info = Column(Integer, ForeignKey("path_info.id"), nullable=False)
#     files_checked = Column(Integer, nullable=False)
#     files_failed = Column(Integer, nullable=False)
#     total_size = Column(Integer, nullable=False)
#
#     def to_json(self, mode=SerializationMode.FULL):
#         if mode == SerializationMode.FULL:
#             return {c.name: getattr(self, c.name) for c in self.__table__.columns}
#         elif mode == SerializationMode.MINIMAL:
#             return {
#                 "total_size": self.total_size
#             }
#         else:
#             raise Exception(f"Unknown mode {mode}")


class LocalJSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        self._mode = kwargs.pop('mode') if 'mode' in kwargs else None
        super().__init__(*args, **kwargs)

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, AppInfo):
            return obj.to_json(mode=self._mode)
        return super().default(obj)


if __name__ == "__main__":
    pass
    # pi1 = PathInfoEntry(path_info=1, files_checked=2, files_failed=3, total_size=4)
    # pi2 = PathInfoEntry(path_info=10, files_checked=11, files_failed=12, total_size=13)

    # print(json.dumps([pi1, pi2], cls=LocalJSONEncoder, indent=4, mode=SerializationMode.MINIMAL))
    # print(json.dumps([pi1, pi2], cls=LocalJSONEncoder, indent=4, mode=SerializationMode.FULL))

