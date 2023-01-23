import asyncio
import threading
from asyncio import StreamReader, StreamWriter
from datetime import datetime
from typing import Tuple

from log_config import get_logger
from setting import BAN_TIME_SEC, HOST, LAST_MSG_COUNT, PORT

logger = get_logger(__name__)


WELCOME_TEXT = (
    "Welcome to chat \n"
    "Command list:"
    "/nickname <your nickname> - choose nickname\n"
    "/pm <user> <message> - send private message to user\n"
    "/ban <user nickname> - report user\n"
    "/delay <date> <time> <message> - to delay message. Example '/delay 2023-01-23 22:26 Hi, i here.'\n"
)


class AuthUser:
    def __init__(self, reader: StreamReader, writer: StreamWriter, reports: int = 0) -> None:
        self.reader = reader
        self.writer = writer
        self.reports = reports
        self.nickname = 'User'
        self.public = False

    async def get_message(self) -> str:
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
        writer.write(WELCOME_TEXT.encode())
        await self.check_messege(user)

    async def check_messege(self, user: AuthUser) -> None:
        """Обработка команд"""
        while True:
            message = await user.get_message()
            logger.warning(f'message: {message}')
            if user.reports < 3:
                if str(message) == '/public':
                    self.public_chat(message, user)
                elif str(message).startswith('/nickname'):
                    self.set_nickname(message, user)
                elif str(message).startswith('/pm'):
                    self.private_message(message, user)
                elif str(message).startswith('/ban'):
                    self.ban(message)
                elif str(message).startswith('/delay'):
                    self.set_delay(message)
                elif user.public:
                    self.public_chat(message, user)

    def public_chat(self, message: str, user: AuthUser) -> None:
        """Общий чат"""
        if user.public:
            msg = f'{user.nickname}: {message}'
            self.public.append(msg)
            for user_in_chat in self.users.values():
                user_in_chat.send_message(msg.encode('utf-8'))
        else:
            user.public = True
            self.users[user.nickname] = user
            for msg in self.public[:LAST_MSG_COUNT]:
                user.send_message(msg.encode('utf-8'))

    def set_nickname(self, message: str, user: AuthUser) -> None:
        """Поменять ник."""
        _, nick = self.parse_command(message, True)
        logger.info(f'User {user.nickname} change nickname {nick}')
        user.nickname = nick

    def private_message(self, message: str, user: AuthUser) -> None:
        """Личное сообщение."""
        command, target_user = self.parse_command(message, True)
        sent_to = self.users.get(target_user)
        # /pm + пробел разделитель + длина имени получателя + пробел, далее идет сообщение
        msg = (f'{user.nickname}: {message[len(command) + 1 + len(target_user) + 1:]}').encode('utf-8')
        if sent_to:
            logger.warning(sent_to)
            sent_to.send_message(msg)

    def ban(self, message: str) -> None:
        """Забанить пользователя"""
        logger.warning('Send report')
        _, target_user = self.parse_command(message, True)
        report_user = self.users.get(target_user)
        if report_user:
            report_user.reports += 1
        if report_user.reports > 2:
            logger.warning(f'{report_user.nickname} user is banned on {BAN_TIME_SEC} sec')
            timer = threading.Timer(BAN_TIME_SEC, function=self.ban_timer, args=(report_user,))
            timer.start()

    def ban_timer(self, user: AuthUser) -> None:
        """Разбанить пользователя по истечению времени."""
        logger.warning(f'Unban user {user.nickname}')
        user.reports = 0

    def set_delay(self, message: str) -> None:
        """Поставить задержку отправки."""
        # '/delay 2023-01-23 22:26 Hi, i here'
        command = self.parse_command(message)
        date_str = message.split(' ')[1] + ' ' + message.split(' ')[2]
        dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
        now = datetime.now()
        sec = (dt - now).total_seconds()
        mes = message[len(command) + 1 + len(date_str) + 1:]
        timer = threading.Timer(sec, function=self.public_chat, args=(mes,))
        timer.start()

    def parse_command(self, message: str, find_key: bool = False) -> Tuple[str, ...]:
        """Получить применяемую команду. Если в качестве ключа передается пользователь, можно его определить."""
        command = message.split(' ')[0]
        if find_key:
            user: str = message.split(' ')[1]
            return command, user
        return command


if __name__ == '__main__':
    server = Server()
    asyncio.run(server.start_server())
