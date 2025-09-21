import websockets
import asyncio
import json
from pathlib import Path

# 用于存储活动连接的集合
connected_clients = set()

async def handler(websocket:websockets.ServerConnection) -> None:
    """处理 WebSocket 连接的函数

    Args:
        websocket (websockets.WebSocketServerProtocol): 当前的 WebSocket 连接
    """
    connected_clients.add(websocket)  # 将新连接添加到活动连接集合
    try:
        async for message in websocket:  # 异步接收客户端消息
            print(f"Received: {message}")  # 输出接收到的消息
            await respond_to_client(websocket, message)  # 响应客户端
    except websockets.ConnectionClosed as e:
        print(f"Connection closed: {e.code}, {e.reason}")  # 捕获连接关闭异常并输出
    finally:
        connected_clients.remove(websocket)  # 确保在连接关闭后移除它

async def respond_to_client(websocket:websockets.ServerConnection, message: str | bytes) -> None:
    """响应客户的消息

    Args:
        websocket (websockets.WebSocketServerProtocol): 客户端的 WebSocket 连接
        message (str | bytes): 来自客户端的消息
    """
    # 生成响应消息，通常可以是根据消息内容处理后的结果
    response = f"Echo: {message}"
    await websocket.send(response)  # 发送响应到客户端
    print(f"Sent: {response}")  # 输出已发送的消息内容

async def broadcast_message(message: str) -> None:
    """向所有连接的客户端广播消息

    Args:
        message (str): 广播的消息内容
    """
    if connected_clients:  # 检查是否存在活动的连接
        await asyncio.wait([ws.send(message) for ws in connected_clients])  # 广播消息
        print(f"Broadcasted: {message}")  # 输出广播的消息内容

async def close_all_connections() -> None:
    """关闭所有的客户端连接"""
    if connected_clients:  # 如果有活动连接
        await asyncio.wait([ws.close() for ws in connected_clients])  # 关闭所有连接
        connected_clients.clear()  # 清空连接集合
        print("All connections closed")  # 输出所有连接关闭的消息

async def main() -> None:
    """启动 WebSocket 服务器的主函数"""
    server = await websockets.serve(
        handler,  # 处理连接的函数
        "localhost",  # 服务器监听的 IP 地址
        8765  # 服务器监听的端口
    )
    print("WebSocket server started on ws://localhost:8765")  # 输出服务器启动信息

    await server.wait_closed()  # 阻止函数退出，直到服务器关闭

# 启动事件循环并运行服务器
asyncio.get_event_loop().run_until_complete(main())