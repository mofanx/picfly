"""picfly 主入口，注册热键调用 PicLab 上传."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from queue import Empty, Queue

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from picfly.tools import piclab, OCR
from pynput import keyboard


def main():
    # 实例化 piclab 和 ocr
    pic = piclab()
    ocr = OCR()

    task_queue = Queue()

    print("全局热键监听已启动...")
    print("F8+9: 截图上传")
    print("F8+0: 粘贴上传")
    print("F8+-: OCR 截图识别")
    print("F8+=: OCR 粘贴板识别")
    print("F8+ESC: 退出程序\n")

    def piclab_screenshot():
        task_queue.put(("piclab_screenshot", pic.screenshot))

    def piclab_clipboard():
        task_queue.put(("piclab_clipboard", pic.clipboard))

    def ocr_screenshot():
        task_queue.put(("ocr_screenshot", ocr.screenshot))

    def ocr_clipboard():
        task_queue.put(("ocr_clipboard", ocr.clipboard))

    def on_exit():
        task_queue.put(("exit", None))

    hotkeys = {
        '<f8>+9': piclab_screenshot,
        '<f8>+0': piclab_clipboard,
        '<f8>+-': ocr_screenshot,
        '<f8>+=': ocr_clipboard,
        '<f8>+<esc>': on_exit,
    }

    listener = keyboard.GlobalHotKeys(hotkeys, suppress=False)
    listener.start()

    try:
        while True:
            try:
                # Wait for a task with a small timeout to allow checking for other signals if needed
                msg, func = task_queue.get(timeout=0.1)
                
                if msg == "exit":
                    print("退出程序...")
                    break
                elif msg == "piclab_screenshot":
                    # This runs on the main thread
                    func()
                elif msg == "piclab_clipboard":
                    func()
                elif msg == "ocr_screenshot":
                    func()
                elif msg == "ocr_clipboard":
                    func()
            except Empty:
                continue
            except KeyboardInterrupt:
                print("\nDetected Ctrl+C, exiting...")
                break
    finally:
        listener.stop()

if __name__ == "__main__":
    main()