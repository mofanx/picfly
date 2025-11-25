from ..utils import BaimiaoApiClient, RegionSelector
import pyclip
from ..utils import desktop_notification
class OCR:
    def __init__(self):
        self.client = BaimiaoApiClient()
        self.selector = RegionSelector()
    
    def screenshot(self):
        # 1. 调用截图
        image = self.selector.screenshot()
        if image is None:
            return

        # 2. 调用 OCR 识别
        try:
            text = self.client.recognize(image)
            if text:
                print(f"\n[OCR 结果]:\n{text}")
                # 3. 复制到剪贴板
                pyclip.copy(text)
                print("[OCR] 已复制到剪贴板")
                desktop_notification(f"OCR 识别成功，识别结果: {text}")
            else:
                print("[OCR] 未识别到文字")
                desktop_notification("未识别到文字")
        except Exception as e:
            print(f"[OCR Error] {e}")
            desktop_notification(f"OCR 识别失败，错误信息: {e}")
    
    def clipboard(self):
        try:
           # 获取图片链接
           image = pyclip.paste().decode("utf-8")
        except (UnicodeDecodeError, Exception):
            # 获取图片二进制
            data = pyclip.paste()
            image = data if data else None
        if image is None:
            return
        try:
            text = self.client.recognize(image)
            if text:
                print(f"\n[OCR 结果]:\n{text}")
                # 3. 复制到剪贴板
                pyclip.copy(text)
                print("[OCR] 已复制到剪贴板")
                desktop_notification(f"OCR 识别成功，识别结果: {text}")
            else:
                print("[OCR] 未识别到文字")
                desktop_notification("未识别到文字")
        except Exception as e:
            print(f"[OCR Error] {e}")
            desktop_notification(f"OCR 识别失败，错误信息: {e}")

if __name__ == "__main__":
    OCR().screenshot()