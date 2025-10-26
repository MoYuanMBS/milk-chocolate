import os
import re
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable
import async_file_copy as asynCopy
import async_file_update as asynUpdate
from status_tracker import StatusTracker

class FileSyncTool:
    def __init__(self, original_folder_path: str, target_folder_path: str) -> None:
        """
        初始化文件同步模块
        param original_folder_path: 原始文件夹路径
        param target_folder_path: 目标文件夹路径
        """
        self.__original_folder = FilesAndDirs(original_folder_path)
        self.__target_folder = FilesAndDirs(target_folder_path)
        self.__chunk_size:int = 4096 * 4096  # 4MB
        self.__buffer_size:int = self.__chunk_size * 4  # 16MB
        self.__max_workers:int = 4
        self.__allowed_regex_pattern: re.Pattern = re.compile(
            r'[a-zA-Z]:[/\\]|'           # Windows盘符
            r'^[/\\]|'                    # 绝对路径开头
            r'(?=.*/)(?=.*\\)', re.UNICODE
        )
        self.offline_mode : bool = True  # 离线模式，默认开启 
        return

    def _get_files_and_pathes(self):
        self.__original_folder.get_file_and_dir_path()
        self.__target_folder.get_file_and_dir_path()
        return

    def __compare_dir_path_difference(
        self, first_compare_path: set[Path], second_compare_path: set[Path]
    ) -> set[Path]:
        """
        比较原始文件夹和目标文件夹中的文件和目录
        """
        comparied_pathes = first_compare_path - second_compare_path
        return comparied_pathes

    def __compare_file_path_difference(
        self,
        first_compare_path: dict[Path, float],
        second_compare_path: dict[Path, float],
    ) -> set[Path]:
        """
        比较原始文件和目标文件中的文件
        返回缺失的文件路径
        """
        return first_compare_path.keys() - second_compare_path.keys()

    def _copy_files(self):
        """
        仅复制缺失的文件到目标文件夹
        """
        files_need_to_copy = self.__compare_file_path_difference(
            self.__original_folder.full_path_with_files,
            self.__target_folder.full_path_with_files,
        )
        # 分离大小文件
        small_files: dict[Path, Path] = {}
        large_files: dict[Path, Path] = {}
        for file in files_need_to_copy:
            if os.path.getsize(self.__original_folder.current_directory / file) <= self.__chunk_size:
                small_files[self.__original_folder.current_directory / file] = self.__target_folder.current_directory / file
            else:
                large_files[self.__original_folder.current_directory / file] = self.__target_folder.current_directory / file
        # 大小文件一起并发复制
        async def copy_files( process_fn: Callable):
            # 控制并发数量
            semaphore = asyncio.Semaphore(self.__max_workers)

            async def copy_small_files_with_semaphore(files_dict: dict[Path, Path], buffer_size: int, process_fn: Callable):
                async with semaphore:
                    await asynCopy.get_chunks_for_smallfiles(files_dict, buffer_size, process_fn)
            
            async def copy_large_files_with_semaphore(files_dict: dict[Path, Path], chunk_size: int, buffer_size: int, process_fn: Callable):
                async with semaphore:
                    await asynCopy.get_chunks_for_largefiles(files_dict, chunk_size, buffer_size, process_fn)

            # 创建所有任务
            tasks = [asyncio.create_task(copy_small_files_with_semaphore(small_files, self.__buffer_size, process_fn)), 
                    asyncio.create_task(copy_large_files_with_semaphore(large_files, self.__chunk_size, self.__buffer_size, process_fn))]
            # 等待所有任务完成
            await asyncio.gather(*tasks)
            return
        
        # 在同步函数中运行异步代码
        if self.offline_mode:
            asyncio.run(copy_files(asynCopy.write_chunk_to_file))
        else:
            pass
        return
    
    def __compare_file_update(self) -> dict[Path,Path]:
        '''
        比较文件是否更新
        '''
        different_files:dict = {}

        for file_path in (
            self.__original_folder.full_path_with_files.keys()
            & self.__target_folder.full_path_with_files.keys()
        ):
            if (
                self.__original_folder.full_path_with_files[file_path]
                > self.__target_folder.full_path_with_files[file_path]
            ):
                different_files[self.__original_folder.current_directory / file_path] = self.__target_folder.current_directory / file_path
        return different_files

    def _update_changed_files(self):
        """
        更新目标文件夹中已更改的文件
        """
        different_files = self.__compare_file_update()
        if not different_files:
            return

        # 分离大小文件
        large_files: dict[Path, Path] = {}
        small_files: dict[Path, Path] = {}
        for ori_path, tar_path in different_files.items():
            if os.path.getsize(ori_path) <= self.__chunk_size:
                small_files[ori_path] = tar_path
            else:
                large_files[ori_path] = tar_path

        # 根据模式选择处理函数
        if self.offline_mode:
            small_process_fn = asynCopy.write_chunk_to_file
            large_process_fn = asynUpdate.update_chunks_to_file
        else:
            # TODO: 实现云端处理函数
            raise NotImplementedError("Online mode is not implemented yet")

        # 按文件大小对大文件排序（小的大文件优先）
        sorted_large_files = sorted(large_files.items(), key=lambda x: os.path.getsize(x[0])) if large_files else []
        large_file_count = len(sorted_large_files)

        # 计算大文件的内部并发数
        if large_file_count == 1 and not small_files:
            # 只有1个大文件且无小文件：充分利用所有worker
            inner_workers = self.__max_workers
        else:
            # 多文件场景：避免嵌套并发
            inner_workers = 1

        # 使用线程池统一处理
        with ThreadPoolExecutor(max_workers = self.__max_workers) as executor:
            futures = []

            # 如果有小文件，优先提交小文件任务（占用1个线程）
            if small_files:
                future = executor.submit(
                    asyncio.run,
                    asynCopy.get_chunks_for_smallfiles(small_files, self.__buffer_size, small_process_fn)
                )
                futures.append(future)

            # 提交所有大文件任务（会使用剩余线程，小文件完成后会自动接手）
            for ori_path, tar_path in sorted_large_files:
                future = executor.submit(
                    asynUpdate.update_files_cdc,
                    (ori_path, tar_path),
                    self.__chunk_size,
                    self.__buffer_size,
                    inner_workers,
                    large_process_fn,
                    self.offline_mode
                )
                futures.append(future)

            # 等待所有任务完成并处理异常
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    StatusTracker.error_update("file update", str(e), "failed")
        return

    def _remove_files(self):
        """
        删除目标文件夹中多余的文件
        """
        files_need_to_remove = self.__compare_file_path_difference(self.__target_folder.full_path_with_files, self.__original_folder.full_path_with_files)

        # 删除多余的文件
        if not files_need_to_remove:
            return
        if self.offline_mode:
            async def async_remove_with_limit():
                # 控制并发数量
                semaphore = asyncio.Semaphore(self.__max_workers)
                
                async def delete_with_semaphore(file_path):
                    async with semaphore:
                        await asynCopy.delete_files(file_path)  # 正确调用
                
                # 创建所有任务
                tasks = [asyncio.create_task(delete_with_semaphore(self.__target_folder.current_directory / file))
                    for file in files_need_to_remove]
                
                # 等待所有任务完成
                await asyncio.gather(*tasks)

            # 在同步函数中运行异步代码
            asyncio.run(async_remove_with_limit())
        else:
            pass
        return

    def _adding_directories(self):
        """
        同步之前初始化好的目录
        会自动同步所有目录
        """
        dir_need_to_create = self.__compare_dir_path_difference(self.__original_folder.all_directory_path, self.__target_folder.all_directory_path)
        # 创建缺失的目录
        if not dir_need_to_create:
            return
        if self.offline_mode:
            async def async_create_with_limit():
                # 控制并发数量
                semaphore = asyncio.Semaphore(self.__max_workers)

                async def create_with_semaphore(dir_path):
                    async with semaphore:
                        await asynCopy.create_directories(dir_path)  # 正确调用

                # 创建所有任务
                tasks = [asyncio.create_task(create_with_semaphore(self.__target_folder.current_directory / dir))
                         for dir in dir_need_to_create]
                # 等待所有任务完成
                await asyncio.gather(*tasks)
            # 在同步函数中运行异步代码
            asyncio.run(async_create_with_limit())
        else:
            pass
        return

    def _remove_directories(self):
        """
        删除目标文件夹中多余的目录
        """
        dir_need_to_remove = {}

        # 删除多余的目录
        for dir in self.__compare_dir_path_difference(
            self.__target_folder.all_directory_path,
            self.__original_folder.all_directory_path,
        ):
            for item in self.__original_folder.all_directory_path:
                if (
                    len(item.parts) < len(dir.parts)
                    and item.parts == dir.parts[: len(item.parts)]
                ):
                    dir_need_to_remove[self.__target_folder.current_directory / dir] = (
                        len(dir.parts) - len(item.parts)
                    )
                else:
                    dir_need_to_remove[self.__target_folder.current_directory / dir] = (
                        len(dir.parts)
                    )

        if not dir_need_to_remove:
            return
        if self.offline_mode:
            async def async_remove_dir_with_limit():
                # 控制并发数量
                semaphore = asyncio.Semaphore(self.__max_workers)

                async def create_with_semaphore(dir_path, depth):
                    async with semaphore:
                        await asynCopy.delete_directories(dir_path, depth)  # 正确调用

                # 创建所有任务
                tasks = [asyncio.create_task(create_with_semaphore(self.__target_folder.current_directory / dir, depth))
                         for dir, depth in dir_need_to_remove.items()]
                # 等待所有任务完成
                await asyncio.gather(*tasks)
            # 在同步函数中运行异步代码
            asyncio.run(async_remove_dir_with_limit())
        else:
            pass
        return

    def change_chunk_size(self, chunk_size: int):
        """
        修改文件复制的块大小
        """
        if chunk_size > 0:
            self.__chunk_size = chunk_size
            StatusTracker.update("chunk size", str(chunk_size), 'set')
            if self.__buffer_size < self.__chunk_size:
                self.__buffer_size = self.__chunk_size * 4 
                StatusTracker.update("buffer size", str(self.__buffer_size), 'sync')
        else:
            StatusTracker.error_update("chunk size", str(chunk_size), 'less 0')
        return
    
    def change_buffer_size(self, buffer_size: int):
        """
        修改文件复制的缓冲区大小
        """
        if buffer_size >= self.__chunk_size:
            self.__buffer_size = buffer_size
        else:
            StatusTracker.error_update("buffer size", str(buffer_size), 'less')
        return
    
    def _change_allowed_regex_pattern(self, pattern: str):
        """
        修改允许的正则表达式模式
        """
        try:
            self.__allowed_regex_pattern = re.compile(pattern, re.UNICODE)
        except re.error:
            raise ValueError("Invalid regex pattern.")
        return

    def advanced_file_and_directory_filtering(
        self,
        file_pattern: str = "",
        directory_pattern: str = "",
        exluded_type: bool = True,
    ):
        """
        仅复制符合正则表达式的文件
        不可与ignored_files_and_directories同时使用
        """
        if re.match(self.__allowed_regex_pattern, file_pattern):
            StatusTracker.error_update("file regex", str(file_pattern), 'invalid')
            return 
        else:
            if file_pattern:
                self.__original_folder.files_regex = re.compile(file_pattern,re.UNICODE)
                self.__target_folder.files_regex = re.compile(file_pattern,re.UNICODE)

        if  re.match(self.__allowed_regex_pattern, directory_pattern):
            StatusTracker.error_update("directory regex", str(directory_pattern), 'invalid')
            return 
        else:
            if directory_pattern:
                self.__original_folder.directories_regex = re.compile(directory_pattern,re.UNICODE)
                self.__target_folder.directories_regex = re.compile(directory_pattern,re.UNICODE)

        self.__original_folder.exluded_type = exluded_type
        self.__target_folder.exluded_type = exluded_type
        return

    def ignored_files_and_directories(
        self,
        files: set[str] = set(),
        directories: set[str] = set(),
        exluded_type: bool = True,
    ):
        """
        忽略指定的文件名或目录名
        不可用和advanced_file_and_directory_filtering同时使用
        """
        erro_dir_names = {" /", ":", "*", "?", '"', "<", ">", "|", "{", "}", "'"}

        files_patterns: str = ""
        for file in files:
            if "." in file and len(file.split(".")) > 0:
                files_patterns += f"{re.escape(file)}|"
        files_regex = re.compile(files_patterns[:-1], re.UNICODE) if files_patterns else None
        self.__original_folder.files_regex = files_regex
        self.__target_folder.files_regex = files_regex

        dir_patterns: str = ""
        for directory in directories:
            if directory not in erro_dir_names:
                dir_patterns += f"{re.escape(directory)}|"
        directories_regex = re.compile(dir_patterns[:-1], re.UNICODE) if dir_patterns else None
        self.__original_folder.directories_regex = directories_regex
        self.__target_folder.directories_regex = directories_regex

        self.__original_folder.exluded_type = exluded_type
        self.__target_folder.exluded_type = exluded_type
        return


