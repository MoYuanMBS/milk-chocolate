import os
import shutil
from pathlib import Path

class filSyncTool():
    def __init__(self,original_folder_path:str,target_folder_path:str) -> None:
        '''
        初始化文件同步模块
        param original_folder_path: 原始文件夹路径
        param target_folder_path: 目标文件夹路径
        '''
        self.original_folder = filesAndDirs(original_folder_path)
        self.target_folder = self.target_folder = filesAndDirs(target_folder_path)

    def get_files_and_pathes(self):
        self.original_folder.get_file_and_dir_path()
        self.target_folder.get_file_and_dir_path()
        return 
    
    def compare_dir_path_difference(self,first_compare_path:set[Path],second_compare_path:set[Path])->set[Path]:
        '''
        比较原始文件夹和目标文件夹中的文件和目录
        '''
        comparied_pathes = first_compare_path - second_compare_path
        return comparied_pathes
    
    def compare_file_path_difference(self,first_compare_path:dict[Path,float],second_compare_path:dict[Path,float])->set[Path]:
        '''
        比较原始文件和目标文件中的文件
        返回缺失的文件路径
        '''
        return first_compare_path.keys() - second_compare_path.keys()

    def copy_files(self):
        '''
        仅复制缺失的文件到目标文件夹
        '''
        files_need_to_copy = self.compare_file_path_difference(self.original_folder.full_path_with_files, self.target_folder.full_path_with_files)

        # 复制缺失的文件
        for file in files_need_to_copy:
            oringinal_file_path = self.original_folder.current_directory / file
            target_file_path = self.target_folder.current_directory / file
            shutil.copy2(oringinal_file_path, target_file_path)
            print(f"Copied file: {oringinal_file_path} to {target_file_path}")
        return
    
    def remove_files(self):
        '''
        删除目标文件夹中多余的文件
        '''
        files_need_to_remove = self.compare_file_path_difference(self.target_folder.full_path_with_files, self.original_folder.full_path_with_files)

        # 删除多余的文件
        for file in files_need_to_remove:
            target_file_path = self.target_folder.current_directory / file
            if target_file_path.exists():
                target_file_path.unlink()
                print(f"Removed file: {target_file_path}")
        return
    
    def update_changed_files(self):
        '''
        更新目标文件夹中已更改的文件
        '''
        for files in self.original_folder.full_path_with_files.keys() & self.target_folder.full_path_with_files.keys():
            if self.original_folder.full_path_with_files[files] > self.target_folder.full_path_with_files[files]:
                original_file_path = self.original_folder.current_directory / files
                target_file_path = self.target_folder.current_directory / files
                if target_file_path.exists():
                    target_file_path.unlink()
                shutil.copy2(original_file_path, target_file_path)
                print(f"Updated file: {target_file_path}")

    
    def adding_directories(self):
        '''
        同步之前初始化好的目录
        会自动同步所有目录
        '''
        dir_need_to_create = self.compare_dir_path_difference(self.original_folder.all_directory_path, self.target_folder.all_directory_path)

        # 删除目标文件夹中多余的目录

        #创建缺失的目录
        for dir in dir_need_to_create:
            target_dir_path = self.target_folder.current_directory / dir
            target_dir_path.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {target_dir_path}")
        return
    
    def remove_directories(self):
        '''
        删除目标文件夹中多余的目录
        '''
        dir_need_to_remove = self.compare_dir_path_difference(self.target_folder.all_directory_path, self.original_folder.all_directory_path)

        # 删除多余的目录
        for dir in dir_need_to_remove:
            target_dir_path = self.target_folder.current_directory / dir
            if target_dir_path.exists() and not any (target_dir_path.iterdir()):
                target_dir_path.rmdir()  # 删除空目录
                print(f"Removed emptydirectory: {target_dir_path}")
        return




            




