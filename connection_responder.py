import websockets
import asyncio
import json
import ssl
from pathlib import Path
from network_config import config
from status_tracker import StatusTracker

# 用于存储活动连接的集合
connected_clients = set()
file_locker:set[Path] = set()
active_tasks:set[asyncio.Task] = set()
max_workers = 5  # 最大并发消息处理数

async def handler(websocket:websockets.ServerConnection) -> None:
    """处理 WebSocket 连接的函数

    Args:
        websocket (websockets.WebSocketServerProtocol): 当前的 WebSocket 连接
    """
    if len(connected_clients) < 1:
        connected_clients.add(websocket) # 将新的连接添加到集合中
        StatusTracker.basic_information_update('client connected', f'address: {websocket.remote_address}')
    else:
        StatusTracker.error_update('connection handler', 'server busy', 'cannot accept new connections')
    
    semaphore = asyncio.Semaphore(max_workers)  # 限制并发消息处理的信号量
    try:
        async for message in websocket:
            # 为每条消息创建一个任务，并传递信号量
            task = asyncio.create_task(process_with_limit(websocket, message, semaphore))
            active_tasks.add(task)  # 将任务添加到活动任务集合
            task.add_done_callback(active_tasks.discard)  # 任务完成后从集合中移除
    except websockets.exceptions.ConnectionClosed as e:
        StatusTracker.error_update('disconnect handler', f'error: {e}', f'address: {websocket.remote_address}')
    except Exception as e:
        StatusTracker.error_update('handler error', f'error: {e}', f'address: {websocket.remote_address}')
    finally:
        if active_tasks:
            await asyncio.gather(*active_tasks, return_exceptions=True)  # 等待所有活动任务完成
        if websocket in connected_clients:
            connected_clients.remove(websocket)  # 从集合中移除断开的连接
            StatusTracker.basic_information_update('server disconnected', f'address: {websocket.remote_address}')

    


async def process_with_limit(websocket:websockets.ServerConnection, message: str | bytes, semaphore: asyncio.Semaphore) -> None:
    '''
    带有处理限制的消息处理函数
    '''
    async with semaphore:
        decode_str = message.decode('utf-8') if isinstance(message, bytes) else message
        await respond_to_client(websocket, decode_str)
    return


async def respond_to_client(websocket:websockets.ServerConnection, message: str | bytes) -> None:
    """响应客户的消息

    Args:
        websocket (websockets.WebSocketServerProtocol): 客户端的 WebSocket 连接
        message (str | bytes): 来自客户端的消息
    """
    # 解析接收到的 JSON 消息
    try:
        data = json.loads(message)
        # 生成 JSON 格式的响应
        response = json.dumps({"type": "response", "data": f"Echo: {data}"})
    except json.JSONDecodeError:
        # 如果不是 JSON，返回简单的 echo
        response = json.dumps({"type": "response", "data": f"Echo: {message}"})

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

    StatusTracker.server_mode = True
    global max_workers
    # 根据配置决定是否启用 SSL
    if not config.allow_plaintext:
        config.check_cert_files_for_server()
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        # 加载服务器证书和私钥
        ssl_context.load_cert_chain(str(config.server_cert), str(config.server_key))
        # 加载 CA 证书以验证客户端
        ssl_context.load_verify_locations(cafile=str(config.ca_cert))
        ssl_context.verify_mode = ssl.CERT_REQUIRED  # 强制客户端提供证书
        ssl_context.check_hostname = False
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2  # 强制使用 TLS 1.2 以上
        #
        host, port = config.host_and_port
        server = await websockets.serve(handler, host, port, ssl=ssl_context)
        StatusTracker.basic_information_update('server running', f'wss://{host}:{port}')

    else:
        ssl_context = None  # 开发模式下不使用 SSL 
        host, port = config.host_and_port
        server = await websockets.serve(handler, host, port)
        StatusTracker.basic_information_update('server running', f'ws://{host}:{port}')
        StatusTracker.warning_update('plaintext mode', 'development only', 'do not use in production')
    
    await server.wait_closed()  # 阻止函数退出，直到服务器关闭

if __name__ == "__main__":
    # 启动事件循环并运行服务器
    config.self_signed_crt_mode = True  # 使用自签名证书
    asyncio.run(main())