"""
网络连接配置模块
用于管理 WebSocket 连接的安全模式
"""
import re
import ssl
import socket
import uuid
import pickle
from pathlib import Path
from typing import Literal, Optional
from status_tracker import StatusTracker


class SelfSignedCertManager:
    """自签名证书管理类"""

    def __init__(self) -> None:

        self.certs_dir:Path = Path(__file__).parent / "certs"
        # 自签ca路径
        self.ca_path: Path = self.certs_dir / "ca"
        self.ca_cert: Path = self.ca_path / "ca.crt" 
        # 服务端证书和密钥文件路径
        self.server_path: Path = self.certs_dir / "server"
        self.server_cert: Path = self.server_path / "server.crt"
        self.server_key: Path = self.server_path / "server.key"
        # 客户端证书和密钥文件路径
        self.client_path: Path = self.certs_dir / "clients"
        self.client_crt: Path = self.client_path / "client.crt"
        self.client_key: Path = self.client_path / "client.key"
        
        # 创建证书目录
        self.ca_path.mkdir(parents=True, exist_ok=True)
        self.server_path.mkdir(parents=True, exist_ok=True)
        self.client_path.mkdir(parents=True, exist_ok=True)

    def update_selfsigned_cert_paths(self, certs_path: Path) -> None:
        """
        更新自签名证书路径
        """
        self.certs_dir = certs_path
        
        self.ca_path = self.certs_dir / "ca"
        self.ca_cert = self.ca_path / "ca.crt"
        
        self.server_path = self.certs_dir / "server"
        self.server_cert = self.server_path / "server.crt" 
        self.server_key = self.server_path / "server.key"

        self.client_path = self.certs_dir / "clients"
        self.client_crt = self.client_path / "client.crt"
        self.client_key = self.client_path / "client.key"

        self.ca_path.mkdir(parents=True, exist_ok=True)
        self.server_path.mkdir(parents=True, exist_ok=True)
        self.client_path.mkdir(parents=True, exist_ok=True)

 
    def generate_client_id(self) -> str:
        """生成唯一的客户端ID"""
        # 基于主机名和UUID的一部分生成ID
        host_name = socket.gethostname().replace('.', '-').replace('_', ' ')
        str_uuid = (str(uuid.uuid4()).split('-')[1])
        return f"{host_name}-{str_uuid}"


    def check_certs_for_client(self) -> None:
        """
        检查证书文件是否存在
        """
        if self.server_cert.exists() and self.client_crt.exists() and self.ca_cert.exists():
            return
        else:
            raise FileNotFoundError("Client certificate files not found or incomplete.")

    def check_cert_files_for_server(self) -> None:
        """
        检查服务器证书文件是否存在
        """
        if self.server_cert.exists() and self.server_key.exists() and self.client_crt.exists() and self.ca_cert.exists():
            return
        else:
            raise FileNotFoundError("Server certificate files not found or incomplete.")


class NetworkConfig(SelfSignedCertManager):
    """网络连接配置类"""

    def __init__(self):
        super().__init__()

        # 服务器配置
        self.__host: str = "localhost"
        self.__port: int = 8765
        self.__use_self_signed_cert: bool = False

        # 安全配置
        self._is_encrypted: bool = False  # 默认不允许明文连接（生产环境）
        self._developer_mode: bool = True   # 开发者模式

    @property
    def allow_plaintext(self) -> bool:
        """是否允许明文连接（仅用于开发）"""
        return self._is_encrypted

    @allow_plaintext.setter
    def allow_plaintext(self, value: bool):
        """
        设置是否允许明文连接
        仅开发模式可用
        """
        if value:
            if self._developer_mode:
                self._is_encrypted = value
                StatusTracker.basic_information_update('allow plaintext', str(value))
            else:
                StatusTracker.warning_update('allow plaintext', 'developer mode unable', 'False')
        else:
            self._is_encrypted = value
            StatusTracker.basic_information_update('allow plaintext', str(value))

    def has_certificates(self) -> bool:
        """检查证书文件是否存在"""
        return self.server_cert.exists() and self.server_key.exists()
    
    @property
    def self_signed_crt_mode(self) -> bool:
        """是否使用自签名证书"""
        return self.__use_self_signed_cert
    
    @self_signed_crt_mode.setter
    def self_signed_crt_mode(self, value: bool) -> None:
        """设置是否使用自签名证书"""
        if value:
            self.check_certs_for_client()
            self.__use_self_signed_cert = value
        else:
            self.__use_self_signed_cert = value
        return

    def get_server_uri(self) -> str:
        """
        获取服务器 URI
        Returns:WebSocket URI
        """
        protocol = "ws" if self._is_encrypted else "wss"
        return f"{protocol}://{self.__host}:{self.__port}"
    
    @property
    def host_and_port(self) -> tuple[str, int]:
        """获取主机和端口"""
        return self.__host, self.__port
    
    @host_and_port.setter
    def set_server_address(self, host: str, port: int) -> None:
        """设置服务器地址和端口"""
        # 验证主机名
        if re.match(r"^[a-zA-Z0-9.\-:]+$", host):
            self.__host = host
            StatusTracker.basic_information_update('set host', host)
        else:
            raise ValueError("invalid host name")
        # 验证端口号
        if 0 < port < 65536:
            self.__port = port
            StatusTracker.basic_information_update('set port', str(port))
        else:
            StatusTracker.warning_update('set port', 'port is invalid', 'use default')

# 全局配置实例
config = NetworkConfig()

if __name__ == "__main__":
    test_config = NetworkConfig()
    print(test_config.ca_path)


