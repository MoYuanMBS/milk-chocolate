# 标准库
import ssl
import json
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

class MessageType(Enum):
    client_id = config.generate_client_id()
    FileContentDict = 'filecontent'
    FilePathDict = 'filepath'
    TargetFolder = 'targetfolder'
    DirPathSet = 'dirpath'
    Test = 'test'
    Error = 'error'

websocket_connection: Optional[ClientConnection] = None

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
            config.check_certs_for_client()
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

async def send_message(message, message_type: MessageType) -> None:
    """发送消息到 WebSocket 服务器"""
    message = json.dumps({"type": message_type.value, "data": message})
    if websocket_connection:  # 检查连接是否已经建立
        await websocket_connection.send(message)  # 通过连接发送消息
        print(f"Sent: {message}")  # 输出已发送的消息内容
    else:
        print("Connection is not established")  # 如果连接未建立，输出错误提示
    return

async def receive_message() -> dict[str, Any]:
    """从 WebSocket 服务器接收消息"""
    if websocket_connection:  # 检查连接是否已经建立
        response = await websocket_connection.recv()  # 接收从服务器发送来的消息
        print(f"Received: {response}")  # 输出接收到的消息内容
        return json.loads(response)  # 返回接收到的消息
    else:
        print("Connection is not established")  # 如果连接未建立，输出错误提示
        return {MessageType.Error.value: '0'}  # 返回一个空字典

async def close_connection() -> None:
    """关闭当前的 WebSocket 连接"""
    if websocket_connection:  # 检查连接是否已经建立
        await websocket_connection.close()  # 关闭连接
        print("Connection closed")  # 输出连接已关闭的消息
    else:
        print("Connection is not established")  # 如果连接未建立，输出错误提示

async def main() -> None:
    """主函数，管理连接、通信和断开的流程"""

    # 自动获取服务器 URI
    try:
        uri = config.get_server_uri()
    except RuntimeError as e:
        print(f"[ERROR] Configuration error: {e}")
        return

    # 根据 URI 类型决定是否验证证书
    if uri.startswith('wss://'):
        # 自签名证书场景：禁用验证
        # 受信任证书场景：启用验证（改为 verify_ssl=True）
        await connect()
    else:
        await connect()

    # 测试发送消息和接收消息
    await send_message("Hello Server!", MessageType.Test)  # 发送一条信息给服务器
    await receive_message()  # 接收服务器的响应

    # 关闭与服务器的连接
    await close_connection()

# 启动事件循环并运行主函数
if __name__ == "__main__":
    config.self_signed_crt_mode = True  # 使用自签名证书
    asyncio.run(main())




