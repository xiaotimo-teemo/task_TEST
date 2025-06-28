import sys
import os
import json
import shutil
from datetime import datetime, timedelta
import requests
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QTextEdit,
                             QComboBox, QSpinBox, QDialog, QDialogButtonBox,
                             QLineEdit, QTreeWidget, QTreeWidgetItem, QSplitter,
                             QGroupBox, QFrame, QScrollArea, QMenuBar,
                             QFileDialog, QMessageBox, QListWidget, QListWidgetItem,
                             QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout,
                             QTabWidget, QSizePolicy, QFormLayout, QRadioButton,
                             QSystemTrayIcon, QMenu, QDoubleSpinBox, QPlainTextEdit,
                             QTreeWidgetItemIterator)
from PySide6.QtCore import Qt, QDateTime, QSize
from PySide6.QtGui import (QColor, QTextCharFormat, QSyntaxHighlighter, QFont,
                          QAction, QTextDocument, QIcon)
import traceback
import difflib
import glob
import subprocess
from urllib.parse import urlparse
import socket
import html
import multiprocessing
import random
import string
from PySide6.QtCore import QThread
import copy

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

class ApiHighlighter(QSyntaxHighlighter):
    def __init__(self, parent: QTextDocument):
        super().__init__(parent)
        
        # 定义各种格式
        self.formats = {
            'url_protocol': self.create_format('#0066CC'),  # 协议 (http://, https://)
            'url_domain': self.create_format('#009933'),    # 域名
            'url_path': self.create_format('#CC6600'),      # 路径
            'url_param': self.create_format('#9933CC'),     # URL参数
            'url_special': self.create_format('#FF3366'),   # 特殊字符 (:/?&=)
        }

    def create_format(self, color, style=None):
        """创建文本格式"""
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color))
        if style == 'bold':
            text_format.setFontWeight(QFont.Weight.Bold)
        elif style == 'italic':
            text_format.setFontItalic(True)
        return text_format

    def highlightBlock(self, text):
        """高亮URL文本"""
        import re
        
        # URL协议
        protocol_pattern = r'(https?://)'
        for match in re.finditer(protocol_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats['url_protocol'])
        
        # 域名
        domain_pattern = r'(?:https?://)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        for match in re.finditer(domain_pattern, text):
            if not text[match.start():match.start(1)].startswith('http'):
                self.setFormat(match.start(), match.end() - match.start(), self.formats['url_domain'])
        
        # 路径
        path_pattern = r'/[^?#\s]*'
        for match in re.finditer(path_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats['url_path'])
        
        # URL参数
        param_pattern = r'[?&][^=&\s]+=[^&\s]*'
        for match in re.finditer(param_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats['url_param'])
        
        # 特殊字符
        special_pattern = r'[:/?&=#]'
        for match in re.finditer(special_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats['url_special'])

class JsonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent: QTextDocument):
        super().__init__(parent)
        
        # 定义各种格式
        self.formats = {
            'brace': self.create_format('#FF6B6B'),         # 大括号 {}
            'bracket': self.create_format('#4ECDC4'),       # 方括号 []
            'colon': self.create_format('#45B7D1'),         # 冒号 :
            'comma': self.create_format('#96CEB4'),         # 逗号 ,
            'string': self.create_format('#2ECC71'),        # 字符串
            'number': self.create_format('#3498DB'),        # 数字
            'boolean': self.create_format('#9B59B6'),       # 布尔值
            'null': self.create_format('#E74C3C'),          # null值
            'key': self.create_format('#F39C12', 'bold')    # 键名
        }

    def create_format(self, color, style=None):
        """创建文本格式"""
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color))
        if style == 'bold':
            text_format.setFontWeight(QFont.Weight.Bold)
        elif style == 'italic':
            text_format.setFontItalic(True)
        return text_format

    def highlightBlock(self, text):
        """高亮JSON文本"""
        import re
        
        # 大括号
        for match in re.finditer(r'[{}]', text):
            self.setFormat(match.start(), 1, self.formats['brace'])
        
        # 方括号
        for match in re.finditer(r'[\[\]]', text):
            self.setFormat(match.start(), 1, self.formats['bracket'])
        
        # 冒号
        for match in re.finditer(r':', text):
            self.setFormat(match.start(), 1, self.formats['colon'])
        
        # 逗号
        for match in re.finditer(r',', text):
            self.setFormat(match.start(), 1, self.formats['comma'])
        
        # 键名
        key_pattern = r'"([^"\\]*(\\.[^"\\]*)*)"(?=\s*:)'
        for match in re.finditer(key_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats['key'])
        
        # 字符串值
        string_pattern = r'"([^"\\]*(\\.[^"\\]*)*)"(?!\s*:)'
        for match in re.finditer(string_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats['string'])
        
        # 数字
        number_pattern = r'\b-?\d+\.?\d*\b'
        for match in re.finditer(number_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats['number'])
        
        # 布尔值
        boolean_pattern = r'\b(true|false)\b'
        for match in re.finditer(boolean_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats['boolean'])
        
        # null值
        null_pattern = r'\bnull\b'
        for match in re.finditer(null_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats['null'])

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
        
        # 设置窗口标题
        self.setWindowTitle('API测试工具')
        
        # 初始化目录
        self.template_dir = os.path.join("api_configs", "templates")
        self.user_dir = os.path.join("api_configs", "user_configs")
        self.position_dir = "position_projects"
        
        # 确保目录存在
        os.makedirs(self.template_dir, exist_ok=True)
        os.makedirs(self.user_dir, exist_ok=True)
        os.makedirs(self.position_dir, exist_ok=True)
        
        # 加载项目配置
        self.project_config_file = os.path.join(self.position_dir, "projects.json")
        self.project_configs = self._load_project_configs()
        
        # 初始化数据相关的属性
        self.position_data = None  # 当前加载的数据
        self.shelf_col = None      # 货架列名
        self.position_col = None   # 仓位列名
        
        # 创建主窗口部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 创建API测试标签页
        api_tab = QWidget()
        self.setup_api_tab(api_tab)
        tab_widget.addTab(api_tab, "API测试")
        
        # 创建货架查询标签页
        shelf_tab = QWidget()
        self.setup_shelf_tab(shelf_tab)
        tab_widget.addTab(shelf_tab, "货架查询")
        
        # 创建仓位查询标签页
        position_tab = QWidget()
        self.setup_position_tab(position_tab)
        tab_widget.addTab(position_tab, "仓位查询")
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 加载已保存的配置
        self.load_saved_configs()
        
        # 加载项目列表
        self._load_projects()
        
        # 设置窗口大小
        self.resize(1200, 800)
        
    def _load_project_configs(self):
        """加载项目配置"""
        try:
            if os.path.exists(self.project_config_file):
                with open(self.project_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            QMessageBox.warning(self, "警告", f"加载项目配置失败: {str(e)}")
            return {}
            
    def _save_project_configs(self):
        """保存项目配置"""
        try:
            with open(self.project_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.project_configs, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "警告", f"保存项目配置失败: {str(e)}")
            
    def create_position_project(self):
        """创建新项目"""
        try:
            # 创建对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("创建新项目")
            layout = QVBoxLayout(dialog)
            
            # 项目名称输入
            name_layout = QHBoxLayout()
            name_label = QLabel("项目名称：")
            name_input = QLineEdit()
            name_layout.addWidget(name_label)
            name_layout.addWidget(name_input)
            layout.addLayout(name_layout)
            
            # 项目描述输入
            desc_layout = QHBoxLayout()
            desc_label = QLabel("项目描述：")
            desc_input = QLineEdit()
            desc_layout.addWidget(desc_label)
            desc_layout.addWidget(desc_input)
            layout.addLayout(desc_layout)
            
            # 按钮
            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")
            button_layout.addStretch()
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            def on_ok():
                name = name_input.text().strip()
                desc = desc_input.text().strip()
                
                if not name:
                    QMessageBox.warning(dialog, "警告", "请输入项目名称")
                    return
                    
                if name in self.project_configs:
                    QMessageBox.warning(dialog, "警告", "项目名称已存在")
                    return
                    
                # 创建项目目录
                project_dir = os.path.join(self.position_dir, name)
                versions_dir = os.path.join(project_dir, "versions")
                os.makedirs(project_dir, exist_ok=True)
                os.makedirs(versions_dir, exist_ok=True)
                
                # 保存项目配置
                self.project_configs[name] = {
                    "name": name,
                    "description": desc,
                    "created_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "version_count": 0
                }
                self._save_project_configs()
                
                # 刷新项目列表
                self._load_projects()
                
                dialog.accept()
                QMessageBox.information(self, "成功", "项目创建成功！")
                
            def on_cancel():
                dialog.reject()
                
            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(on_cancel)
            
            # 显示对话框
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建项目失败: {str(e)}")
            
    def import_position_data(self):
        """导入仓位数据"""
        try:
            # 获取当前项目
            project_name = self.shelf_project_combo.currentText()
            if not project_name or project_name == "请选择项目":
                QMessageBox.warning(self, "警告", "请先选择项目")
                return
                
            # 选择文件
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择Excel文件",
                "",
                "Excel Files (*.xlsx *.xls)"
            )
            
            if not file_path:
                return
                
            # 读取文件
            df = pd.read_excel(file_path)
            
            # 检查是否有仓位列
            has_position = False
            for col in df.columns:
                if "仓位" in str(col).lower() or "position" in str(col).lower():
                    has_position = True
                    break
                    
            if not has_position:
                QMessageBox.warning(self, "警告", "文件中没有仓位列")
                return
                
            # 生成版本号
            project_config = self.project_configs[project_name]
            version = f"v1.0.{project_config['version_count'] + 1}"
            
            # 保存文件
            versions_dir = os.path.join(self.position_dir, project_name, "versions")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(versions_dir, f"{version}_{timestamp}.xlsx")
            df.to_excel(save_path, index=False)
            
            # 更新项目配置
            project_config["version_count"] += 1
            project_config["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_project_configs()
            
            # 重新加载文件列表
            self._load_files(project_name)
            
            QMessageBox.information(self, "成功", "数据导入成功！")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入数据失败: {str(e)}")
            
    def delete_position_file(self):
        """删除仓位数据文件"""
        try:
            # 获取当前项目和文件
            project_name = self.shelf_project_combo.currentText()
            if not project_name or project_name == "请选择项目":
                QMessageBox.warning(self, "警告", "请先选择项目")
                return
                
            file_index = self.shelf_file_combo.currentIndex()
            if file_index <= 0:
                QMessageBox.warning(self, "警告", "请先选择文件")
                return
                
            file_path = self.shelf_file_combo.itemData(file_index)
            if not file_path or not os.path.exists(file_path):
                QMessageBox.warning(self, "警告", "文件不存在")
                return
                
            # 确认删除
            reply = QMessageBox.question(
                self,
                "确认",
                "确定要删除该文件吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 删除文件
                os.remove(file_path)
                
                # 更新项目配置
                project_config = self.project_configs[project_name]
                project_config["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._save_project_configs()
                
                # 重新加载文件列表
                self._load_files(project_name)
                
                QMessageBox.information(self, "成功", "文件删除成功！")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除文件失败: {str(e)}")
            
    def delete_position_project(self):
        """删除项目"""
        try:
            # 获取当前项目
            project_name = self.shelf_project_combo.currentText()
            if not project_name or project_name == "请选择项目":
                QMessageBox.warning(self, "警告", "请先选择项目")
                return
                
            # 确认删除
            reply = QMessageBox.question(
                self,
                "确认",
                "确定要删除该项目吗？这将删除项目的所有数据！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 删除项目目录
                project_dir = os.path.join(self.position_dir, project_name)
                if os.path.exists(project_dir):
                    shutil.rmtree(project_dir)
                
                # 删除项目配置
                del self.project_configs[project_name]
                self._save_project_configs()
                
                # 重新加载项目列表
                self._load_projects()
                
                # 清空相关控件
                self.shelf_file_combo.clear()
                self.shelf_file_combo.addItem("请选择文件")
                self.shelf_list.clear()
                self.shelf_table.setRowCount(0)
                self.shelf_table.setColumnCount(0)
                self.shelf_stats_label.setText("总货架数：0")
                self.shelf_search.clear()
                self.query_button.setEnabled(False)
                
                QMessageBox.information(self, "成功", "项目删除成功！")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除项目失败: {str(e)}")

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
        self.dynamic_data_configs = {}  # 存储动态数据配置
        main_layout = QHBoxLayout(tab)
        
        # 创建左侧的保存配置列表面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 模板配置列表
        template_label = QLabel("模板配置:")
        template_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.template_list = QListWidget()
        self.template_list.itemDoubleClicked.connect(self.load_api_config)
        left_layout.addWidget(template_label)
        left_layout.addWidget(self.template_list)
        
        # 用户配置列表
        user_label = QLabel("用户配置:")
        user_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.user_list = QListWidget()
        self.user_list.itemDoubleClicked.connect(self.load_api_config)
        left_layout.addWidget(user_label)
        left_layout.addWidget(self.user_list)
        
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

    def format_json_text(self, text_edit):
        """格式化JSON文本并进行校验"""
        try:
            # 获取当前文本
            text = text_edit.toPlainText().strip()
            if not text:
                return True, "空文本"
            
            # 尝试解析JSON
            parsed = json.loads(text)
            
            # 格式化JSON
            formatted = json.dumps(parsed, indent=4, ensure_ascii=False)
            
            # 更新文本框
            text_edit.setPlainText(formatted)
            return True, "格式化成功"
            
        except json.JSONDecodeError as e:
            return False, f"JSON格式错误: {str(e)}"
        except Exception as e:
            return False, f"发生错误: {str(e)}"

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
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入请求URL...")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        
        # 添加本机IP显示
        local_ip = self.get_local_ip()
        ip_label = QLabel(f"本机IP: {local_ip}")
        ip_label.setStyleSheet("color: #666; padding: 0 10px;")
        url_layout.addWidget(ip_label)
        
        layout.addLayout(url_layout)
        
        # 请求头和请求体布局
        headers_body_layout = QHBoxLayout()
        
        # 请求头部分
        headers_group = QGroupBox("请求头")
        headers_layout = QVBoxLayout()
        self.headers_input = JsonEditor()
        headers_layout.addWidget(self.headers_input)
        headers_group.setLayout(headers_layout)
        headers_body_layout.addWidget(headers_group)
        
        # 请求体部分
        body_group = QGroupBox("请求体")
        body_layout = QVBoxLayout()
        self.body_input = JsonEditor()
        body_layout.addWidget(self.body_input)
        body_group.setLayout(body_layout)
        headers_body_layout.addWidget(body_group)
        
        layout.addLayout(headers_body_layout)
        
        # 批量请求控制
        batch_layout = QHBoxLayout()
        
        # 调用次数
        count_label = QLabel("调用次数:")
        self.count_input = QSpinBox()
        self.count_input.setMinimum(1)
        self.count_input.setMaximum(1000)
        self.count_input.setValue(1)
        batch_layout.addWidget(count_label)
        batch_layout.addWidget(self.count_input)
        
        # 请求间隔
        interval_label = QLabel("请求间隔(秒):")
        self.interval_input = QDoubleSpinBox()
        self.interval_input.setMinimum(0)
        self.interval_input.setMaximum(60)
        self.interval_input.setValue(0)
        batch_layout.addWidget(interval_label)
        batch_layout.addWidget(self.interval_input)
        
        batch_layout.addStretch()
        
        # 动态数据按钮
        self.dynamic_data_button = QPushButton("动态数据配置")
        self.dynamic_data_button.clicked.connect(self.show_dynamic_data_dialog)
        self.dynamic_data_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                margin-right: 8px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        batch_layout.addWidget(self.dynamic_data_button)

        # 发送按钮
        self.send_button = QPushButton("发送请求")
        self.send_button.clicked.connect(self.send_request)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        batch_layout.addWidget(self.send_button)
        
        layout.addLayout(batch_layout)
        
        # 响应显示区域
        response_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧响应内容
        response_left = QWidget()
        response_left_layout = QVBoxLayout(response_left)
        
        response_label = QLabel("响应内容:")
        response_left_layout.addWidget(response_label)
        
        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        self.response_text.setFont(QFont("Menlo", 12))
        response_left_layout.addWidget(self.response_text)
        
        response_splitter.addWidget(response_left)
        
        # 右侧请求信息
        response_right = QWidget()
        response_right_layout = QVBoxLayout(response_right)
        
        info_label = QLabel("请求信息:")
        response_right_layout.addWidget(info_label)
        
        self.info_table = QTableWidget()
        self.info_table.setColumnCount(4)
        self.info_table.setHorizontalHeaderLabels(["URL", "状态码", "耗时(ms)", "结果"])
        self.info_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        response_right_layout.addWidget(self.info_table)
        
        response_splitter.addWidget(response_right)
        
        # 设置左右比例为2:1
        response_splitter.setStretchFactor(0, 2)
        response_splitter.setStretchFactor(1, 1)
        
        layout.addWidget(response_splitter)
        
    def send_request(self):
        try:
            url = self.url_input.text().strip()
            method = self.method_combo.currentText()
            count = self.count_input.value()
            interval = self.interval_input.value()
            
            if not url:
                QMessageBox.warning(self, "警告", "请输入URL")
                return
            
            # 校验并格式化请求头
            headers_text = self.headers_input.text()
            if headers_text.strip():
                try:
                    headers = json.loads(headers_text)
                except json.JSONDecodeError as e:
                    QMessageBox.warning(self, "警告", f"请求头JSON格式错误: {str(e)}")
                    return
            else:
                headers = {}
            
            # 校验并格式化请求体
            body = None
            if method in ["POST", "PUT", "PATCH"]:
                body_text = self.body_input.text()
                if body_text.strip():
                    try:
                        body = json.loads(body_text)
                    except json.JSONDecodeError as e:
                        QMessageBox.warning(self, "警告", f"请求体JSON格式错误: {str(e)}")
                        return
            
            # 清空响应区域
            self.response_text.clear()
            self.info_table.setRowCount(0)
            
            # 获取动态数据配置
            dynamic_configs = list(self.dynamic_data_configs.values())
            
            # 执行请求
            for i in range(count):
                # 准备请求体
                current_body = body
                
                # 如果有动态数据配置，生成并应用动态数据
                if dynamic_configs:
                    try:
                        # 随机选择一个配置
                        config = random.choice(dynamic_configs)
                        # 生成动态数据
                        dynamic_data = self.generate_dynamic_data(config)
                        # 应用到请求体
                        current_body = self.apply_dynamic_data(body, dynamic_data)
                    except Exception as e:
                        QMessageBox.critical(self, "错误", f"生成动态数据失败: {str(e)}")
                        return
                
                # 发送请求
                start_time = datetime.now()
                try:
                    response = requests.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=current_body if current_body is not None else None,
                        timeout=30
                    )
                    
                    # 计算请求时间
                    elapsed = (datetime.now() - start_time).total_seconds() * 1000
                    
                    # 添加到信息表格
                    row = self.info_table.rowCount()
                    self.info_table.insertRow(row)
                    self.info_table.setItem(row, 0, QTableWidgetItem(url))
                    self.info_table.setItem(row, 1, QTableWidgetItem(str(response.status_code)))
                    self.info_table.setItem(row, 2, QTableWidgetItem(f"{elapsed:.2f}"))
                    
                    status_item = QTableWidgetItem("成功" if response.status_code < 400 else "失败")
                    status_item.setForeground(QColor("#4CAF50" if response.status_code < 400 else "#F44336"))
                    self.info_table.setItem(row, 3, status_item)
                    
                    # 显示响应内容
                    try:
                        response_text = response.json()
                        formatted_response = json.dumps(response_text, indent=4, ensure_ascii=False)
                    except:
                        formatted_response = response.text
                    
                    if i > 0:
                        self.response_text.append("\n" + "-" * 50 + "\n")
                    self.response_text.append(f"请求 {i + 1}:\n{formatted_response}")
                    
                except Exception as e:
                    # 添加错误信息到表格
                    row = self.info_table.rowCount()
                    self.info_table.insertRow(row)
                    self.info_table.setItem(row, 0, QTableWidgetItem(url))
                    self.info_table.setItem(row, 1, QTableWidgetItem("--"))
                    self.info_table.setItem(row, 2, QTableWidgetItem("--"))
                    
                    status_item = QTableWidgetItem("失败")
                    status_item.setForeground(QColor("#F44336"))
                    self.info_table.setItem(row, 3, status_item)
                    
                    # 显示错误信息
                    if i > 0:
                        self.response_text.append("\n" + "-" * 50 + "\n")
                    self.response_text.append(f"请求 {i + 1} 失败:\n{str(e)}")
                
                # 等待指定的间隔时间
                if i < count - 1 and interval > 0:
                    QThread.msleep(int(interval * 1000))
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发送请求失败: {str(e)}")

    def format_json_and_show_result(self, text_edit):
        """格式化JSON并显示结果"""
        success, message = self.format_json_text(text_edit)
        if success:
            if message != "空文本":
                QMessageBox.information(self, "成功", "JSON格式化成功")
        else:
            QMessageBox.warning(self, "警告", message)

    def get_next_template_number(self):
        """获取下一个模板配置序号"""
        if not os.path.exists(self.template_dir):
            return "001"
            
        try:
            # 获取所有模板配置的序号
            numbers = []
            for item in os.listdir(self.template_dir):
                if os.path.isdir(os.path.join(self.template_dir, item)):
                    try:
                        # 提取数字部分
                        number = int(''.join(filter(str.isdigit, item.split('_')[0])))
                        numbers.append(number)
                    except ValueError:
                        continue
            
            if not numbers:
                return "001"
            
            # 找到最大序号并返回下一个序号
            next_number = max(numbers) + 1
            return f"{next_number:03d}"
            
        except Exception as e:
            print(f"获取模板序号时出错: {str(e)}")
            return "001"

    def create_new_config(self):
        """创建新的API配置"""
        dialog = QDialog(self)
        dialog.setWindowTitle("新建API配置")
        dialog.setModal(True)
        
        # 设置对话框大小
        dialog.resize(600, 800)
        
        layout = QVBoxLayout(dialog)
        
        # 创建表单布局
        form_layout = QFormLayout()
        
        # API名称输入
        name_input = QLineEdit()
        name_input.setPlaceholderText("请输入API名称")
        form_layout.addRow("API名称:", name_input)
        
        # 请求方法选择
        method_combo = QComboBox()
        method_combo.addItems(["POST", "GET", "PUT", "DELETE"])
        form_layout.addRow("请求方法:", method_combo)
        
        # URL输入
        url_input = QLineEdit()
        url_input.setPlaceholderText("请输入请求URL")
        form_layout.addRow("请求URL:", url_input)
        
        # 请求头输入
        headers_input = QTextEdit()
        headers_input.setPlaceholderText("请输入请求头（JSON格式）")
        headers_input.setMaximumHeight(150)
        # 设置默认的请求头
        default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        headers_input.setPlainText(json.dumps(default_headers, indent=4, ensure_ascii=False))
        form_layout.addRow("请求头:", headers_input)
        
        # 请求参数输入
        params_input = QTextEdit()
        params_input.setPlaceholderText("请输入请求参数（JSON格式）")
        params_input.setMaximumHeight(150)
        form_layout.addRow("请求参数:", params_input)
        
        # 请求体输入
        body_input = QTextEdit()
        body_input.setPlaceholderText("请输入请求体（JSON格式）")
        body_input.setMaximumHeight(150)
        form_layout.addRow("请求体:", body_input)
        
        # 配置类型选择
        type_layout = QHBoxLayout()
        template_radio = QRadioButton("模板配置")
        user_radio = QRadioButton("用户配置")
        template_radio.setChecked(True)  # 默认选中模板配置
        type_layout.addWidget(template_radio)
        type_layout.addWidget(user_radio)
        form_layout.addRow("配置类型:", type_layout)
        
        layout.addLayout(form_layout)
        
        # 添加格式化按钮
        format_layout = QHBoxLayout()
        format_headers_btn = QPushButton("格式化请求头")
        format_params_btn = QPushButton("格式化请求参数")
        format_body_btn = QPushButton("格式化请求体")
        
        format_layout.addWidget(format_headers_btn)
        format_layout.addWidget(format_params_btn)
        format_layout.addWidget(format_body_btn)
        layout.addLayout(format_layout)
        
        # 添加按钮布局
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # 添加状态显示区域
        status_label = QLabel()
        status_label.setStyleSheet("color: red;")
        layout.addWidget(status_label)
        
        def format_json_text(text_edit):
            """格式化JSON文本并进行校验"""
            try:
                # 获取当前文本
                text = text_edit.toPlainText().strip()
                if not text:
                    return True, "空文本"
                
                # 尝试解析JSON
                parsed = json.loads(text)
                
                # 格式化JSON
                formatted = json.dumps(parsed, indent=4, ensure_ascii=False)
                
                # 更新文本框
                text_edit.setPlainText(formatted)
                return True, "格式化成功"
                
            except json.JSONDecodeError as e:
                return False, f"JSON格式错误: {str(e)}"
            except Exception as e:
                return False, f"发生错误: {str(e)}"
        
        def on_format_headers():
            success, message = format_json_text(headers_input)
            status_label.setText(message)
            status_label.setStyleSheet("color: green;" if success else "color: red;")
            
        def on_format_params():
            success, message = format_json_text(params_input)
            status_label.setText(message)
            status_label.setStyleSheet("color: green;" if success else "color: red;")
            
        def on_format_body():
            success, message = format_json_text(body_input)
            status_label.setText(message)
            status_label.setStyleSheet("color: green;" if success else "color: red;")
        
        format_headers_btn.clicked.connect(on_format_headers)
        format_params_btn.clicked.connect(on_format_params)
        format_body_btn.clicked.connect(on_format_body)
        
        def on_text_changed():
            # 只检查API名称是否已填写
            name = name_input.text().strip()
            ok_button.setEnabled(bool(name))
            
        name_input.textChanged.connect(on_text_changed)
        on_text_changed()  # 初始化按钮状态
        
        def on_config_type_changed(index):
            # 根据配置类型更新界面
            is_template = template_radio.isChecked()
            if is_template:
                # 模板配置时，清空请求参数和请求体
                params_input.clear()
                body_input.clear()
            
        template_radio.toggled.connect(lambda: on_config_type_changed(0))
        user_radio.toggled.connect(lambda: on_config_type_changed(1))
        
        def on_ok():
            """处理确定按钮点击事件"""
            try:
                # 获取输入内容
                name = name_input.text().strip()
                if not name:
                    QMessageBox.warning(dialog, "警告", "请输入API名称")
                    return
                
                # 检查名称是否已存在
                config_type = "template" if template_radio.isChecked() else "user"
                base_dir = self.template_dir if config_type == "template" else self.user_dir
                config_dir = os.path.join(base_dir, name)
                
                if os.path.exists(config_dir):
                    QMessageBox.warning(dialog, "警告", "该名称已存在")
                    return
                
                # 创建配置目录
                os.makedirs(config_dir)
                os.makedirs(os.path.join(config_dir, "versions"))
                
                # 构建配置数据
                config = {
                    "name": name,
                    "method": method_combo.currentText(),
                    "url": url_input.text().strip(),
                    "headers": json.loads(headers_input.toPlainText().strip() or "{}"),
                    "params": json.loads(params_input.toPlainText().strip() or "{}"),
                    "body": json.loads(body_input.toPlainText().strip() or "{}")
                }
                
                # 保存配置文件
                current_file = os.path.join(config_dir, "current.json")
                with open(current_file, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
                
                dialog.accept()
                
            except json.JSONDecodeError as e:
                QMessageBox.warning(dialog, "警告", f"JSON格式错误: {str(e)}")
            except Exception as e:
                QMessageBox.critical(dialog, "错误", f"保存配置失败: {str(e)}")
                
        def on_cancel():
            dialog.reject()
            
        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(on_cancel)
        
        # 显示对话框
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                # 创建配置目录
                config_type = "template" if template_radio.isChecked() else "user"
                base_dir = self.template_dir if config_type == "template" else self.user_dir
                config_dir = os.path.join(base_dir, name)
                os.makedirs(config_dir)
                os.makedirs(os.path.join(config_dir, "versions"))
                
                # 构建配置数据
                config = {
                    "name": name,
                    "method": method_combo.currentText(),
                    "url": url_input.text().strip(),
                    "headers": json.loads(headers_input.toPlainText().strip() or "{}"),
                    "params": json.loads(params_input.toPlainText().strip() or "{}"),
                    "body": json.loads(body_input.toPlainText().strip() or "{}"),
                    "version": "v1.0.0",
                    "created_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # 保存配置文件
                current_file = os.path.join(config_dir, "current.json")
                with open(current_file, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                
                # 保存版本文件
                version_file = os.path.join(config_dir, "versions", "v1.0.0.json")
                with open(version_file, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                
                # 刷新配置列表
                self.load_saved_configs()
                
                QMessageBox.information(self, "成功", "配置创建成功！")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建配置失败: {str(e)}")
                # 如果创建失败，清理已创建的目录
                if os.path.exists(config_dir):
                    try:
                        shutil.rmtree(config_dir)
                    except:
                        pass

    def save_api_config(self):
        """保存当前API配置"""
        # 获取当前选中的列表和项目
        current_template = self.template_list.currentItem()
        current_user = self.user_list.currentItem()
        
        if not current_template and not current_user:
            QMessageBox.warning(self, "警告", "请先选择一个配置！")
            return
            
        # 保存当前选中的配置信息
        current_item = current_template if current_template else current_user
        config_type = "template" if current_template else "user"
        current_row = self.template_list.currentRow() if current_template else self.user_list.currentRow()
        base_dir = self.template_dir if config_type == "template" else self.user_dir
            
        # 创建保存对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("保存配置")
        layout = QVBoxLayout(dialog)
        
        # 配置名称显示
        name_layout = QHBoxLayout()
        name_label = QLabel("配置名称:")
        name_display = QLabel(current_item.text())
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
            current_file = os.path.join(base_dir, current_item.text(), "current.json")
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
            
            # 获取下一个版本号
            version = self.get_next_version(current_item.text(), config_type)
            
            try:
                # 校验并获取请求头
                headers_text = self.headers_input.text().strip()
                if headers_text:
                    try:
                        headers = json.loads(headers_text)
                    except json.JSONDecodeError as e:
                        QMessageBox.warning(self, "警告", f"请求头JSON格式错误: {str(e)}")
                    return
                else:
                    headers = {}
                
                # 获取URL
                url = self.url_input.text().strip()
                if not url:
                    QMessageBox.warning(self, "警告", "请输入URL")
                    return
                
                # 校验并获取请求体
                body_text = self.body_input.text().strip()
                if body_text:
                    try:
                        body = json.loads(body_text)
                    except json.JSONDecodeError as e:
                        QMessageBox.warning(self, "警告", f"请求体JSON格式错误: {str(e)}")
                        return
                else:
                    body = {}
                
                # 准备配置数据
                config_data = {
                    "method": self.method_combo.currentText(),
                    "url": url,
                    "headers": headers,
                    "body": body,
                    "count": self.count_input.value(),
                    "version": version,
                    "theme": theme,
                    "comment": version_comment,
                    "timestamp": datetime.now().isoformat(),
                    "config_type": config_type
                }
                
                try:
                    # 创建配置目录
                    config_dir = os.path.join(base_dir, current_item.text())
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
                    
                    # 刷新配置列表并恢复选中状态
                    self.load_saved_configs()
                    if config_type == "template":
                        self.template_list.setCurrentRow(current_row)
                    else:
                        self.user_list.setCurrentRow(current_row)
                    
                    QMessageBox.information(
                        self,
                        "成功",
                        f"配置已保存！\n版本号: {version}\n主题: {theme}\n备注: {version_comment}"
                    )
                    
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "错误",
                        f"保存配置失败：{str(e)}"
                    )
                    
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "错误",
                    f"准备配置数据失败：{str(e)}"
                )

    def get_next_version(self, config_name, config_type):
        """获取下一个版本号"""
        # 确定配置目录
        base_dir = self.template_dir if config_type == "template" else self.user_dir
        versions_dir = os.path.join(base_dir, config_name, "versions")
        
        if not os.path.exists(versions_dir):
            return "v1.0.0"  # 如果没有版本目录，返回初始版本号
            
        try:
            # 获取所有版本文件
            version_files = [f for f in os.listdir(versions_dir) if f.endswith('.json')]
            if not version_files:
                return "v1.0.0"  # 如果没有版本文件，返回初始版本号
            
            # 读取所有版本号
            versions = []
            for vf in version_files:
                with open(os.path.join(versions_dir, vf), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    version = data.get('version', '')
                    if version.startswith('v') and version.count('.') == 2:
                        versions.append(version)
            
            if not versions:
                return "v1.0.0"  # 如果没有有效的版本号，返回初始版本号
            
            # 找到最新的版本号
            latest_version = sorted(versions, key=lambda v: [int(n) for n in v[1:].split('.')])[-1]
            
            # 解析版本号
            major, minor, patch = map(int, latest_version[1:].split('.'))
            
            # 增加补丁号
            patch += 1
            if patch > 9:  # 如果补丁号超过9
                patch = 0
                minor += 1  # 增加次版本号
                if minor > 9:  # 如果次版本号超过9
                    minor = 0
                    major += 1  # 增加主版本号
            
            return f"v{major}.{minor}.{patch}"
            
        except Exception as e:
            print(f"获取版本号时出错: {str(e)}")
            return "v1.0.0"  # 出错时返回初始版本号

    def load_saved_configs(self):
        """加载模板配置和用户配置"""
        self.template_list.clear()
        self.user_list.clear()
        
        try:
            # 加载模板配置
            if os.path.exists(self.template_dir):
                # 获取所有模板配置
                template_items = []
                for item in os.listdir(self.template_dir):
                    config_path = os.path.join(self.template_dir, item)
                    if os.path.isdir(config_path) and os.path.exists(os.path.join(config_path, 'current.json')):
                        try:
                            # 尝试从名称中提取序号
                            number = int(''.join(filter(str.isdigit, item.split('_')[0])))
                            template_items.append((number, item))
                        except ValueError:
                            # 如果无法提取数字,将其放在最后
                            template_items.append((float('inf'), item))
                
                # 按序号排序
                template_items.sort(key=lambda x: x[0])
                
                # 添加到列表
                for _, item in template_items:
                    list_item = QListWidgetItem(item)
                    list_item.setData(Qt.ItemDataRole.UserRole, "template")
                    self.template_list.addItem(list_item)
            
            # 加载用户配置
            if os.path.exists(self.user_dir):
                for item in os.listdir(self.user_dir):
                    config_path = os.path.join(self.user_dir, item)
                    if os.path.isdir(config_path) and os.path.exists(os.path.join(config_path, 'current.json')):
                        list_item = QListWidgetItem(item)
                        list_item.setData(Qt.ItemDataRole.UserRole, "user")
                        self.user_list.addItem(list_item)
                        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载配置列表失败: {str(e)}")

    def load_api_config(self, item):
        """从列表中选择配置时加载配置"""
        if not item:
            return
            
        config_name = item.text()
        config_type = item.data(Qt.ItemDataRole.UserRole)
        self.load_api_config_by_name(config_name, config_type)

    def delete_api_config(self):
        """删除选中的配置"""
        # 获取当前选中的列表和项目
        current_template = self.template_list.currentItem()
        current_user = self.user_list.currentItem()
        
        if not current_template and not current_user:
            QMessageBox.warning(self, "警告", "请选择要删除的配置")
            return
            
        # 确定要删除的项目和其类型
        if current_template:
            current_item = current_template
            config_type = "template"
            base_dir = self.template_dir
        else:
            current_item = current_user
            config_type = "user"
            base_dir = self.user_dir
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除{'模板' if config_type == 'template' else '用户'}配置 '{current_item.text()}' 吗？这将删除所有版本历史！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                config_path = os.path.join(base_dir, current_item.text())
                shutil.rmtree(config_path)
                self.load_saved_configs()  # 刷新配置列表
                QMessageBox.information(self, "成功", "配置删除成功！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除配置失败: {str(e)}")

    def show_version_history(self):
        """显示版本历史"""
        # 获取当前选中的列表和项目
        current_template = self.template_list.currentItem()
        current_user = self.user_list.currentItem()
        
        if not current_template and not current_user:
            QMessageBox.warning(self, "警告", "请先选择一个配置！")
            return
            
        # 保存当前选中的配置信息
        current_item = current_template if current_template else current_user
        config_type = "template" if current_template else "user"
        current_row = self.template_list.currentRow() if current_template else self.user_list.currentRow()
        base_dir = self.template_dir if config_type == "template" else self.user_dir
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"版本历史 - {current_item.text()}")
        
        # 获取主窗口大小
        main_window_geometry = self.geometry()
        
        # 设置对话框大小为主窗口的80%
        dialog_width = int(main_window_geometry.width() * 0.8)
        dialog_height = int(main_window_geometry.height() * 0.8)
        
        # 创建主布局
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 添加配置类型标签
        type_label = QLabel(f"配置类型: {'模板配置' if config_type == 'template' else '用户配置'}")
        type_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(type_label)
        
        # 添加颜色说明
        legend_widget = QWidget()
        legend_layout = QHBoxLayout(legend_widget)
        legend_layout.setContentsMargins(0, 0, 0, 0)
        legend_layout.setSpacing(20)
        
        # 当前版本说明
        current_version_legend = QWidget()
        current_version_layout = QHBoxLayout(current_version_legend)
        current_version_layout.setContentsMargins(0, 0, 0, 0)
        current_version_layout.setSpacing(5)
        
        current_version_color = QLabel()
        current_version_color.setFixedSize(16, 16)
        current_version_color.setStyleSheet("background-color: #FFEBEE; border: 1px solid #EF5350; border-radius: 2px;")
        current_version_text = QLabel("当前版本")
        current_version_text.setStyleSheet("color: #666666;")
        
        current_version_layout.addWidget(current_version_color)
        current_version_layout.addWidget(current_version_text)
        current_version_layout.addStretch()
        
        # 历史版本说明
        history_version_legend = QWidget()
        history_version_layout = QHBoxLayout(history_version_legend)
        history_version_layout.setContentsMargins(0, 0, 0, 0)
        history_version_layout.setSpacing(5)
        
        history_version_color = QLabel()
        history_version_color.setFixedSize(16, 16)
        history_version_color.setStyleSheet("background-color: white; border: 1px solid #ddd; border-radius: 2px;")
        history_version_text = QLabel("历史版本")
        history_version_text.setStyleSheet("color: #666666;")
        
        history_version_layout.addWidget(history_version_color)
        history_version_layout.addWidget(history_version_text)
        history_version_layout.addStretch()
        
        # 添加说明到布局
        legend_layout.addWidget(current_version_legend)
        legend_layout.addWidget(history_version_legend)
        legend_layout.addStretch()
        
        layout.addWidget(legend_widget)
        
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
        versions_dir = os.path.join(base_dir, current_item.text(), "versions")
        current_file = os.path.join(base_dir, current_item.text(), "current.json")
        
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
                current_version = current_config.get("version", "")
        except Exception:
            current_config = {}
            current_version = ""
        
        # 设置列宽比例
        column_ratios = [0.06, 0.12, 0.12, 0.15, 0.3, 0.1, 0.075, 0.075]  # 总和为1
        
        for row, version_file in enumerate(version_files):
            # 设置行高
            table.setRowHeight(row, 40)
            
            with open(os.path.join(versions_dir, version_file), "r", encoding="utf-8") as f:
                version_data = json.load(f)
            
            # 检查是否是当前版本
            is_current_version = version_data.get("version", "") == current_version
            
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
            
            # 如果是当前版本，设置背景色
            if is_current_version:
                for col in range(5):  # 只对前5列设置背景色
                    item = table.item(row, col)
                    if item:
                        item.setBackground(QColor("#FFEBEE"))  # 浅红色背景
                        item.setForeground(QColor("#D32F2F"))  # 深红色文字
                        item.setToolTip("当前使用的版本")
                        font = item.font()
                        font.setBold(True)  # 加粗文字
                        item.setFont(font)
            
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
            def create_restore_callback(n, vd, f, t):
                return lambda checked=False: self.restore_version(n, vd, f, t)
            restore_button.clicked.connect(create_restore_callback(
                current_item.text(),
                version_data,
                version_file,
                config_type
            ))
            # 如果是当前版本，禁用回滚按钮
            if is_current_version:
                restore_button.setEnabled(False)
                restore_button.setToolTip("当前版本无需回滚")
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
            def create_delete_callback(n, f, t):
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
                            base_dir = self.template_dir if t == "template" else self.user_dir
                            version_file_path = os.path.join(base_dir, n, "versions", f)
                            os.remove(version_file_path)
                            dialog.reject()  # 关闭当前对话框
                            self.show_version_history()  # 重新打开显示新的版本列表
                            # 恢复选中状态
                            if t == "template":
                                self.template_list.setCurrentRow(current_row)
                            else:
                                self.user_list.setCurrentRow(current_row)
                            QMessageBox.information(self, "成功", "版本已成功删除！")
                        except Exception as e:
                            QMessageBox.critical(self, "错误", f"删除版本时出错：{str(e)}")
                return delete_version
            
            delete_button.clicked.connect(create_delete_callback(
                current_item.text(),
                version_file,
                config_type
            ))
            # 如果是当前版本，禁用删除按钮
            if is_current_version:
                delete_button.setEnabled(False)
                delete_button.setToolTip("不能删除当前使用的版本")
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

    def format_json_for_diff(self, data):
        """格式化JSON用于对比显示，优化body字段的格式"""
        if not isinstance(data, dict):
            return json.dumps(data, indent=4, ensure_ascii=False)
        
        # 定义字段的显示顺序和分组
        field_order = [
            # 基本信息组
            "method", "url",
            # 请求头组
            "headers",
            # 请求体组
            "body",
            # 其他信息组
            "count", "theme", "version", "timestamp", "comment", "config_type"
        ]
        
        # 处理body字段如果是字符串形式的JSON
        if isinstance(data.get('body'), str):
            try:
                data['body'] = json.loads(data['body'])
            except:
                pass
        
        result = []
        # 获取最长键名的长度，用于对齐
        max_key_length = max(len(str(k)) for k in data.keys()) if data else 0
        
        # 按照预定义顺序处理字段
        for key in field_order:
            if key in data:
                value = data[key]
                # 对齐键名
                key_str = f'"{key}"'
                padding = ' ' * (max_key_length - len(str(key)))
                
                if key == 'headers':
                    # 处理headers，保持紧凑格式
                    if isinstance(value, dict):
                        headers_str = json.dumps(value, indent=4, ensure_ascii=False)
                        # 缩进除第一行外的所有行
                        indented_headers = headers_str.replace('\n', '\n    ')
                        result.append(f'{padding}{key_str}: {indented_headers}')
                elif key == 'body':
                    # 处理body，使用更好的格式化
                    if isinstance(value, dict):
                        body_str = json.dumps(value, indent=4, ensure_ascii=False)
                        # 缩进除第一行外的所有行
                        indented_body = body_str.replace('\n', '\n    ')
                        result.append(f'{padding}{key_str}: {indented_body}')
                    else:
                        # 如果body不是dict，直接使用原始值
                        value_str = json.dumps(value, ensure_ascii=False)
                        result.append(f'{padding}{key_str}: {value_str}')
                else:
                    # 处理其他字段
                    if isinstance(value, dict):
                        value_str = json.dumps(value, indent=4, ensure_ascii=False)
                        # 缩进除第一行外的所有行
                        indented_value = value_str.replace('\n', '\n    ')
                        result.append(f'{padding}{key_str}: {indented_value}')
                    else:
                        value_str = json.dumps(value, ensure_ascii=False)
                        result.append(f'{padding}{key_str}: {value_str}')
        
        # 处理未在预定义顺序中的其他字段
        for key, value in data.items():
            if key not in field_order:
                key_str = f'"{key}"'
                padding = ' ' * (max_key_length - len(str(key)))
                value_str = json.dumps(value, ensure_ascii=False)
                result.append(f'{padding}{key_str}: {value_str}')
        
        # 组合最终的JSON字符串
        return '{\n    ' + ',\n    '.join(result) + '\n}'

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
        
        # 添加图例说明
        legend_widget = QWidget()
        legend_layout = QHBoxLayout(legend_widget)
        legend_layout.setContentsMargins(0, 0, 0, 0)
        legend_layout.setSpacing(20)
        
        # 添加删除的内容图例
        deleted_legend = QWidget()
        deleted_layout = QHBoxLayout(deleted_legend)
        deleted_layout.setContentsMargins(0, 0, 0, 0)
        deleted_layout.setSpacing(5)
        deleted_color = QLabel()
        deleted_color.setFixedSize(16, 16)
        deleted_color.setStyleSheet("background-color: #FFE6E6; border: 1px solid #FF8080; border-radius: 2px;")
        deleted_text = QLabel("删除的内容")
        deleted_text.setStyleSheet("color: #666666;")
        deleted_layout.addWidget(deleted_color)
        deleted_layout.addWidget(deleted_text)
        
        # 添加新增的内容图例
        added_legend = QWidget()
        added_layout = QHBoxLayout(added_legend)
        added_layout.setContentsMargins(0, 0, 0, 0)
        added_layout.setSpacing(5)
        added_color = QLabel()
        added_color.setFixedSize(16, 16)
        added_color.setStyleSheet("background-color: #E6FFE6; border: 1px solid #80FF80; border-radius: 2px;")
        added_text = QLabel("新增的内容")
        added_text.setStyleSheet("color: #666666;")
        added_layout.addWidget(added_color)
        added_layout.addWidget(added_text)
        
        # 添加修改的内容图例
        modified_legend = QWidget()
        modified_layout = QHBoxLayout(modified_legend)
        modified_layout.setContentsMargins(0, 0, 0, 0)
        modified_layout.setSpacing(5)
        modified_color = QLabel()
        modified_color.setFixedSize(16, 16)
        modified_color.setStyleSheet("background-color: #E6E6FF; border: 1px solid #8080FF; border-radius: 2px;")
        modified_text = QLabel("修改的内容")
        modified_text.setStyleSheet("color: #666666;")
        modified_layout.addWidget(modified_color)
        modified_layout.addWidget(modified_text)
        
        # 将图例添加到布局
        legend_layout.addWidget(deleted_legend)
        legend_layout.addWidget(added_legend)
        legend_layout.addWidget(modified_legend)
        legend_layout.addStretch()
        
        info_layout.addWidget(legend_widget)
        
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
            
            # 使用优化的格式化方法
            current_json = self.format_json_for_diff(current_compare)
            version_json = self.format_json_for_diff(version_compare)
            
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
            style = """
                <style>
                    .diff-add { background-color: #E6FFE6; }  /* 浅绿色 */
                    .diff-del { background-color: #FFE6E6; }  /* 浅红色 */
                    .diff-mod { background-color: #E6E6FF; }  /* 浅蓝色 */
                    .diff-normal { }
                    pre { margin: 0; white-space: pre-wrap; }
                    .line { padding: 2px 5px; }
                </style>
            """
            
            current_html.append(style)
            version_html.append(style)
            
            current_html.append("<pre>")
            version_html.append("<pre>")
            
            # 用于跟踪上一行的状态
            prev_state = None
            
            # 处理每一行
            for line in diff:
                if line.startswith('  '):  # 相同的行
                    escaped_line = html.escape(line[2:])
                    current_html.append(f'<div class="line diff-normal">{escaped_line}</div>')
                    version_html.append(f'<div class="line diff-normal">{escaped_line}</div>')
                    prev_state = 'normal'
                elif line.startswith('- '):  # 在当前配置中删除的行
                    escaped_line = html.escape(line[2:])
                    if prev_state == 'del':
                        # 继续使用删除样式
                        current_html.append(f'<div class="line diff-del">{escaped_line}</div>')
                    else:
                        # 新的删除块
                        current_html.append(f'<div class="line diff-del">{escaped_line}</div>')
                    prev_state = 'del'
                elif line.startswith('+ '):  # 在历史版本中新增的行
                    escaped_line = html.escape(line[2:])
                    if prev_state == 'add':
                        # 继续使用新增样式
                        version_html.append(f'<div class="line diff-add">{escaped_line}</div>')
                    else:
                        # 新的新增块
                        version_html.append(f'<div class="line diff-add">{escaped_line}</div>')
                    prev_state = 'add'
                elif line.startswith('? '):  # 差异标记行，跳过
                    continue
            
            current_html.append("</pre>")
            version_html.append("</pre>")
            
            # 设置HTML内容
            current_text.setHtml(''.join(current_html))
            version_text.setHtml(''.join(version_html))
            
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

    def restore_version(self, config_name, version_data, version_file, config_type):
        """回滚到指定版本"""
        # 保存当前选中的行
        current_row = self.template_list.currentRow() if config_type == "template" else self.user_list.currentRow()
        
        reply = QMessageBox.question(
            self,
            "确认回滚",
            f"确定要回滚到版本 {os.path.splitext(version_file)[0]} 吗？\n这将覆盖当前配置。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 确定配置目录
                base_dir = self.template_dir if config_type == "template" else self.user_dir
                
                # 1. 更新current.json
                current_file = os.path.join(base_dir, config_name, "current.json")
                with open(current_file, "w", encoding="utf-8") as f:
                    json.dump(version_data, f, ensure_ascii=False, indent=4)
                
                # 2. 在主界面加载配置
                self.load_api_config_by_name(config_name, config_type)
                
                # 3. 关闭版本历史对话框
                dialog = None
                for widget in QApplication.topLevelWidgets():
                    if isinstance(widget, QDialog) and widget.windowTitle().startswith("版本历史"):
                        dialog = widget
                        break
                
                if dialog:
                    dialog.reject()  # 使用reject替代done，避免模态对话框的问题
                
                # 4. 恢复选中状态
                if config_type == "template":
                    self.template_list.setCurrentRow(current_row)
                else:
                    self.user_list.setCurrentRow(current_row)
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "错误",
                    f"回滚失败：{str(e)}"
                )

    def load_api_config_by_name(self, config_name, config_type):
        """根据配置名称加载配置"""
        try:
            # 确定配置目录
            base_dir = self.template_dir if config_type == "template" else self.user_dir
            current_file = os.path.join(base_dir, config_name, "current.json")
            
            # 读取配置文件
            with open(current_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            # 更新界面显示
            self.method_combo.setCurrentText(config_data.get("method", "GET"))
            self.url_input.setText(config_data.get("url", ""))
            
            # 处理请求头
            headers = config_data.get("headers", {})
            if isinstance(headers, str):
                try:
                    headers = json.loads(headers)
                except:
                    headers = {}
            if not isinstance(headers, dict):
                headers = {}
            headers_str = json.dumps(headers, indent=4, ensure_ascii=False)
            self.headers_input.setText(headers_str)
            
            # 处理请求体
            body = config_data.get("body", {})
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except:
                    body = {"content": body}
            elif not isinstance(body, dict):
                body = {"content": str(body)}
            body_str = json.dumps(body, indent=4, ensure_ascii=False)
            self.body_input.setText(body_str)
            
            # 设置调用次数
            self.count_input.setValue(config_data.get("count", 1))
            
            # 显示成功提示
            QMessageBox.information(self, "成功", "配置已加载")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载配置失败：{str(e)}")
            traceback.print_exc()

    def format_response(self, response, error=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = f"=== 请求时间: {timestamp} ===\n\n"
        
        # 添加请求信息
        result += "=== 请求信息 ===\n"
        result += f"URL: {response.request.url if not error else self.url_input.text()}\n"
        result += f"Method: {response.request.method if not error else self.method_combo.currentText()}\n"
        
        # 添加请求头
        result += "\n=== 请求头 ===\n"
        if not error:
            headers = dict(response.request.headers)
            result += json.dumps(headers, indent=4, ensure_ascii=False)
        else:
            try:
                headers = json.loads(self.headers_input.text() or "{}")
                result += json.dumps(headers, indent=4, ensure_ascii=False)
            except:
                result += "无法解析请求头\n"
        
        # 添加请求体
        if self.method_combo.currentText() in ["POST", "PUT", "PATCH"]:
            result += "\n\n=== 请求体 ===\n"
            try:
                body = json.loads(self.body_input.text() or "{}")
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

    def import_position_file(self):
        """导入仓位信息文件"""
        pass  # 删除这个重复的方法

    def setup_position_tab(self, tab):
        """设置仓位信息标签页"""
        layout = QVBoxLayout(tab)
        
        # 创建顶部工具栏
        toolbar = QHBoxLayout()
        
        # 创建项目按钮
        create_project_btn = QPushButton("创建项目")
        create_project_btn.clicked.connect(self.create_position_project)
        toolbar.addWidget(create_project_btn)
        
        # 导入数据按钮
        self.import_button = QPushButton("导入仓位信息")
        self.import_button.clicked.connect(self.import_position_data)
        self.import_button.setEnabled(False)  # 初始禁用
        toolbar.addWidget(self.import_button)
        
        # 查看历史按钮
        self.history_button = QPushButton("查看历史版本")  # 保存为实例变量
        self.history_button.clicked.connect(self.show_position_history)
        self.history_button.setEnabled(False)  # 初始禁用
        toolbar.addWidget(self.history_button)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 创建项目选择区域
        project_layout = QHBoxLayout()
        project_label = QLabel("选择项目：")
        self.project_combo = QComboBox()
        
        # 添加默认选项
        self.project_combo.blockSignals(True)  # 阻止信号
        self.project_combo.addItem("请选择项目")
        self.project_combo.setCurrentIndex(0)
        self.project_combo.blockSignals(False)  # 恢复信号
        
        project_layout.addWidget(project_label)
        project_layout.addWidget(self.project_combo)
        project_layout.addStretch()
        layout.addLayout(project_layout)
        
        # 创建主要内容区域的水平布局
        main_layout = QHBoxLayout()
        
        # 左侧文件列表区域
        file_group = QGroupBox("文件列表")
        file_layout = QVBoxLayout(file_group)
        
        self.file_list = QListWidget()
        file_layout.addWidget(self.file_list)
        
        # 文件操作按钮
        file_buttons = QHBoxLayout()
        self.delete_file_btn = QPushButton("删除文件")
        self.delete_file_btn.setEnabled(False)
        self.delete_file_btn.clicked.connect(self.delete_position_file)
        file_buttons.addWidget(self.delete_file_btn)
        file_layout.addLayout(file_buttons)
        
        # 将左侧布局添加到主布局
        main_layout.addWidget(file_group, stretch=1)
        
        # 右侧表格区域
        table_group = QGroupBox("数据详情")
        table_layout = QVBoxLayout(table_group)
        self.position_table = QTableWidget()
        self.position_table.setColumnCount(0)
        self.position_table.setRowCount(0)
        table_layout.addWidget(self.position_table)
        
        # 将右侧表格添加到主布局
        main_layout.addWidget(table_group, stretch=2)
        
        # 将主布局添加到总布局
        layout.addLayout(main_layout)
        
        # 连接信号
        self.project_combo.currentIndexChanged.connect(self.on_project_selected)
        self.file_list.itemSelectionChanged.connect(self.on_file_selected)
        
        # 最后加载项目列表
        self.load_position_projects()
                        
    def load_position_projects(self):
        """加载仓位信息项目列表"""
        try:
            # 暂时阻止信号触发
            self.project_combo.blockSignals(True)
            
            # 清空下拉框
            self.project_combo.clear()
            
            # 添加默认选项
            self.project_combo.addItem("请选择项目")
            
            # 确保目录存在
            if not os.path.exists(self.position_dir):
                os.makedirs(self.position_dir)
                self.project_combo.setCurrentIndex(0)
                self.project_combo.blockSignals(False)
                return
            
            # 获取所有项目目录
            projects = []
            for item in os.listdir(self.position_dir):
                config_file = os.path.join(self.position_dir, item, "config.json")
                if os.path.isdir(os.path.join(self.position_dir, item)) and os.path.exists(config_file):
                    try:
                        with open(config_file, "r", encoding="utf-8") as f:
                            config = json.load(f)
                            projects.append({
                                "name": item,
                                "config": config
                            })
                    except Exception as e:
                        print(f"加载项目配置失败：{str(e)}")
            
            # 按项目名称排序
            projects.sort(key=lambda x: x["name"])
            
            # 添加项目到下拉框
            for project in projects:
                self.project_combo.addItem(project["name"])
            
            # 恢复信号并设置默认选项
            self.project_combo.setCurrentIndex(0)
            self.project_combo.blockSignals(False)
            
            # 清空文件列表和表格
            self.file_list.clear()
            self.position_table.setRowCount(0)
            self.position_table.setColumnCount(0)
            
        except Exception as e:
            self.project_combo.blockSignals(False)  # 确保信号被恢复
            QMessageBox.critical(self, "错误", f"加载项目列表失败：{str(e)}")
            
    def on_project_selected(self, index):
        """处理项目选择变化"""
        try:
            # 检查索引的有效性
            if index < 0 or index >= self.project_combo.count():
                return
                
            # 如果选择的是默认项（index = 0）
            if index == 0:
                self.import_button.setEnabled(False)
                self.history_button.setEnabled(False)
                self.delete_file_btn.setEnabled(False)
                self.file_list.clear()
                self.position_table.setRowCount(0)
                self.position_table.setColumnCount(0)
                return
                
            # 启用相关按钮
            self.import_button.setEnabled(True)
            self.history_button.setEnabled(True)
            
            # 更新文件列表
            project_name = self.project_combo.currentText()
            self.update_file_list(project_name)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"切换项目失败：{str(e)}")
            # 发生错误时重置界面状态
            self.import_button.setEnabled(False)
            self.history_button.setEnabled(False)
            self.delete_file_btn.setEnabled(False)
            self.file_list.clear()
            self.position_table.setRowCount(0)
            self.position_table.setColumnCount(0)

    def update_file_list(self, project_name):
        """更新文件列表"""
        try:
            self.file_list.clear()
            versions_dir = os.path.join(self.position_dir, project_name, "versions")
            
            if not os.path.exists(versions_dir):
                return
                
            # 获取所有版本文件
            version_files = []
            for filename in os.listdir(versions_dir):
                if filename.endswith('.xlsx'):
                    filepath = os.path.join(versions_dir, filename)
                    version_files.append({
                        'filename': filename,
                        'version': filename.split('_')[0],
                        'timestamp': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M:%S"),
                        'path': filepath
                    })
            
            # 按时间排序
            version_files.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # 添加到列表
            for version in version_files:
                item = QListWidgetItem(f"{version['filename']} ({version['timestamp']})")
                item.setData(Qt.ItemDataRole.UserRole, version)
                self.file_list.addItem(item)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"更新文件列表失败：{str(e)}")

    def on_file_selected(self):
        """处理文件选择变化"""
        selected_items = self.file_list.selectedItems()
        self.delete_file_btn.setEnabled(len(selected_items) > 0)
        
        # 清空货架列表和统计信息
        self.shelf_list.clear()
        self.shelf_stats_label.setText("总货架数：0")
        self.shelf_search.clear()
        
        if len(selected_items) > 0:
            version_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
            try:
                df = pd.read_excel(version_data['path'])
                
                # 查找货架列
                shelf_column = None
                for col in df.columns:
                    if "仓位" in str(col).lower() or "position" in str(col).lower():
                        shelf_column = col
                        break
                
                # 如果找到货架列，添加到货架列表
                if shelf_column is not None:
                    # 获取唯一的货架编号并排序
                    unique_shelves = sorted(df[shelf_column].unique())
                    valid_shelves = [shelf for shelf in unique_shelves if pd.notna(shelf)]
                    
                    # 更新货架统计信息
                    self.shelf_stats_label.setText(f"总货架数：{len(valid_shelves)}")
                    
                    # 添加到货架列表
                    for shelf in valid_shelves:
                        item = QListWidgetItem(str(shelf))
                        item.setForeground(QColor(255, 0, 0))  # 设置红色文字
                        self.shelf_list.addItem(item)
                
                # 更新完整数据表格
                self.update_position_table(df)
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载文件失败：{str(e)}")
                self.shelf_list.clear()  # 清空货架列表
                self.shelf_stats_label.setText("总货架数：0")
                self.position_table.setRowCount(0)
                self.position_table.setColumnCount(0)

    def generate_next_version(self, current_version):
        """生成下一个版本号"""
        try:
            # 解析当前版本号
            version_parts = current_version.lstrip('v').split('.')
            major, minor, patch = map(int, version_parts)
            
            # 增加补丁号
            patch += 1
            if patch > 9:
                patch = 0
                minor += 1
                if minor > 9:
                    minor = 0
                    major += 1
            
            return f"v{major}.{minor}.{patch}"
            
        except:
            return "v1.0.0"

    def update_position_table(self, df):
        """更新表格显示"""
        try:
            # 保存数据用于查询
            self.position_data = df
            
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
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"更新表格失败：{str(e)}")

    def setup_shelf_tab(self, tab):
        """设置货架查询标签页"""
        try:
            # 创建布局
            layout = QVBoxLayout()
            tab.setLayout(layout)
            
            # 创建顶部工具栏
            toolbar = QHBoxLayout()
            layout.addLayout(toolbar)
            
            # 项目选择下拉框
            project_label = QLabel("项目：")
            toolbar.addWidget(project_label)
            self.shelf_project_combo = QComboBox()
            self.shelf_project_combo.addItem("请选择项目")
            toolbar.addWidget(self.shelf_project_combo)
            
            # 文件选择下拉框
            file_label = QLabel("文件：")
            toolbar.addWidget(file_label)
            self.shelf_file_combo = QComboBox()
            self.shelf_file_combo.addItem("请选择文件")
            toolbar.addWidget(self.shelf_file_combo)
            
            # 货架编号输入框
            shelf_label = QLabel("货架编号：")
            toolbar.addWidget(shelf_label)
            self.shelf_input = QLineEdit()
            self.shelf_input.setPlaceholderText("请输入6位数字货架编号")
            toolbar.addWidget(self.shelf_input)
            
            # 查询按钮
            self.query_button = QPushButton("查询")
            self.query_button.setEnabled(False)
            toolbar.addWidget(self.query_button)
            
            # 添加弹性空间
            toolbar.addStretch()
            
            # 创建统计信息标签
            self.query_stats_label = QLabel()
            self.query_stats_label.setStyleSheet("color: blue;")  # 设置文字颜色为蓝色
            layout.addWidget(self.query_stats_label)
            
            # 创建货架列表和表格的水平布局
            content_layout = QHBoxLayout()
            layout.addLayout(content_layout)
            
            # 左侧货架列表
            list_layout = QVBoxLayout()
            content_layout.addLayout(list_layout)
            
            # 货架统计标签
            self.shelf_stats_label = QLabel("总货架数：0")
            list_layout.addWidget(self.shelf_stats_label)
            
            # 货架搜索框
            self.shelf_search = QLineEdit()
            self.shelf_search.setPlaceholderText("搜索货架编号")
            list_layout.addWidget(self.shelf_search)
            
            # 货架列表
            self.shelf_list = QListWidget()
            list_layout.addWidget(self.shelf_list)
            
            # 右侧表格
            self.shelf_table = QTableWidget()
            self.shelf_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            content_layout.addWidget(self.shelf_table)
            
            # 设置列表和表格的宽度比例
            content_layout.setStretch(0, 1)
            content_layout.setStretch(1, 3)
            
            # 初始化数据
            self.position_data = None
            self.shelf_col = None
            self.position_col = None
            self.current_file = None
            
            # 连接信号
            self.shelf_project_combo.activated.connect(self.on_shelf_project_selected)
            self.shelf_file_combo.activated.connect(self.on_shelf_file_selected)
            self.shelf_search.textChanged.connect(self.on_shelf_search)
            self.shelf_list.itemClicked.connect(self.on_shelf_item_clicked)
            self.query_button.clicked.connect(self.on_shelf_query_clicked)
            
            # 加载项目列表
            self._load_projects()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"初始化货架查询界面失败: {str(e)}")

    def on_shelf_project_selected(self, index):
        """处理项目选择"""
        try:
            # 暂时阻断信号
            self.shelf_file_combo.blockSignals(True)
            
            # 重置状态
            self.shelf_file_combo.clear()
            self.shelf_list.clear()
            self.shelf_table.setRowCount(0)
            self.shelf_table.setColumnCount(0)
            self.shelf_stats_label.setText("总货架数：0")
            self.shelf_search.clear()
            self.query_stats_label.clear()  # 清空统计信息
            self.query_button.setEnabled(False)
            
            # 获取项目名称
            project_name = self.shelf_project_combo.currentText()
            if not project_name or project_name == "请选择项目":
                self.shelf_file_combo.addItem("请选择文件")
                self.shelf_file_combo.blockSignals(False)
                return
            
            # 检查项目目录
            project_dir = os.path.join(self.position_dir, project_name)
            versions_dir = os.path.join(project_dir, "versions")
            
            if not os.path.exists(versions_dir):
                os.makedirs(versions_dir)
                QMessageBox.information(self, "提示", "该项目还没有任何文件，请先导入数据")
                self.shelf_file_combo.addItem("请选择文件")
                self.shelf_file_combo.blockSignals(False)
                return
            
            # 获取所有Excel文件
            files = []
            for filename in os.listdir(versions_dir):
                if filename.endswith('.xlsx'):
                    filepath = os.path.join(versions_dir, filename)
                    files.append({
                        'name': filename,
                        'path': filepath,
                        'time': os.path.getmtime(filepath)
                    })
            
            # 检查是否有文件
            if not files:
                QMessageBox.information(self, "提示", "该项目还没有任何文件，请先导入数据")
                self.shelf_file_combo.addItem("请选择文件")
                self.shelf_file_combo.blockSignals(False)
                return
            
            # 按时间排序
            files.sort(key=lambda x: x['time'], reverse=True)
            
            # 添加默认选项
            self.shelf_file_combo.addItem("请选择文件")
            
            # 添加文件列表
            for file in files:
                self.shelf_file_combo.addItem(file['name'], file['path'])
            
            # 恢复信号
            self.shelf_file_combo.blockSignals(False)
            
        except Exception as e:
            self.shelf_file_combo.blockSignals(False)  # 确保信号被恢复
            QMessageBox.critical(self, "错误", f"切换项目失败: {str(e)}")
        
    def on_shelf_file_selected(self, index):
        """处理文件选择"""
        try:
            # 暂时阻断信号
            self.shelf_list.blockSignals(True)
            
            # 重置状态
            self.shelf_list.clear()
            self.shelf_table.setRowCount(0)
            self.shelf_table.setColumnCount(0)
            self.shelf_stats_label.setText("总货架数：0")
            self.shelf_search.clear()
            self.query_stats_label.clear()  # 清空统计信息
            self.query_button.setEnabled(False)
            
            # 获取文件路径
            if index <= 0:
                self.shelf_list.blockSignals(False)
                return
            
            file_path = self.shelf_file_combo.itemData(index)
            if not file_path or not os.path.exists(file_path):
                self.shelf_list.blockSignals(False)
                return
                
            # 加载数据
            try:
                self._load_data(file_path)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载数据失败: {str(e)}")
            
            # 恢复信号
            self.shelf_list.blockSignals(False)
            
        except Exception as e:
            self.shelf_list.blockSignals(False)  # 确保信号被恢复
            QMessageBox.critical(self, "错误", f"切换文件失败: {str(e)}")
            
    def _load_data(self, file_path):
        """加载文件数据"""
        try:
            # 读取文件
            df = pd.read_excel(file_path)
            
            # 查找货架列和仓位列
            self.shelf_col = None
            self.position_col = None
            for col in df.columns:
                col_str = str(col)
                if "货架" in col_str:
                    # 检查该列的值是否都是6位数字（允许有空值）
                    values = [str(val) for val in df[col].tolist() if pd.notna(val)]
                    if all(val.isdigit() and len(val) == 6 for val in values):
                        self.shelf_col = col
                elif "仓位" in col_str:
                    self.position_col = col
                
                if self.shelf_col and self.position_col:  # 如果都找到了就退出循环
                    break
                
            if not self.shelf_col:
                QMessageBox.warning(self, "警告", "文件中没有有效的货架列（需要包含'货架'且值为6位数字）")
                return
                
            if not self.position_col:
                QMessageBox.warning(self, "警告", "文件中没有仓位列")
                return
                
            # 获取所有货架编号
            unique_shelves = df[self.shelf_col].unique()
            valid_shelves = [str(int(shelf)).zfill(6) for shelf in unique_shelves if pd.notna(shelf)]  # 确保都是6位数字
                    
            # 更新货架统计信息
            self.shelf_stats_label.setText(f"总货架数：{len(valid_shelves)}")
                    
            # 添加到货架列表
            for shelf in valid_shelves:
                item = QListWidgetItem(str(shelf))
                item.setForeground(QColor(255, 0, 0))  # 设置红色文字
                self.shelf_list.addItem(item)
                
            # 保存数据
            self.position_data = df
            
            # 更新表格
            self.shelf_table.setRowCount(len(df))
            self.shelf_table.setColumnCount(len(df.columns))
            
            # 设置表头
            self.shelf_table.setHorizontalHeaderLabels([str(col) for col in df.columns])
            
            # 填充数据
            for i in range(len(df)):
                for j in range(len(df.columns)):
                    value = df.iloc[i, j]
                    # 如果是货架列，确保显示为6位数字
                    if df.columns[j] == self.shelf_col and pd.notna(value):
                        item = QTableWidgetItem(str(int(value)).zfill(6))
                        item.setForeground(QColor(255, 0, 0))  # 设置红色文字
                    else:
                        item = QTableWidgetItem(str(value))
                    self.shelf_table.setItem(i, j, item)
            
            # 自适应列宽
            self.shelf_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            
            # 启用查询按钮
            self.query_button.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载数据失败: {str(e)}")
            
    def on_shelf_search(self, text):
        """处理货架搜索"""
        try:
            # 清空表格
            self.shelf_table.setRowCount(0)
            
            if not text:
                return
                
            # 过滤并显示结果
            if self.position_data is not None and self.shelf_col is not None:
                # 获取匹配的行
                mask = self.position_data[self.shelf_col].astype(str).str.contains(text, case=False)
                matched_data = self.position_data[mask]
                
                # 更新表格
                self.shelf_table.setRowCount(len(matched_data))
                for i, (_, row) in enumerate(matched_data.iterrows()):
                    # 添加货架号
                    shelf_item = QTableWidgetItem(str(row[self.shelf_col]))
                    self.shelf_table.setItem(i, 0, shelf_item)
                    
                    # 添加仓位号
                    if self.position_col:
                        position_item = QTableWidgetItem(str(row[self.position_col]))
                        self.shelf_table.setItem(i, 1, position_item)
                        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"搜索失败: {str(e)}")
            
    def on_shelf_item_clicked(self, item):
        """处理货架项点击"""
        try:
            # 设置搜索框内容
            self.shelf_input.setText(item.text())
            
            # 触发查询
            self.on_shelf_query_clicked()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理点击事件失败: {str(e)}")

    def on_shelf_query_clicked(self):
        """处理查询按钮点击"""
        try:
            # 获取查询条件
            shelf_id = self.shelf_input.text().strip()
            if not shelf_id:
                QMessageBox.warning(self, "警告", "请输入货架编号")
                return
                
            # 检查是否为6位数字
            if not shelf_id.isdigit() or len(shelf_id) != 6:
                QMessageBox.warning(self, "警告", "请输入6位数字的货架编号")
                return
                
            # 检查数据是否存在
            if self.position_data is None:
                QMessageBox.warning(self, "警告", "请先选择数据文件")
                return
                
            # 检查是否已找到货架列和仓位列
            if not hasattr(self, 'shelf_col') or not self.shelf_col:
                QMessageBox.warning(self, "警告", "文件中没有有效的货架列（需要包含'货架'且值为6位数字）")
                return
                
            if not hasattr(self, 'position_col') or not self.position_col:
                QMessageBox.warning(self, "警告", "文件中没有仓位列")
                return
                
            # 过滤数据
            filtered_data = self.position_data[self.position_data[self.shelf_col].astype(str).str.zfill(6) == shelf_id]
            if len(filtered_data) == 0:
                QMessageBox.warning(self, "警告", "未找到匹配的记录")
                return
                
            # 设置表格的行数和列数
            self.shelf_table.setRowCount(len(filtered_data))
            self.shelf_table.setColumnCount(len(filtered_data.columns))
            
            # 设置表头
            self.shelf_table.setHorizontalHeaderLabels([str(col) for col in filtered_data.columns])
            
            # 填充数据
            for i in range(len(filtered_data)):
                for j in range(len(filtered_data.columns)):
                    value = filtered_data.iloc[i, j]
                    col = filtered_data.columns[j]
                    
                    # 根据列类型设置显示格式
                    if col == self.shelf_col and pd.notna(value):
                        # 货架列显示为6位数字
                        item = QTableWidgetItem(str(int(value)).zfill(6))
                        item.setForeground(QColor(255, 0, 0))  # 设置红色文字
                    elif col == self.position_col and pd.notna(value):
                        # 仓位列设置为蓝色
                        item = QTableWidgetItem(str(value))
                        item.setForeground(QColor(0, 0, 255))  # 设置蓝色文字
                    else:
                        item = QTableWidgetItem(str(value))
                    self.shelf_table.setItem(i, j, item)
            
            # 自适应列宽
            self.shelf_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            
            # 显示统计信息
            positions = filtered_data[self.position_col].tolist()
            unique_positions = list(set([str(p) for p in positions if pd.notna(p)]))
            stats_text = (
                f"货架编号：{shelf_id}  |  "
                f"关联仓位数：{len(unique_positions)}  |  "
                f"关联仓位：{', '.join(unique_positions)}"
            )
            self.query_stats_label.setText(stats_text)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查询失败: {str(e)}")

    def ping_url(self):
        """测试URL连通性"""
        try:
            url = self.url_input.text().strip()
            if not url:
                QMessageBox.warning(self, "警告", "请输入URL")
                return
            
            # 发送请求
            start_time = datetime.now()
            response = requests.get(url)
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            
            # 显示结果
            if response.ok:
                QMessageBox.information(self, "成功", f"连接成功！\n响应时间：{elapsed:.2f}ms\n状态码：{response.status_code}")
            else:
                QMessageBox.warning(self, "警告", f"连接失败！\n响应时间：{elapsed:.2f}ms\n状态码：{response.status_code}")
            
        except requests.ConnectionError as e:
            QMessageBox.critical(self, "错误", f"连接失败：{str(e)}")
        except requests.Timeout as e:
            QMessageBox.critical(self, "错误", f"连接超时：{str(e)}")
        except requests.RequestException as e:
            QMessageBox.critical(self, "错误", f"请求失败：{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发生错误：{str(e)}")
            
    def get_local_ip(self):
        """获取本机IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except socket.error as e:
            QMessageBox.critical(self, "错误", f"获取IP地址失败：{str(e)}")
            return "127.0.0.1"
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发生错误：{str(e)}")
            return "127.0.0.1"
            
    def query_position(self):
        """查询货架信息"""
        try:
            # 获取输入的货架编号
            shelf_code = self.shelf_input.text().strip()
        
            # 验证输入
            if not shelf_code or not shelf_code.isdigit() or len(shelf_code) != 6:
                QMessageBox.warning(self, "警告", "请输入6位数字的货架编号")
                return
            
            # 检查是否有数据
            if not hasattr(self, 'position_data') or self.position_data is None:
                QMessageBox.warning(self, "警告", "请先选择数据文件")
                return
            
            # 检查是否已找到货架列和仓位列
            if not hasattr(self, 'shelf_col') or not self.shelf_col:
                QMessageBox.warning(self, "警告", "文件中没有有效的货架列（需要包含'货架'且值为6位数字）")
                return
                
            if not hasattr(self, 'position_col') or not self.position_col:
                QMessageBox.warning(self, "警告", "文件中没有仓位列")
                return
            
            # 过滤数据
            filtered_data = self.position_data[self.position_data[self.shelf_col].astype(str).str.zfill(6) == shelf_code]
            
            # 显示结果
            if filtered_data.empty:
                QMessageBox.information(self, "提示", "未找到匹配的数据")
                self.shelf_table.setRowCount(0)
                self.shelf_table.setColumnCount(0)
            else:
                # 更新表格
                self.shelf_table.setRowCount(len(filtered_data))
                self.shelf_table.setColumnCount(len(filtered_data.columns))
                self.shelf_table.setHorizontalHeaderLabels([str(col) for col in filtered_data.columns])
                
                # 填充数据
                for i in range(len(filtered_data)):
                    for j in range(len(filtered_data.columns)):
                        value = filtered_data.iloc[i, j]
                        col = filtered_data.columns[j]
                        # 根据列类型设置显示格式
                        if col == self.shelf_col and pd.notna(value):
                            # 货架列显示为6位数字
                            item = QTableWidgetItem(str(int(value)).zfill(6))
                            item.setForeground(QColor(255, 0, 0))  # 设置红色文字
                        elif col == self.position_col and pd.notna(value):
                            # 仓位列设置为蓝色
                            item = QTableWidgetItem(str(value))
                            item.setForeground(QColor(0, 0, 255))  # 设置蓝色文字
                        else:
                            item = QTableWidgetItem(str(value))
                        self.shelf_table.setItem(i, j, item)
                
                # 自适应列宽
                self.shelf_table.resizeColumnsToContents()
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查询失败: {str(e)}")
            self.shelf_table.setRowCount(0)
            self.shelf_table.setColumnCount(0)

    def update_shelf_table(self, df):
        """更新货架表格"""
        try:
            # 重置界面状态
            self.shelf_table.setRowCount(0)
            self.shelf_table.setColumnCount(0)
            self.shelf_list.clear()
            self.shelf_stats_label.setText("总货架数：0")
            self.shelf_search.clear()
            self.position_data = df  # 保存数据用于查询
            
            # 如果已找到货架列，添加到货架列表
            if hasattr(self, 'shelf_col') and self.shelf_col is not None:
                # 获取唯一的货架编号并排序
                unique_shelves = sorted(df[self.shelf_col].unique())
                valid_shelves = [str(int(shelf)).zfill(6) for shelf in unique_shelves if pd.notna(shelf)]
                
                # 更新货架统计信息
                self.shelf_stats_label.setText(f"总货架数：{len(valid_shelves)}")
                
                # 添加到货架列表
                for shelf in valid_shelves:
                    item = QListWidgetItem(str(shelf))
            # 设置表格的行数和列数
            self.shelf_table.setRowCount(len(df))
            self.shelf_table.setColumnCount(len(df.columns))
            
            # 设置表头
            self.shelf_table.setHorizontalHeaderLabels([str(col) for col in df.columns])
            
            # 填充数据
            for i in range(len(df)):
                for j in range(len(df.columns)):
                    value = df.iloc[i, j]
                    col = df.columns[j]
                    
                    # 根据列类型设置显示格式
                    if col == self.shelf_col and pd.notna(value):
                        # 货架列显示为6位数字
                        item = QTableWidgetItem(str(int(value)).zfill(6))
                        item.setForeground(QColor(255, 0, 0))  # 设置红色文字
                    elif col == self.position_col and pd.notna(value):
                        # 仓位列设置为蓝色
                        item = QTableWidgetItem(str(value))
                        item.setForeground(QColor(0, 0, 255))  # 设置蓝色文字
                    else:
                        item = QTableWidgetItem(str(value))
                    self.shelf_table.setItem(i, j, item)
            
            # 自适应列宽
            self.shelf_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            
            # 添加表格排序功能
            self.shelf_table.setSortingEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"显示货架信息失败：{str(e)}")

    def show_position_history(self):
        """显示仓位信息历史版本"""
        if not self.project_combo.currentText():
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return
            
        project_name = self.project_combo.currentText()
        project_dir = os.path.join(self.position_dir, project_name)
        versions_dir = os.path.join(project_dir, "versions")
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"版本历史 - {project_name}")
        dialog.setModal(True)
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # 创建表格
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["版本号", "文件名", "更新时间", "文件大小", "操作"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(table)
        
        try:
            # 获取所有版本文件
            version_files = []
            for filename in os.listdir(versions_dir):
                if filename.endswith('.xlsx'):
                    filepath = os.path.join(versions_dir, filename)
                    version_files.append({
                        'filename': filename,
                        'version': filename.split('_')[0],
                        'timestamp': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M:%S"),
                        'size': os.path.getsize(filepath),
                        'path': filepath
                    })
            
            # 按时间排序
            version_files.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # 填充表格
            table.setRowCount(len(version_files))
            for row, version in enumerate(version_files):
                # 版本号
                table.setItem(row, 0, QTableWidgetItem(version['version']))
                # 文件名
                table.setItem(row, 1, QTableWidgetItem(version['filename']))
                # 更新时间
                table.setItem(row, 2, QTableWidgetItem(version['timestamp']))
                # 文件大小
                size_str = f"{version['size'] / 1024:.1f} KB" if version['size'] < 1024 * 1024 else f"{version['size'] / 1024 / 1024:.1f} MB"
                table.setItem(row, 3, QTableWidgetItem(size_str))
                
                # 操作按钮
                button_widget = QWidget()
                button_layout = QHBoxLayout(button_widget)
                button_layout.setContentsMargins(5, 0, 5, 0)
                
                load_button = QPushButton("加载")
                load_button.clicked.connect(lambda checked, v=version: self.load_position_version(v))
                button_layout.addWidget(load_button)
                
                delete_button = QPushButton("删除")
                delete_button.clicked.connect(lambda checked, v=version: self.delete_position_version(v))
                button_layout.addWidget(delete_button)
                
                table.setCellWidget(row, 4, button_widget)
        
        except Exception as e:
            QMessageBox.critical(dialog, "错误", f"加载版本历史失败：{str(e)}")
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)
        
        dialog.exec()
        
    def load_position_version(self, version):
        """加载指定版本的数据"""
        try:
            df = pd.read_excel(version['path'])
            self.update_position_table(df)
            
            QMessageBox.information(
                self,
                "成功",
                f"已加载版本：{version['version']}\n更新时间：{version['timestamp']}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载版本失败：{str(e)}")
            
    def delete_position_version(self, version):
        """删除指定版本"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除版本 {version['version']} 吗？\n此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(version['path'])
                self.show_position_history()  # 刷新历史窗口
                QMessageBox.information(self, "成功", "版本已删除")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除版本失败：{str(e)}")

    def _load_projects(self):
        """加载项目列表"""
        try:
            # 清空下拉框
            self.shelf_project_combo.clear()
            self.shelf_project_combo.addItem("请选择项目")
            
            # 获取所有项目目录
            if os.path.exists(self.position_dir):
                projects = []
                for item in os.listdir(self.position_dir):
                    item_path = os.path.join(self.position_dir, item)
                    if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "versions")):
                        projects.append(item)
                
                # 按字母顺序排序
                projects.sort()
                
                # 添加到下拉框
                for project in projects:
                    self.shelf_project_combo.addItem(project)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载项目列表失败: {str(e)}")
            
    def _load_files(self, project_name):
        """加载项目文件"""
        try:
            # 检查项目目录
            project_dir = os.path.join(self.position_dir, project_name)
            versions_dir = os.path.join(project_dir, "versions")
            
            if not os.path.exists(versions_dir):
                os.makedirs(versions_dir)
                QMessageBox.information(self, "提示", "该项目还没有任何文件，请先导入数据")
            return
        
            # 获取所有Excel文件
            files = []
            for filename in os.listdir(versions_dir):
                if filename.endswith('.xlsx'):
                    filepath = os.path.join(versions_dir, filename)
                    files.append({
                        'name': filename,
                        'path': filepath,
                        'time': os.path.getmtime(filepath)
                    })
            
            # 检查是否有文件
            if not files:
                QMessageBox.information(self, "提示", "该项目还没有任何文件，请先导入数据")
                return
            
            # 按时间排序
            files.sort(key=lambda x: x['time'], reverse=True)
            
            # 添加到下拉框
            for file in files:
                self.shelf_file_combo.addItem(file['name'], file['path'])
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载项目文件失败: {str(e)}")

    def show_dynamic_data_dialog(self):
        """显示动态数据配置对话框"""
        try:
            # 获取请求体内容
            body_text = self.body_input.text().strip()
            if not body_text:
                QMessageBox.warning(self, "警告", "请先填写请求体")
                return
                
            # 解析请求体JSON
            try:
                body_data = json.loads(body_text)
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "警告", f"请求体JSON格式错误: {str(e)}")
                return
                
            # 获取所有参数名称
            parameters = []
            def extract_params(data, prefix=""):
                if isinstance(data, dict):
                    for key, value in data.items():
                        full_key = f"{prefix}.{key}" if prefix else key
                        if isinstance(value, (dict, list)):
                            extract_params(value, full_key)
                        else:
                            parameters.append(full_key)
                elif isinstance(data, list) and data:
                    extract_params(data[0], f"{prefix}[0]")
                    
            extract_params(body_data)
            
            if not parameters:
                QMessageBox.warning(self, "警告", "请求体中没有找到可配置的参数")
                return
                
            # 显示配置对话框
            dialog = DynamicDataDialog(body_text, self)
            
            # 加载项目列表
            projects = []
            projects_dir = "position_projects"
            if os.path.exists(projects_dir):
                for project in os.listdir(projects_dir):
                    if os.path.isdir(os.path.join(projects_dir, project)):
                        projects.append(project)
            dialog.project_combo.addItems([""] + projects)
            
            # 如果用户确认配置
            if dialog.exec() == QDialog.DialogCode.Accepted:
                config = dialog.get_config()
                if config:
                    # 生成配置ID
                    if not config.id:
                        existing_ids = [int(cid.split("_")[1]) for cid in self.dynamic_data_configs.keys() if cid.startswith("config_")]
                        next_id = max(existing_ids) + 1 if existing_ids else 1
                        config.id = f"config_{next_id}"
                    
                    # 设置时间戳
                    now = datetime.now()
                    if not config.created_time:
                        config.created_time = now.strftime("%Y-%m-%d %H:%M:%S")
                    config.last_updated = now.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 保存配置
                    self.dynamic_data_configs[config.id] = config
                    QMessageBox.information(self, "成功", "动态数据配置已保存")
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"配置动态数据失败: {str(e)}")
            
    def generate_dynamic_data(self, config):
        """根据配置生成动态数据"""
        try:
            data = {}
            for param, source_config in config.data_sources.items():
                source_config = DataSourceConfig.from_dict(source_config)
                if source_config.type == DataSourceConfig.TYPE_RANDOM:
                    # 生成随机数据
                    chars = ""
                    if source_config.format == "数字":
                        chars = string.digits
                    elif source_config.format == "字母":
                        chars = string.ascii_letters
                    else:  # 字母数字
                        chars = string.ascii_letters + string.digits
                    
                    data[param] = ''.join(random.choice(chars) for _ in range(source_config.length))
                    
                else:  # 文件数据
                    # 从文件获取数据
                    file_path = os.path.join("position_projects", source_config.project, "versions", source_config.file)
                    if not os.path.exists(file_path):
                        raise FileNotFoundError(f"找不到文件: {file_path}")
                        
                    # 读取Excel文件
                    df = pd.read_excel(file_path)
                    
                    # 如果有货架查询条件
                    if source_config.shelf_query:
                        # 查找货架列
                        shelf_col = None
                        for col in df.columns:
                            if "货架" in str(col) and df[col].dtype == object:
                                shelf_col = col
                                break
                                
                        if not shelf_col:
                            raise ValueError("找不到货架列")
                            
                        # 过滤数据
                        df = df[df[shelf_col] == source_config.shelf_query]
                        
                    if df.empty:
                        raise ValueError("没有找到匹配的数据")
                        
                    # 查找仓位列
                    position_col = None
                    for col in df.columns:
                        if "仓位" in str(col):
                            position_col = col
                            break
                            
                    if not position_col:
                        raise ValueError("找不到仓位列")
                        
                    # 随机选择一个仓位
                    positions = []
                    for pos in df[position_col]:
                        if pd.notna(pos):  # 检查是否为空值
                            positions.append(str(pos))
                    if positions:
                        data[param] = random.choice(positions)
                    else:
                        raise ValueError("没有有效的仓位数据")
                    
            return data
            
        except Exception as e:
            raise Exception(f"生成动态数据失败: {str(e)}")
            
    def apply_dynamic_data(self, body_data, dynamic_data):
        """将动态数据应用到请求体中"""
        def get_array_indices(path):
            """从路径中提取数组索引模式"""
            parts = path.split(".")
            indices = []
            for part in parts:
                if "[" in part and "]" in part:
                    # 提取所有数组索引
                    start = part.find("[")
                    end = part.find("]")
                    index = part[start+1:end]
                    if index == "*":  # 如果是通配符
                        indices.append("*")
                    else:
                        try:
                            indices.append(int(index))
                        except ValueError:
                            indices.append(None)
                else:
                    indices.append(None)
            return indices
            
        def set_value(data, path, value):
            parts = path.split(".")
            indices = get_array_indices(path)
            
            # 清理路径部分，移除数组索引
            clean_parts = []
            for part in parts:
                if "[" in part:
                    clean_parts.append(part.split("[")[0])
                else:
                    clean_parts.append(part)
            
            current = data
            for i, (part, index) in enumerate(zip(clean_parts[:-1], indices[:-1])):
                if not part:  # 跳过空部分
                    continue
                    
                if index == "*":  # 如果是通配符，应用到所有元素
                    if not isinstance(current, list):
                        raise ValueError(f"路径 {path} 中的 '*' 不是指向数组")
                    for item in current:
                        if isinstance(item, dict):
                            if part not in item:
                                item[part] = [] if indices[i+1] is not None else {}
                    current = [item[part] for item in current if isinstance(item, dict)]
                else:
                    if index is not None:  # 如果是数组索引
                        if part:  # 如果是字典中的数组
                            if part not in current:
                                current[part] = []
                            while len(current[part]) <= index:
                                current[part].append({})
                            current = current[part][index]
                        else:  # 如果直接是数组
                            while len(current) <= index:
                                current.append({})
                            current = current[index]
                    else:  # 如果是普通字典键
                        if part not in current:
                            current[part] = [] if indices[i+1] is not None else {}
                        current = current[part]
            
            # 处理最后一部分
            last_part = clean_parts[-1]
            last_index = indices[-1]
            
            if last_index == "*":  # 如果最后一部分是通配符
                if isinstance(current, list):
                    for item in current:
                        if isinstance(item, dict):
                            item[last_part] = value
                else:
                    raise ValueError(f"路径 {path} 中的 '*' 不是指向数组")
            elif last_index is not None:  # 如果最后一部分是数组索引
                if last_part:  # 如果是字典中的数组
                    if last_part not in current:
                        current[last_part] = []
                    while len(current[last_part]) <= last_index:
                        current[last_part].append(None)
                    current[last_part][last_index] = value
                else:  # 如果直接是数组
                    while len(current) <= last_index:
                        current.append(None)
                    current[last_index] = value
            else:  # 如果最后一部分是普通字典键
                current[last_part] = value
                
        result = copy.deepcopy(body_data)
        for path, value in dynamic_data.items():
            set_value(result, path, value)
            
        return result



class JsonEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建文本编辑器
        self.text_edit = QPlainTextEdit()
        self.text_edit.setFont(QFont("Menlo" if sys.platform == "darwin" else "Consolas", 12))
        layout.addWidget(self.text_edit)
        
        # 创建工具栏
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        
        # 格式化按钮
        format_btn = QPushButton("格式化")
        format_btn.clicked.connect(self.format_json)
        toolbar.addWidget(format_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 语法高亮器
        self.highlighter = JsonHighlighter(self.text_edit.document())
    
    def format_json(self):
        """格式化JSON文本"""
        try:
            text = self.text_edit.toPlainText().strip()
            if not text:
                return
            
            data = json.loads(text)
            formatted = json.dumps(data, indent=4, ensure_ascii=False)
            self.text_edit.setPlainText(formatted)
            
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "警告", f"JSON格式错误: {str(e)}")
    
    def text(self):
        """获取文本内容"""
        return self.text_edit.toPlainText()
    
    def setText(self, text):
        """设置文本内容"""
        self.text_edit.setPlainText(text)
    
    def clear(self):
        """清空文本内容"""
        self.text_edit.clear()

class DynamicDataConfig:
    def __init__(self):
        self.id: str = ""                  # 配置ID
        self.name: str = ""                # 配置名称
        self.parameters: list = []         # 选中的参数列表
        self.data_sources: dict = {}       # 参数数据源配置 {param_name: source_config}
        self.created_time: str = ""        # 创建时间
        self.last_updated: str = ""        # 最后更新时间
        
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "parameters": self.parameters,
            "data_sources": self.data_sources,
            "created_time": self.created_time,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建实例"""
        config = cls()
        config.id = data.get("id")
        config.name = data.get("name", "")
        config.parameters = data.get("parameters", [])
        config.data_sources = data.get("data_sources", {})
        config.created_time = data.get("created_time")
        config.last_updated = data.get("last_updated")
        return config

class DataSourceConfig:
    TYPE_RANDOM = "random"
    TYPE_FILE = "file"
    
    def __init__(self):
        self.type: str = ""               # 数据源类型：random或file
        self.format: str = ""             # 随机数据格式
        self.length: int = 0              # 随机数据长度
        self.project: str = ""            # 项目名称
        self.file: str = ""               # 文件名称
        self.shelf_query: str = ""        # 货架查询条件
        
    def to_dict(self):
        """转换为字典"""
        return {
            "type": self.type,
            "format": self.format,
            "length": self.length,
            "project": self.project,
            "file": self.file,
            "shelf_query": self.shelf_query
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建实例"""
        config = cls()
        config.type = data.get("type")
        config.format = data.get("format")
        config.length = data.get("length")
        config.project = data.get("project")
        config.file = data.get("file")
        config.shelf_query = data.get("shelf_query")
        return config

