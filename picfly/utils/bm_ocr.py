# -*- coding: utf-8 -*-
"""白描 OCR API Python 客户端封装"""
from __future__ import annotations

import os
import io
from typing import Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import ReadableBuffer

import requests
from PIL import Image


class BaimiaoApiClient:
    """白描 OCR API 调用封装"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        """初始化客户端.

        Args:
            base_url: 服务地址（例如 http://localhost:8000）。
            api_key:  调用时放在 Authorization 里的密钥。
            timeout:  请求超时时间（秒）。
        """
        if base_url is None:
            base_url = os.environ.get("BAIMIAO_BASE_URL")
        if api_key is None:
            api_key = os.environ.get("BAIMIAO_API_KEY")

        if not base_url:
            raise ValueError("请传入 base_url，或设置环境变量 BAIMIAO_BASE_URL")
        if not api_key:
            raise ValueError("请传入 api_key，或设置环境变量 BAIMIAO_API_KEY")

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def recognize(self, image_source: Union[str, Image.Image, bytes, "ReadableBuffer"]) -> str:
        """提交图片进行 OCR 识别，返回纯文本结果。

        Args:
            image_source: 图片来源，可以是：
                - URL 字符串（http:// 或 https:// 开头）
                - 本地文件路径
                - PIL Image 对象
                - bytes 或类字节对象（如从粘贴板获取的图片二进制数据）

        Returns:
            识别出的文字（带换行）。
        """
        if not image_source:
            raise ValueError("image_source 必须是非空")

        endpoint = f"{self.base_url}/ocr"

        try:
            if isinstance(image_source, str):
                if image_source.startswith("http://") or image_source.startswith("https://"):
                    payload = {"image_url": image_source}
                    response = self.session.post(endpoint, json=payload, timeout=self.timeout)
                else:
                    if not os.path.isfile(image_source):
                        raise FileNotFoundError(f"找不到文件：{image_source}")
                    with open(image_source, "rb") as file_handler:
                        files = {
                            "file": (
                                os.path.basename(image_source),
                                file_handler,
                                "application/octet-stream",
                            )
                        }
                        response = self.session.post(endpoint, files=files, timeout=self.timeout)
            elif isinstance(image_source, Image.Image):
                # Convert PIL Image to bytes
                img_byte_arr = io.BytesIO()
                image_source.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                files = {
                    "file": (
                        "screenshot.png",
                        img_byte_arr,
                        "image/png",
                    )
                }
                response = self.session.post(endpoint, files=files, timeout=self.timeout)
            elif isinstance(image_source, (bytes, bytearray, memoryview)):
                # 直接处理二进制图片数据（如从粘贴板获取）
                img_byte_arr = io.BytesIO(bytes(image_source))
                files = {
                    "file": (
                        "clipboard.png",
                        img_byte_arr,
                        "application/octet-stream",
                    )
                }
                response = self.session.post(endpoint, files=files, timeout=self.timeout)
            else:
                raise ValueError("不支持的图片类型")

            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:  # pragma: no cover
            raise RuntimeError(f"OCR 请求失败：{exc}") from exc


def main() -> None:
        
    client = BaimiaoApiClient()
    
    url = "https://example.com/sample.png"

    image = "test.png"

    text = client.recognize(image)
    print(text)

    print("\n")
    text = client.recognize(url)
    print(text)


if __name__ == "__main__":
    main()