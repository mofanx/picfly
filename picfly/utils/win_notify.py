from plyer import notification
import time
from typing import Optional


def desktop_notification(message="", title="picfly", timeout=5, icon_path: Optional[str] = None):
    """
    桌面气泡通知。

    Args:
        title (str): 通知的标题。
        message (str): 通知的内容。
        timeout (int): 通知在屏幕上显示的时间（秒）。默认为 5。
    """
    # 截断超长字符串（避免超限）
    title = title[:20]  # 标题最多20字符
    message = message[:64]  # 内容最多64字符
    app_icon = icon_path or ""
    notification.notify(
        title=title,
        message=message,
        app_name="IMTools",  # 通知来源名称
        app_icon=app_icon,  # DBus 需字符串，空串表示无图标
        timeout=timeout  # 自动关闭时间
    )

    # # 等待通知显示完成（避免脚本提前退出导致通知不显示）
    # time.sleep(timeout)

# 调用示例
if __name__ == "__main__":
    desktop_notification(
        message="这是一条桌面气泡通知～\n支持多行文本显示",
    )