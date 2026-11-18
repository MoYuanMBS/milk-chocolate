import re
from enum import Enum, auto
from pathlib import Path
from typing import TypeAlias, Union, TYPE_CHECKING
from dataclasses import dataclass
if TYPE_CHECKING:
    from sync_files import PassiveFileSyncTool

class ServerMode(Enum):
    SERVER_ORIGIN = 'ser_ori'
    '''服务器运算，并最为源文件模式'''
    SERVER_TARGET = 'ser_tar'
    '''服务器运算，并最为目标文件模式'''
    CLIENT_ORIGIN = 'cli_ori'
    '''客户端运算，并最为源文件模式'''
    CLIENT_TARGET = 'cli_tar'
    '''客户端运算，并最为目标文件模式'''

class MessageType(Enum):
    BASIC_INFO = auto()
    FULL_DIRECTORY_PATH = auto()
    FILE_CHUNKS = auto()
    REMOTE_FOLDER = auto()
    REMOTE_FILE = auto()
    CREATE_FOLDER = auto()
    STATUS_UPDATE = auto()
    REPONSE = auto()
    TEST = auto()
    ERROR = auto()
    AUTO_REPLY = auto()

class FilesTyping():
    '''TypeAlias for all files related typing'''
    basic_info: TypeAlias = 'PassiveFileSyncTool'
    '''基本信息: PassiveFileSyncTool 类'''
    file_chunks: TypeAlias = dict[Path, dict[int, bytes]]
    '''文件块: {target_file_path: {chunk_offset: chunk_data}}'''
    send_file_chunks: TypeAlias = dict[str, tuple[int, bytes, bool]]
    '''发送文件块: {client_id: (message_type, message, finish_mark)}'''
    reponse_type: TypeAlias = tuple[bool, ]
    '''响应类型: {client_id: (message_type, message)}'''
    test_type: TypeAlias = str
    '''测试类型: str'''
    FilesTypingUnion: TypeAlias = Union[test_type, file_chunks, send_file_chunks]
    '''FilesTyping中的任何类型: test_type | file_chunks | send_file_chunks'''



