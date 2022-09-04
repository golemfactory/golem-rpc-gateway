import asyncio
import logging

from sqlalchemy.orm import Session

from chain_check import get_short_block_info
from db import db_engine
from model import ProviderInstance
from multiprocessing import Process

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def test_connections():
    with Session(db_engine) as session:
        instances = session.query(ProviderInstance).filter(ProviderInstance.status == "running").all()

        for instance in instances:
            try:
                addresses = instance.addresses.split(";")
                for address in addresses:
                    info = await get_short_block_info(address)
                    logger.debug(f"Got info for {address}: {info}")
            except Exception as e:
                logger.error(f"Error while testing connection to {instance.provider_name} at {address}: {e}")
                instance.status = "failed"
                session.commit()


async def test_connections_loop():
    while True:
        try:
            await test_connections()
        except Exception as e:
            print(e)
        finally:
            await asyncio.sleep(10)
