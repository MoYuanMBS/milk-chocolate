import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import aiofiles
import hashlib
from typing import Callable
from status_tracker import StatusTracker

current_status:dict= {}

def hash_file_blocks(file_path:Path, chunk_size:int, buffer_size:int) -> dict[int,str]:
    '''
    计算文件的每个块的哈希值
    '''
    hashes = {}
    with open(file_path, 'rb') as f:
        offest = 0
        while buffer := f.read(buffer_size):
            for i in range(0, len(buffer), chunk_size):
                chunk = buffer[i:i + chunk_size]
                chunk_hush = hashlib.md5(chunk).hexdigest()
                hashes[offest] = chunk_hush
                offest += len(chunk)
    return hashes

def copmaring_file_chunks(original_hasher:dict[int,str], target_hasher:dict[int,str]) -> dict[int,str]:
    '''
    比较两个文件的块哈希值，返回不同的块
    '''
    differing_chunks = {offset: "DELETE" for offset in target_hasher.keys() - original_hasher.keys()}
    for offset, original_hash in original_hasher.items():
        target_hash = target_hasher.get(offset)
        if target_hash is None or target_hash != original_hash:
            differing_chunks[offset] = original_hash # Placeholder for the actual chunk data

    return differing_chunks

async def get_chunks_for_largefiles(original_file_path:Path, target_file_path:Path, hash_dict:dict[int,str], chunk_size:int, buffer_size:int, process_fn:Callable) -> None:
    '''
    根据哈希和偏移获取文件块
    '''
    async with aiofiles.open(original_file_path, 'rb') as file:
        file_chunk_dict = {}
        chunk_size_count = 0
        for offset in sorted(hash_dict.keys()):  # 确保按顺序处理
            await file.seek(offset)  # 移动到指定偏移
            file_chunk_dict[offset]= await file.read(chunk_size)  # 读取块
            chunk_size_count += len(file_chunk_dict[offset])
            if chunk_size_count >= buffer_size:
                # 动态调用传入的处理函数，根据环境进行本地或云端操作
                await process_fn({target_file_path: file_chunk_dict})
                file_chunk_dict = {}
                chunk_size_count = 0
        await process_fn({target_file_path: file_chunk_dict})  # 处理剩余的块
        StatusTracker.update(process_fn.__name__, str(original_file_path.name), str(target_file_path.parent))
    return

async def get_chunks_for_smallfiles(file_path:dict[Path,Path], chunk_size:int, buffer_size:int, process_fn:Callable) -> None:
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
            StatusTracker.update(process_fn.__name__, str(original_file_path.name), str(target_file_path.parent))
            if chunk_size_count >= buffer_size:
                # 动态调用传入的处理函数，根据环境进行本地或云端操作
                current_status['current_file'] = file_chunk_dict
                await process_fn(file_chunk_dict)
                file_chunk_dict = {}
                chunk_size_count = 0
            await process_fn(file_chunk_dict)  # 处理剩余的块
    return

async def write_chunk_to_file(file_chunks:dict[Path,dict[int,bytes]]) -> None:
    '''
    将块写入目标文件的指定偏移
    '''
    for target_file_path, file_chunk in file_chunks.items():
        async with aiofiles.open(target_file_path, 'a+b') as file:
            for offset, chunk in file_chunk.items():
                await file.seek(offset)
                await file.write(chunk)
    return

if __name__ == "__main__":
    original_file = Path(r"D:\temp\asdsdasd\_DSC4721 - 副本.JPG")
    ori_small_file = {
    r"D:\temp\smallfiles\profile.lua", 
    r"D:\temp\smallfiles\settings.lua", 
    r"D:\temp\smallfiles\settings_keys.lua", 
    r"D:\temp\smallfiles\settings_keys_v2.lua"
}
    target_file = Path(r"D:\temp\_DSC4721 - 副本.JPG")
    target_file_small = Path(r"C:\Users\Public\temp\smallfiles")
    orig_hash = hash_file_blocks(original_file, chunk_size=1024*1024, buffer_size=4*1024*1024)
    targ_hash = hash_file_blocks(target_file, chunk_size=1024*1024, buffer_size=4*1024*1024)
    diff = copmaring_file_chunks(orig_hash, targ_hash)
    func = get_chunks_for_largefiles(original_file,target_file,diff,chunk_size=1024*1024, buffer_size=4*1024*1024, process_fn=write_chunk_to_file)
    
    #小文件测试
    small_file_dict = {}
    for item in ori_small_file:
        small_file_dict[Path(item)] = target_file_small / Path(item).name

    func2 = get_chunks_for_smallfiles(small_file_dict, chunk_size=1024*1024, buffer_size=4*1024*1024, process_fn=write_chunk_to_file)

    asyncio.run(func2)
    # print(diff)
    print(current_status)

    pass

