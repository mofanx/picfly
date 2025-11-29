import asyncio
import os
import shutil
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

import tkinter as tk
from PIL import Image, ImageGrab
from pynput import keyboard


class ScreenshotError(RuntimeError):
    """截图流程相关异常。"""


def _is_wayland_session() -> bool:
    return bool(
        os.environ.get("WAYLAND_DISPLAY")
        or os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
    )


class PortalScreenshotBackend:
    """Wayland 场景使用 XDG Portal 截图。"""

    def __init__(self) -> None:
        if not sys.platform.startswith("linux"):
            raise ScreenshotError("Portal 后端仅支持 Linux")
        self._imports = self._lazy_imports()

    @staticmethod
    def _lazy_imports():
        try:
            from dbus_next import BusType, Message, MessageType, Variant
            from dbus_next.aio import MessageBus
        except ImportError as exc:  # pragma: no cover - 运行期提示
            raise ScreenshotError(
                "缺少 dbus-next，请先执行 `mamba activate base && mamba install dbus-next -c conda-forge`"
            ) from exc
        return {
            "BusType": BusType,
            "Message": Message,
            "MessageType": MessageType,
            "Variant": Variant,
            "MessageBus": MessageBus,
        }

    def capture_image(self) -> Image.Image:
        with tempfile.TemporaryDirectory() as tmp:
            temp_path = Path(tmp) / "portal.png"
            asyncio.run(self._capture_to(temp_path))
            with Image.open(temp_path) as img:
                return img.copy()

    async def _capture_to(self, target: Path) -> None:
        imports = self._imports
        MessageBus = imports["MessageBus"]
        BusType = imports["BusType"]
        Message = imports["Message"]
        MessageType = imports["MessageType"]
        Variant = imports["Variant"]

        bus = await MessageBus(bus_type=BusType.SESSION).connect()
        options = {
            "handle_token": Variant("s", f"cascade_{int(time.time() * 1000)}"),
            "interactive": Variant("b", True),
        }
        message = Message(
            destination="org.freedesktop.portal.Desktop",
            path="/org/freedesktop/portal/desktop",
            interface="org.freedesktop.portal.Screenshot",
            member="Screenshot",
            signature="sa{sv}",
            body=["", options],
        )
        reply = await bus.call(message)
        handle_path = reply.body[0]

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        def handler(msg):
            if msg.message_type == MessageType.SIGNAL and msg.path == handle_path and msg.member == "Response":
                if not future.done():
                    future.set_result(msg.body)
                return True
            return False

        bus.add_message_handler(handler)
        try:
            code, results = await asyncio.wait_for(future, timeout=60)
        finally:
            bus.remove_message_handler(handler)

        if code != 0:
            raise ScreenshotError("Wayland Portal 截图被取消")

        uri_variant = results.get("uri") if isinstance(results, dict) else None
        if not uri_variant:
            raise ScreenshotError("Wayland Portal 未返回截图文件")
        uri = uri_variant.value if hasattr(uri_variant, "value") else uri_variant
        if not uri.startswith("file://"):
            raise ScreenshotError(f"未知的 URI: {uri}")
        source = Path(urllib.parse.unquote(uri[7:]))
        if not source.exists():
            raise ScreenshotError(f"Portal 生成的临时文件不存在: {source}")
        shutil.copy2(source, target)


class MSSRegionGrabber:
    """使用 mss 抓取指定区域。"""

    def __init__(self) -> None:
        try:
            from mss import mss
        except ImportError as exc:  # pragma: no cover - 运行期提示
            raise ScreenshotError(
                "缺少 mss，请先执行 `mamba activate base && mamba install mss -c conda-forge`"
            ) from exc
        self._mss = mss

    def grab(self, bbox):
        left, top, right, bottom = bbox
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            raise ScreenshotError("无效的截图区域")
        with self._mss() as sct:
            raw = sct.grab({"left": left, "top": top, "width": width, "height": height})
            return Image.frombytes("RGB", raw.size, raw.rgb)


