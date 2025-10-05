from sync_files import FileSyncTool

class FileSyncModule(FileSyncTool):
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
    import time
    base_directory = r"D:\temp"
    target_directory = r"C:\Users\Public\temp"
    ignored_dir = {"asdsdasd"}
    ignored_files = {"test.txt", "example.docx"}
    ignored_dir_regex = r'testtt'
    ignored_files_regex = r'.*\.py$|test\.txt$'
    # first_file = filesAndDirs(base_directory)
    # first_file.get_file_and_dir_path(set(), set(), set())
    # for item in first_file.all_directory_path:
    #     print(item)

    start_time = time.time()
    c = FileSyncModule(base_directory, target_directory)
    # c.ignored_files_and_directories(directories=ignored_dir, files=ignored_files)
    c.advanced_file_and_directory_filtering(ignored_files_regex, ignored_dir_regex, True)
    c.sync_files_and_directories()
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")