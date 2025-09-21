import enum

class StatusTracker:
    """
    一个用于跟踪文件操作状态的类。这个类维护一个全局状态字典，包含当前处理状态的上下文信息。
    """
    _status: dict[str, dict[str, str]] = {}

    @classmethod
    def update(cls, context: str, source_file: str, target_file: str) -> None:
        """
        更新状态字典中的当前上下文和状态信息。

        参数:
            context (str): 正在执行的处理类型（例如，'hashing', 'processing_large_file'）。
            file_identifier (str): 正在处理的文件标识符。
            message (str): 描述当前处理状态的信息。
        """
        if context not in cls._status:
            cls._status[context] = {}
            cls._status[context][source_file] = target_file
        elif source_file not in cls._status[context]:
            cls._status[context] = {}
            cls._status[context][source_file] = target_file
        cls.print_status()

    @classmethod
    def print_status(cls) -> None:
        """打印所有处理过程的当前状态。"""

        print(f"当前状态: {cls._status}")


