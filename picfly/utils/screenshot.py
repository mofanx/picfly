import tempfile
import time
from pathlib import Path

from pynput import keyboard
from PIL import ImageGrab
import tkinter as tk
import os


class RegionSelector:
    def __init__(self) -> None:
        self._start_x = 0
        self._start_y = 0
        self._rect = None
        self._glow_rects = []
        self._bbox = None
        self._root = None
        self._canvas = None

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

        bbox = self.select()
        if not bbox:
            print("[Screenshot] 操作被取消。")
            return
        image = ImageGrab.grab(bbox=bbox)
        # temp_path = Path(tempfile.gettempdir()) / f"screenshot_{int(time.time() * 1000)}.png"
        # image.save(temp_path)
        # print(f"[Screenshot] 已保存至: {temp_path}")

        return image

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