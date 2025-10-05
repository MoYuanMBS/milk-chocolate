
class StatusTracker:
    """
    一个用于跟踪文件操作状态的类。这个类维护一个全局状态字典，包含当前处理状态的上下文信息。
    """
    _status: dict[str, tuple[str, str]] = {}
    _error_status: dict[str, tuple[str, str]] = {}

    @classmethod
    def update(cls, context: str, source_file: str, target_file: str) -> None:
        """
        更新状态字典中的当前上下文和状态信息。
        """
        cls._status[context] = (source_file, target_file)
        cls.print_status()
        cls._status = {}

    @classmethod
    def error_update(cls, context: str, source_file: str, reason: str) -> None:
        """
        更新错误状态字典中的当前上下文和状态信息。
        """
        cls._error_status[context] = (source_file, reason)
        cls.print_error_status()
        cls._error_status = {}

    @classmethod
    def print_status(cls) -> None:
        """打印所有处理过程的当前状态。"""
        for context, files in cls._status.items():
            print(f'{context}:{files[0]} -> {files[1]}')
    
    @classmethod
    def print_error_status(cls) -> None:
        """打印所有处理过程的错误状态。"""
        for context, files in cls._error_status.items():
            print(f'{context}:{files[0]} -> {files[1]}')


