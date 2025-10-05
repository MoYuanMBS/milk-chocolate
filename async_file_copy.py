import asyncio
import aiofiles
import aiofiles.os
import shutil
from typing import Callable
from pathlib import Path
from status_tracker import StatusTracker

#########################################################################
#文件块读取与写入

async def get_chunks_for_smallfiles(file_path:dict[Path,Path], buffer_size:int, process_fn:Callable) -> None:
    '''
    小文件读取
    '''
    chunk_size_count = 0
    file_chunk_dict = {}
    for original_file_path, target_file_path in file_path.items():
        async with aiofiles.open(original_file_path, 'rb') as file:
            file_data = await file.read()
            file_chunk_dict[target_file_path] = {0: file_data}  # 读取整个文件
            chunk_size_count += len(file_data)
            if chunk_size_count >= buffer_size:
                # 动态调用传入的处理函数，根据环境进行本地或云端操作
                await process_fn(file_chunk_dict, True)
                file_chunk_dict = {}
                chunk_size_count = 0
    if file_chunk_dict:
        await process_fn(file_chunk_dict, True)  # 处理剩余的块
    return

async def get_chunks_for_largefiles(file_path:dict[Path,Path], chunk_size:int, buffer_size:int, process_fn:Callable) -> None:
    '''
    大文件读取
    '''
    for original_file_path, target_file_path in file_path.items():
        file_offset: int = 0  # 文件偏移量
        buffer_data: dict[Path, dict[int, bytes]] = {}  # 缓冲区数据
        current_buffer_size: int = 0  # 当前缓冲区大小
        
        async with aiofiles.open(original_file_path, 'rb') as large_file:
            while True:
                file_data: bytes = await large_file.read(chunk_size)
                
                if not file_data:  # 文件读取完毕
                    if buffer_data:  # 处理剩余的缓冲数据
                        await process_fn(buffer_data, True)
                    break
                
                # 累积数据到缓冲区
                if target_file_path not in buffer_data:
                    buffer_data[target_file_path] = {}
                buffer_data[target_file_path][file_offset] = file_data
                
                current_buffer_size += len(file_data)
                file_offset += len(file_data)
                
                # 当缓冲区达到指定大小时，处理并清空
                if current_buffer_size >= buffer_size:
                    await process_fn(buffer_data, False)
                    buffer_data = {}
                    current_buffer_size = 0
    
    return

async def write_chunk_to_file(file_chunks:dict[Path,dict[int,bytes]],finish_mark:bool) -> None:
    '''
    将块写入目标文件的指定偏移
    '''
    for target_file_path, file_chunk in file_chunks.items():
        if not target_file_path.exists():
            target_file_path.touch()
        async with aiofiles.open(target_file_path, 'r+b') as file:
            for offset, chunk in sorted(file_chunk.items()):
                if chunk == 'delete':
                    await file.truncate(offset)
                await file.seek(offset)
                await file.write(chunk)
        if finish_mark:
            StatusTracker.update('write', str(target_file_path.name), str(target_file_path.parent))
    return

########################################################################
#删除文件/文件夹
async def delete_files(file_to_delete:Path) -> None:
    '''
    删除目标文件夹中多余的文件
    '''
    if file_to_delete.exists():
        try:
            await aiofiles.os.remove(file_to_delete)
            StatusTracker.update('delete_files', str(file_to_delete.name), str(file_to_delete.parent))
        except Exception as e:
            StatusTracker.error_update('delete_files', str(file_to_delete), f'failed: {e}')
    else:
        StatusTracker.error_update('delete_files', str(file_to_delete), 'not exist')
    return

async def delete_directories(path:Path, depth:int) -> bool:
    '''
    删除空目录, depth控制删除的深度
    '''
    path_temp = path
    for _ in range(depth):
        if not path_temp.exists():
            return False
        for item in path_temp.iterdir():
            if item.is_file():
                return False
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: shutil.rmtree(path_temp, ignore_errors=True))
         # 删除空目录
        path_temp = path_temp.parent
    StatusTracker.update('delete_directories', str(path_temp), '')
    return True

async def create_directories(path:Path) -> None:
    '''
    创建缺失文件目录
    '''
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: path.mkdir(parents=True, exist_ok=True))
    StatusTracker.update('create_directories', str(path), '')
    return

if __name__ == "__main__":
    import time
    original_file = Path(r"D:\temp\_DSC4721 - 副本.JPG")
    update_original_file = Path(r"D:\temp\_DSC4255.png")
    update_target_file = Path(r"D:\temp\asdsdasd\_DSC4255.png")
    ori_small_file = {
    r"D:\temp\smallfiles\profile.lua", 
    r"D:\temp\smallfiles\settings.lua", 
    r"D:\temp\smallfiles\settings_keys.lua", 
    r"D:\temp\smallfiles\settings_keys_v2.lua"
}
    ori_large_files ={
        r'D:\temp\Multiwheel\IMG_6880.MOV',
        r'D:\temp\Multiwheel\IMG_6881.MOV',
        r'D:\temp\Multiwheel\IMG_6882.MOV'
    }
    target_file_Large = Path(r"C:\Users\Public\temp\video")
    target_file = Path(r"D:\temp\asdsdasd\_DSC4721 - 副本.JPG")
    target_file_small = Path(r'C:\Users\Public\temp\smallfiles')
    # orig_hash = get_file_hash_blocks(original_file, chunk_size=1024*1024, buffer_size=4*1024*1024)
    # targ_hash = get_file_hash_blocks(target_file, chunk_size=1024*1024, buffer_size=4*1024*1024)
    # diff = comparing_file_chunks(orig_hash, targ_hash)
    # for k, v in diff.items():
    #     print(f'offset: {k}, hash: {v}')
    # func = get_chunks_from_hash(original_file,target_file,diff,chunk_size=1024*1024, buffer_size=4*1024*1024, process_fn=update_chunk_to_file)
    # asyncio.run(func)
    
    #小文件测试
    start_time = time.time()
    small_file_dict = {}
    for item in ori_small_file:
        small_file_dict[Path(item)] = target_file_small / Path(item).name

    func2 = get_chunks_for_smallfiles(small_file_dict, buffer_size=4*1024*1024, process_fn=write_chunk_to_file)
    asyncio.run(func2)
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")

    # 大文件测试
    # start_time = time.time()
    # large_file_dict = {}
    # for item in ori_large_files:
    #     large_file_dict[Path(item)] = target_file_Large / Path(item).name
    # print(large_file_dict)
    # func3 = get_chunks_for_largefiles(large_file_dict, chunk_size=1024*1024, buffer_size=4*1024*1024, process_fn=write_chunk_to_file)
    # asyncio.run(func3)
    # end_time = time.time()
    # print(f"Time taken: {end_time - start_time} seconds")

    #文件夹测试
    dir_to_delete = Path(r"C:\Users\Public\temp\test")
    file_to_delete = Path(r"C:\Users\Public\temp\test\新建 文本文档.txt")
    dir_to_create = Path(r"C:\Users\Public\temp\test\1\2\3\4\5")
    asyncio.run(delete_files(file_to_delete))
    asyncio.run(delete_directories(dir_to_delete, depth=3))
    asyncio.run(create_directories(dir_to_create))

    # 文件更新测试

    

