import websockets
import asyncio
import json
from enum import Enum
from pathlib import Path
from typing import Any

class MessageType(Enum):
    FileContentDict = 'filecontent'
    FilePathDict = 'filepath'
    TargetFolder = 'targetfolder'
    DirPathSet = 'dirpath'
    Test = 'test'
    Error = 'error'

websocket_connection = None

async def connect(uri: str) -> None:
    """连接到指定的 WebSocket 服务器"""
    global websocket_connection  # 使用全局变量来存储连接对象
    # 开始与服务器建立 WebSocket 连接
    websocket_connection = await websockets.connect(uri)
    print("Connected to the server")  # 输出连接成功的消息
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
    uri = "ws://localhost:8765"  # WebSocket 服务器的 URI
    await connect(uri)  # 建立连接
    
    # 测试发送消息和接收消息
    await send_message("Hello Server!", MessageType.Test)  # 发送一条信息给服务器
    await receive_message()  # 接收服务器的响应

    # 关闭与服务器的连接
    await close_connection()

# 启动事件循环并运行主函数
asyncio.get_event_loop().run_until_complete(main())




