import sys
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QTabWidget, QPushButton, QTextEdit, QSpinBox, 
                           QLabel, QFileDialog, QMessageBox, QGridLayout,
                           QTableWidget, QTableWidgetItem, QHeaderView,
                           QComboBox, QHBoxLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCharFormat, QSyntaxHighlighter
import requests
import pandas as pd
from datetime import datetime
import traceback

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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("接口调用工具")
        self.setMinimumSize(1000, 800)  # 增加窗口大小
        
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
        layout = QVBoxLayout(tab)
        
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