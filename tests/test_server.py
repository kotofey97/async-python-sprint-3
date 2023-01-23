from server import Server, AuthUser
from client import Client


class TestServer:
    def setup(self) -> None:
        self.server = Server()
        self.client = Client()
        self.user = AuthUser('Stream', 'Writer')

    def test_set_nickname(self):
        self.server.set_nickname('/nickname Test', self.user)
        assert self.user.nickname == 'Test'

    def test_public_chat(self):
        self.user.public = True
        self.server.public_chat('Hi', self.user)
        assert self.server.public == ['User: Hi']

    def test_ban(self):
        self.server.users['Test'] = self.user
        self.server.ban('/ban Test')
        assert self.user.reports == 1
