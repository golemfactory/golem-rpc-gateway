import json

from sqlalchemy.future import select

import db
import model
import asyncio


async def list_all_instances():
    async with db.async_session() as session:
        result = await session.execute(
            select(model.ProviderInstance)
            .filter(model.ProviderInstance.status == "running"))

        return result.scalars().all()


async def main():
    res = await list_all_instances()
    print(json.dumps(res, cls=model.LocalJSONEncoder, indent=4, mode=model.SerializationMode.FULL))


if __name__ == "__main__":
    asyncio.run(main())