class RegionSelector:
    def __init__(self) -> None:
        self._start_x = 0
        self._start_y = 0
        self._rect = None
        self._glow_rects = []
        self._bbox = None
        self._root = None
        self._canvas = None
        self._portal_backend = None
        self._portal_disabled = False
        self._mss_grabber = None

    def select(self):
        self._root = tk.Tk()
        self._root.attributes("-fullscreen", True)
        self._root.attributes("-alpha", 0.3)
        self._root.attributes("-topmost", True)
        self._root.configure(bg="black")

        self._canvas = tk.Canvas(self._root, cursor="cross", bg="gray", highlightthickness=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._canvas.bind("<ButtonPress-1>", self._on_button_press)
        self._canvas.bind("<B1-Motion>", self._on_move_press)
        self._canvas.bind("<ButtonRelease-1>", self._on_button_release)
        self._root.bind("<Escape>", self._cancel)

        self._root.focus_force()
        self._root.grab_set()

        self._root.mainloop()
        return self._bbox

    def _portal_supported(self) -> bool:
        return sys.platform.startswith("linux") and _is_wayland_session()

    def _get_portal_backend(self):
        if self._portal_disabled:
            raise ScreenshotError("Portal 后端不可用")
        if self._portal_backend is None:
            try:
                self._portal_backend = PortalScreenshotBackend()
            except ScreenshotError as exc:
                self._portal_disabled = True
                raise exc
        return self._portal_backend

    def _get_mss_grabber(self):
        if self._mss_grabber is None:
            self._mss_grabber = MSSRegionGrabber()
        return self._mss_grabber

    def _on_button_press(self, event):
        self._start_x = event.x
        self._start_y = event.y
        if self._rect:
            self._canvas.delete(self._rect)
        if self._glow_rects:
            for glow in self._glow_rects:
                self._canvas.delete(glow)
        self._glow_rects = []

        glow_styles = (("#5bb0ff", 2), ("#2f80ed", 1))
        for color, width in glow_styles:
            glow_rect = self._canvas.create_rectangle(
                self._start_x,
                self._start_y,
                event.x,
                event.y,
                outline=color,
                width=width,
            )
            self._glow_rects.append(glow_rect)

        self._rect = self._canvas.create_rectangle(
            self._start_x,
            self._start_y,
            event.x,
            event.y,
            outline="#02e16e",
            width=1,
        )

    def _on_move_press(self, event):
        if not self._rect:
            return
        self._canvas.coords(self._rect, self._start_x, self._start_y, event.x, event.y)
        for glow in self._glow_rects:
            self._canvas.coords(glow, self._start_x, self._start_y, event.x, event.y)

    def _on_button_release(self, event):
        if not self._rect:
            return
        x0, y0 = self._start_x, self._start_y
        x1, y1 = event.x, event.y
        left, right = sorted([x0, x1])
        top, bottom = sorted([y0, y1])
        if left != right and top != bottom:
            self._bbox = (left, top, right, bottom)
        for glow in self._glow_rects:
            self._canvas.delete(glow)
        self._glow_rects.clear()
        self._rect = None
        self._root.destroy()

    def _cancel(self, _event):
        if self._root is None:
            return
        self._bbox = None
        for glow in self._glow_rects:
            self._canvas.delete(glow)
        self._glow_rects.clear()
        self._rect = None
        try:
            self._root.destroy()
        except tk.TclError:
            pass
        self._root = None

    def cancel(self):
        if self._root is not None:
            self._cancel(None)

    def screenshot(self):
        if self._portal_supported():
            try:
                backend = self._get_portal_backend()
            except ScreenshotError as exc:
                print(f"[Screenshot] Portal 后端不可用：{exc}，将尝试使用传统方式。")
            else:
                try:
                    return backend.capture_image()
                except asyncio.CancelledError:
                    print("[Screenshot] 操作被取消。")
                    return
                except ScreenshotError as exc:
                    if "取消" in str(exc):
                        print("[Screenshot] 操作被取消。")
                        return
                    print(f"[Screenshot] Portal 截图失败：{exc}，将尝试使用传统方式。")
                except Exception as exc:
                    print(f"[Screenshot] Portal 截图出现异常：{exc}，将尝试使用传统方式。")

        bbox = self.select()
        if not bbox:
            print("[Screenshot] 操作被取消。")
            return

        try:
            return ImageGrab.grab(bbox=bbox)
        except Exception as exc:
            if sys.platform.startswith("linux"):
                try:
                    grabber = self._get_mss_grabber()
                    return grabber.grab(bbox)
                except ScreenshotError as backend_exc:
                    raise RuntimeError(f"Linux 截图失败：{backend_exc}") from backend_exc
            raise exc


def main():
    selector = RegionSelector()
    listener = None

    def stop_listener():
        nonlocal listener
        print("退出程序...")
        if listener is not None:
            listener.stop()

    hotkeys = {
        '<f8>+8': selector.screenshot,
        '<f8>+<esc>': stop_listener,
    }

    with keyboard.GlobalHotKeys(hotkeys, suppress=False) as hotkey_listener:
        listener = hotkey_listener
        hotkey_listener.join()

if __name__ == "__main__":
    
    main()