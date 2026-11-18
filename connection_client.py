# 标准库
import ssl
import pickle
import asyncio
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# 第三方库
import websockets
from websockets.asyncio.client import ClientConnection

# 本地模块
from network_config import config
from status_tracker import StatusTracker
from typeing_and_emnu import MessageType, FilesTyping

websocket_connection: Optional[ClientConnection] = None
client_id:str = config.generate_client_id()

async def connect() -> None:
    """
    连接到指定的 WebSocket 服务器
    """
    global websocket_connection  # 使用全局变量来存储连接对象
    ssl_context = ssl.create_default_context()

    # 强制使用加密连接
    if not config.allow_plaintext:
        # 使用自签名证书
        if config.self_signed_crt_mode:
            ssl_context.check_hostname = False
            ssl_context.load_verify_locations(str(config.ca_cert))
            ssl_context.load_cert_chain(certfile=str(config.client_crt), keyfile=str(config.client_key))
        else:
            # 使用受信任证书
            config.check_certs_for_client(False)
            ssl_context.load_cert_chain(certfile=str(config.client_crt), keyfile=str(config.client_key))
    else:
        # 允许明文连接（开发模式）
        ssl_context = None
    
    # 建立 WebSocket 连接
    try:
        if not config.allow_plaintext:
            uri = config.get_server_uri()
            websocket_connection = await websockets.connect(uri, ssl=ssl_context)
        else:
            uri = config.get_server_uri()
            websocket_connection = await websockets.connect(uri)
    except Exception as e:
        StatusTracker.error_update('websocket connection', f'{e}', 'failed to connect')
        raise e
    StatusTracker.update('websocket connection', 'established', 'success')
    return

async def send_file_chunks(file_chunks: FilesTyping.file_chunks, finish_mark: bool) -> None:
    """发送文件块到 WebSocket 服务器"""
    message = pickle.dumps({client_id: (MessageType.FILE_CHUNKS, file_chunks, finish_mark)})
    if websocket_connection:  # 检查连接是否已经建立
        await websocket_connection.send(message)  # 通过连接发送消息
        if finish_mark:
            for target_file_path in file_chunks.keys():
                StatusTracker.update('send', str(target_file_path), 'to server')
    else:
        StatusTracker.error_update('send file chunks', 'WebSocket', 'not established')
        return

async def send_message(message: FilesTyping.FilesTypingUnion, message_type: MessageType) -> None:
    """发送消息到 WebSocket 服务器"""
    if websocket_connection:  # 检查连接是否已经建立
        await websocket_connection.send(pickle.dumps({client_id: (message_type, message)}))
        StatusTracker.update('send', f'message type: {message_type.name}', 'to server')
    else:
        StatusTracker.error_update('send message', 'WebSocket', 'not established')

async def receive_message() -> tuple[MessageType, FilesTyping.FilesTypingUnion]:
    """从 WebSocket 服务器接收消息"""
    if websocket_connection:  # 检查连接是否已经建立
        response = await websocket_connection.recv()  # 接收从服务器发送来的消息
        if isinstance(response, bytes):  # 如果接收到的是字节类型的数据
            decode_response: dict[str, tuple[MessageType, FilesTyping.FilesTypingUnion]] = pickle.loads(response)
            server_id, full_message = next(iter(decode_response.items()))
            StatusTracker.update('receive', f'message from server: {server_id}', f'{full_message[0].name}: {full_message[1]}')
            return full_message
        elif isinstance(response, str):
            StatusTracker.warning_update('receive', 'message from server: UNKNOWN ID', f'{MessageType.TEST.name}:{response}')
            return (MessageType.TEST, response)
        else:
            StatusTracker.error_update('receive message', 'unknown data type', 'failed to decode')
            return (MessageType.ERROR, 'unknown data type')
    else:
        raise ConnectionError('连接丢失，无法接收消息')

async def close_connection() -> None:
    """关闭当前的 WebSocket 连接"""
    if websocket_connection:  # 检查连接是否已经建立
        await websocket_connection.close()  # 关闭连接
        print("Connection closed")  # 输出连接已关闭的消息
    else:
        print("Connection is not established")  # 如果连接未建立，输出错误提示

async def init_server_connection(basic_info) -> None:
    """初始化与服务器的连接并同步基本信息"""

    await connect()  # 建立与服务器的连接

    # 同步基本信息到服务器
    await send_message(basic_info, MessageType.BASIC_INFO)  # 发送一条信息给服务器
    message_type, message = await receive_message()  # 接收服务器的响应
    if message_type == MessageType.BASIC_INFO:
        

    return

# 启动事件循环并运行主函数
if __name__ == "__main__":
    from sync_files import PassiveFileSyncTool
    a = PassiveFileSyncTool(r'D:\Games\RSI Launcher', r'D:\temp')
    config.self_signed_crt_mode = True  # 使用自签名证书
    asyncio.run(init_server_connection(a))
    message: FilesTyping.test_type = str('adbadasd')
    c = send_message(message, MessageType.BASIC_INFO)



