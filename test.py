letters = 5
c = letters * (10 ** 1)

print(c)  # Output: 50000

from pathlib import Path

def simplify_directory_set(directories):
    # 将输入的目录转换为 WindowsPath 对象并排序
    paths = sorted(Path(d) for d in directories)
    simplified_paths = set()  # 使用集合来存储简化后的路径

    for path in paths:
        # 标志用来决定是否将当前路径添加到集合中
        should_add = True  

        # 检查当前路径的父路径是否已经在集合中
        for parent in path.parents:
            if parent in simplified_paths:
                should_add = False  # 找到已有父路径，不需要添加
                break  

        if should_add:
            simplified_paths.add(path)  # 添加到集合

    # 返回集合，集合中的元素是 WindowsPath 对象
    return simplified_paths

# 示例目录列表
directories = [
    "1086940\\remote\\_SAVE_Public\\Savegames\\Story\\氲-32121233741__AutoSave_11",
    "1086940\\remote\\_SAVE_Public\\Savegames\\Story\\氲-461012323752__QuickSave_6",
    "1066780\\local\\texture_cache\\B35067087D07F808099643BC9BEE5F93",
    "1066780\\local\\texture_cache",
    "227300\\remote\\profiles\\E9A6A7E38082\\save\\1",
    "config\\shaderhitcache\\c66a1b49f8999bb9\\04545f553948f7c85fba8f9da48b172c",
    "1086940\\remote\\_SAVE_Public\\Savegames\\Story\\氲-411012321734__AutoSave_2"
]

simplified_directories = simplify_directory_set(directories)

for directory in simplified_directories:
    print(directory)


a = set([1, 2, 3])
b = set([3, 4, 5])

print(a - b) 
print(b - a)
# 输出: {1, 2}

c = {1: 'a', 2: 'b', 3: 'c'}
b = {3: 'f', 4: 'd', 5: 'e'}
print(c.keys() - b.keys())  # 输出: {1, 2}
print(type(b.keys() - c.keys()) )  # 输出: {4, 5}

for k, v in c.items():
    print(k, v)

d = {'a': 1, 'b': 2, 'c': 3}
e = {'c': 4, 'd': 5, 'e': 6}

for key in d.keys() & e.keys():
    if d[key] > e[key]:
        print('ahhhh')
    else:
        print('bhhhh')
