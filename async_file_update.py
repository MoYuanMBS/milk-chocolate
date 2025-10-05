import os
import asyncio
from pathlib import Path
import hashlib
import fastcdc
import aiofiles
from typing import TypeAlias, Callable

from status_tracker import StatusTracker



#声明TypeAlias
chunkHash: TypeAlias = dict[int, tuple[str, int]]
chunkDifferences: TypeAlias = dict[str, dict[tuple[int,int],int]]
updateFileChunks: TypeAlias = dict[str, dict[tuple[int,int],tuple[int,bytes]]]

async def get_file_hash_blocks(file_path:Path, chunk_size:int) -> chunkHash:
    '''
    动态计算文件的每个块的哈希值
    '''
    # dict[chunk_offset:int, tuple[chunk_hash:str, chunk_length:int]]
    hashes: chunkHash = {}
    # 先用同步方式获取chunk信息（fastcdc需要）
    chunks_info = list(fastcdc.fastcdc(file_path, min_size = chunk_size//4, avg_size = chunk_size, max_size = chunk_size*4))

    # 异步读取文件并计算hash
    async with aiofiles.open(file_path, 'rb') as f:
        for chunk in chunks_info:
            await f.seek(chunk.offset)
            data = await f.read(chunk.length)
            chunk_hash = hashlib.md5(data).hexdigest()
            hashes[chunk.offset] = (chunk_hash, chunk.length)
    StatusTracker.update('get hash', str(file_path.name), '')
    return hashes

def comparing_file_chunks(ori_hashes:chunkHash, tar_hashes:chunkHash) -> chunkDifferences:
    '''
    比较两个文件的块，返回源文件中不同的块
    '''
    #chunkDifferences:dict[func:str,dict[tuple[ori_offset:int, tar_offset:int],chunk_length:int]]
    different_chunks: chunkDifferences = {'changed':{}, 'moved':{}, 'unchanged':{}}
    #unchanged_blocks: list[tuple[offset_int, length_int]] = []
    unchanged_blocks: list[tuple[int, int]] = []

    # 构建hash到offset以及hash到length的映射
    ori_hash_to_length_dict: dict[str,int] = {v[0]:v[1] for _,v in ori_hashes.items()}
    ori_hash_to_offset_dict: dict[str, set[int]] = {}
    for offset, (hash_val, _) in ori_hashes.items():
        ori_hash_to_offset_dict.setdefault(hash_val, set()).add(offset)
    # tar hash到offset映射
    tar_hash_to_offset_dict: dict[str, set[int]] = {}
    for offset, (hash_val, _) in tar_hashes.items():
        tar_hash_to_offset_dict.setdefault(hash_val, set()).add(offset)

    # 处理hash相同的块
    gathered_hashes: set[str] = tar_hash_to_offset_dict.keys() & ori_hash_to_offset_dict.keys()
    for hash_val in gathered_hashes:
        # 块未变化
        for offset in tar_hash_to_offset_dict[hash_val] & ori_hash_to_offset_dict[hash_val]:
            unchanged_blocks.append((offset, ori_hash_to_length_dict[hash_val]))
            tar_hash_to_offset_dict[hash_val].remove(offset)
            ori_hash_to_offset_dict[hash_val].remove(offset)
        # 移动的块
        while tar_hash_to_offset_dict[hash_val] and ori_hash_to_offset_dict[hash_val]:
            tar_offset = tar_hash_to_offset_dict[hash_val].pop()
            ori_offset = ori_hash_to_offset_dict[hash_val].pop()
            different_chunks['moved'][(ori_offset, tar_offset)] = ori_hash_to_length_dict[hash_val]
        # 处理剩余的新增块
        for offset in ori_hash_to_offset_dict[hash_val]:
            different_chunks['changed'][(offset, -1)] = ori_hash_to_length_dict[hash_val]


    #处理新增和更改的块
    for hash_val in ori_hash_to_offset_dict.keys() - tar_hash_to_offset_dict.keys():
        for offset in ori_hash_to_offset_dict[hash_val]:
            different_chunks['changed'][(offset, -1)] = ori_hash_to_length_dict[hash_val]
    
    # 整理unchanged块
    if unchanged_blocks:
        unchanged_blocks.sort()
        start, length = unchanged_blocks[0]
        end = start + length
        merged_ranges: list[tuple[int, int]] = []
        # 3. 合并逻辑
        for next_start, next_length in unchanged_blocks[1:]:
            if next_start == end:  # 连续
                end = next_start + next_length
            else:  # 不连续
                merged_ranges.append((start, end - start))
                start = next_start
                end = start + next_length
        # 添加最后一个范围
        merged_ranges.append((start, end - start))
        for start_offset, length in merged_ranges:
            different_chunks['unchanged'][(start_offset, start_offset)] = length

    return different_chunks

async def get_chunks_from_hash(original_file_path:Path, target_file_path:Path, hash_dict:chunkDifferences, chunk_size:int, buffer_size:int, process_fn:Callable) -> None:
    '''
    根据哈希和偏移获取文件块
    '''
    #updateFileChunks:dict[func:str,dict[tuple[ori_offset:int, tar_offset:int],tuple[chunk_length:int, chunk_data:bytes]]]
    update_file_chunks:updateFileChunks = {}
    chunk_size_count = 0

    async def check_and_process_chunks():
        nonlocal chunk_size_count
        if chunk_size_count >= buffer_size:
            await process_fn(update_file_chunks, False, target_file_path, chunk_size)
            update_file_chunks.clear()
            chunk_size_count = 0

    async with aiofiles.open(original_file_path, 'rb') as file:
        for type_key, chunks in hash_dict.items():
            if type_key == 'changed':
                for (ori_offset, tar_offset), chunk_length in sorted(chunks.items()):  # 确保按顺序处理
                    # 读取修改块数据
                    await file.seek(ori_offset)
                    chunk_data = await file.read(chunk_length)
                    update_file_chunks.setdefault(type_key, {})[(ori_offset, tar_offset)] = (chunk_length, chunk_data)
                    chunk_size_count += chunk_length
                    await check_and_process_chunks()
            elif type_key == 'moved':
                for (ori_offset, tar_offset), chunk_length in sorted(chunks.items()):  # 确保按顺序处理
                    # 移动块转写
                    update_file_chunks.setdefault(type_key, {})[(ori_offset, tar_offset)] = (chunk_length, b'')
            elif type_key == 'unchanged':
                for (ori_offset, tar_offset), chunk_length in sorted(chunks.items()):  # 确保按顺序处理
                    # 不变块转写
                    update_file_chunks.setdefault(type_key, {})[(ori_offset, tar_offset)] = (chunk_length, b'')

        if update_file_chunks:
            await process_fn(update_file_chunks, True, target_file_path, chunk_size)
        return

async def update_chunks_to_file(update_chunks:updateFileChunks, finish_mark:bool, target_file_path:Path, chunk_size:int) -> None:
    '''
    更新文件块到目标文件
    '''
    temp_file_path = target_file_path.with_suffix('.tmp')
    if not temp_file_path.exists():
        temp_file_path.touch()
    # 收集所有块并按ori_offset排序
    all_chunks = []
    for type_key, chunk in update_chunks.items():
        for (ori_offset, tar_offset), data in chunk.items():
            all_chunks.append((ori_offset, tar_offset, type_key, data))
    # 按ori_offset排序，确保顺序写入
    all_chunks.sort(key=lambda x: x[0])

    async with aiofiles.open(temp_file_path, 'r+b') as dest_file:
        async with aiofiles.open(target_file_path, 'rb') as source_file:
            for ori_offset, tar_offset, type_key, (chunk_length, chunk_data) in all_chunks:
                if type_key == 'changed':
                    # 写入修改或新增块
                    await dest_file.seek(ori_offset)
                    await dest_file.write(chunk_data)
                elif type_key == 'moved':
                    # 读取并写入移动块
                    await source_file.seek(tar_offset)
                    data = await source_file.read(chunk_length)
                    await dest_file.seek(ori_offset)
                    await dest_file.write(data)
                elif type_key == 'unchanged':
                    # 分批读取并写入不变块，避免大块一次性读取
                    remaining = chunk_length
                    current_offset = ori_offset
                    while remaining > 0:
                        read_size = min(chunk_size, remaining)
                        await source_file.seek(current_offset)
                        data = await source_file.read(read_size)
                        await dest_file.seek(current_offset)
                        await dest_file.write(data)
                        current_offset += read_size
                        remaining -= read_size
    # 替换原文件
    if finish_mark:
        os.replace(temp_file_path, target_file_path)
        StatusTracker.update('update', str(target_file_path.name), str(target_file_path.parent))
    return

def update_files_cdc(file_path: tuple[Path, Path], chunk_size:int, buffer_size: int, max_workers:int, process_fn: Callable, offline_mode: bool) -> None:
    '''
    使用CDC算法更新文件
    '''
    semaphore = asyncio.Semaphore(max_workers)
    # 并发获取文件哈希
    async def get_hash_main(file_path: tuple[Path, Path], chunk_size:int, offline_mode: bool)-> tuple[chunkHash, chunkHash]:
        if offline_mode:
            task_list = []
            task_list.append(asyncio.create_task(get_file_hash_blocks(file_path[0], chunk_size=chunk_size)))
            task_list.append(asyncio.create_task(get_file_hash_blocks(file_path[1], chunk_size=chunk_size)))
            async with semaphore:
                orig_hash, targ_hash = await asyncio.gather(*task_list)
        else:
            #此功能暂未实现
            async with semaphore:
                orig_hash = await get_file_hash_blocks(file_path[0], chunk_size=chunk_size)
                targ_hash = await process_fn(file_path[1], chunk_size=chunk_size)
        return orig_hash, targ_hash
    # 同步比较chunk
    orig_hash, targ_hash = asyncio.run(get_hash_main(file_path, chunk_size, offline_mode))
    differing_chunks = comparing_file_chunks(orig_hash, targ_hash)
    StatusTracker.update('compare complete', str(file_path[0].name), str(file_path[1].name))
    # 并发更新文件
    async def update_chunk_main():
        async with semaphore:
            await get_chunks_from_hash(file_path[0], file_path[1], differing_chunks, chunk_size=chunk_size, buffer_size=buffer_size, process_fn=process_fn)
    asyncio.run(update_chunk_main())
    return
    
if __name__ == "__main__":
    import time
    update_original_file = Path(r"D:\temp\_DSC4255.png")
    update_target_file = Path(r"D:\temp\asdsdasd\_DSC4255.png")
    start_time = time.time()
    
    # async def main():
    #     task_list = []
    #     task_list.append(asyncio.create_task(get_file_hash_blocks(update_original_file, chunk_size=1024*1024)))
    #     task_list.append(asyncio.create_task(get_file_hash_blocks(update_target_file, chunk_size=1024*1024)))
    #     orig_hash, targ_hash = await asyncio.gather(*task_list)
    #     return orig_hash, targ_hash

    # orig_hash, targ_hash = asyncio.run(main())
    # differing_chunks = comparing_file_chunks(orig_hash, targ_hash)
    # for k, v in differing_chunks.items():
    #     print(k, v)
    # func = get_chunks_from_hash(update_original_file, update_target_file, differing_chunks, buffer_size=5*1024*1024, process_fn=update_chunks_to_file)
    # asyncio.run(func)
    # end_time = time.time()
    # print(f"Time taken: {end_time - start_time} seconds")

    update_files_cdc((update_original_file, update_target_file), chunk_size=1024*1024, buffer_size=3*1024*1024, max_workers=4, process_fn=update_chunks_to_file, offline_mode=True)
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")   
