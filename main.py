import sys
import os
import json
import shutil
from datetime import datetime
import requests
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QTextEdit,
                             QComboBox, QSpinBox, QDialog, QDialogButtonBox,
                             QLineEdit, QTreeWidget, QTreeWidgetItem, QSplitter,
                             QGroupBox, QFrame, QScrollArea, QMenuBar,
                             QFileDialog, QMessageBox, QListWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QGridLayout,
                             QTabWidget, QSizePolicy, QFormLayout)
from PySide6.QtCore import Qt, QDateTime, QSize
from PySide6.QtGui import (QColor, QTextCharFormat, QSyntaxHighlighter, QFont,
                          QAction)
import traceback
import difflib
import glob
import html

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        
        # 获取主窗口的当前大小
        main_window = self.parent()
        if isinstance(main_window, QMainWindow):
            current_width = main_window.size().width()
            current_height = main_window.size().height()
        else:
            current_width = 800
            current_height = 600
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 常规设置组
        general_group = QGroupBox("常规设置")
        general_layout = QVBoxLayout(general_group)
        
        # 窗口设置
        window_group = QGroupBox("窗口设置")
        window_layout = QGridLayout(window_group)
        
        # 预设窗口大小下拉框
        size_label = QLabel("预设窗口大小:")
        self.size_combo = QComboBox()
        self.size_combo.addItems([
            "800x600 (小)",
            "1024x768 (中)",
            "1280x800 (大)",
            "1440x900 (超大)",
            "自定义"
        ])
        
        # 根据当前窗口大小设置默认选项
        current_size = f"{current_width}x{current_height}"
        preset_sizes = {
            "800x600": 0,
            "1024x768": 1,
            "1280x800": 2,
            "1440x900": 3
        }
        
        size_found = False
        for size, index in preset_sizes.items():
            if size in current_size:
                self.size_combo.setCurrentIndex(index)
                size_found = True
                break
        
        if not size_found:
            self.size_combo.setCurrentIndex(4)  # 设置为"自定义"
        
        window_layout.addWidget(size_label, 0, 0)
        window_layout.addWidget(self.size_combo, 0, 1)
        
        # 自定义大小输入框
        self.custom_size_widget = QWidget()
        custom_size_layout = QHBoxLayout(self.custom_size_widget)
        custom_size_layout.setContentsMargins(0, 0, 0, 0)
        
        width_label = QLabel("宽度:")
        self.width_input = QSpinBox()
        self.width_input.setRange(800, 1920)
        self.width_input.setValue(current_width)
        
        height_label = QLabel("高度:")
        self.height_input = QSpinBox()
        self.height_input.setRange(600, 1080)
        self.height_input.setValue(current_height)
        
        custom_size_layout.addWidget(width_label)
        custom_size_layout.addWidget(self.width_input)
        custom_size_layout.addWidget(height_label)
        custom_size_layout.addWidget(self.height_input)
        
        window_layout.addWidget(self.custom_size_widget, 1, 0, 1, 2)
        
        # 根据选择显示/隐藏自定义大小输入框
        def on_size_changed(index):
            self.custom_size_widget.setVisible(index == 4)
            if index < 4:
                try:
                    # 提取数字部分并分割
                    size_text = self.size_combo.currentText().split(" ")[0]  # 获取 "800x600" 部分
                    width, height = map(int, size_text.split("x"))
                    self.width_input.setValue(width)
                    self.height_input.setValue(height)
                except (ValueError, IndexError) as e:
                    print(f"解析窗口大小时出错: {e}")
        
        self.size_combo.currentIndexChanged.connect(on_size_changed)
        on_size_changed(self.size_combo.currentIndex())
        
        general_layout.addWidget(window_group)
        layout.addWidget(general_group)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_window_size(self):
        """获取设置的窗口大小"""
        return self.width_input.value(), self.height_input.value()

class JsonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.json_format = QTextCharFormat()
        self.json_format.setForeground(QColor("#000080"))  # 深蓝色
        
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#008000"))  # 绿色
        
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#0000FF"))  # 蓝色
        
        self.bool_format = QTextCharFormat()
        self.bool_format.setForeground(QColor("#FF00FF"))  # 紫色

    def highlightBlock(self, text):
        import re
        
        # 高亮字符串
        string_pattern = r'"[^"\\]*(\\.[^"\\]*)*"'
        for match in re.finditer(string_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.string_format)
        
        # 高亮数字
        number_pattern = r'\b\d+\.?\d*\b'
        for match in re.finditer(number_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.number_format)
        
        # 高亮布尔值
        bool_pattern = r'\b(true|false|null)\b'
        for match in re.finditer(bool_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.bool_format)

