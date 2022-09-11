import aiohttp
import requests
import datetime

async def get_chain_id(url):
    post_data = {
        "jsonrpc": "2.0",
        "method": "web3_clientVersion",
        "params": [],
        "id": 1
    }
    # todo: change to async api
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=post_data, timeout=2) as result:
            if result.status == 200:
                block = await result.json()

    return block["result"]


async def get_block_info(url):
    post_data = {
        "jsonrpc": "2.0",
        "method": "eth_getBlockByNumber",
        "params": ["latest", False],
        "id": 1
    }
    # todo: change to async api
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=post_data, timeout=2) as result:
            if result.status == 200:
                block = await result.json()

    return block["result"]


async def get_short_block_info(url):
    chain_id = await get_chain_id(url)

    block = await get_block_info(url)
    block_short_info = {
        "timestamp": block["timestamp"],
        "number": block["number"]
        }
    return block_short_info
