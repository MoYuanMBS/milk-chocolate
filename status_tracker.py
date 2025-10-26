from pathlib import Path
from datetime import datetime, timezone

class StatusTracker:
    """
    一个用于跟踪文件操作状态的类。这个类维护一个全局状态字典，包含当前处理状态的上下文信息。
    使用时间戳+计数器作为key存储完整日志历史。
    """
    _status: dict[int, tuple[str, str, str]] = {}  # {timestamp_id: (context, source_file, target_file)}
    _warning_status: dict[int, tuple[str, str, str]] = {}  # {timestamp_id: (context, reason, status)}
    _error_status: dict[int, tuple[str, str, str]] = {}  # {timestamp_id: (context, reason, status)}
    _basic_imformations: dict[str, str] = {}  # {information: changed_to}
    _counter: int = 0
    _last_timestamp: str = ""
    server_mode: bool = False

    @classmethod
    def _generate_timestamp_id(cls) -> int:
        """
        生成基于时间的唯一ID，格式: YYYYMMDDHHMMSSxx (int)
        """
        now = datetime.now(timezone.utc)
        current_timestamp = now.strftime('%Y%m%d%H%M%S')

        # 如果时间戳变了（新的一秒），重置计数器
        if cls._last_timestamp != current_timestamp:
            cls._counter = 0
            cls._last_timestamp = current_timestamp

        cls._counter += 1
        # 返回int: 时间戳 + 3位计数器
        return int(current_timestamp) * 1000 + cls._counter

    @classmethod
    def update(cls, context: str, source_file: str, target_file: str) -> None:
        """
        更新状态字典中的当前上下文和状态信息。
        """
        id = cls._generate_timestamp_id()
        cls._status[id] = (context, source_file, target_file)
        cls.__print_status(id)

    @classmethod
    def error_update(cls, context: str, reason: str, status: str) -> None:
        """
        更新错误状态字典中的当前上下文和状态信息。
        """
        id = cls._generate_timestamp_id()
        cls._error_status[id] = (context, reason, status)
        cls.__print_error_status(id)
    
    @classmethod
    def basic_information_update(cls, infor: str, changed_to: str) -> None:
        """
        更新基本信息。
        """
        cls._basic_imformations[infor] = changed_to
        cls.__print_basic_information(infor)

    @classmethod
    def warning_update(cls, context: str, reason: str, status: str) -> None:
        """
        更新警告状态字典中的当前上下文和状态信息。
        """
        id = cls._generate_timestamp_id()
        cls._warning_status[id] = (context, reason, status)


##############################      print status    #################### 
    
    
    @classmethod
    def __print_status(cls, id: int) -> None:
        """打印所有处理过程的当前状态。"""
        print_str = cls._status[id]
        print(f'{print_str[0]}:{print_str[1]} -> {print_str[2]}')
        if cls.server_mode:
            pass

    @classmethod
    def __print_error_status(cls, id: int) -> None:
        """打印所有处理过程的错误状态。"""
        print_str = cls._error_status[id]
        print(f'{print_str[0]} error:{print_str[1]} -> {print_str[2]}')
    
    @classmethod
    def __print_basic_information(cls, infor:str) -> None:
        """打印基本信息。"""
        print(f'Information:{infor} is changed to {cls._basic_imformations[infor]}')




##############################      log process    #################### 

    @classmethod
    def write_log_to_file(cls) -> None:
        now = datetime.now()
        current_timestamp = now.strftime('%Y%m%d%H%M%S')
        log_path = Path.cwd() / 'log' / f'{current_timestamp}.log'
        events_time: set[int] = cls._status.keys() | cls._error_status.keys()
        
        def date_formate(date_id:str):
            '''
            id转日期
            '''
            date = date_id[:-3:]
            date_utc = datetime.strptime(date,"%Y%m%d%H%M%S")
            dt_utc = date_utc.replace(tzinfo=timezone.utc)   # 标记为 UTC
            dt_local = dt_utc.astimezone()  
            return dt_local

        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, 'a+', encoding='utf-8') as log:
                log.write('【basic infor】\n')
                for key, value in cls._basic_imformations.items():
                    log.write(f'{key}:{value}\n')
                log.write(f'\n{"-"*30}\n')
                for date_id in sorted(events_time):
                    if date_id in cls._status.keys():
                        date = date_formate(str(date_id))
                        content, file, path = cls._status[date_id]
                        write_str = f'【{date}】 【Status】 {content}:{file} -> {path}'
                    elif date_id in cls._error_status.keys():
                        date = date_formate(str(date_id))
                        content, file, path = cls._error_status[date_id]
                        write_str = f'【{date}】 【Error】 {content}:{file} -> {path}'
                    else:
                        write_str = ''
                    log.write(write_str)
                    log.write('\n')
        except Exception as e:
            cls.error_update('write logs', str(e), 'failed')
        

if __name__ == "__main__":
    StatusTracker.basic_information_update('123','gfdgdf')
    StatusTracker.update('write','aac','chjd')
    StatusTracker.update('write','afdf','ch大使d')
    StatusTracker.update('write','aafdfc','你说的')
    StatusTracker.write_log_to_file()