import asyncio
import threading
from asyncio import StreamReader, StreamWriter
from datetime import datetime

from log_config import get_logger
from setting import HOST, PORT

logger = get_logger(__name__)

BAN_TIME_SEC = 30

WELCOME = ("Welcome to chat \n"
           "Please choose you nickname \n"
           "Write /nickname <your nickname> \n"
           "You can send private msg \n"
           "Write /pm <nickname> <message>\n"
           "Write /ban <nick> to block user\n"
           "If you want to delay message - \n"
           "write /delay <minutes> <message> \n"
           "Write quit to leave chat \n")



class AuthUser:
    def __init__(self, reader: StreamReader, writer: StreamWriter, reports: int = 0) -> None:
        self.reader = reader
        self.writer = writer
        self.reports = reports
        self.nickname = 'User'
        self.public = False

    async def get_message(self) -> str:
        logger.warning(f'word')
        return str((await self.reader.read(255)).decode("utf8"))

    def send_message(self, message: bytes) -> None:
        return self.writer.write(message)


class Server:
    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.public = []
        self.users = {}

    async def start_server(self) -> None:
        try:
            server = await asyncio.start_server(self.authentication, self.host, self.port)
            addr = server.sockets[0].getsockname()
            logger.warning(f'Start server on {addr}')
            async with server:
                await server.serve_forever()
        except Exception as e:
            logger.exception(e)
            raise e

    async def authentication(self, reader: StreamReader, writer: StreamWriter) -> None:
        logger.warning('Authentification user')
        user = AuthUser(reader, writer)
        writer.write(WELCOME.encode())
        await self.check_messege(user)

    def set_nickname(self, user: AuthUser, message: str) -> None:
        logger.warning('Set nickname')
        nick = message.split('-')[-1]
        user.nickname = nick

    async def check_messege(self, user: AuthUser) -> None:
        while True:
            message = await user.get_message()
            logger.warning(f'message: {message}')
            if user.reports < 3:
                logger.warning('Check messege')
                if str(message) == '/public':
                    self.public_chat(message, user)
                elif str(message).startswith('/nickname'):
                    self.set_nickname(user, message)
                elif str(message).startswith('/pm'):
                    self.private_message(user, message)
                elif str(message).startswith('/ban'):
                    self.ban(message)
                elif str(message).startswith('/timer'):
                    self.send_timer(message)
                elif user.public:
                    self.public_chat(message, user)

    def public_chat(self, message: str, user: AuthUser) -> None:
        logger.warning('Is public chat')
        if user.public:
            save_msg = f'{user.nickname} send: {message}'
            self.public.append(save_msg)
            for value in self.users.values():
                value.send_message(save_msg.encode('utf-8'))
        else:
            user.public = True
            self.users[user.nickname] = user
            for last_msg in self.public[:20]:
                user.send_message(last_msg.encode('utf-8'))

    def private_message(self, user: AuthUser, message: str) -> None:
        logger.warning('Send private message')
        get_private = message.split('to')[-1]
        msg = ((message.split('-')[1])).replace('to', 'from').encode('utf-8')
        sent_to = self.users.get(get_private)
        if sent_to:
            logger.warning(sent_to)
            sent_to.send_message(msg)

    def ban(self, message: str) -> None:
        logger.warning('Send report')
        user = message.split('to')[-1]
        report_user = self.users.get(user)
        if report_user:
            report_user.reports += 1
        if report_user.reports > 2:
            logger.warning(f'{report_user.nickname} user is banned on {BAN_TIME_SEC} sec')
            timer = threading.Timer(BAN_TIME_SEC, function=self.timer_ban, args=(report_user,))
            timer.start()

    @staticmethod
    def timer_ban(user: AuthUser) -> None:
        logger.warning(f'Unblock user {user.nickname}')
        user.reports = 0

    def send_timer(self, message: str) -> None:
        get_date = ' '.join(message.split(' ')[-6:])
        mes = message.split('-')[1]
        date_time_obj = datetime.strptime(get_date, '%Y, %m, %d, %H, %M, %S')
        now = datetime.now()
        sec = (date_time_obj - now).total_seconds()
        timer = threading.Timer(sec, function=self.public_chat, args=(mes,))
        timer.start()


if __name__ == '__main__':
    server = Server()
    asyncio.run(server.start_server())
