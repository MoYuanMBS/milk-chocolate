import os
import re
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


class fileSyncTool:
    def __init__(self, original_folder_path: str, target_folder_path: str) -> None:
        """
        初始化文件同步模块
        param original_folder_path: 原始文件夹路径
        param target_folder_path: 目标文件夹路径
        """
        self.__original_folder = filesAndDirs(original_folder_path)
        self.__target_folder = filesAndDirs(target_folder_path)
        self.__chunk_size = 4096 * 4096  # 4MB
        self.__allowed_regex_pattern: re.Pattern = re.compile(
            r"^[\w\u4e00-\u9fff.*?]+$", re.UNICODE
        )
        self.__ignored_files_regex: re.Pattern | None = None
        self.__ignored_directories_regex: re.Pattern | None = None
        self.__ignored_type: bool = True  # 忽略/只读文件和目录

    def _get_files_and_pathes(self):
        self.__original_folder.get_file_and_dir_path(
            self.__ignored_files_regex,
            self.__ignored_directories_regex,
            self.__ignored_type,
        )
        self.__target_folder.get_file_and_dir_path(
            self.__ignored_files_regex,
            self.__ignored_directories_regex,
            self.__ignored_type,
        )
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

    def __copy_file_with_chunk(
        self, organinal_file_path: Path, target_file_path: Path, print_ticket: int
    ):
        with open(organinal_file_path, "rb") as src_file, open(
            target_file_path, "wb"
        ) as dst_file:
            while True:
                chunk = src_file.read(self.__chunk_size)
                if not chunk:
                    break
                dst_file.write(chunk)
        if print_ticket == 3:
            print(f"Copied file: {organinal_file_path} to {target_file_path}")
        elif print_ticket == 4:
            print(f"updated file: {target_file_path}")

    def _copy_files(self):
        """
        仅复制缺失的文件到目标文件夹
        """
        files_need_to_copy = self.__compare_file_path_difference(
            self.__original_folder.full_path_with_files,
            self.__target_folder.full_path_with_files,
        )

        # 复制缺失的文件
        with ThreadPoolExecutor() as executor:
            futures = []
            for file in files_need_to_copy:
                original_file_path = self.__original_folder.current_directory / file
                target_file_path = self.__target_folder.current_directory / file
                future = executor.submit(
                    self.__copy_file_with_chunk, original_file_path, target_file_path, 3
                )
                futures.append(future)

            # 等待所有线程完成
            for future in as_completed(futures):
                try:
                    future.result()  # 可以用于捕获异常
                except Exception as e:
                    print(f"Error copying file: {e}")

        return

    def _remove_files(self):
        """
        删除目标文件夹中多余的文件
        """
        files_need_to_remove = self.__compare_file_path_difference(
            self.__target_folder.full_path_with_files,
            self.__original_folder.full_path_with_files,
        )

        # 删除多余的文件
        for file in files_need_to_remove:
            target_file_path = self.__target_folder.current_directory / file
            if target_file_path.exists():
                target_file_path.unlink()
                print(f"Removed file: {target_file_path}")
        return

    def _update_changed_files(self):
        """
        更新目标文件夹中已更改的文件
        """
        with ThreadPoolExecutor() as executor:
            futures = []
            # 更新已更改的文件
            for files in (
                self.__original_folder.full_path_with_files.keys()
                & self.__target_folder.full_path_with_files.keys()
            ):
                if (
                    self.__original_folder.full_path_with_files[files]
                    > self.__target_folder.full_path_with_files[files]
                ):
                    original_file_path = (
                        self.__original_folder.current_directory / files
                    )
                    target_file_path = self.__target_folder.current_directory / files
                    if target_file_path.exists():
                        target_file_path.unlink()
                    future = executor.submit(
                        self.__copy_file_with_chunk,
                        original_file_path,
                        target_file_path,
                        4,
                    )
                    futures.append(future)

            # 等待所有线程完成
            for future in as_completed(futures):
                try:
                    future.result()  # 可以用于捕获异常
                except Exception as e:
                    print(f"Error updating file: {e}")

    def _adding_directories(self):
        """
        同步之前初始化好的目录
        会自动同步所有目录
        """
        dir_need_to_create = self.__compare_dir_path_difference(
            self.__original_folder.all_directory_path,
            self.__target_folder.all_directory_path,
        )

        # 删除目标文件夹中多余的目录

        # 创建缺失的目录
        for dir in dir_need_to_create:
            target_dir_path = self.__target_folder.current_directory / dir
            target_dir_path.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {target_dir_path}")
        return

    def _remove_directories(self):
        """
        删除目标文件夹中多余的目录
        """
        dir_need_to_remove = {}

        def remove_empty_dirs(path: Path, depth: int) -> bool:
            path_temp = path
            for _ in range(depth):
                if not path_temp.exists():
                    return False
                for item in path_temp.iterdir():
                    if item.is_file():
                        return False
                shutil.rmtree(path_temp, ignore_errors=True)
                path_temp = path_temp.parent
            return True

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

        for dir_path, depth in dir_need_to_remove.items():
            if remove_empty_dirs(dir_path, depth):
                print(f"Removed directory: {dir_path}")
        return

    def change_chunk_size(self, chunk_size: int):
        """
        修改文件复制的块大小
        """
        if chunk_size > 0:
            self.__chunk_size = chunk_size
        else:
            raise ValueError("Chunk size must be a positive integer.")
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
        ignored_type: bool = True,
    ):
        """
        仅复制符合正则表达式的文件
        不可与ignored_files_and_directories同时使用
        """
        if not self.__allowed_regex_pattern.match(file_pattern):
            return "Invalid file pattern. Only alphanumeric characters, underscores, and certain symbols are allowed."
        else:
            if file_pattern:
                self.__ignored_files_regex = re.compile(file_pattern)

        if not self.__allowed_regex_pattern.match(directory_pattern):
            return "Invalid directory pattern. Only alphanumeric characters, underscores, and certain symbols are allowed."
        else:
            if directory_pattern:
                self.__ignored_directories_regex = re.compile(directory_pattern)

        self.__ignored_type = ignored_type
        return

    def ignored_files_and_directories(
        self,
        files: set[str] = set(),
        directories: set[str] = set(),
        ignored_type: bool = True,
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
        self.__ignored_files_regex = (
            re.compile(files_patterns[:-1]) if files_patterns else None
        )

        dir_patterns: str = ""
        for directory in directories:
            if directory not in erro_dir_names:
                dir_patterns += f"{re.escape(directory)}|"
        self.__ignored_directories_regex = (
            re.compile(dir_patterns[:-1]) if dir_patterns else None
        )

        self.__ignored_type = ignored_type
        return


class filesAndDirs:
    def __init__(self, base_dir_path: str) -> None:
        self.current_directory = Path(base_dir_path)
        self.full_path_with_files: dict[Path, float] = {}
        self.all_directory_path = set()
        return

    def get_file_and_dir_path(
        self,
        files_ignored_regex: re.Pattern | None,
        directories_ignored_regex: re.Pattern | None,
        ignore_type: bool,
    ):
        temp_directory_path_set = set()
        for item in set(Path.rglob(self.current_directory, "**/*")):
            if item.is_file():
                temp_file_result = self.filtering(
                    item.name, files_ignored_regex, ignore_type
                )
                temp_dir_result = self.filtering(
                    item, directories_ignored_regex, ignore_type
                )
                if (
                    (temp_file_result and temp_dir_result)
                    if ignore_type
                    else (temp_file_result or temp_dir_result)
                ):
                    self.full_path_with_files[
                        item.relative_to(self.current_directory)
                    ] = os.path.getmtime(item)
                    temp_directory_path_set.add(
                        item.parent.relative_to(self.current_directory)
                    )
            elif item.is_dir():
                if self.filtering(item, directories_ignored_regex, ignore_type):
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
        self, copmared_path: Path | str, pattern: re.Pattern | None, ignored_type: bool
    ) -> bool:
        """
        过滤文件和目录
        copmared_path: 需要过滤的路径
        pattern: 正则表达式模式
        ignored_type: 是否忽略只读文件和目录
        """
        if pattern is None:
            return True if ignored_type else False
        else:
            if pattern.search(str(copmared_path)):
                return False if ignored_type else True
            else:
                return True if ignored_type else False


