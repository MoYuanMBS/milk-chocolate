import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

def copy_file(original_file_path, target_file_path):
    shutil.copy2(original_file_path, target_file_path)
    print(f"Copied file: {original_file_path} to {target_file_path}")

def copy_files(self):
    '''
    仅复制缺失的文件到目标文件夹，通过多线程提高效率
    '''
    files_need_to_copy = self.compare_file_path_difference(self.original_folder.full_path_with_files, self.target_folder.full_path_with_files)

    # 创建线程池
    with ThreadPoolExecutor() as executor:
        futures = []
        for file in files_need_to_copy:
            original_file_path = self.original_folder.current_directory / file
            target_file_path = self.target_folder.current_directory / file
            # 提交每个文件复制任务到线程池
            future = executor.submit(copy_file, original_file_path, target_file_path)
            futures.append(future)
        
        # 等待所有线程完成
        for future in as_completed(futures):
            try:
                future.result()  # 可以用于捕获异常
            except Exception as e:
                print(f"Error copying file: {e}")

    return