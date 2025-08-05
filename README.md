# milk-chocolate
####**Milk Chocolate** 是一个文件夹同步模块，亦可以当作命令行文件同步器。
**目前支持的功能：**
- 本模块仅使用**Python 标准库**，无需安装其他依赖项！！！
- 支持Windows，Mac和Linux文件夹
	- 也支持不同系统文件夹相互同步
	（当然你要能读到其他系统文件夹哈！）
- 支持空文件夹同步
- 支持文件更新同步
- 支持使用正则表达式pass文件及文件夹
- 支持pass文件或文件夹时候选择忽略或只读模式
- 不会使用正则表达式的话也不用担心哦！
	- 也支持简单的文件及问价夹筛选功能
	~~其实会自动帮你写正则啦~~~

**To do list:**
- 支持局域网及服务器文件夹同步
	- 个人nas同步
	- 服务器同步文件用以备份等
- 支持一下正则保存，调用什么的
- 完善debug logger
- 可以的话用yield作为return来替换现有的运行内print
	-  这样就可以自定义输出语言什么的惹~

####调用方法：
**初始化**
``` python
from sync_files import fileSyncModule

#Initialize with original_folder_path & target_folder_path
original_folder_path = r'C:\Users\Username\Samples\examples' 
target_folder_path = r'I:\vtuber\MeUmy\745493\T'

sfm = fileSyncModule(orinal, target)
```
**添加需要过滤的文件/文件夹**
```python
#如果你会使用正则表达式，可以使用下面的代码来忽略特定的文件或目录
file_ignore = r'(.*\.mp4|.*\.jpg|.*\.png|.*\.gif|.*\.webp|.*\.jpeg)'
dir_ignore = r'(.*\.git|.*\.idea|.*\.vscode|.*\.DS_Store)'
#需要注意的是，这里take的是正则表达式的字符串形式，而不是编译后的正则表达式对象
#正则是使用unicode模式，仅包含\u4e00-\u9fff以及范围内的字符
#如果想改变的话请使用以下函数先行修改：
sfm._change_allowed_regex_pattern(r"^[\w\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\u31f0-\u31ff\u3000-\u303f\uff66-\uff9f]+$") #支持日文

sfm.advanced_file_and_directory_filtering(file_ignore, dir_ignore,ignored_type=True)
#这里的ignored_type=True表示忽略文件和目录，默认为True表示忽略文件, True切换为只读写对应文件&文件夹模式

#如果你不会使用正则表达式，也可使用简易过滤模式：
ignored_files_set = {'AveMujica.mp4', 'example.txt'}
ignored_dirs_set = {'example_dir', 'test_folder'}
sfm.ignored_files_and_directories(ignored_files_set, ignored_dirs_set, ignored_type=True)
#ignored_files_set必须是完整文件名
#ignored_dirs_set必须是文件夹名
#这里的ignored_type=True表示忽略文件和目录，默认为True表示忽略文件, True切换为只读写对应文件&文件夹模式
```
**调用**
```python
sfm.sync_files_and_directories()
#有不函数可供切换不同同模式使用
```
好了，您已经学会如何使用了，赶紧pull下来使用吧！

####依赖要求：
- 推荐使用:
**Python 3.10 +**
- 最低配置：
**Python 3.8 +**

####碎碎念：
- A:为什么项目名字叫**Milk Chocolate**？
	- 一定是有个[起名字的人](https://github.com/LaoshuBaby)在贪吃惹！
