import pyclip
import keyboard
import time
import platform

def type_result(text):

    Simulate_Paste = True
    Restore_Clip = True
    # 模拟粘贴
    if Simulate_Paste:

        # 保存剪切板
        try:
            temp = pyclip.paste().decode('utf-8')
        except:
            temp = ''

        # 复制结果
        pyclip.copy(text)

        # 粘贴结果
        if platform.system() == 'Darwin':
            keyboard.press(55)
            keyboard.press(9)
            keyboard.release(55)
            keyboard.release(9)
        else:
            keyboard.send('ctrl + v')

        # 还原剪贴板
        if Restore_Clip:
            time.sleep(0.1)
            pyclip.copy(temp)

    # 模拟打印
    else:
        keyboard.write(text)

if __name__ == "__main__":
    type_result("你好")