class VersionHistoryDialog(QDialog):
    def __init__(self, config_name, history_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"版本历史 - {config_name}")
        self.setModal(True)
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # 版本列表
        self.version_tree = QTreeWidget()
        self.version_tree.setHeaderLabels(["版本", "创建时间", "备注"])
        self.version_tree.setColumnWidth(0, 150)
        self.version_tree.setColumnWidth(1, 200)
        layout.addWidget(self.version_tree)
        
        # 版本内容预览
        preview_label = QLabel("版本内容预览:")
        layout.addWidget(preview_label)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        layout.addWidget(self.preview_text)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.restore_button = QPushButton("恢复到此版本")
        self.restore_button.clicked.connect(self.restore_version)
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.restore_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
        
        # 加载版本历史
        self.history_dir = history_dir
        self.load_versions()
        
        # 连接版本选择信号
        self.version_tree.itemClicked.connect(self.show_version_preview)

    def load_versions(self):
        try:
            versions = []
            for filename in os.listdir(self.history_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.history_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        versions.append((
                            filename,
                            data.get('_version_info', {}).get('timestamp', ''),
                            data.get('_version_info', {}).get('comment', '')
                        ))
            
            # 按时间戳排序，最新的在前
            versions.sort(key=lambda x: x[1], reverse=True)
            
            # 添加到树形控件
            for version in versions:
                item = QTreeWidgetItem(self.version_tree)
                item.setText(0, version[0].replace('.json', ''))
                item.setText(1, version[1])
                item.setText(2, version[2])
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载版本历史失败: {str(e)}")

    def show_version_preview(self, item):
        try:
            filename = f"{item.text(0)}.json"
            filepath = os.path.join(self.history_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 移除版本信息后再显示
                if '_version_info' in data:
                    del data['_version_info']
                self.preview_text.setText(json.dumps(data, indent=4, ensure_ascii=False))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载版本预览失败: {str(e)}")

    def restore_version(self):
        current_item = self.version_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请选择要恢复的版本")
            return
            
        reply = QMessageBox.question(
            self,
            "确认恢复",
            f"确定要恢复到版本 '{current_item.text(0)}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.accept()

    def get_selected_version(self):
        item = self.version_tree.currentItem()
        return f"{item.text(0)}.json" if item else None

class SaveApiDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("保存接口配置")
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 配置名称输入
        name_layout = QHBoxLayout()
        name_label = QLabel("配置名称:")
        self.name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # 版本备注输入
        comment_layout = QHBoxLayout()
        comment_label = QLabel("版本备注:")
        self.comment_input = QLineEdit()
        comment_layout.addWidget(comment_label)
        comment_layout.addWidget(self.comment_input)
        layout.addLayout(comment_layout)
        
        # 确定和取消按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_name(self):
        return self.name_input.text().strip()
    
    def get_comment(self):
        return self.comment_input.text().strip()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("配置管理工具")
        
        # 设置默认窗口大小为中等大小（1024x768）
        self.resize(1024, 768)
        
        # 获取屏幕大小
        screen = QApplication.primaryScreen().geometry()
        # 计算窗口居中位置
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        # 移动窗口到居中位置
        self.move(x, y)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 创建API调用标签页
        api_tab = QWidget()
        self.setup_api_tab(api_tab)
        self.tab_widget.addTab(api_tab, "API调用")
        
        # 创建仓位信息标签页
        position_tab = QWidget()
        self.setup_position_tab(position_tab)
        self.tab_widget.addTab(position_tab, "仓位信息")
        
        # 创建货架解析标签页
        shelf_tab = QWidget()
        self.setup_shelf_tab(shelf_tab)
        self.tab_widget.addTab(shelf_tab, "货架解析")
        
        # 创建配置保存目录
        self.config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_configs')
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 加载保存的配置列表
        self.load_saved_configs()

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        # 新建配置
        new_action = QAction("新建配置", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.create_new_config)
        file_menu.addAction(new_action)
        
        # 退出
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 应用窗口大小设置
            width, height = dialog.get_window_size()
            self.resize(width, height)
            
            # 将窗口移动到屏幕中央
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - width) // 2
            y = (screen.height() - height) // 2
            self.move(x, y)

    def setup_api_tab(self, tab):
        # 创建水平布局来放置左侧的保存配置列表和右侧的主要内容
        main_layout = QHBoxLayout(tab)
        
        # 创建左侧的保存配置列表面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 保存的配置列表
        saved_label = QLabel("已保存的配置:")
        self.saved_list = QListWidget()
        self.saved_list.itemDoubleClicked.connect(self.load_api_config)
        left_layout.addWidget(saved_label)
        left_layout.addWidget(self.saved_list)
        
        # 按钮布局
        button_layout = QVBoxLayout()
        
        # 新建配置按钮
        new_button = QPushButton("新建配置")
        new_button.clicked.connect(self.create_new_config)
        button_layout.addWidget(new_button)
        
        # 保存和删除按钮
        save_button = QPushButton("保存当前配置")
        save_button.clicked.connect(self.save_api_config)
        delete_button = QPushButton("删除选中配置")
        delete_button.clicked.connect(self.delete_api_config)
        
        # 版本历史按钮
        history_button = QPushButton("查看版本历史")
        history_button.clicked.connect(self.show_version_history)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(delete_button)
        button_layout.addWidget(history_button)
        left_layout.addLayout(button_layout)
        
        # 设置左侧面板的最大宽度
        left_panel.setMaximumWidth(200)
        main_layout.addWidget(left_panel)
        
        # 创建右侧的主要内容面板
        self.right_panel = QWidget()  # 将right_panel设为实例变量
        self.setup_right_panel()  # 将右侧面板设置抽取为单独的方法
        main_layout.addWidget(self.right_panel)

    def setup_right_panel(self):
        """设置右侧面板的内容"""
        layout = QVBoxLayout(self.right_panel)
        
        # 请求方法和URL布局
        url_layout = QHBoxLayout()
        
        # 请求方法选择
        self.method_combo = QComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE", "PATCH"])
        url_layout.addWidget(self.method_combo)
        
        # URL输入
        url_label = QLabel("请求URL:")
        self.url_input = QTextEdit()
        self.url_input.setMaximumHeight(60)
        self.url_input.setPlaceholderText("输入请求URL...")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # 请求头部
        headers_label = QLabel("请求头:")
        self.headers_input = QTextEdit()
        self.headers_input.setMaximumHeight(150)
        # 设置默认的请求头
        default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ApiTestTool/1.0",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache"
        }
        self.headers_input.setText(json.dumps(default_headers, indent=4, ensure_ascii=False))
        layout.addWidget(headers_label)
        layout.addWidget(self.headers_input)
        
        # 为请求头添加语法高亮
        self.headers_highlighter = JsonHighlighter(self.headers_input.document())
        
        # 请求体输入
        body_label = QLabel("请求体:")
        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText("输入JSON格式的请求体...")
        layout.addWidget(body_label)
        layout.addWidget(self.body_input)
        
        # 为请求体添加语法高亮
        self.body_highlighter = JsonHighlighter(self.body_input.document())
        
        # 调用次数设置
        count_layout = QHBoxLayout()
        count_label = QLabel("调用次数:")
        self.count_input = QSpinBox()
        self.count_input.setMinimum(1)
        self.count_input.setMaximum(1000)
        count_layout.addWidget(count_label)
        count_layout.addWidget(self.count_input)
        count_layout.addStretch()
        layout.addLayout(count_layout)
        
        # 发送按钮
        self.send_button = QPushButton("发送请求")
        self.send_button.clicked.connect(self.send_request)
        layout.addWidget(self.send_button)
        
        # 结果显示
        result_label = QLabel("调用结果:")
        self.result_display = QTextEdit()
        self.result_display.setReadOnly(True)
        layout.addWidget(result_label)
        layout.addWidget(self.result_display)
        
        # 为响应结果添加语法高亮
        self.result_highlighter = JsonHighlighter(self.result_display.document())

    def create_new_config(self):
        """创建新配置"""
        # 创建输入对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("新建API配置")
        dialog.setModal(True)
        
        # 设置对话框大小和位置
        dialog.resize(500, 400)
        # 相对于主窗口居中
        dialog_x = self.x() + (self.width() - dialog.width()) // 2
        dialog_y = self.y() + (self.height() - dialog.height()) // 2
        dialog.move(dialog_x, dialog_y)
        
        # 创建布局
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # 创建输入框和选择框
        name_input = QLineEdit(dialog)
        name_input.setPlaceholderText("请输入API名称（必填）")
        name_input.setMinimumWidth(300)
        
        method_combo = QComboBox(dialog)
        method_combo.addItems(["GET", "POST", "PUT", "DELETE", "PATCH"])
        
        url_input = QLineEdit(dialog)
        url_input.setPlaceholderText("请输入API地址（选填）")
        url_input.setMinimumWidth(300)
        
        # 添加到表单布局
        form_layout.addRow("API名称:", name_input)
        form_layout.addRow("请求方法:", method_combo)
        form_layout.addRow("API地址:", url_input)
        
        # 创建请求头和请求体的输入区域
        headers_label = QLabel("请求头:", dialog)
        headers_input = QTextEdit(dialog)
        headers_input.setPlaceholderText("请输入请求头（JSON格式）")
        headers_input.setMaximumHeight(100)
        # 设置默认的请求头
        default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        headers_input.setPlainText(json.dumps(default_headers, indent=4, ensure_ascii=False))
        
        body_label = QLabel("请求体（选填）:", dialog)
        body_input = QTextEdit(dialog)
        body_input.setPlaceholderText("请输入请求体（JSON格式，选填）")
        body_input.setMaximumHeight(100)
        
        # 添加到主布局
        layout.addLayout(form_layout)
        layout.addWidget(headers_label)
        layout.addWidget(headers_input)
        layout.addWidget(body_label)
        layout.addWidget(body_input)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 创建按钮
        ok_button = QPushButton("确定", dialog)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        ok_button.setEnabled(False)  # 初始状态禁用
        
        cancel_button = QPushButton("取消", dialog)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5A6268;
            }
        """)
        
        # 添加按钮到布局
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        
        # 添加按钮布局到主布局
        layout.addLayout(button_layout)
        
        # 添加输入验证
        def on_text_changed():
            # 只检查API名称是否已填写
            ok_button.setEnabled(bool(name_input.text().strip()))
        
        name_input.textChanged.connect(on_text_changed)
        
        # 绑定按钮事件
        result = [None]  # 使用列表存储结果，以便在内部函数中修改
        
        def on_ok():
            name = name_input.text().strip()
            if not name:
                QMessageBox.warning(dialog, "警告", "请输入API名称")
                return
            
            # 检查配置名称是否已存在
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_configs")
            if os.path.exists(os.path.join(config_dir, name)):
                QMessageBox.warning(dialog, "警告", "API名称已存在，请重新输入")
                return
            
            # 验证请求头格式
            try:
                headers = json.loads(headers_input.toPlainText() or "{}")
                if not isinstance(headers, dict):
                    raise ValueError("请求头必须是一个JSON对象")
            except json.JSONDecodeError:
                QMessageBox.warning(dialog, "警告", "请求头格式错误，请检查JSON格式")
                return
            except ValueError as e:
                QMessageBox.warning(dialog, "警告", str(e))
                return
            
            # 验证请求体格式（如果有输入）
            body = {}
            if body_input.toPlainText().strip():
                try:
                    body = json.loads(body_input.toPlainText())
                    if not isinstance(body, dict):
                        raise ValueError("请求体必须是一个JSON对象")
                except json.JSONDecodeError:
                    QMessageBox.warning(dialog, "警告", "请求体格式错误，请检查JSON格式")
                    return
                except ValueError as e:
                    QMessageBox.warning(dialog, "警告", str(e))
                    return
            
            # 构建配置数据
            result[0] = {
                "name": name,
                "method": method_combo.currentText(),
                "url": url_input.text().strip(),
                "headers": headers,
                "body": body
            }
            dialog.accept()
        
        def on_cancel():
            dialog.reject()
        
        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(on_cancel)
        
        # 显示对话框
        if dialog.exec() == QDialog.DialogCode.Accepted and result[0]:
            config_data = result[0]
            try:
                # 创建配置目录
                config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_configs", config_data["name"])
                os.makedirs(config_dir, exist_ok=True)
                os.makedirs(os.path.join(config_dir, "versions"), exist_ok=True)
                
                # 添加版本信息
                config_data.update({
                    "theme": config_data["name"],
                    "version": "1.0.0",
                    "timestamp": QDateTime.currentDateTime().toString("yyyyMMdd_hhmmss"),
                    "comment": "初始配置"
                })
                
                # 保存配置
                config_file = os.path.join(config_dir, "current.json")
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4, ensure_ascii=False)
                
                # 保存版本历史
                version_file = os.path.join(config_dir, "versions", f"{config_data['timestamp']}.json")
                with open(version_file, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4, ensure_ascii=False)
                
                # 更新已保存配置列表
                self.load_saved_configs()
                
                QMessageBox.information(self, "成功", f"已创建新API配置：{config_data['name']}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建配置失败：{str(e)}")
                # 如果创建失败，清理已创建的目录
                if os.path.exists(config_dir):
                    try:
                        shutil.rmtree(config_dir)
                    except:
                        pass
                return

    def save_api_config(self):
        """保存当前API配置"""
        # 获取当前选中的配置名称
        current_item = self.saved_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "错误", "请先选择一个配置！")
            return
            
        config_name = current_item.text()
        
        # 创建输入对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(f"保存配置 - {config_name}")
        layout = QVBoxLayout(dialog)
        
        # 配置名称显示（只读）
        name_layout = QHBoxLayout()
        name_label = QLabel("配置名称:")
        name_display = QLabel(config_name)
        name_display.setStyleSheet("font-weight: bold;")
        name_layout.addWidget(name_label)
        name_layout.addWidget(name_display)
        name_layout.addStretch()
        layout.addLayout(name_layout)
        
        # 主题输入
        theme_layout = QHBoxLayout()
        theme_label = QLabel("主题:")
        theme_input = QLineEdit()
        
        # 读取当前主题
        try:
            current_file = os.path.join("api_configs", config_name, "current.json")
            with open(current_file, "r", encoding="utf-8") as f:
                current_data = json.load(f)
                theme_input.setText(current_data.get("theme", ""))
        except:
            pass
            
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(theme_input)
        layout.addLayout(theme_layout)
        
        # 版本备注输入
        comment_label = QLabel("版本备注:")
        comment_input = QTextEdit()
        comment_input.setMaximumHeight(100)
        layout.addWidget(comment_label)
        layout.addWidget(comment_input)
        
        # 对话框按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            theme = theme_input.text().strip()
            version_comment = comment_input.toPlainText().strip()
            
            # 生成版本号（格式：yyyyMMdd_HHmmss）
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 准备配置数据
            config_data = {
                "method": self.method_combo.currentText(),
                "url": self.url_input.toPlainText(),
                "headers": json.loads(self.headers_input.toPlainText()),
                "body": self.body_input.toPlainText(),
                "count": self.count_input.value(),
                "version": version,
                "theme": theme,
                "comment": version_comment,
                "timestamp": datetime.now().isoformat()
            }
            
            try:
                # 创建配置目录
                config_dir = os.path.join("api_configs", config_name)
                versions_dir = os.path.join(config_dir, "versions")
                os.makedirs(versions_dir, exist_ok=True)
                
                # 保存当前版本到versions目录
                version_file = os.path.join(versions_dir, f"{version}.json")
                with open(version_file, "w", encoding="utf-8") as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=4)
                
                # 更新current.json
                current_file = os.path.join(config_dir, "current.json")
                with open(current_file, "w", encoding="utf-8") as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=4)
                
                QMessageBox.information(
                    self,
                    "成功",
                    f"配置已保存！\n版本号: {version}\n主题: {theme}\n备注: {version_comment}"
                )
                
                # 刷新配置列表
                self.load_saved_configs()
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "错误",
                    f"保存配置失败：{str(e)}"
                )

    def load_saved_configs(self):
        self.saved_list.clear()
        try:
            for item in os.listdir(self.config_dir):
                config_path = os.path.join(self.config_dir, item)
                if os.path.isdir(config_path) and os.path.exists(os.path.join(config_path, 'current.json')):
                    self.saved_list.addItem(item)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载配置列表失败: {str(e)}")

    def load_api_config(self, item):
        """从列表中选择配置时加载配置"""
        if item:
            config_name = item.text()
            self.load_api_config_by_name(config_name)

    def delete_api_config(self):
        current_item = self.saved_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请选择要删除的配置")
            return
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除配置 '{current_item.text()}' 吗？这将删除所有版本历史！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                config_path = os.path.join(self.config_dir, current_item.text())
                shutil.rmtree(config_path)
                self.load_saved_configs()  # 刷新配置列表
                QMessageBox.information(self, "成功", "配置删除成功！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除配置失败: {str(e)}")

    def show_version_history(self):
        """显示版本历史"""
        if not self.saved_list.currentItem():
            QMessageBox.warning(self, "警告", "请先选择一个配置！")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle(f"版本历史 - {self.saved_list.currentItem().text()}")
        
        # 获取主窗口大小
        main_window_geometry = self.geometry()
        
        # 设置对话框大小为主窗口的80%
        dialog_width = int(main_window_geometry.width() * 0.8)
        dialog_height = int(main_window_geometry.height() * 0.8)
        
        # 创建主布局
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 添加版本数量标签
        version_count_label = QLabel()
        version_count_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 12px;
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(version_count_label)
        
        # 创建表格
        table = QTableWidget()
        table.setColumnCount(8)  # 增加删除列
        table.setHorizontalHeaderLabels(["序号", "主题", "版本号", "时间", "备注", "查看对比", "回滚", "删除"])
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        
        # 设置表格样式
        table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 5px;
                border: none;
                border-right: 1px solid #ddd;
                border-bottom: 1px solid #ddd;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        
        # 获取versions目录
        versions_dir = os.path.join("api_configs", self.saved_list.currentItem().text(), "versions")
        current_file = os.path.join("api_configs", self.saved_list.currentItem().text(), "current.json")
        
        if not os.path.exists(versions_dir):
            os.makedirs(versions_dir)
        
        # 获取所有版本文件
        version_files = sorted(
            [f for f in os.listdir(versions_dir) if f.endswith('.json')],
            reverse=True
        )
        
        # 更新版本数量标签
        version_count_label.setText(f"共 {len(version_files)} 个版本")
        
        # 设置表格行数
        table.setRowCount(len(version_files))
        
        # 读取当前配置
        try:
            with open(current_file, "r", encoding="utf-8") as f:
                current_config = json.load(f)
        except Exception:
            current_config = {}
        
        # 设置列宽比例
        column_ratios = [0.06, 0.12, 0.12, 0.15, 0.3, 0.1, 0.075, 0.075]  # 总和为1
        
        for row, version_file in enumerate(version_files):
            # 设置行高
            table.setRowHeight(row, 40)
            
            with open(os.path.join(versions_dir, version_file), "r", encoding="utf-8") as f:
                version_data = json.load(f)
            
            # 序号（第一列）
            index_item = QTableWidgetItem(str(row + 1))
            index_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            index_item.setBackground(QColor("#F8F9FA"))
            font = index_item.font()
            font.setBold(True)
            index_item.setFont(font)
            table.setItem(row, 0, index_item)
            
            # 主题（第二列）
            theme = version_data.get("theme", "无")
            theme_item = QTableWidgetItem(theme)
            theme_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 1, theme_item)
            
            # 版本号（第三列）
            version = version_data.get("version", os.path.splitext(version_file)[0])
            version_item = QTableWidgetItem(version)
            version_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 2, version_item)
            
            # 时间（第四列）
            timestamp = version_data.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    formatted_time = timestamp
            else:
                formatted_time = "未知"
            time_item = QTableWidgetItem(formatted_time)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 3, time_item)
            
            # 备注（第五列）
            comment = version_data.get("comment", "无")
            comment_item = QTableWidgetItem(comment)
            comment_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(row, 4, comment_item)
            
            # 查看对比按钮（第六列）
            button_widget = QWidget()
            button_layout = QHBoxLayout(button_widget)
            button_layout.setContentsMargins(5, 0, 5, 0)
            button_layout.setSpacing(5)
            
            view_button = QPushButton("查看对比")
            view_button.setStyleSheet("""
                QPushButton {
                    background-color: #007BFF;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
            """)
            def create_view_callback(vd):
                return lambda checked=False: self.show_version_diff(current_config, vd)
            view_button.clicked.connect(create_view_callback(version_data))
            button_layout.addWidget(view_button)
            table.setCellWidget(row, 5, button_widget)
            
            # 回滚按钮（第七列）
            restore_widget = QWidget()
            restore_layout = QHBoxLayout(restore_widget)
            restore_layout.setContentsMargins(5, 0, 5, 0)
            restore_layout.setSpacing(5)
            
            restore_button = QPushButton("回滚")
            restore_button.setStyleSheet("""
                QPushButton {
                    background-color: #FFC107;
                    color: black;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
            def create_restore_callback(n, vd, f):
                return lambda checked=False: self.restore_version(n, vd, f)
            restore_button.clicked.connect(create_restore_callback(
                self.saved_list.currentItem().text(),
                version_data,
                version_file
            ))
            restore_layout.addWidget(restore_button)
            table.setCellWidget(row, 6, restore_widget)
            
            # 删除按钮（第八列）
            delete_widget = QWidget()
            delete_layout = QHBoxLayout(delete_widget)
            delete_layout.setContentsMargins(5, 0, 5, 0)
            delete_layout.setSpacing(5)
            
            delete_button = QPushButton("删除")
            delete_button.setStyleSheet("""
                QPushButton {
                    background-color: #DC3545;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            def create_delete_callback(n, f):
                def delete_version(checked=False):
                    reply = QMessageBox.question(
                        self,
                        "确认删除",
                        f"确定要删除这个版本吗？\n此操作不可恢复。",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        try:
                            version_file_path = os.path.join(versions_dir, f)
                            os.remove(version_file_path)
                            dialog.reject()  # 关闭当前对话框
                            self.show_version_history()  # 重新打开显示新的版本列表
                            QMessageBox.information(self, "成功", "版本已成功删除！")
                        except Exception as e:
                            QMessageBox.critical(self, "错误", f"删除版本时出错：{str(e)}")
                return delete_version
            
            delete_button.clicked.connect(create_delete_callback(
                self.saved_list.currentItem().text(),
                version_file
            ))
            delete_layout.addWidget(delete_button)
            table.setCellWidget(row, 7, delete_widget)
        
        # 设置列宽
        header = table.horizontalHeader()
        
        # 设置每列的大小策略
        for i in range(len(column_ratios)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            table.setColumnWidth(i, int(dialog_width * column_ratios[i]))
        
        # 添加表格到布局
        layout.addWidget(table)
        
        # 添加关闭按钮
        close_button = QPushButton("关闭")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5A6268;
            }
        """)
        close_button.clicked.connect(dialog.reject)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        # 设置对话框大小
        dialog.resize(dialog_width, dialog_height)
        
        # 将对话框移动到主窗口中心
        x = main_window_geometry.x() + (main_window_geometry.width() - dialog_width) // 2
        y = main_window_geometry.y() + (main_window_geometry.height() - dialog_height) // 2
        dialog.move(x, y)
        
        dialog.exec()

    def show_version_diff(self, current_config, version_data):
        """显示版本对比"""
        # 获取版本历史窗口的大小（如果存在）
        history_dialog = None
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QDialog) and widget.windowTitle().startswith("版本历史"):
                history_dialog = widget
                break
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"版本对比 - {version_data.get('version', '未知版本')}")
        
        # 如果找到版本历史窗口，设置为其80%大小
        if history_dialog:
            dialog_width = int(history_dialog.width() * 0.8)
            dialog_height = int(history_dialog.height() * 0.8)
            # 相对于版本历史窗口居中
            x = history_dialog.x() + (history_dialog.width() - dialog_width) // 2
            y = history_dialog.y() + (history_dialog.height() - dialog_height) // 2
        else:
            # 如果找不到版本历史窗口，则相对于主窗口的64%大小（80% * 80%）
            main_window_geometry = self.geometry()
            dialog_width = int(main_window_geometry.width() * 0.64)
            dialog_height = int(main_window_geometry.height() * 0.64)
            # 相对于主窗口居中
            x = main_window_geometry.x() + (main_window_geometry.width() - dialog_width) // 2
            y = main_window_geometry.y() + (main_window_geometry.height() - dialog_height) // 2
        
        # 设置对话框大小和位置
        dialog.resize(dialog_width, dialog_height)
        dialog.move(x, y)
        
        # 设置对话框模态
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)  # 防止分割部分被完全折叠
        
        # 上部分显示基本信息
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建一个表格来显示版本信息
        info_table = QTableWidget()
        info_table.setColumnCount(2)
        info_table.setHorizontalHeaderLabels(["项目", "内容"])
        info_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        info_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        info_table.verticalHeader().setVisible(False)
        info_table.setMaximumHeight(150)
        
        # 准备显示的信息
        info_items = [
            ("版本号", version_data.get("version", "未知")),
            ("主题", version_data.get("theme", "无")),
            ("创建时间", version_data.get("timestamp", "未知")),
            ("备注", version_data.get("comment", "无"))
        ]
        
        info_table.setRowCount(len(info_items))
        for row, (key, value) in enumerate(info_items):
            # 设置行高
            info_table.setRowHeight(row, 30)
            # 添加键
            key_item = QTableWidgetItem(key)
            key_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            key_item.setBackground(QColor("#F8F9FA"))
            font = key_item.font()
            font.setBold(True)
            key_item.setFont(font)
            info_table.setItem(row, 0, key_item)
            # 添加值
            value_item = QTableWidgetItem(str(value))
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            info_table.setItem(row, 1, value_item)
        
        info_layout.addWidget(info_table)
        
        # 下部分显示JSON对比
        diff_widget = QWidget()
        diff_layout = QHBoxLayout(diff_widget)
        diff_layout.setContentsMargins(0, 0, 0, 0)
        diff_layout.setSpacing(10)
        
        # 创建两个文本框用于显示JSON
        current_text = QTextEdit()
        current_text.setReadOnly(True)
        current_text.setFont(QFont("Menlo", 10))  # 使用 Menlo 字体
        version_text = QTextEdit()
        version_text.setReadOnly(True)
        version_text.setFont(QFont("Menlo", 10))  # 使用 Menlo 字体
        
        # 添加标题标签
        current_label = QLabel("当前配置")
        current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        current_label.setStyleSheet("font-weight: bold; padding: 5px;")
        version_label = QLabel("历史版本")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("font-weight: bold; padding: 5px;")
        
        # 创建左右两侧的布局
        left_layout = QVBoxLayout()
        left_layout.addWidget(current_label)
        left_layout.addWidget(current_text)
        
        right_layout = QVBoxLayout()
        right_layout.addWidget(version_label)
        right_layout.addWidget(version_text)
        
        diff_layout.addLayout(left_layout)
        diff_layout.addLayout(right_layout)
        
        try:
            # 移除不需要比较的字段
            current_compare = current_config.copy()
            version_compare = version_data.copy()
            for key in ['version', 'timestamp', 'comment']:
                current_compare.pop(key, None)
                version_compare.pop(key, None)
            
            # 格式化JSON以便比较
            current_json = json.dumps(current_compare, indent=4, ensure_ascii=False)
            version_json = json.dumps(version_compare, indent=4, ensure_ascii=False)
            
            # 将JSON文本分割成行
            current_lines = current_json.splitlines()
            version_lines = version_json.splitlines()
            
            # 使用difflib比较差异
            differ = difflib.Differ()
            diff = list(differ.compare(current_lines, version_lines))
            
            # 在文本框中显示差异
            current_html = []
            version_html = []
            
            # 添加样式
            current_html.append("<style>")
            current_html.append(".diff-add { background-color: #d7ffd7; }")  # 浅绿色
            current_html.append(".diff-del { background-color: #ffd7d7; }")  # 浅红色
            current_html.append(".diff-normal { }")
            current_html.append("</style>")
            current_html.append("<pre>")
            
            version_html.append("<style>")
            version_html.append(".diff-add { background-color: #d7ffd7; }")
            version_html.append(".diff-del { background-color: #ffd7d7; }")
            version_html.append(".diff-normal { }")
            version_html.append("</style>")
            version_html.append("<pre>")
            
            # 处理每一行
            for line in diff:
                if line.startswith('  '):  # 相同的行
                    current_html.append(f'<span class="diff-normal">{html.escape(line[2:])}</span>')
                    version_html.append(f'<span class="diff-normal">{html.escape(line[2:])}</span>')
                elif line.startswith('- '):  # 在当前配置中存在的行
                    current_html.append(f'<span class="diff-del">{html.escape(line[2:])}</span>')
                elif line.startswith('+ '):  # 在历史版本中存在的行
                    version_html.append(f'<span class="diff-add">{html.escape(line[2:])}</span>')
            
            current_html.append("</pre>")
            version_html.append("</pre>")
            
            # 设置HTML内容
            current_text.setHtml('\n'.join(current_html))
            version_text.setHtml('\n'.join(version_html))
            
        except Exception as e:
            QMessageBox.critical(dialog, "错误", f"显示版本对比时出错：{str(e)}")
            return
        
        splitter.addWidget(info_widget)
        splitter.addWidget(diff_widget)
        
        # 计算分割器的大小比例
        total_height = dialog_height - 80  # 减去按钮和边距的高度
        splitter.setSizes([int(total_height * 0.3), int(total_height * 0.7)])  # 上部分占30%，下部分占70%
        
        layout.addWidget(splitter)
        
        # 添加关闭按钮
        close_button = QPushButton("关闭")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5A6268;
            }
        """)
        close_button.clicked.connect(dialog.close)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        dialog.exec()

    def refresh_version_history(self, dialog, config_name):
        """刷新版本历史对话框"""
        if dialog:
            dialog.reject()  # 使用reject替代close
        self.show_version_history()

    def restore_version(self, config_name, version_data, version_file):
        """回滚到指定版本"""
        reply = QMessageBox.question(
            self,
            "确认回滚",
            f"确定要回滚到版本 {os.path.splitext(version_file)[0]} 吗？\n这将覆盖当前配置。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 1. 更新current.json
                current_file = os.path.join("api_configs", config_name, "current.json")
                with open(current_file, "w", encoding="utf-8") as f:
                    json.dump(version_data, f, ensure_ascii=False, indent=4)
                
                # 2. 在主界面加载配置
                self.load_api_config_by_name(config_name)
                
                # 3. 关闭版本历史对话框
                dialog = None
                for widget in QApplication.topLevelWidgets():
                    if isinstance(widget, QDialog) and widget.windowTitle().startswith("版本历史"):
                        dialog = widget
                        break
                
                if dialog:
                    dialog.reject()  # 使用reject替代done，避免模态对话框的问题
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "错误",
                    f"回滚失败：{str(e)}"
                )

    def load_api_config_by_name(self, config_name):
        """根据配置名称加载配置"""
        try:
            # 1. 读取配置文件
            current_file = os.path.join("api_configs", config_name, "current.json")
            with open(current_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            # 2. 切换到API调用标签页
            self.tab_widget.setCurrentIndex(0)
            
            # 3. 选中配置列表中的项目
            for i in range(self.saved_list.count()):
                if self.saved_list.item(i).text() == config_name:
                    self.saved_list.setCurrentRow(i)
                    break
            
            # 4. 更新界面显示
            self.method_combo.setCurrentText(config_data.get("method", "GET"))
            self.url_input.setText(config_data.get("url", ""))
            # 确保headers是字典类型，然后转换为格式化的JSON字符串
            headers = config_data.get("headers", {})
            if not isinstance(headers, dict):
                headers = {}
            headers_str = json.dumps(headers, indent=4, ensure_ascii=False)
            self.headers_input.setPlainText(headers_str)
            
            # 确保body是字典类型，然后转换为格式化的JSON字符串
            body = config_data.get("body", {})
            if not isinstance(body, dict):
                body = {}
            body_str = json.dumps(body, indent=4, ensure_ascii=False)
            self.body_input.setPlainText(body_str)
            self.count_input.setValue(config_data.get("count", 1))
            
            # 5. 显示成功提示
            QMessageBox.information(
                self,
                "成功",
                f"配置已加载"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "错误",
                f"加载配置失败：{str(e)}"
            )

    def setup_position_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # 文件导入按钮
        self.import_button = QPushButton("导入仓位信息文件")
        self.import_button.clicked.connect(self.import_position_file)
        layout.addWidget(self.import_button)
        
        # 显示导入的数据
        self.position_table = QTableWidget()
        self.position_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.position_table)

    def setup_shelf_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # 货架编号输入
        shelf_label = QLabel("输入货架编号:")
        self.shelf_input = QTextEdit()
        self.shelf_input.setMaximumHeight(60)
        self.shelf_input.setPlaceholderText("输入6位数字的货架编号...")
        layout.addWidget(shelf_label)
        layout.addWidget(self.shelf_input)
        
        # 查询按钮
        self.query_button = QPushButton("查询仓位")
        self.query_button.clicked.connect(self.query_position)
        layout.addWidget(self.query_button)
        
        # 显示查询结果
        self.shelf_table = QTableWidget()
        self.shelf_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.shelf_table)

    def format_response(self, response, error=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = f"=== 请求时间: {timestamp} ===\n\n"
        
        # 添加请求信息
        result += "=== 请求信息 ===\n"
        result += f"URL: {response.request.url if not error else self.url_input.toPlainText()}\n"
        result += f"Method: {response.request.method if not error else self.method_combo.currentText()}\n"
        
        # 添加请求头
        result += "\n=== 请求头 ===\n"
        if not error:
            headers = dict(response.request.headers)
            result += json.dumps(headers, indent=4, ensure_ascii=False)
        else:
            try:
                headers = json.loads(self.headers_input.toPlainText() or "{}")
                result += json.dumps(headers, indent=4, ensure_ascii=False)
            except:
                result += "无法解析请求头\n"
        
        # 添加请求体
        if self.method_combo.currentText() in ["POST", "PUT", "PATCH"]:
            result += "\n\n=== 请求体 ===\n"
            try:
                body = json.loads(self.body_input.toPlainText() or "{}")
                result += json.dumps(body, indent=4, ensure_ascii=False)
            except:
                result += "无法解析请求体\n"
        
        # 添加响应信息
        if not error:
            result += f"\n\n=== 响应状态 ===\n"
            result += f"Status Code: {response.status_code}\n"
            result += f"Reason: {response.reason}\n"
            
            result += "\n=== 响应头 ===\n"
            result += json.dumps(dict(response.headers), indent=4, ensure_ascii=False)
            
            result += "\n\n=== 响应体 ===\n"
            try:
                json_response = response.json()
                result += json.dumps(json_response, indent=4, ensure_ascii=False)
            except:
                result += response.text
        else:
            result += f"\n\n=== 错误信息 ===\n"
            result += str(error)
            if hasattr(error, '__traceback__'):
                result += "\n\n=== 详细错误 ===\n"
                result += traceback.format_exc()
        
        result += "\n\n" + "="*50 + "\n\n"
        return result

    def send_request(self):
        try:
            url = self.url_input.toPlainText().strip()
            method = self.method_combo.currentText()
            count = self.count_input.value()
            
            if not url:
                QMessageBox.warning(self, "警告", "请输入URL")
                return
            
            # 解析请求头
            try:
                headers = json.loads(self.headers_input.toPlainText() or "{}")
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "警告", f"请求头JSON格式错误: {str(e)}")
                return
            
            # 解析请求体（如果需要）
            body = None
            if method in ["POST", "PUT", "PATCH"]:
                try:
                    body = self.body_input.toPlainText().strip()
                    if body:
                        body = json.loads(body)
                except json.JSONDecodeError as e:
                    QMessageBox.warning(self, "警告", f"请求体JSON格式错误: {str(e)}")
                    return
            
            self.result_display.clear()
            for i in range(count):
                try:
                    response = requests.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=body if body else None
                    )
                    
                    # 格式化并显示响应
                    result = self.format_response(response)
                    self.result_display.append(result)
                    QApplication.processEvents()  # 更新UI
                    
                except Exception as e:
                    # 格式化并显示错误
                    result = self.format_response(None, error=e)
                    self.result_display.append(result)
                    QApplication.processEvents()
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发生错误: {str(e)}")

    def import_position_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择文件",
            "",
            "Excel Files (*.xlsx *.xls);;CSV Files (*.csv)"
        )
        
        if file_name:
            try:
                if file_name.endswith('.csv'):
                    df = pd.read_csv(file_name)
                else:
                    df = pd.read_excel(file_name)
                
                self.position_data = df
                self.update_position_table(df)
                QMessageBox.information(self, "成功", "文件导入成功！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"文件导入失败: {str(e)}")

    def update_position_table(self, df):
        # 设置表格的行数和列数
        self.position_table.setRowCount(len(df))
        self.position_table.setColumnCount(len(df.columns))
        
        # 设置表头
        self.position_table.setHorizontalHeaderLabels([str(col) for col in df.columns])
        
        # 填充数据
        for i in range(len(df)):
            for j in range(len(df.columns)):
                item = QTableWidgetItem(str(df.iloc[i, j]))
                # 如果是仓位编号列，设置为红色
                column_name = str(df.columns[j]).lower()
                if "仓位" in column_name or "position" in column_name:
                    item.setForeground(QColor(255, 0, 0))
                self.position_table.setItem(i, j, item)
        
        # 自适应列宽
        self.position_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    def query_position(self):
        shelf_code = self.shelf_input.toPlainText().strip()
        
        if not shelf_code or not shelf_code.isdigit() or len(shelf_code) != 6:
            QMessageBox.warning(self, "警告", "请输入6位数字的货架编号")
            return
            
        if not hasattr(self, 'position_data'):
            QMessageBox.warning(self, "警告", "请先导入仓位信息")
            return
            
        try:
            matches = self.position_data[
                self.position_data.apply(
                    lambda row: str(shelf_code) in str(row), axis=1
                )
            ]
            
            if matches.empty:
                self.shelf_table.setRowCount(0)
                self.shelf_table.setColumnCount(0)
                QMessageBox.information(self, "提示", "未找到匹配的仓位信息")
            else:
                # 更新查询结果表格
                self.shelf_table.setRowCount(len(matches))
                self.shelf_table.setColumnCount(len(matches.columns))
                self.shelf_table.setHorizontalHeaderLabels([str(col) for col in matches.columns])
                
                for i in range(len(matches)):
                    for j in range(len(matches.columns)):
                        item = QTableWidgetItem(str(matches.iloc[i, j]))
                        # 如果是仓位编号列，设置为红色
                        column_name = str(matches.columns[j]).lower()
                        if "仓位" in column_name or "position" in column_name:
                            item.setForeground(QColor(255, 0, 0))
                        self.shelf_table.setItem(i, j, item)
                
                # 自适应列宽
                self.shelf_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查询失败: {str(e)}")

    def create_config_tab(self, config_file):
        """创建配置标签页"""
        try:
            # 读取配置文件
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 创建新的标签页
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            tab_layout.setSpacing(10)
            tab_layout.setContentsMargins(10, 10, 10, 10)
            
            # 创建表单布局
            form_layout = QFormLayout()
            form_layout.setSpacing(10)
            
            # API名称（只读）
            name_label = QLineEdit(tab)
            name_label.setText(str(config_data.get("name", "")))
            name_label.setReadOnly(True)
            form_layout.addRow("API名称:", name_label)
            
            # 请求方法
            method_combo = QComboBox(tab)
            method_combo.addItems(["GET", "POST", "PUT", "DELETE", "PATCH"])
            method_combo.setCurrentText(str(config_data.get("method", "GET")))
            form_layout.addRow("请求方法:", method_combo)
            
            # API地址
            url_input = QLineEdit(tab)
            url_input.setText(str(config_data.get("url", "")))
            form_layout.addRow("API地址:", url_input)
            
            # 添加表单布局
            tab_layout.addLayout(form_layout)
            
            # 请求头
            headers_label = QLabel("请求头:", tab)
            headers_input = QTextEdit(tab)
            headers_input.setMaximumHeight(150)
            # 确保headers是字典类型，然后转换为格式化的JSON字符串
            headers = config_data.get("headers", {})
            if not isinstance(headers, dict):
                headers = {}
            headers_str = json.dumps(headers, indent=4, ensure_ascii=False)
            headers_input.setPlainText(headers_str)
            tab_layout.addWidget(headers_label)
            tab_layout.addWidget(headers_input)
            
            # 请求体
            body_label = QLabel("请求体:", tab)
            body_input = QTextEdit(tab)
            body_input.setMaximumHeight(150)
            # 确保body是字典类型，然后转换为格式化的JSON字符串
            body = config_data.get("body", {})
            if not isinstance(body, dict):
                body = {}
            body_str = json.dumps(body, indent=4, ensure_ascii=False)
            body_input.setPlainText(body_str)
            tab_layout.addWidget(body_label)
            tab_layout.addWidget(body_input)
            
            # 创建按钮布局
            button_layout = QHBoxLayout()
            button_layout.setSpacing(10)
            
            # 保存按钮
            save_button = QPushButton("保存配置", tab)
            save_button.setStyleSheet("""
                QPushButton {
                    background-color: #28A745;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            
            # 发送请求按钮
            send_button = QPushButton("发送请求", tab)
            send_button.setStyleSheet("""
                QPushButton {
                    background-color: #007BFF;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
            """)
            
            # 版本历史按钮
            history_button = QPushButton("版本历史", tab)
            history_button.setStyleSheet("""
                QPushButton {
                    background-color: #17A2B8;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #138496;
                }
            """)
            
            # 添加按钮到布局
            button_layout.addWidget(save_button)
            button_layout.addWidget(send_button)
            button_layout.addWidget(history_button)
            button_layout.addStretch()
            
            # 添加按钮布局到主布局
            tab_layout.addLayout(button_layout)
            
            # 创建响应显示区域
            response_label = QLabel("响应结果:", tab)
            response_text = QTextEdit(tab)
            response_text.setReadOnly(True)
            response_text.setPlaceholderText("这里将显示API响应结果...")
            tab_layout.addWidget(response_label)
            tab_layout.addWidget(response_text)
            
            # 绑定按钮事件
            def on_save():
                try:
                    # 验证并解析JSON
                    try:
                        headers = json.loads(headers_input.toPlainText() or "{}")
                        if not isinstance(headers, dict):
                            raise ValueError("请求头必须是一个JSON对象")
                    except json.JSONDecodeError:
                        QMessageBox.warning(self, "警告", "请求头格式错误，请检查JSON格式")
                        return
                    except ValueError as e:
                        QMessageBox.warning(self, "警告", str(e))
                        return

                    try:
                        body = json.loads(body_input.toPlainText() or "{}")
                        if not isinstance(body, dict):
                            raise ValueError("请求体必须是一个JSON对象")
                    except json.JSONDecodeError:
                        QMessageBox.warning(self, "警告", "请求体格式错误，请检查JSON格式")
                        return
                    except ValueError as e:
                        QMessageBox.warning(self, "警告", str(e))
                        return

                    # 获取当前配置
                    current_config = {
                        "name": name_label.text(),
                        "method": method_combo.currentText(),
                        "url": url_input.text(),
                        "headers": headers,
                        "body": body,
                        "theme": config_data["name"],
                        "version": self.generate_version(),
                        "timestamp": QDateTime.currentDateTime().toString("yyyyMMdd_hhmmss"),
                        "comment": "更新配置"
                    }
                    
                    # 保存配置
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(current_config, f, indent=4, ensure_ascii=False)
                    
                    # 保存版本历史
                    version_dir = os.path.join(os.path.dirname(config_file), "versions")
                    version_file = os.path.join(version_dir, f"{current_config['timestamp']}.json")
                    with open(version_file, 'w', encoding='utf-8') as f:
                        json.dump(current_config, f, indent=4, ensure_ascii=False)
                    
                    QMessageBox.information(self, "成功", "配置已保存")
                    
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"保存配置失败：{str(e)}")
            
            def on_send():
                try:
                    # 获取请求参数
                    method = method_combo.currentText()
                    url = url_input.text().strip()
                    
                    if not url:
                        QMessageBox.warning(self, "警告", "请输入API地址")
                        return
                    
                    # 验证并解析请求头
                    try:
                        headers = json.loads(headers_input.toPlainText() or "{}")
                        if not isinstance(headers, dict):
                            raise ValueError("请求头必须是一个JSON对象")
                    except json.JSONDecodeError:
                        QMessageBox.warning(self, "警告", "请求头格式错误，请检查JSON格式")
                        return
                    except ValueError as e:
                        QMessageBox.warning(self, "警告", str(e))
                        return
                    
                    # 验证并解析请求体
                    try:
                        body = json.loads(body_input.toPlainText() or "{}")
                        if not isinstance(body, dict):
                            raise ValueError("请求体必须是一个JSON对象")
                    except json.JSONDecodeError:
                        QMessageBox.warning(self, "警告", "请求体格式错误，请检查JSON格式")
                        return
                    except ValueError as e:
                        QMessageBox.warning(self, "警告", str(e))
                        return
                    
                    # 发送请求
                    import requests
                    response = requests.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=body if method in ['POST', 'PUT', 'PATCH'] else None,
                        params=body if method == 'GET' else None
                    )
                    
                    # 显示响应结果
                    try:
                        response_json = response.json()
                        response_text.setPlainText(json.dumps(response_json, indent=4, ensure_ascii=False))
                    except:
                        response_text.setPlainText(response.text)
                    
                except requests.exceptions.RequestException as e:
                    QMessageBox.critical(self, "错误", f"发送请求失败：{str(e)}")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"发送请求失败：{str(e)}")
            
            save_button.clicked.connect(on_save)
            send_button.clicked.connect(on_send)
            history_button.clicked.connect(lambda: self.show_version_history(config_data))
            
            # 将标签页添加到标签页组件
            self.tab_widget.addTab(tab, config_data.get("name", "未命名"))
            
            # 切换到新创建的标签页
            self.tab_widget.setCurrentWidget(tab)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载配置失败：{str(e)}")
            return

    def generate_version(self):
        """生成新的版本号"""
        return datetime.now().strftime("%Y%m%d%H%M%S")  # 使用时间戳作为版本号

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 