class FilesAndDirs:
    def __init__(self, base_dir_path: str) -> None:
        self.current_directory = Path(base_dir_path) # 同步文件夹的绝对路径
        self.full_path_with_files: dict[Path, float] = {} # 所有文件的相对路径和修改时间
        self.all_directory_path = set() # 所有目录的相对路径
        self.files_regex: re.Pattern | None = None # 忽略的文件正则表达式
        self.directories_regex: re.Pattern | None = None # 忽略的目录正则表达式
        self.exluded_type: bool = True # 忽略/只读文件和目录
        return

    def get_file_and_dir_path(self) -> None:
        temp_directory_path_set = set()
        for item in set(Path.rglob(self.current_directory, "**/*")):
            if item.is_file():
                temp_file_result = self.filtering(
                    item.name, self.files_regex
                )
                temp_dir_result = self.filtering(
                    item, self.directories_regex
                )
                if (
                    (temp_file_result and temp_dir_result)
                    if self.exluded_type
                    else (temp_file_result or temp_dir_result)
                ):
                    self.full_path_with_files[
                        item.relative_to(self.current_directory)
                    ] = os.path.getmtime(item)
                    temp_directory_path_set.add(
                        item.parent.relative_to(self.current_directory)
                    )
            elif item.is_dir():
                if self.filtering(item, self.directories_regex):
                    temp_directory_path_set.add(
                        item.relative_to(self.current_directory)
                    )
        # for item in temp_directory_path_set:
        #     print(item)
        self.simplify_directory_path(temp_directory_path_set)
        return

    def simplify_directory_path(self, directory_path: set[Path]):

        for path in directory_path:
            # 移除当前路径的祖先路径，只有在路径层级足够时才进行比较
            to_remove = {
                item
                for item in self.all_directory_path
                if len(path.parts) >= len(item.parts)
                and path.parts[: len(item.parts)] == item.parts
            }
            self.all_directory_path -= to_remove

            # 只有当 item 的层级少于或等于 path 时，才检测 path 是否被覆盖
            if not any(
                len(item.parts) <= len(path.parts)
                and item.parts == path.parts[: len(item.parts)]
                for item in self.all_directory_path
            ):
                self.all_directory_path.add(path)

        return

    def filtering(
        self, copmared_path: Path | str, pattern: re.Pattern | None
    ) -> bool:
        """
        过滤文件和目录
        copmared_path: 需要过滤的路径
        pattern: 正则表达式模式
        ignored_type: 是否忽略只读文件和目录
        """
        if pattern is None:
            return self.exluded_type
        else:
            if pattern.search(str(copmared_path)):
                return not self.exluded_type
            else:
                return self.exluded_type

if __name__ == "__main__":
    base_directory = r"D:\temp"
    target_directory = r"C:\Users\Public\temp"
    a = FilesAndDirs(base_directory)
    a.files_regex = re.compile(r'(.*\.)', re.UNICODE)
    a.get_file_and_dir_path()
    for item in a.all_directory_path:
        print(item)
    print("-"*40)
    for item in a.full_path_with_files.keys():
        print(f'{item}: {a.full_path_with_files[item]}')
