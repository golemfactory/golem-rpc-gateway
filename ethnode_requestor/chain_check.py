import requests
import datetime

async def get_block_info(url):
    post_data = {
        "jsonrpc": "2.0",
        "method": "eth_getBlockByNumber",
        "params": ["latest", False],
        "id": 1
    }
    # todo: change to async api
    result = requests.post(url, json=post_data)
    if result.status_code == 200:
        block = result.json()

    return block["result"]


async def get_short_block_info(url):
    block = await get_block_info(url)
    block_short_info = {
        "timestamp": block["timestamp"],
        "number": block["number"]
        }
    return block_short_info
