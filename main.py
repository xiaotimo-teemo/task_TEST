import sys
import json
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QTabWidget, QPushButton, QTextEdit, QSpinBox, 
                           QLabel, QFileDialog, QMessageBox, QGridLayout,
                           QTableWidget, QTableWidgetItem, QHeaderView,
                           QComboBox, QHBoxLayout, QListWidget, QDialog,
                           QDialogButtonBox, QLineEdit, QTreeWidget,
                           QTreeWidgetItem, QSplitter)
from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QColor, QTextCharFormat, QSyntaxHighlighter
import requests
import pandas as pd
from datetime import datetime
import traceback
import shutil

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
        self.setWindowTitle("接口调用工具")
        self.setMinimumSize(1200, 800)  # 增加窗口大小以适应新的布局
        
        # 创建配置保存目录
        self.config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_configs')
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 创建主窗口部件和布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 创建选项卡
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # 添加接口调用选项卡
        api_tab = QWidget()
        tabs.addTab(api_tab, "接口调用")
        self.setup_api_tab(api_tab)
        
        # 添加仓位信息选项卡
        position_tab = QWidget()
        tabs.addTab(position_tab, "仓位信息")
        self.setup_position_tab(position_tab)
        
        # 添加货架解析选项卡
        shelf_tab = QWidget()
        tabs.addTab(shelf_tab, "货架解析")
        self.setup_shelf_tab(shelf_tab)

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
        right_panel = QWidget()
        layout = QVBoxLayout(right_panel)
        
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
        
        main_layout.addWidget(right_panel)
        
        # 加载保存的配置列表
        self.load_saved_configs()

    def save_api_config(self):
        # 获取当前配置
        config = {
            "method": self.method_combo.currentText(),
            "url": self.url_input.toPlainText(),
            "headers": self.headers_input.toPlainText(),
            "body": self.body_input.toPlainText(),
            "count": self.count_input.value()
        }
        
        # 弹出保存对话框
        dialog = SaveApiDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_name()
            comment = dialog.get_comment()
            
            if not name:
                QMessageBox.warning(self, "警告", "请输入配置名称")
                return
            
            try:
                # 创建配置目录和版本目录
                config_path = os.path.join(self.config_dir, name)
                versions_path = os.path.join(config_path, 'versions')
                os.makedirs(versions_path, exist_ok=True)
                
                # 添加版本信息
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                version_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                config['_version_info'] = {
                    'timestamp': timestamp,
                    'comment': comment
                }
                
                # 保存当前版本
                version_file = os.path.join(versions_path, f'{version_id}.json')
                with open(version_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
                
                # 更新当前配置文件（复制最新版本）
                current_file = os.path.join(config_path, 'current.json')
                shutil.copy2(version_file, current_file)
                
                self.load_saved_configs()  # 刷新配置列表
                QMessageBox.information(self, "成功", "配置保存成功！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")

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
        try:
            config_path = os.path.join(self.config_dir, item.text())
            current_file = os.path.join(config_path, 'current.json')
            
            with open(current_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 移除版本信息
            if '_version_info' in config:
                del config['_version_info']
            
            # 更新界面
            index = self.method_combo.findText(config["method"])
            if index >= 0:
                self.method_combo.setCurrentIndex(index)
            self.url_input.setText(config["url"])
            self.headers_input.setText(config["headers"])
            self.body_input.setText(config["body"])
            self.count_input.setValue(config["count"])
            
            QMessageBox.information(self, "成功", "配置加载成功！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载配置失败: {str(e)}")

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
        current_item = self.saved_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请选择要查看历史的配置")
            return
        
        try:
            config_name = current_item.text()
            versions_path = os.path.join(self.config_dir, config_name, 'versions')
            
            dialog = VersionHistoryDialog(config_name, versions_path, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # 用户选择恢复某个版本
                selected_version = dialog.get_selected_version()
                if selected_version:
                    version_file = os.path.join(versions_path, selected_version)
                    current_file = os.path.join(self.config_dir, config_name, 'current.json')
                    shutil.copy2(version_file, current_file)
                    
                    # 重新加载配置
                    self.load_api_config(current_item)
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查看版本历史失败: {str(e)}")

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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 