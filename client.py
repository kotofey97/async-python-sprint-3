import asyncio

from aioconsole import ainput

from log_config import get_logger
from setting import HOST, PORT, MAX_BYTES

logger = get_logger(__name__)


class Client:
    def __init__(self, server_host=HOST, server_port=PORT):
        self.server_host = server_host
        self.server_port = server_port

    async def client_connection(self) -> None:
        self.reader, self.writer = await asyncio.open_connection(
            self.server_host, self.server_port)
        await asyncio.gather(
            self.send_to_server(),
            self.receive_messages()
        )

    async def receive_messages(self):
        server_message = None
        while server_message != "quit":
            server_message = await self.get_from_server()
            await asyncio.sleep(0.1)
            print(f"{server_message}")

    async def get_from_server(self) -> str:
        return (await self.reader.read(MAX_BYTES)).decode("utf8")

    async def send_to_server(self) -> None:
        while True:
            response = await ainput(">>> ")
            self.writer.write(response.encode('utf-8'))
            await self.writer.drain()


if __name__ == '__main__':
    client = Client()
    asyncio.run(client.client_connection())