class DynamicDataDialog(QDialog):
    def __init__(self, parameters, parent=None):
        super().__init__(parent)
        self.parameters = parameters  # 可选的参数列表
        self.dynamic_config = DynamicDataConfig()
        self.data_sources = {}  # 临时存储数据源配置
        
        self.setWindowTitle("动态数据配置")
        self.resize(800, 600)
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 配置名称
        name_layout = QHBoxLayout()
        name_label = QLabel("配置名称：")
        self.name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # 参数选择
        param_group = QGroupBox("选择参数（双击选择）")
        param_layout = QVBoxLayout(param_group)
        
        # 创建树形视图
        self.param_tree = QTreeWidget()
        self.param_tree.setHeaderLabels(["参数名称", "值"])
        self.param_tree.setAlternatingRowColors(True)
        self.param_tree.setStyleSheet("""
            QTreeWidget {
                font-family: Menlo, Consolas, monospace;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 4px;
            }
        """)
        
        # 添加参数到树形视图
        def add_json_to_tree(data, parent=None, path=""):
            if isinstance(data, dict):
                for key, value in data.items():
                    current_path = f"{path}.{key}" if path else key
                    if parent is None:
                        item = QTreeWidgetItem(self.param_tree)
                    else:
                        item = QTreeWidgetItem(parent)
                    item.setText(0, key)
                    if isinstance(value, (dict, list)):
                        item.setForeground(0, QColor("#2196F3"))  # 蓝色显示非叶子节点
                        add_json_to_tree(value, item, current_path)
                    else:
                        item.setText(1, str(value))
                        item.setData(0, Qt.ItemDataRole.UserRole, current_path)
            elif isinstance(data, list) and data:
                # 显示数组的所有元素
                array_root = QTreeWidgetItem(parent or self.param_tree)
                array_root.setText(0, "[]")
                array_root.setForeground(0, QColor("#2196F3"))
                
                # 添加数组长度信息
                array_info = QTreeWidgetItem(array_root)
                array_info.setText(0, f"长度: {len(data)}")
                array_info.setForeground(0, QColor("#666666"))
                
                # 添加所有元素
                for i, item in enumerate(data):
                    if isinstance(item, (dict, list)):
                        array_item = QTreeWidgetItem(array_root)
                        array_item.setText(0, f"[{i}]")
                        array_item.setForeground(0, QColor("#2196F3"))
                        current_path = f"{path}[{i}]" if path else f"[{i}]"
                        add_json_to_tree(item, array_item, current_path)
                    else:
                        array_item = QTreeWidgetItem(array_root)
                        array_item.setText(0, f"[{i}]")
                        array_item.setText(1, str(item))
                        current_path = f"{path}[{i}]" if path else f"[{i}]"
                        array_item.setData(0, Qt.ItemDataRole.UserRole, current_path)
        
        # 解析JSON并添加到树形视图
        try:
            add_json_to_tree(json.loads(parameters))
        except:
            # 如果不是有效的JSON字符串，则使用原来的参数列表
            for param in parameters:
                item = QTreeWidgetItem(self.param_tree)
                item.setText(0, param)
                item.setData(0, Qt.ItemDataRole.UserRole, param)
        
        # 展开所有节点
        self.param_tree.expandAll()
        
        # 调整列宽
        self.param_tree.setColumnWidth(0, 300)
        
        # 创建已选参数列表
        self.selected_params = QListWidget()
        self.selected_params.setStyleSheet("""
            QListWidget {
                font-family: Menlo, Consolas, monospace;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 4px;
            }
        """)
        
        # 处理双击事件
        def on_tree_double_clicked(item, column):
            if item.childCount() == 0:  # 只处理叶子节点
                param_path = item.data(0, Qt.ItemDataRole.UserRole)
                if param_path:
                    # 检查是否已经选择
                    existing_items = self.selected_params.findItems(param_path, Qt.MatchFlag.MatchExactly)
                    if not existing_items:
                        # 如果是数组元素，提供选择
                        if "[" in param_path and "]" in param_path:
                            choice = QMessageBox.question(
                                self,
                                "数组元素选择",
                                "是否应用到数组的所有元素？",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No
                            )
                            
                            if choice == QMessageBox.StandardButton.Yes:
                                # 替换具体的索引为通配符
                                parts = param_path.split(".")
                                modified_parts = []
                                for part in parts:
                                    if "[" in part and "]" in part:
                                        start = part.find("[")
                                        end = part.find("]")
                                        modified_part = part[:start] + "[*]" + part[end+1:]
                                        modified_parts.append(modified_part)
                                    else:
                                        modified_parts.append(part)
                                param_path = ".".join(modified_parts)
                                
                        self.selected_params.addItem(param_path)
                        item.setForeground(0, QColor("#4CAF50"))  # 绿色显示已选择的参数
                    
        self.param_tree.itemDoubleClicked.connect(on_tree_double_clicked)
        
        # 添加删除按钮
        def on_remove_selected():
            for item in self.selected_params.selectedItems():
                # 找到对应的树节点并恢复颜色
                param_path = item.text()
                def restore_color(item):
                    for i in range(item.childCount()):
                        child = item.child(i)
                        if child.data(0, Qt.ItemDataRole.UserRole) == param_path:
                            child.setForeground(0, QColor("black"))
                            return True
                        if restore_color(child):
                            return True
                    return False
                
                # 遍历树恢复颜色
                restore_color(self.param_tree.invisibleRootItem())
                
                # 从已选列表中删除
                self.selected_params.takeItem(self.selected_params.row(item))
        
        remove_button = QPushButton("删除选中参数")
        remove_button.clicked.connect(on_remove_selected)
        
        # 布局
        param_layout.addWidget(self.param_tree)
        param_layout.addWidget(QLabel("已选参数："))
        param_layout.addWidget(self.selected_params)
        param_layout.addWidget(remove_button)
        layout.addWidget(param_group)
        
        # 数据源配置
        source_group = QGroupBox("数据源配置")
        source_layout = QVBoxLayout(source_group)
        
        # 数据源类型选择
        type_layout = QHBoxLayout()
        type_label = QLabel("数据源类型：")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["随机生成", "文件数据"])
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        source_layout.addLayout(type_layout)
        
        # 随机生成配置
        self.random_widget = QWidget()
        random_layout = QGridLayout(self.random_widget)
        
        format_label = QLabel("数据格式：")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["数字", "字母", "字母数字"])
        random_layout.addWidget(format_label, 0, 0)
        random_layout.addWidget(self.format_combo, 0, 1)
        
        length_label = QLabel("数据长度：")
        self.length_spin = QSpinBox()
        self.length_spin.setRange(1, 100)
        random_layout.addWidget(length_label, 1, 0)
        random_layout.addWidget(self.length_spin, 1, 1)
        
        source_layout.addWidget(self.random_widget)
        
        # 文件数据配置
        self.file_widget = QWidget()
        file_layout = QGridLayout(self.file_widget)
        
        project_label = QLabel("选择项目：")
        self.project_combo = QComboBox()
        file_layout.addWidget(project_label, 0, 0)
        file_layout.addWidget(self.project_combo, 0, 1)
        
        file_label = QLabel("选择文件：")
        self.file_combo = QComboBox()
        file_layout.addWidget(file_label, 1, 0)
        file_layout.addWidget(self.file_combo, 1, 1)
        
        query_label = QLabel("货架查询：")
        self.query_input = QLineEdit()
        file_layout.addWidget(query_label, 2, 0)
        file_layout.addWidget(self.query_input, 2, 1)
        
        source_layout.addWidget(self.file_widget)
        layout.addWidget(source_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        save_button = QPushButton("保存")
        cancel_button = QPushButton("取消")
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # 信号连接
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        
        # 初始化界面
        self.on_type_changed(0)
        
    def on_type_changed(self, index):
        """处理数据源类型变化"""
        if index == 0:  # 随机生成
            self.random_widget.setVisible(True)
            self.file_widget.setVisible(False)
        else:  # 文件数据
            self.random_widget.setVisible(False)
            self.file_widget.setVisible(True)
            
    def on_project_changed(self, index):
        """处理项目选择变化"""
        try:
            self.file_combo.clear()
            if index <= 0:
                return
                
            project_name = self.project_combo.currentText()
            project_dir = os.path.join("position_projects", project_name, "versions")
            
            if not os.path.exists(project_dir):
                return
                
            # 获取所有Excel文件
            files = []
            for filename in os.listdir(project_dir):
                if filename.endswith('.xlsx'):
                    files.append(filename)
            
            # 按名称排序
            files.sort(reverse=True)
            
            # 添加到下拉框
            self.file_combo.addItems(files)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载项目文件失败: {str(e)}")
            
    def get_config(self):
        """获取配置数据"""
        try:
            # 获取基本信息
            self.dynamic_config.name = self.name_input.text().strip()
            self.dynamic_config.parameters = [item.text() for item in self.selected_params.findItems("*", Qt.MatchFlag.MatchWildcard)]
            
            # 获取数据源配置
            for param in self.dynamic_config.parameters:
                source_config = DataSourceConfig()
                if self.type_combo.currentIndex() == 0:  # 随机生成
                    source_config.type = DataSourceConfig.TYPE_RANDOM
                    source_config.format = self.format_combo.currentText()
                    source_config.length = self.length_spin.value()
                else:  # 文件数据
                    source_config.type = DataSourceConfig.TYPE_FILE
                    source_config.project = self.project_combo.currentText()
                    source_config.file = self.file_combo.currentText()
                    source_config.shelf_query = self.query_input.text().strip()
                
                self.dynamic_config.data_sources[param] = source_config.to_dict()
            
            return self.dynamic_config
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取配置失败: {str(e)}")
            return None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 