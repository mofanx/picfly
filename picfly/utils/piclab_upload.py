"""PicLab 图片上传工具类。

使用前请在环境变量中配置:

* ``PICLAB_BASE_URL``: 上传接口地址
* ``PICLAB_API_KEY``: 认证所需的 Bearer Token
* ``PICLAB_VERIFY_SSL``: (可选) ``false`` 时跳过证书校验
* ``PICLAB_TIMEOUT``: (可选) 默认请求超时时间，单位秒
* ``PICLAB_USE_SYSTEM_PROXY``: (可选) ``true`` 时允许读取系统/环境代理

示例:

>>> uploader = PicLabUploader()
>>> result = uploader.upload("/path/to/local.png")
>>> print(result)
"""

from __future__ import annotations

import base64
import os
import re
import time
from io import BytesIO
from mimetypes import guess_type
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
from urllib.parse import unquote, urlparse

import requests

try:  # PIL 在截图脚本中已使用，这里再次尝试导入
    from PIL import Image
except ImportError:  # pragma: no cover - PIL 不可用时优雅降级
    Image = None  # type: ignore


class PicLabUploader:
    """封装 PicLab 图床上传接口，支持多种图片输入来源."""

    _KNOWN_SUFFIXES = {
        "png",
        "jpg",
        "jpeg",
        "jfif",
        "gif",
        "bmp",
        "tif",
        "tiff",
        "webp",
        "heic",
        "heif",
        "heics",
        "heifs",
        "avif",
        "svg",
        "ico",
    }

    def __init__(
        self,
        base_url: Optional[str] = None,
        API_KEY: Optional[str] = None,
        *,
        verify_ssl: Optional[bool] = None,
        timeout: Optional[int] = None,
        use_system_proxy: Optional[bool] = None,
    ) -> None:
        self.base_url = base_url or os.getenv("PICLAB_BASE_URL")
        self.API_KEY = API_KEY or os.getenv("PICLAB_API_KEY")
        self.verify_ssl = (
            verify_ssl
            if verify_ssl is not None
            else self._env_flag(os.getenv("PICLAB_VERIFY_SSL", "true"))
        )
        self.timeout = timeout or int(os.getenv("PICLAB_TIMEOUT", "30"))
        use_system_proxy = (
            use_system_proxy
            if use_system_proxy is not None
            else self._env_flag(os.getenv("PICLAB_USE_SYSTEM_PROXY", "false"))
        )
        self._session = requests.Session()
        self._session.trust_env = use_system_proxy
        if not self.base_url:
            raise ValueError("未配置 PICLAB_BASE_URL 环境变量或 base_url 参数。")
        if not self.API_KEY:
            raise ValueError("未配置 PICLAB_API_KEY 环境变量或 API_KEY 参数。")

    def upload(
        self,
        source: Union[str, bytes, bytearray, Path, "Image.Image", BytesIO],
        *,
        filename: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """上传图片到 PicLab.

        参数:
            source: 图片来源，支持
                - 远程图片 URL (以 http/https 开头的字符串)
                - 本地文件路径或 Path 对象
                - 原始二进制数据 (bytes、bytearray、BytesIO)
                - Pillow Image 对象 (例如 ImageGrab.grab 的结果)
                - base64 编码字符串 (可包含 data:image/...;base64, 前缀)
            filename: 上传时使用的文件名，缺省则自动生成。
            timeout: 网络请求超时时间，秒。

        返回:
            接口返回的 JSON 数据；若响应非 JSON，将返回包含 status_code 与 raw 文本的字典。
        """

        try:
            file_bytes, resolved_name, mime_type = self._prepare_file_payload(source, filename)
        except requests.exceptions.Timeout as exc:
            return {"success": False, "error": f"下载远程图片超时: {exc}"}
        except requests.exceptions.ConnectionError as exc:
            return {"success": False, "error": f"下载远程图片连接失败: {exc}"}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "error": f"下载远程图片失败: {exc}"}

        headers = {"Authorization": f"Bearer {self.API_KEY}"}
        files = {"file": (resolved_name, file_bytes, mime_type)}

        try:
            response = self._session.post(
                self.base_url,
                headers=headers,
                files=files,
                timeout=timeout or self.timeout,
                verify=self.verify_ssl,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as exc:
            return {"success": False, "error": f"上传超时: {exc}"}
        except requests.exceptions.ConnectionError as exc:
            return {"success": False, "error": f"上传连接失败: {exc}"}
        except requests.HTTPError as exc:
            detail = self._extract_error_detail(response)
            return {"success": False, "error": f"上传失败: {exc} | Response: {detail}"}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "error": f"上传请求失败: {exc}"}

        try:
            return response.json()
        except ValueError:
            return {"status_code": response.status_code, "raw": response.text}

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------
    def _prepare_file_payload(
        self,
        source: Union[str, bytes, bytearray, Path, "Image.Image", BytesIO],
        filename: Optional[str],
    ) -> Tuple[bytes, str, str]:
        if isinstance(source, (bytes, bytearray)):
            resolved_name = self._finalize_filename(filename)
            return bytes(source), resolved_name, self._guess_mime(resolved_name)

        if isinstance(source, BytesIO):
            resolved_name = self._finalize_filename(filename)
            return source.getvalue(), resolved_name, self._guess_mime(resolved_name)

        if Image is not None and isinstance(source, Image.Image):
            buffer = BytesIO()
            fmt = (source.format or "PNG").upper()
            source.save(buffer, format=fmt)
            resolved_name = self._finalize_filename(filename, fallback_suffix=fmt.lower())
            return buffer.getvalue(), resolved_name, f"image/{fmt.lower()}"

        if isinstance(source, Path):
            raw_name = filename or source.name
            suffix = Path(raw_name).suffix.lstrip(".") or "png"
            resolved_name = self._finalize_filename(raw_name, fallback_suffix=suffix)
            return source.read_bytes(), resolved_name, self._guess_mime(resolved_name)

        if isinstance(source, str):
            source = source.strip()
            if source.lower().startswith(("http://", "https://")):
                return self._download_remote_file(source, filename)

            possible_path = Path(source)
            if possible_path.exists():
                raw_name = filename or possible_path.name
                suffix = possible_path.suffix.lstrip(".") or "png"
                resolved_name = self._finalize_filename(raw_name, fallback_suffix=suffix)
                return possible_path.read_bytes(), resolved_name, self._guess_mime(resolved_name)

            b64_data = self._decode_base64(source)
            if b64_data is not None:
                resolved_name = self._finalize_filename(filename)
                return b64_data, resolved_name, self._guess_mime(resolved_name)

            raise ValueError("无法识别的字符串来源：既不是 URL、本地路径，也不是有效的 base64 数据。")

        raise TypeError("不支持的 source 类型，请传入路径、URL、bytes、BytesIO、Pillow Image 或 base64 字符串。")

    def _download_remote_file(self, url: str, filename: Optional[str]) -> Tuple[bytes, str, str]:
        response = self._session.get(url, timeout=self.timeout, verify=self.verify_ssl)
        response.raise_for_status()
        mime = response.headers.get("Content-Type", "")
        suffix = self._suffix_from_mime(mime)
        parsed = urlparse(url)
        raw_name = filename or Path(parsed.path).name
        resolved_name = self._finalize_filename(raw_name, fallback_suffix=suffix)
        mime = mime or self._guess_mime(resolved_name)
        return response.content, resolved_name, mime

    @staticmethod
    def _decode_base64(data: str) -> Optional[bytes]:
        if data.startswith("data:") and "," in data:
            data = data.split(",", 1)[1]
        try:
            return base64.b64decode(data, validate=True)
        except (base64.binascii.Error, ValueError):
            return None

    @staticmethod
    def _default_filename(suffix: str = "png") -> str:
        return f"piclab_{int(time.time() * 1000)}.{suffix}"

    @staticmethod
    def _env_flag(value: str) -> bool:
        return value.strip().lower() not in {"0", "false", "no", "off"}

    @staticmethod
    def _guess_mime(name: str) -> str:
        mime, _ = guess_type(name)
        if mime:
            return mime
        suffix = Path(name).suffix.lstrip(".").lower()
        custom = {
            "webp": "image/webp",
            "heic": "image/heic",
            "heif": "image/heif",
            "heics": "image/heic",
            "heifs": "image/heif",
        }
        return custom.get(suffix, "application/octet-stream")

    @staticmethod
    def _extract_error_detail(response: requests.Response) -> str:
        try:
            data = response.json()
            return str(data)
        except ValueError:
            return response.text[:500]

    def _finalize_filename(self, raw_name: Optional[str], *, fallback_suffix: str = "png") -> str:
        sanitized = self._sanitize_filename(raw_name or "")
        if not sanitized:
            return self._default_filename(fallback_suffix)

        suffix = Path(sanitized).suffix.lstrip(".").lower()
        if suffix and self._is_known_suffix(suffix):
            return sanitized

        sanitized = sanitized.rstrip(".") or self._default_filename(fallback_suffix)
        fallback_suffix = fallback_suffix or "png"
        return f"{sanitized}.{fallback_suffix.lstrip('.')}"

    @classmethod
    def _is_known_suffix(cls, suffix: str) -> bool:
        return suffix.lower() in cls._KNOWN_SUFFIXES

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        if not name:
            return ""
        name = unquote(name)
        name = name.split("?")[0].split("#")[0]
        name = name.replace("\\", "/")
        name = name.rsplit("/", 1)[-1]
        name = name.strip()
        if not name:
            return ""
        cleaned = re.sub(r"[^\w.\-]+", "_", name)
        return cleaned.strip("._")

    @staticmethod
    def _suffix_from_mime(mime: str) -> str:
        if not mime:
            return "png"
        subtype = mime.split("/", 1)[-1].split(";")[0].lower()
        if subtype in {"jpeg", "pjpeg"}:
            return "jpg"
        if subtype in {"heic", "heif", "heics", "heifs"}:
            return subtype
        if subtype == "webp":
            return "webp"
        if subtype.endswith("+xml"):
            subtype = subtype.split("+", 1)[0]
        if subtype.endswith("+json"):
            subtype = "json"
        if subtype == "svg+xml":
            return "svg"
        if not subtype:
            return "png"
        return subtype


if __name__ == "__main__":
    uploader = PicLabUploader()
    result = uploader.upload("https://www.ignant.com/wp-content/uploads/2014/05/Underwood_Light_Sculptures_05-1440x1440.jpg")
    print(result)