class filesAndDirs():
    def __init__(self,base_dir_path:str) -> None:
        self.current_directory = Path(base_dir_path)
        self.full_path_with_files = {}
        self.all_directory_path = set()
        return

    def get_file_and_dir_path(self):
        temp_directory_path_set = set()
        for item in set(Path.rglob(self.current_directory,'**/*')):
            if item.is_file():
                self.full_path_with_files[item.relative_to(self.current_directory)] = os.path.getmtime(item)
                temp_directory_path_set.add(item.parent.relative_to(self.current_directory))
            elif item.is_dir():
                temp_directory_path_set.add(item.relative_to(self.current_directory))
        # for item in temp_directory_path_set:
        #     print(item)
        self.simplify_directory_path(temp_directory_path_set)
        return 

    def simplify_directory_path(self, directory_path: set[Path]):

        for path in directory_path:
            # 移除当前路径的祖先路径，只有在路径层级足够时才进行比较
            to_remove = {item for item in self.all_directory_path if len(path.parts) >= len(item.parts) and path.parts[:len(item.parts)] == item.parts}
            self.all_directory_path -= to_remove
            
            # 只有当 item 的层级少于或等于 path 时，才检测 path 是否被覆盖
            if not any(len(item.parts) <= len(path.parts) and item.parts == path.parts[:len(item.parts)] for item in self.all_directory_path):
                self.all_directory_path.add(path)

        return
    



class filSyncModule(filSyncTool):
    def __init__(self, original_folder_path: str, target_folder_path: str) -> None:
        super().__init__(original_folder_path, target_folder_path)

    def copy_files_only(self):
        '''
        仅复制缺失的文件到目标文件夹
        '''
        self.get_files_and_pathes()
        self.adding_directories()
        self.copy_files()
        return
    
    def sync_files_only(self):
        '''
        仅复制和更新文件和目录
        '''
        self.get_files_and_pathes()
        self.adding_directories()
        self.copy_files()
        self.update_changed_files()
        return
    
    def sync_files_and_directories(self):
        '''
        完全同步文件和目录
        会删除多余文件及目录
        '''
        self.get_files_and_pathes()
        self.remove_files()
        self.remove_directories()
        self.adding_directories()
        self.copy_files()
        self.update_changed_files()
        return


# def simplify_directory_path(directory_path:set[Path]):
#     simplifyed_directory_path = set()
#     for path in directory_path:
#         for item in simplifyed_directory_path:
#             if set(path.parts) >= set(item.parts):
#                 print(set(path.parts))
#                 print(set(item.parts))
#                 simplifyed_directory_path.remove(item)
#                 simplifyed_directory_path.add(path)
#             elif set(path.parts) <= set(item.parts):
#                 pass
#             else:
#                 simplifyed_directory_path.add(path)
#     if not simplifyed_directory_path:
#         print("No directory path found.")
#     for item in simplifyed_directory_path:
#         print(item)
#     return simplify_directory_path

if __name__ == "__main__":
    base_directory = r'D:\temp'
    target_directory = r'C:\Users\Public\test'
    first_file = filesAndDirs(base_directory)
    first_file.get_file_and_dir_path()
    for item in first_file.all_directory_path:
        print(item)
    
    c = filSyncModule(base_directory, target_directory)
    c.sync_files_and_directories()
    

        


        


























# for directory_path, directory, files in os.walk(base_directory,topdown=True):
#     # print(f"Directory_path: {directory_path}")
#     # print(f"Directory: {directory}")
#     # print(f"Files: {files}")
#     if files:
#         for file in files:
#             full_path = os.path.join(directory_path, file)
#             full_path_with_files.add(full_path)
#     elif directory:
#         for dir in directory:
#             full_directory_path =os.path.join(directory_path, dir)
#             for item in full_path_with_files:
#                 if item.startswith(full_directory_path + os.sep) and item != full_directory_path:


#     def remove_common_path(path1:str,path2:str) -> str:
#         common_path = os.path.commonpath([path1, path2])
#         revelent_path_1 = path1.relative_to(common_path)
#         revelent_path_2 = path2.relative_to(common_path)