from ..utils import PicLabUploader
from ..utils import RegionSelector
import pyclip
from ..utils import desktop_notification

class piclab:
    def __init__(self):
        self.selector = RegionSelector()
        self.uploader = PicLabUploader()
    
    def screenshot(self):
        image = self.selector.screenshot()
        if image is None:
            return
        result = self.uploader.upload(image)
        if result.get("success") is False:
            print(f"[Error] {result['error']}")
        else:
            print(result)
            pyclip.copy(result['markdown'])
            desktop_notification(f"上传成功，图片链接: {result['url']}")

    def clipboard(self):
        try:
           # 获取图片链接
           image = pyclip.paste().decode("utf-8")
        except (UnicodeDecodeError, Exception):
            # 获取图片二进制
            data = pyclip.paste()
            image = data if data else None
        if image is None:
            desktop_notification("剪贴板数据为空")
            return
        result = self.uploader.upload(image)
        if result.get("success") is False:
            print(f"[Error] {result['error']}")
        else:
            print(result)
            pyclip.copy(result['markdown'])
            desktop_notification(f"上传成功，图片链接: {result['url']}")

    def cancel(self):
        self.selector.cancel()
    


if __name__ == "__main__":
    piclab().screenshot()

