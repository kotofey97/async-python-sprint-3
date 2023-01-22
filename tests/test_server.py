import asyncio
from pytest import raises
from server import Server
from client import Client, Authentication


class TestServer:
    def setup(self) -> None:
        self.server = Server()
        self.client = Client()
        self.user = Authentication('Stream','Writer')

    def test_server_error(self) -> None:
        with raises(Exception):
            server = Server(1,2)
            asyncio.run(server.start_server())

    def test_set_nickname(self):
        self.server.set_nickname(self.user,'/nickname Jo')
        assert self.user.nickname == 'Jo'

    def test_strick(self):
        self.server.users[' Jo']=self.user
        self.server.ban('/report to Jo')
        assert self.user.reports == 1

    def test_public_chat(self):
        self.user.public = True
        self.server.public_chat('hi', self.user)
        assert self.server.public == ['bot send: hi']