class fileSyncModule(fileSyncTool):
    def __init__(self, original_folder_path: str, target_folder_path: str) -> None:
        super().__init__(original_folder_path, target_folder_path)

    def copy_files_only(self):
        """
        仅复制缺失的文件到目标文件夹
        """
        self._get_files_and_pathes()
        self._adding_directories()
        self._copy_files()
        return

    def sync_files_only(self):
        """
        仅复制缺失和更新修改过的文件
        """
        self._get_files_and_pathes()
        self._adding_directories()
        self._copy_files()
        self._update_changed_files()
        return

    def sync_files_and_directories(self):
        """
        完全同步文件和目录
        会删除多余文件及目录
        """
        self._get_files_and_pathes()
        self._remove_files()
        self._remove_directories()
        self._adding_directories()
        self._copy_files()
        self._update_changed_files()
        return

    def update_files(self):
        """
        仅同步以更改的文件
        """
        self._get_files_and_pathes()
        self._update_changed_files()
        return
    
    def Delete_excess_files(self):
        """
        删除目标文件夹中多余的文件和目录
        """
        self._get_files_and_pathes()
        self._remove_files()
        self._remove_directories()
        return


if __name__ == "__main__":
    base_directory = r"D:\temp"
    target_directory = r"C:\Users\Public\test"
    ignored_dir = {"asdsdasd"}
    ignored_files = {"test.txt", "example.docx"}
    # first_file = filesAndDirs(base_directory)
    # first_file.get_file_and_dir_path(set(), set(), set())
    # for item in first_file.all_directory_path:
    #     print(item)

    c = fileSyncModule(base_directory, target_directory)
    c.ignored_files_and_directories(directories=ignored_dir, files=ignored_files)
    c.sync_files_and_directories()

