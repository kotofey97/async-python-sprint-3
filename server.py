import asyncio
import threading
from asyncio import StreamReader, StreamWriter
from datetime import datetime
from typing import Optional

from log_config import get_logger
from setting import BAN_TIME_SEC, HOST, LAST_MSG_COUNT, PORT, REPORTS_FOR_BAN, MAX_BYTES

logger = get_logger(__name__)


WELCOME_TEXT = (
    "Welcome to chat \n"
    "Command list:"
    "/public - join in public chat"
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
        # в инете не нашла, как обойтись без указывания MAX_BYTES
        # пыталась EOF отловить или \n - не получилось
        return (await self.reader.read(MAX_BYTES)).decode("utf8")

    def send_message(self, message: str) -> None:
        return self.writer.write(message.encode('utf-8'))


class Command():
    PUBLIC = 'public'
    PM = 'pm'
    NICKNAME = 'nickname'
    BAN = 'ban'
    DELAY = 'delay'

    def __init__(self, name, key_nick=None, key_datetime=None, message=None) -> None:
        self.name: Optional[str] = name
        self.key_nick: Optional[str] = key_nick
        self.key_datetime: Optional[str] = key_datetime
        self.message: Optional[str] = message


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
        user.send_message(WELCOME_TEXT)
        await self.check_message(user)

    async def check_message(self, user: AuthUser) -> None:
        """Обработка команд"""
        while True:
            message = await user.get_message()
            logger.warning(f'message: {message}')
            if user.reports < REPORTS_FOR_BAN:
                if message.startswith('/'):
                    command = self.parse_command(message)
                    match command.name:
                        case Command.PM:
                            self.private_message(command.message, command.key_nick, user)
                        case Command.DELAY:
                            self.set_delay(command.message, command.key_datetime, user)
                        case Command.BAN:
                            self.ban(command.key_nick)
                        case Command.NICKNAME:
                            self.set_nickname(command.key_nick, user)
                        case Command.PUBLIC:
                            self.public_chat(user)
                elif user.public:
                    self.public_chat(user, message)

    def public_chat(self, user: AuthUser, message: Optional[str] = None) -> None:
        """Общий чат"""
        if user.public and message:
            msg = f'{user.nickname}: {message}'
            self.public.append(msg)
            for user_in_chat in self.users.values():
                user_in_chat.send_message(msg)
        else:
            user.public = True
            self.users[user.nickname] = user
            for msg in self.public[:LAST_MSG_COUNT]:
                user.send_message(msg)

    def set_nickname(self, nick: str, user: AuthUser) -> None:
        """Поменять ник."""
        logger.info(f'User {user.nickname} change nickname {nick}')
        user.nickname = nick

    def private_message(self, message: str, target_user: str, user: AuthUser) -> None:
        """Личное сообщение."""
        sent_to = self.users.get(target_user)
        msg = f'{user.nickname}: {message}'
        if sent_to:
            logger.warning(sent_to)
            sent_to.send_message(msg)

    def ban(self, target_user: str) -> None:
        """Забанить пользователя"""
        logger.warning('Send report to {target_user}')
        report_user = self.users.get(target_user)
        if report_user:
            report_user.reports += 1
        if report_user.reports >= REPORTS_FOR_BAN:
            logger.warning(f'{report_user.nickname} user is banned on {BAN_TIME_SEC} sec')
            timer = threading.Timer(BAN_TIME_SEC, function=self.ban_timer, args=(report_user,))
            timer.start()

    def ban_timer(self, user: AuthUser) -> None:
        """Разбанить пользователя по истечению времени."""
        logger.warning(f'Unban user {user.nickname}')
        user.reports = 0

    def set_delay(self, message: str, date_str: str, user: AuthUser) -> None:
        """Поставить задержку отправки."""
        # '/delay 2023-01-23 22:26 Hi, i here'
        try:
            # приведем к datetime здесь, тк легче пользователю об ошибке сообщение отправить
            dt: datetime = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
        except Exception:
            error = f"Bad datetime format: {date_str}, try 'yyyy-mm-dd HH-MM' (example 2023-01-23 22:26)"
            return user.send_message(error)
        now = datetime.now()
        sec = (dt - now).total_seconds()
        timer = threading.Timer(sec, function=self.public_chat, args=(user, message,))
        timer.start()

    def parse_command(self, message: str):
        """Получить применяемую команду. Если передается ключ, можно его определить."""
        name: str = message.split(' ')[0][1:]
        user = dt = msg = None
        match name:
            case Command.PM:
                user: str = message.split(' ')[1]
                msg: str = message[1 + len(name) + 1 + len(user) + 1:]
            case Command.DELAY:
                dt: str = message.split(' ')[1] + ' ' + message.split(' ')[2]
                msg: str = message[1 + len(name) + 1 + len(dt) + 1:]
            case Command.BAN | Command.NICKNAME:
                user: str = message.split(' ')[1]
        return Command(name=name, key_nick=user, key_datetime=dt, message=msg)


if __name__ == '__main__':
    server = Server()
    asyncio.run(server.start_server())
