"""前端入口：初始化 QApplication 并加载深色主题。

模块拆分：
- config.py          环境/后端地址/FPS 配置
- theme.py           深色 QSS 与调色板
- i18n.py            COCO 类别中英文映射
- overlay.py         视频叠加绘制（纯函数）
- camera_thread.py   采集 + WebSocket 通信线程
- main_window.py     主窗口
"""
import sys

from PyQt5.QtWidgets import QApplication

from main_window import MainWindow
from theme import DARK_QSS


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
