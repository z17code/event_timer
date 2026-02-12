import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import sys
from datetime import datetime, timedelta
import threading
import time
from PIL import Image, ImageDraw
import pystray
import platform
import ctypes
import re
import winsound


class SimpleTimerWindow:
    """简易计时窗口"""

    def __init__(self, main_app):
        self.main_app = main_app
        self.window = None

    def create_window(self):
        """创建简易窗口"""
        if self.window is not None:
            self.window.destroy()

        self.window = tk.Toplevel()
        self.window.title("事件计时器 - 简易模式")
        self.window.geometry("300x200")
        self.window.configure(bg=self.main_app.bg_color)
        self.window.attributes("-topmost", True)
        self.window.protocol('WM_DELETE_WINDOW', self.on_close)

        # 移除窗口的关闭按钮
        if platform.system() == "Windows":
            self.window.attributes("-toolwindow", 1)

        # 标题
        title_label = tk.Label(
            self.window,
            text="正在计时的事件",
            bg=self.main_app.bg_color,
            fg=self.main_app.accent_color,
            font=("Arial", 12, "bold")
        )
        title_label.pack(pady=(10, 5))

        # 事件列表
        self.events_frame = tk.Frame(self.window, bg=self.main_app.bg_color)
        self.events_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 更新事件列表
        self.update_events_list()

        # 控制按钮
        button_frame = tk.Frame(self.window, bg=self.main_app.bg_color)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # 显示主窗口按钮
        show_main_button = tk.Button(
            button_frame,
            text="显示主窗口",
            command=self.show_main_window,
            bg=self.main_app.accent_color,
            fg="white",
            width=12,
            activebackground=self.main_app.accent_color,
            activeforeground="white",
            relief="flat"
        )
        show_main_button.pack(side=tk.LEFT, padx=(0, 10))

        # 停止所有按钮
        stop_all_button = tk.Button(
            button_frame,
            text="停止所有",
            command=self.stop_all_events,
            bg=self.main_app.stop_color,
            fg="white",
            width=12,
            activebackground=self.main_app.stop_color,
            activeforeground="white",
            relief="flat"
        )
        stop_all_button.pack(side=tk.LEFT)

        # 启动定时更新
        self.update_timer()

        return self.window

    def update_events_list(self):
        """更新事件列表显示"""
        # 清空现有内容
        for widget in self.events_frame.winfo_children():
            widget.destroy()

        if not self.main_app.current_events:
            tk.Label(
                self.events_frame,
                text="当前没有正在计时的事件",
                bg=self.main_app.bg_color,
                fg=self.main_app.fg_color
            ).pack(pady=20)
            return

        # 创建滚动区域
        canvas = tk.Canvas(self.events_frame, bg=self.main_app.bg_color, height=120)
        scrollbar = tk.Scrollbar(self.events_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.main_app.bg_color)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 显示每个事件
        for event_name, event_data in self.main_app.current_events.items():
            event_frame = tk.Frame(scrollable_frame, bg=self.main_app.bg_color)
            event_frame.pack(fill=tk.X, pady=2)

            # 事件名称
            tk.Label(
                event_frame,
                text=f"{event_name}:",
                bg=self.main_app.bg_color,
                fg=self.main_app.accent_color,
                width=20,
                anchor="w"
            ).pack(side=tk.LEFT)

            # 计时时间
            start_time = event_data["start_time"]
            current_time = datetime.now()
            duration = current_time - start_time
            duration_str = self.main_app.format_duration(duration.total_seconds())

            time_label = tk.Label(
                event_frame,
                text=duration_str,
                bg=self.main_app.bg_color,
                fg=self.main_app.fg_color,
                width=8
            )
            time_label.pack(side=tk.LEFT, padx=(0, 5))

            # 停止按钮
            stop_button = tk.Button(
                event_frame,
                text="停止",
                command=lambda e=event_name: self.stop_single_event(e),
                bg=self.main_app.stop_color,
                fg="white",
                width=5,
                activebackground=self.main_app.stop_color,
                activeforeground="white",
                relief="flat"
            )
            stop_button.pack(side=tk.RIGHT)

            # 保存时间标签用于更新
            event_data["simple_window_time_label"] = time_label

    def update_timer(self):
        """更新计时器显示"""
        if self.window and self.window.winfo_exists():
            # 更新每个事件的时间
            for event_name, event_data in self.main_app.current_events.items():
                if "simple_window_time_label" in event_data:
                    start_time = event_data["start_time"]
                    current_time = datetime.now()
                    duration = current_time - start_time
                    duration_str = self.main_app.format_duration(duration.total_seconds())
                    event_data["simple_window_time_label"].config(text=duration_str)

            # 如果没有事件了，关闭简易窗口
            if not self.main_app.current_events:
                self.window.destroy()
                self.window = None
                return

            # 继续更新
            self.window.after(1000, self.update_timer)

    def stop_single_event(self, event_name):
        """停止单个事件"""
        self.main_app.stop_single_timing(event_name)
        self.update_events_list()

    def stop_all_events(self):
        """停止所有事件"""
        for event_name in list(self.main_app.current_events.keys()):
            self.main_app.stop_single_timing(event_name)
        self.update_events_list()

    def show_main_window(self):
        """显示主窗口"""
        if self.window:
            self.window.destroy()
            self.window = None
        self.main_app.show_from_tray()

    def on_close(self):
        """窗口关闭事件"""
        # 不做任何事，防止用户关闭窗口
        pass


class EventTimerApp:
    def __init__(self, root):
        self.root = root

        # 检测系统主题
        self.is_dark_mode = self.detect_system_theme()

        # 获取程序所在目录
        if getattr(sys, 'frozen', False):
            # 如果是打包成exe的情况
            program_dir = os.path.dirname(sys.executable)
        else:
            # 如果是脚本运行
            program_dir = os.path.dirname(os.path.abspath(__file__))

        # 创建config文件夹
        config_dir = os.path.join(program_dir, "config")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        # 设置颜色主题
        self.setup_theme()

        # 初始化变量
        self.current_events = {}  # 支持多个事件同时计时
        self.events_history = []
        self.event_names_data = {}  # 事件名称及其使用频率
        self.event_templates = []  # 事件模板
        self.tags_data = {}  # 标签数据
        self.config_dir = config_dir  # 保存配置文件夹路径
        self.data_file = os.path.join(config_dir, "events_history.json")
        self.names_file = os.path.join(config_dir, "event_names.json")
        self.templates_file = os.path.join(config_dir, "event_templates.json")
        self.tags_file = os.path.join(config_dir, "event_tags.json")
        self.settings_file = os.path.join(config_dir, "settings.json")
        self.tray_icon = None
        self.is_hidden_to_tray = False
        self.dropdown_visible = False
        self.last_dropdown_hover_index = -1
        self.notification_thread = None
        self.notification_active = False
        self.notification_interval = 30  # 默认30分钟
        self.auto_stop_on_notification = False  # 通知时是否自动停止所有事件

        # 模板执行相关变量
        self.current_template = None  # 当前执行的模板
        self.template_event_index = 0  # 当前执行到模板的第几个事件
        self.template_events_queue = []  # 模板事件队列

        # 简易窗口
        self.simple_window = SimpleTimerWindow(self)

        # 加载数据
        self.load_history()
        self.load_event_names()
        self.load_templates()
        self.load_tags()
        self.load_settings()

        # 创建UI
        self.create_widgets()

        # 更新当前时间显示
        self.update_time_display()

        # 设置窗口关闭行为
        self.root.protocol('WM_DELETE_WINDOW', self.hide_to_tray)

        # 创建系统托盘图标
        self.create_system_tray()

        # 确保窗口初始化时显示在任务栏
        self.root.after(100, self.ensure_window_visibility)

        # 绑定事件
        self.bind_events()

        # 启动通知检查
        self.start_notification_checker()

    def ensure_window_visibility(self):
        """确保窗口在任务栏可见"""
        if platform.system() == "Windows":
            hwnd = self.root.winfo_id()
            ctypes.windll.user32.ShowWindow(hwnd, 1)  # SW_SHOWNORMAL

    def detect_system_theme(self):
        """检测系统主题（深色/浅色）"""
        try:
            if platform.system() == "Windows":
                import winreg
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return value == 0
            elif platform.system() == "Darwin":
                import subprocess
                cmd = 'defaults read -g AppleInterfaceStyle 2>/dev/null'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return "Dark" in result.stdout
        except:
            pass

        return False

    def setup_theme(self):
        """设置颜色主题"""
        if self.is_dark_mode:
            # 深色主题
            self.bg_color = "#2b2b2b"
            self.fg_color = "#ffffff"
            self.entry_bg = "#3c3c3c"
            self.entry_fg = "#ffffff"
            self.button_bg = "#4a4a4a"
            self.button_fg = "#ffffff"
            self.button_active = "#5a5a5a"
            self.tree_bg = "#3c3c3c"
            self.tree_fg = "#ffffff"
            self.tree_sel_bg = "#007acc"
            self.accent_color = "#007acc"
            self.start_color = "#2e7d32"
            self.stop_color = "#c62828"
            self.clear_color = "#ef6c00"
            self.template_color = "#9C27B0"
            self.tag_color = "#2196F3"
            self.dropdown_bg = "#3c3c3c"
            self.dropdown_fg = "#ffffff"
            self.dropdown_sel_bg = "#007acc"
            self.dropdown_hover_bg = "#505050"
            self.dropdown_border = "#555555"
        else:
            # 浅色主题
            self.bg_color = "#f5f5f5"
            self.fg_color = "#000000"
            self.entry_bg = "#ffffff"
            self.entry_fg = "#000000"
            self.button_bg = "#e0e0e0"
            self.button_fg = "#000000"
            self.button_active = "#d0d0d0"
            self.tree_bg = "#ffffff"
            self.tree_fg = "#000000"
            self.tree_sel_bg = "#0078d7"
            self.accent_color = "#2196F3"
            self.start_color = "#4CAF50"
            self.stop_color = "#f44336"
            self.clear_color = "#FF9800"
            self.template_color = "#9C27B0"
            self.tag_color = "#2196F3"
            self.dropdown_bg = "#ffffff"
            self.dropdown_fg = "#000000"
            self.dropdown_sel_bg = "#0078d7"
            self.dropdown_hover_bg = "#e0e0e0"
            self.dropdown_border = "#cccccc"

        # 应用主题到主窗口
        self.root.configure(bg=self.bg_color)
        self.root.title("事件计时器")
        self.root.geometry("900x650")

        # 尝试设置窗口图标
        try:
            icon_paths = [
                "timer_icon.ico",
                "icon.ico",
                "resources/timer_icon.ico",
                "resources/icon.ico"
            ]

            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    self.root.iconbitmap(icon_path)
                    break
        except:
            self.create_default_icon()

    def create_default_icon(self):
        """创建默认图标（如果没有图标文件）"""
        try:
            image = Image.new('RGB', (32, 32), color=self.accent_color)
            draw = ImageDraw.Draw(image)
            draw.ellipse([4, 4, 28, 28], outline='white', width=2)
            draw.line([16, 16, 16, 10], fill='white', width=2)
            draw.line([16, 16, 22, 16], fill='white', width=2)

            temp_icon = "temp_icon.ico"
            image.save(temp_icon)
            self.root.iconbitmap(temp_icon)
        except Exception as e:
            print(f"创建默认图标失败: {e}")

    def create_widgets(self):
        # 主容器
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 顶部控制区域
        top_frame = tk.Frame(main_frame, bg=self.bg_color)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # 左上方：事件名称输入和开始按钮
        left_frame = tk.Frame(top_frame, bg=self.bg_color)
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(left_frame, text="事件名称:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=(0, 10))

        # 创建输入框容器，用于定位下拉列表
        self.entry_container = tk.Frame(left_frame, bg=self.bg_color)
        self.entry_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # 创建输入框
        self.event_entry = tk.Entry(self.entry_container, width=30, bg=self.entry_bg, fg=self.entry_fg,
                                    insertbackground=self.fg_color, relief="flat")
        self.event_entry.pack(fill=tk.X, expand=True)

        # 标签输入框（修改：默认空）
        tag_frame = tk.Frame(left_frame, bg=self.bg_color)
        tag_frame.pack(side=tk.LEFT, fill=tk.X, expand=False, padx=(0, 10))

        tk.Label(tag_frame, text="标签:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=(0, 5))
        self.tag_entry = tk.Entry(tag_frame, width=15, bg=self.entry_bg, fg=self.entry_fg,
                                  insertbackground=self.fg_color, relief="flat")
        self.tag_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        # 移除了默认的"#工作"标签

        # 开始按钮
        self.start_button = tk.Button(
            left_frame,
            text="开始计时",
            command=self.start_timing,
            bg=self.start_color,
            fg="white",
            width=8,
            activebackground=self.start_color,
            activeforeground="white",
            relief="flat",
            cursor="hand2"
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))

        # 右上方：模板管理按钮
        right_frame = tk.Frame(top_frame, bg=self.bg_color)
        right_frame.pack(side=tk.RIGHT)

        # 模板按钮
        template_button = tk.Button(
            right_frame,
            text="模板管理",
            command=self.show_template_manager,
            bg=self.template_color,
            fg="white",
            width=10,
            activebackground=self.template_color,
            activeforeground="white",
            relief="flat",
            cursor="hand2"
        )
        template_button.pack(side=tk.LEFT, padx=(0, 5))

        # 标签管理按钮
        tag_manager_button = tk.Button(
            right_frame,
            text="标签管理",
            command=self.show_tag_manager,
            bg=self.tag_color,
            fg="white",
            width=10,
            activebackground=self.tag_color,
            activeforeground="white",
            relief="flat",
            cursor="hand2"
        )
        tag_manager_button.pack(side=tk.LEFT, padx=(0, 5))

        # 模板快速选择下拉框
        template_var = tk.StringVar()
        template_var.set("选择模板")
        self.template_combo = ttk.Combobox(
            right_frame,
            textvariable=template_var,
            values=[t["name"] for t in self.event_templates],
            width=12,
            state="readonly"
        )
        self.template_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.template_combo.bind("<<ComboboxSelected>>", self.on_template_selected)

        # 置顶复选框放在右上角
        self.topmost_var = tk.BooleanVar(value=False)
        self.topmost_check = tk.Checkbutton(
            right_frame,
            text="窗口置顶",
            variable=self.topmost_var,
            command=self.toggle_topmost,
            bg=self.bg_color,
            fg=self.fg_color,
            selectcolor=self.bg_color,
            activebackground=self.bg_color,
            activeforeground=self.fg_color
        )
        self.topmost_check.pack(side=tk.LEFT, padx=(0, 5))

        # 创建下拉列表框架（开始时隐藏）
        self.dropdown_frame = tk.Frame(self.root, bg=self.dropdown_border, relief="solid", borderwidth=1)
        self.dropdown_frame.place_forget()

        # 创建简单的Listbox作为下拉列表
        self.dropdown_listbox = tk.Listbox(
            self.dropdown_frame,
            bg=self.dropdown_bg,
            fg=self.dropdown_fg,
            selectbackground=self.dropdown_sel_bg,
            selectforeground="white",
            height=8,
            relief="flat",
            activestyle="none",
            exportselection=False,
            highlightthickness=0,
            borderwidth=0
        )

        # 添加滚动条
        dropdown_scrollbar = tk.Scrollbar(self.dropdown_frame, orient="vertical",
                                          bg=self.dropdown_bg, troughcolor=self.dropdown_bg)
        self.dropdown_listbox.config(yscrollcommand=dropdown_scrollbar.set)
        dropdown_scrollbar.config(command=self.dropdown_listbox.yview)

        self.dropdown_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dropdown_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 当前正在计时的事件区域
        current_timers_frame = tk.LabelFrame(main_frame, text="当前正在计时的事件", bg=self.bg_color, fg=self.fg_color)
        current_timers_frame.pack(fill=tk.X, pady=(0, 10))

        # 创建滚动区域用于显示多个计时器
        canvas = tk.Canvas(current_timers_frame, bg=self.bg_color, height=120)
        scrollbar = tk.Scrollbar(current_timers_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=self.bg_color)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 用于存储当前计时器标签和按钮的引用
        self.timer_widgets = {}

        # 历史记录区域（添加标签筛选）
        history_frame = tk.LabelFrame(main_frame, text="历史记录", bg=self.bg_color, fg=self.fg_color)
        history_frame.pack(fill=tk.BOTH, expand=True)

        # 历史记录筛选工具栏
        filter_frame = tk.Frame(history_frame, bg=self.bg_color)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(filter_frame, text="筛选:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=(0, 5))

        # 标签筛选下拉框
        self.filter_tag_var = tk.StringVar()
        self.filter_tag_var.set("所有标签")
        self.filter_tag_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_tag_var,
            values=["所有标签"] + list(self.tags_data.keys()),
            width=15,
            state="readonly"
        )
        self.filter_tag_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.filter_tag_combo.bind("<<ComboboxSelected>>", self.on_filter_tag_selected)

        # 日期筛选
        tk.Label(filter_frame, text="日期:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=(0, 5))
        self.filter_date_var = tk.StringVar()
        self.filter_date_var.set("所有日期")
        self.filter_date_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_date_var,
            values=["所有日期", "今天", "本周", "本月", "最近7天", "最近30天"],
            width=10,
            state="readonly"
        )
        self.filter_date_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.filter_date_combo.bind("<<ComboboxSelected>>", self.on_filter_date_selected)

        # 重置筛选按钮
        reset_filter_button = tk.Button(
            filter_frame,
            text="重置筛选",
            command=self.reset_filters,
            bg=self.button_bg,
            fg=self.button_fg,
            activebackground=self.button_active,
            activeforeground=self.button_fg,
            relief="flat",
            cursor="hand2"
        )
        reset_filter_button.pack(side=tk.LEFT)

        # 创建Treeview显示历史记录
        style = ttk.Style()
        style.theme_use('clam')

        # 配置Treeview样式
        style.configure("Treeview",
                        background=self.tree_bg,
                        foreground=self.tree_fg,
                        fieldbackground=self.tree_bg,
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        background=self.button_bg,
                        foreground=self.fg_color,
                        relief="flat")
        style.configure("Treeview.Cell",
                        anchor="center")
        style.map('Treeview', background=[('selected', self.tree_sel_bg)])

        columns = ("事件名称", "标签", "开始时间", "结束时间", "持续时间")
        self.history_tree = ttk.Treeview(
            history_frame,
            columns=columns,
            show="headings",
            style="Treeview"
        )

        # 设置列标题和居中对齐
        for col in columns:
            self.history_tree.heading(col, text=col, anchor="center")
            if col == "事件名称":
                self.history_tree.column(col, width=180, anchor="center")
            elif col == "标签":
                self.history_tree.column(col, width=100, anchor="center")
            else:
                self.history_tree.column(col, width=120, anchor="center")

        # 添加滚动条
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        # 布局Treeview和滚动条
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 0))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 底部按钮和状态栏
        bottom_frame = tk.Frame(main_frame, bg=self.bg_color)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))

        clear_button = tk.Button(
            bottom_frame,
            text="清空历史",
            command=self.clear_history,
            bg=self.clear_color,
            fg="white",
            width=15,
            activebackground=self.clear_color,
            activeforeground="white",
            relief="flat",
            cursor="hand2"
        )
        clear_button.pack(side=tk.LEFT, padx=(0, 10))

        # 通知设置按钮
        notification_button = tk.Button(
            bottom_frame,
            text="通知设置",
            command=self.show_notification_settings,
            bg=self.accent_color,
            fg="white",
            width=15,
            activebackground=self.accent_color,
            activeforeground="white",
            relief="flat",
            cursor="hand2"
        )
        notification_button.pack(side=tk.LEFT, padx=(0, 10))

        # 打开配置文件夹按钮
        open_folder_button = tk.Button(
            bottom_frame,
            text="打开配置文件夹",
            command=self.open_config_folder,
            bg=self.accent_color,
            fg="white",
            width=15,
            activebackground=self.accent_color,
            activeforeground="white",
            relief="flat",
            cursor="hand2"
        )
        open_folder_button.pack(side=tk.LEFT, padx=(0, 10))

        # 底部状态栏
        self.status_bar = tk.Label(
            bottom_frame,
            text="就绪",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg=self.button_bg,
            fg=self.fg_color
        )
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 为历史记录Treeview创建右键菜单
        self.create_history_context_menu()

        # 初始化历史记录显示
        self.update_history_display()

    def bind_events(self):
        """绑定事件处理"""
        # 输入框事件
        self.event_entry.bind("<KeyRelease>", self.on_entry_keyrelease)
        self.event_entry.bind("<FocusIn>", self.on_entry_focus_in)
        self.event_entry.bind("<FocusOut>", self.on_entry_focus_out)
        self.event_entry.bind("<Return>", lambda e: self.start_timing())
        self.event_entry.bind("<Escape>", lambda e: self.lose_focus())

        # 标签输入框事件
        self.tag_entry.bind("<FocusIn>", lambda e: self.hide_dropdown())

        # 下拉列表事件
        self.dropdown_listbox.bind("<ButtonRelease-1>", self.on_dropdown_select)
        self.dropdown_listbox.bind("<Return>", self.on_dropdown_select)
        self.dropdown_listbox.bind("<Escape>", lambda e: self.hide_dropdown())
        # 绑定鼠标移动事件，实现悬停效果
        self.dropdown_listbox.bind("<Motion>", self.on_dropdown_motion)

        # 绑定全局点击事件，点击其他地方隐藏下拉列表并失去焦点
        self.root.bind("<Button-1>", self.global_click_handler)

        # 绑定全局ESC键事件
        self.root.bind("<Escape>", lambda e: self.lose_focus())

        # 历史记录Treeview右键事件
        self.history_tree.bind("<Button-3>", self.show_history_context_menu)

    def lose_focus(self):
        """使输入框失去焦点"""
        self.root.focus_set()
        self.hide_dropdown()
        return "break"

    def global_click_handler(self, event):
        """全局点击事件处理"""
        widget = event.widget

        if widget == self.event_entry or widget == self.tag_entry:
            return

        if widget == self.dropdown_listbox or widget == self.dropdown_frame:
            return

        widget_path = []
        current_widget = widget
        while current_widget:
            widget_path.append(str(current_widget))
            current_widget = current_widget.master

        widget_path_str = ' '.join(widget_path)

        if ('scrollable_frame' in widget_path_str or
                'history_tree' in widget_path_str or
                'current_timers_frame' in widget_path_str):
            return

        self.hide_dropdown()
        self.lose_focus()

    def on_dropdown_motion(self, event):
        """处理下拉列表鼠标移动事件，实现悬停效果"""
        index = self.dropdown_listbox.nearest(event.y)
        self.dropdown_listbox.selection_clear(0, tk.END)

        if index >= 0:
            self.dropdown_listbox.selection_set(index)
            self.dropdown_listbox.see(index)

    def create_history_context_menu(self):
        """创建历史记录右键菜单"""
        self.history_context_menu = tk.Menu(self.root, tearoff=0, bg=self.button_bg, fg=self.fg_color)
        self.history_context_menu.add_command(label="删除选中项", command=self.delete_selected_history)
        self.history_context_menu.add_command(label="编辑标签", command=self.edit_selected_tag)

    def show_history_context_menu(self, event):
        """显示历史记录右键菜单"""
        item = self.history_tree.identify_row(event.y)
        if item:
            self.history_tree.selection_set(item)
            self.history_context_menu.post(event.x_root, event.y_root)

    def delete_selected_history(self):
        """删除选中的历史记录"""
        selected_items = self.history_tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择要删除的历史记录")
            return

        if messagebox.askyesno("确认", f"确定要删除选中的 {len(selected_items)} 条记录吗？"):
            deleted_events = []
            for item in selected_items:
                values = self.history_tree.item(item, 'values')
                if values:
                    event_name = values[0]
                    start_time_display = values[2]

                    for i, history in enumerate(self.events_history):
                        display_start = self.format_time_for_display(history["start_time"])

                        if (history["event"] == event_name and
                                display_start == start_time_display):
                            deleted_events.append((event_name, history["start_time"]))
                            del self.events_history[i]
                            break

            self.update_history_display()
            self.save_history()
            self.status_bar.config(text=f"已删除 {len(deleted_events)} 条历史记录")

    def edit_selected_tag(self):
        """编辑选中记录的标签"""
        selected_items = self.history_tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择要编辑标签的记录")
            return

        if len(selected_items) > 1:
            messagebox.showwarning("提示", "只能编辑单条记录的标签")
            return

        item = selected_items[0]
        values = self.history_tree.item(item, 'values')

        if not values:
            return

        event_name = values[0]
        current_tags = values[1]
        start_time_display = values[2]

        for i, history in enumerate(self.events_history):
            display_start = self.format_time_for_display(history["start_time"])
            if (history["event"] == event_name and
                    display_start == start_time_display):
                new_tags = simpledialog.askstring("编辑标签",
                                                  f"事件: {event_name}\n当前标签: {current_tags}\n请输入新标签:",
                                                  initialvalue=current_tags)
                if new_tags is not None:
                    history["tags"] = new_tags

                    for tag in self.parse_tags(new_tags):
                        if tag in self.tags_data:
                            self.tags_data[tag] += 1
                        else:
                            self.tags_data[tag] = 1

                    self.save_history()
                    self.save_tags()
                    self.update_history_display()
                    self.update_filter_tag_combo()

                    self.status_bar.config(text=f"已更新事件标签: {event_name}")
                break

    def format_time_for_display(self, datetime_str):
        """将完整时间格式转换为只显示时和分"""
        try:
            dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%H:%M")
        except:
            return datetime_str

    def format_duration(self, seconds):
        """将持续时间格式化为0h00m格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h{minutes:02d}m"

    def on_entry_keyrelease(self, event):
        """输入框按键释放事件 - 更新下拉列表"""
        if event.keysym in ['Up', 'Down', 'Left', 'Right', 'Return']:
            return

        self.update_dropdown_list()

    def on_entry_focus_in(self, event):
        """输入框获得焦点事件 - 显示下拉列表"""
        self.update_dropdown_list()

    def on_entry_focus_out(self, event):
        """输入框失去焦点事件 - 立即隐藏下拉列表"""
        self.root.after(50, self.check_and_hide_dropdown)

    def check_and_hide_dropdown(self):
        """检查并隐藏下拉列表"""
        if not self.event_entry.focus_get() and not self.is_mouse_over_dropdown():
            self.hide_dropdown()

    def is_mouse_over_dropdown(self):
        """检查鼠标是否在下拉列表上方"""
        try:
            mouse_x = self.root.winfo_pointerx() - self.root.winfo_rootx()
            mouse_y = self.root.winfo_pointery() - self.root.winfo_rooty()

            dropdown_x = self.dropdown_frame.winfo_x()
            dropdown_y = self.dropdown_frame.winfo_y()
            dropdown_width = self.dropdown_frame.winfo_width()
            dropdown_height = self.dropdown_frame.winfo_height()

            return (dropdown_x <= mouse_x <= dropdown_x + dropdown_width and
                    dropdown_y <= mouse_y <= dropdown_y + dropdown_height)
        except:
            return False

    def update_dropdown_list(self):
        """更新下拉列表内容"""
        text = self.event_entry.get().strip()

        if text:
            matches = []
            for name, data in self.event_names_data.items():
                score = 0

                if name == text:
                    score += 1000
                elif name.startswith(text):
                    score += 500
                elif text in name:
                    score += 100

                score += data.get("count", 0) * 10

                last_used = data.get("last_used", "1970-01-01 00:00:00")
                try:
                    last_used_dt = datetime.strptime(last_used, "%Y-%m-%d %H:%M:%S")
                    days_since = (datetime.now() - last_used_dt).days
                    if days_since < 30:
                        score += (30 - days_since) * 5
                except:
                    pass

                if score > 0:
                    matches.append((name, score))

            matches.sort(key=lambda x: x[1], reverse=True)
            items = [match[0] for match in matches[:20]]
        else:
            if self.event_names_data:
                items = sorted(self.event_names_data.items(),
                               key=lambda x: (x[1].get("count", 0),
                                              x[1].get("last_used", "")),
                               reverse=True)[:20]
                items = [item[0] for item in items]
            else:
                items = []

        self.dropdown_listbox.delete(0, tk.END)

        if items:
            for item in items:
                self.dropdown_listbox.insert(tk.END, item)
        else:
            self.dropdown_listbox.insert(tk.END, "暂无历史事件")

        if self.dropdown_listbox.size() > 0:
            self.show_dropdown()
        else:
            self.hide_dropdown()

    def show_dropdown(self):
        """显示下拉列表"""
        x = self.event_entry.winfo_rootx() - self.root.winfo_rootx()
        y = self.event_entry.winfo_rooty() - self.root.winfo_rooty() + self.event_entry.winfo_height()
        width = self.event_entry.winfo_width()

        item_count = min(8, self.dropdown_listbox.size())
        height = item_count * 20 + 4

        self.dropdown_frame.place(x=x, y=y, width=width, height=height)
        self.dropdown_frame.lift()
        self.dropdown_visible = True
        self.event_entry.focus_set()

    def hide_dropdown(self):
        """隐藏下拉列表"""
        self.dropdown_frame.place_forget()
        self.dropdown_visible = False
        self.dropdown_listbox.selection_clear(0, tk.END)

    def on_dropdown_select(self, event=None):
        """选择下拉列表项"""
        selection = self.dropdown_listbox.curselection()
        if selection:
            selected_text = self.dropdown_listbox.get(selection[0])

            if selected_text == "暂无历史事件":
                return

            self.event_entry.delete(0, tk.END)
            self.event_entry.insert(0, selected_text)
            self.hide_dropdown()
            self.event_entry.focus()

    def toggle_topmost(self):
        """切换窗口置顶状态"""
        self.root.attributes("-topmost", self.topmost_var.get())

    # ===== 标签系统功能 =====

    def parse_tags(self, tag_string):
        """解析标签字符串，返回标签列表"""
        if not tag_string:
            return []

        tags = []
        for part in tag_string.split(','):
            for subpart in part.split():
                tag = subpart.strip()
                if tag:
                    if tag.startswith('#'):
                        tag = tag[1:]
                    tags.append(tag)

        return list(set(tags))

    def show_tag_manager(self):
        """显示标签管理器"""
        tag_window = tk.Toplevel(self.root)
        tag_window.title("标签管理")
        tag_window.geometry("400x350")
        tag_window.configure(bg=self.bg_color)
        tag_window.transient(self.root)
        tag_window.grab_set()

        # 标签列表
        listbox_frame = tk.Frame(tag_window, bg=self.bg_color)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(listbox_frame, text="标签列表 (双击标签添加到输入框):", bg=self.bg_color, fg=self.fg_color).pack(
            anchor="w")

        tag_listbox = tk.Listbox(
            listbox_frame,
            bg=self.entry_bg,
            fg=self.entry_fg,
            selectbackground=self.dropdown_sel_bg,
            selectforeground="white",
            height=10
        )
        tag_listbox.pack(fill=tk.BOTH, expand=True, pady=(5, 10))

        # 显示标签和使用次数
        for tag, count in sorted(self.tags_data.items(), key=lambda x: x[1], reverse=True):
            tag_listbox.insert(tk.END, f"{tag} ({count}次)")

        # 双击事件 - 将标签添加到输入框
        def on_tag_double_click(event):
            selection = tag_listbox.curselection()
            if selection:
                selected_text = tag_listbox.get(selection[0])
                tag_name = selected_text.split(' (')[0]  # 提取标签名

                # 获取当前标签输入框的内容
                current_tags = self.tag_entry.get().strip()
                if current_tags:
                    # 如果已经有标签，用逗号分隔添加新标签
                    new_tags = f"{current_tags}, #{tag_name}"
                else:
                    new_tags = f"#{tag_name}"

                # 更新标签输入框
                self.tag_entry.delete(0, tk.END)
                self.tag_entry.insert(0, new_tags)

                self.status_bar.config(text=f"已添加标签: #{tag_name}")
                tag_window.destroy()

        tag_listbox.bind("<Double-Button-1>", on_tag_double_click)

        # 按钮框架
        button_frame = tk.Frame(tag_window, bg=self.bg_color)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # 添加标签
        add_frame = tk.Frame(button_frame, bg=self.bg_color)
        add_frame.pack(fill=tk.X, pady=(0, 5))

        tk.Label(add_frame, text="添加标签:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT)
        new_tag_entry = tk.Entry(add_frame, bg=self.entry_bg, fg=self.entry_fg, width=20)
        new_tag_entry.pack(side=tk.LEFT, padx=(5, 5))

        def add_tag():
            tag = new_tag_entry.get().strip()
            if tag:
                if tag in self.tags_data:
                    # 如果标签已存在，增加使用次数
                    self.tags_data[tag] += 1
                else:
                    # 新标签初始化为0次
                    self.tags_data[tag] = 0

                self.save_tags()
                self.update_filter_tag_combo()

                # 刷新列表
                tag_listbox.delete(0, tk.END)
                for tag, count in sorted(self.tags_data.items(), key=lambda x: x[1], reverse=True):
                    tag_listbox.insert(tk.END, f"{tag} ({count}次)")

                new_tag_entry.delete(0, tk.END)
                self.status_bar.config(text=f"已添加标签: {tag}")

        add_button = tk.Button(
            add_frame,
            text="添加",
            command=add_tag,
            bg=self.tag_color,
            fg="white",
            width=8,
            activebackground=self.tag_color,
            activeforeground="white",
            relief="flat"
        )
        add_button.pack(side=tk.LEFT)

        # 删除选中标签
        def delete_selected_tag():
            selection = tag_listbox.curselection()
            if not selection:
                messagebox.showwarning("提示", "请先选择要删除的标签")
                return

            selected_text = tag_listbox.get(selection[0])
            tag = selected_text.split(' (')[0]

            if messagebox.askyesno("确认", f"确定要删除标签 '{tag}' 吗？"):
                if tag in self.tags_data:
                    del self.tags_data[tag]
                    self.save_tags()
                    self.update_filter_tag_combo()

                    for history in self.events_history:
                        if "tags" in history:
                            tags_list = self.parse_tags(history["tags"])
                            if tag in tags_list:
                                tags_list.remove(tag)
                                history["tags"] = ", ".join(tags_list)

                    self.save_history()
                    self.update_history_display()

                    tag_listbox.delete(0, tk.END)
                    for tag, count in sorted(self.tags_data.items(), key=lambda x: x[1], reverse=True):
                        tag_listbox.insert(tk.END, f"{tag} ({count}次)")

                    self.status_bar.config(text=f"已删除标签: {tag}")

        delete_button = tk.Button(
            button_frame,
            text="删除选中标签",
            command=delete_selected_tag,
            bg=self.stop_color,
            fg="white",
            width=15,
            activebackground=self.stop_color,
            activeforeground="white",
            relief="flat"
        )
        delete_button.pack(side=tk.LEFT, padx=(0, 10))

        # 关闭按钮
        close_button = tk.Button(
            button_frame,
            text="关闭",
            command=tag_window.destroy,
            bg=self.button_bg,
            fg=self.button_fg,
            width=10,
            activebackground=self.button_active,
            activeforeground=self.button_fg,
            relief="flat"
        )
        close_button.pack(side=tk.RIGHT)

    def update_filter_tag_combo(self):
        """更新标签筛选下拉框"""
        current_value = self.filter_tag_var.get()
        self.filter_tag_combo['values'] = ["所有标签"] + list(self.tags_data.keys())

        if current_value in self.filter_tag_combo['values']:
            self.filter_tag_var.set(current_value)
        else:
            self.filter_tag_var.set("所有标签")

    # ===== 模板系统功能 =====

    def show_template_manager(self):
        """显示模板管理器"""
        template_window = tk.Toplevel(self.root)
        template_window.title("模板管理")
        template_window.geometry("500x400")
        template_window.configure(bg=self.bg_color)
        template_window.transient(self.root)
        template_window.grab_set()

        # 模板列表
        listbox_frame = tk.Frame(template_window, bg=self.bg_color)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(listbox_frame, text="模板列表:", bg=self.bg_color, fg=self.fg_color).pack(anchor="w")

        template_listbox = tk.Listbox(
            listbox_frame,
            bg=self.entry_bg,
            fg=self.entry_fg,
            selectbackground=self.dropdown_sel_bg,
            selectforeground="white",
            height=10
        )
        template_listbox.pack(fill=tk.BOTH, expand=True, pady=(5, 10))

        for i, template in enumerate(self.event_templates):
            events_count = len(template.get("events", []))
            template_listbox.insert(tk.END, f"{template['name']} ({events_count}个事件)")

        # 按钮框架
        button_frame = tk.Frame(template_window, bg=self.bg_color)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # 创建新模板
        def create_new_template():
            create_window = tk.Toplevel(template_window)
            create_window.title("创建新模板")
            create_window.geometry("400x350")
            create_window.configure(bg=self.bg_color)
            create_window.transient(template_window)
            create_window.grab_set()

            # 模板名称
            tk.Label(create_window, text="模板名称:", bg=self.bg_color, fg=self.fg_color).pack(anchor="w", padx=10,
                                                                                               pady=(10, 5))
            name_entry = tk.Entry(create_window, bg=self.entry_bg, fg=self.entry_fg, width=30)
            name_entry.pack(fill=tk.X, padx=10, pady=(0, 10))

            # 事件列表
            tk.Label(create_window, text="事件列表 (每行一个事件):", bg=self.bg_color, fg=self.fg_color).pack(
                anchor="w", padx=10, pady=(0, 5))
            events_text = tk.Text(create_window, bg=self.entry_bg, fg=self.entry_fg, height=8)
            events_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

            # 标签输入
            tk.Label(create_window, text="默认标签 (可选, 将应用于所有事件):", bg=self.bg_color, fg=self.fg_color).pack(
                anchor="w", padx=10, pady=(0, 5))
            tags_entry = tk.Entry(create_window, bg=self.entry_bg, fg=self.entry_fg, width=30)
            tags_entry.pack(fill=tk.X, padx=10, pady=(0, 10))

            def save_template():
                name = name_entry.get().strip()
                if not name:
                    messagebox.showwarning("提示", "请输入模板名称")
                    return

                events_text_content = events_text.get("1.0", tk.END).strip()
                if not events_text_content:
                    messagebox.showwarning("提示", "请至少添加一个事件")
                    return

                default_tags = tags_entry.get().strip()
                events = []
                for line in events_text_content.split('\n'):
                    line = line.strip()
                    if line:
                        events.append({"name": line, "tags": default_tags})

                self.event_templates.append({
                    "name": name,
                    "events": events
                })

                self.save_templates()

                # 更新下拉框
                self.template_combo['values'] = [t["name"] for t in self.event_templates]

                # 刷新列表
                template_listbox.delete(0, tk.END)
                for i, template in enumerate(self.event_templates):
                    events_count = len(template.get("events", []))
                    template_listbox.insert(tk.END, f"{template['name']} ({events_count}个事件)")

                create_window.destroy()
                self.status_bar.config(text=f"已创建模板: {name}")

            save_button = tk.Button(
                create_window,
                text="保存模板",
                command=save_template,
                bg=self.template_color,
                fg="white",
                width=15,
                activebackground=self.template_color,
                activeforeground="white",
                relief="flat"
            )
            save_button.pack(side=tk.LEFT, padx=10, pady=(0, 10))

            cancel_button = tk.Button(
                create_window,
                text="取消",
                command=create_window.destroy,
                bg=self.button_bg,
                fg=self.button_fg,
                width=10,
                activebackground=self.button_active,
                activeforeground=self.button_fg,
                relief="flat"
            )
            cancel_button.pack(side=tk.RIGHT, padx=10, pady=(0, 10))

        # 使用选中模板
        def use_selected_template():
            selection = template_listbox.curselection()
            if not selection:
                messagebox.showwarning("提示", "请先选择要使用的模板")
                return

            template_index = selection[0]
            template = self.event_templates[template_index]

            if messagebox.askyesno("使用模板",
                                   f"确定要使用模板 '{template['name']}' 吗？\n\n该模板包含 {len(template['events'])} 个事件，将依次开始计时。"):
                # 设置当前模板和执行队列
                self.current_template = template
                self.template_event_index = 0
                self.template_events_queue = template["events"].copy()

                # 清空输入框
                self.event_entry.delete(0, tk.END)
                self.tag_entry.delete(0, tk.END)

                # 开始第一个事件
                self.start_next_template_event()

                # 关闭模板管理器窗口
                template_window.destroy()

        # 删除选中模板
        def delete_selected_template():
            selection = template_listbox.curselection()
            if not selection:
                messagebox.showwarning("提示", "请先选择要删除的模板")
                return

            template_index = selection[0]
            template_name = self.event_templates[template_index]["name"]

            if messagebox.askyesno("确认", f"确定要删除模板 '{template_name}' 吗？"):
                del self.event_templates[template_index]
                self.save_templates()

                # 更新下拉框
                self.template_combo['values'] = [t["name"] for t in self.event_templates]

                # 刷新列表
                template_listbox.delete(0, tk.END)
                for i, template in enumerate(self.event_templates):
                    events_count = len(template.get("events", []))
                    template_listbox.insert(tk.END, f"{template['name']} ({events_count}个事件)")

                self.status_bar.config(text=f"已删除模板: {template_name}")

        # 按钮
        create_button = tk.Button(
            button_frame,
            text="新建模板",
            command=create_new_template,
            bg=self.template_color,
            fg="white",
            width=15,
            activebackground=self.template_color,
            activeforeground="white",
            relief="flat"
        )
        create_button.pack(side=tk.LEFT, padx=(0, 10))

        use_button = tk.Button(
            button_frame,
            text="使用选中模板",
            command=use_selected_template,
            bg=self.start_color,
            fg="white",
            width=15,
            activebackground=self.start_color,
            activeforeground="white",
            relief="flat"
        )
        use_button.pack(side=tk.LEFT, padx=(0, 10))

        delete_button = tk.Button(
            button_frame,
            text="删除选中模板",
            command=delete_selected_template,
            bg=self.stop_color,
            fg="white",
            width=15,
            activebackground=self.stop_color,
            activeforeground="white",
            relief="flat"
        )
        delete_button.pack(side=tk.LEFT, padx=(0, 10))

        # 关闭按钮
        close_button = tk.Button(
            button_frame,
            text="关闭",
            command=template_window.destroy,
            bg=self.button_bg,
            fg=self.button_fg,
            width=10,
            activebackground=self.button_active,
            activeforeground=self.button_fg,
            relief="flat"
        )
        close_button.pack(side=tk.RIGHT)

    def on_template_selected(self, event):
        """模板下拉框选择事件"""
        template_name = self.template_combo.get()
        if template_name == "选择模板":
            return

        for template in self.event_templates:
            if template["name"] == template_name:
                # 设置当前模板和执行队列
                self.current_template = template
                self.template_event_index = 0
                self.template_events_queue = template["events"].copy()

                # 清空输入框
                self.event_entry.delete(0, tk.END)
                self.tag_entry.delete(0, tk.END)

                # 开始第一个事件
                self.start_next_template_event()
                break

    def start_next_template_event(self):
        """开始模板中的下一个事件"""
        if not self.current_template or not self.template_events_queue:
            return

        if self.template_event_index >= len(self.template_events_queue):
            # 所有事件都完成了
            self.status_bar.config(text=f"模板 '{self.current_template['name']}' 的所有事件已完成")
            self.current_template = None
            self.template_event_index = 0
            self.template_events_queue = []
            return

        # 获取下一个事件
        event_data = self.template_events_queue[self.template_event_index]
        event_name = event_data["name"]
        event_tags = event_data.get("tags", "")

        # 检查事件是否已经在计时
        if event_name in self.current_events:
            messagebox.showwarning("事件已存在", f"事件 '{event_name}' 已经在计时中")
            # 跳过这个事件，继续下一个
            self.template_event_index += 1
            self.root.after(100, self.start_next_template_event)
            return

        # 设置输入框
        self.event_entry.delete(0, tk.END)
        self.event_entry.insert(0, event_name)

        if event_tags:
            self.tag_entry.delete(0, tk.END)
            self.tag_entry.insert(0, event_tags)

        # 开始计时
        self.start_timing_from_template()

        # 更新索引
        self.template_event_index += 1

        # 显示提示
        remaining = len(self.template_events_queue) - self.template_event_index
        if remaining > 0:
            self.status_bar.config(
                text=f"模板 '{self.current_template['name']}' 进行中: {event_name} (还有 {remaining} 个事件)")

        # 重置下拉框选择
        self.template_combo.set("选择模板")

    def start_timing_from_template(self):
        """从模板开始计时（专为模板调用）"""
        event_name = self.event_entry.get().strip()

        if not event_name:
            return

        if event_name in self.current_events:
            return

        start_time = datetime.now()
        tags = self.tag_entry.get().strip()

        self.current_events[event_name] = {
            "start_time": start_time,
            "tags": tags,
            "from_template": True  # 标记来自模板
        }

        # 更新事件名称数据
        if event_name in self.event_names_data:
            self.event_names_data[event_name]["count"] += 1
        else:
            self.event_names_data[event_name] = {"count": 1}

        self.event_names_data[event_name]["last_used"] = start_time.strftime("%Y-%m-%d %H:%M:%S")
        self.save_event_names()

        # 更新标签数据
        parsed_tags = self.parse_tags(tags)
        for tag in parsed_tags:
            if tag in self.tags_data:
                self.tags_data[tag] += 1
            else:
                self.tags_data[tag] = 1

        self.save_tags()
        self.update_filter_tag_combo()

        # 清空输入框
        self.event_entry.delete(0, tk.END)

        # 隐藏下拉列表
        self.hide_dropdown()

        # 添加计时器显示
        self.add_timer_display(event_name, start_time, parsed_tags)

        # 更新系统托盘图标提示
        self.update_tray_tooltip()

    # ===== 通知系统功能 =====

    def start_notification_checker(self):
        """启动通知检查器"""
        if not self.notification_active:
            return

        # 停止现有的通知线程（如果存在）
        if self.notification_thread and self.notification_thread.is_alive():
            self.notification_active = False
            time.sleep(0.1)  # 给线程一点时间停止

        self.notification_active = True

        def notification_loop():
            # 存储每个事件的最后通知时间
            event_notification_times = {}

            while self.notification_active:
                current_time = time.time()

                # 检查当前所有事件
                for event_name in list(self.current_events.keys()):
                    event_data = self.current_events[event_name]
                    start_time = event_data["start_time"]

                    # 计算事件已经运行的时间（秒）
                    elapsed_seconds = (datetime.now() - start_time).total_seconds()
                    elapsed_minutes = elapsed_seconds / 60

                    # 检查是否达到通知间隔
                    if elapsed_minutes >= self.notification_interval:
                        # 检查这个事件是否已经发送过通知
                        if event_name not in event_notification_times:
                            # 第一次发送通知
                            event_notification_times[event_name] = current_time
                            self.root.after(0, lambda e=event_name: self.show_single_event_notification(e))
                        else:
                            # 检查距离上次通知的时间
                            last_notification_time = event_notification_times[event_name]
                            time_since_last_notification = (current_time - last_notification_time) / 60

                            # 如果距离上次通知已经超过通知间隔，再次发送通知
                            if time_since_last_notification >= self.notification_interval:
                                event_notification_times[event_name] = current_time
                                self.root.after(0, lambda e=event_name: self.show_single_event_notification(e))

                # 移除已经停止的事件
                for event_name in list(event_notification_times.keys()):
                    if event_name not in self.current_events:
                        del event_notification_times[event_name]

                # 每分钟检查一次
                for _ in range(60):
                    if not self.notification_active:
                        return
                    time.sleep(1)

        self.notification_thread = threading.Thread(target=notification_loop, daemon=True)
        self.notification_thread.start()

    def show_single_event_notification(self, event_name):
        """显示单个事件的通知"""
        if event_name not in self.current_events:
            return

        # 如果设置了自动停止，直接停止事件
        if self.auto_stop_on_notification:
            self.stop_single_timing(event_name)
            return

        try:
            winsound.Beep(1000, 500)
        except:
            pass

        event_data = self.current_events[event_name]
        start_time = event_data["start_time"]
        current_time = datetime.now()
        duration = current_time - start_time
        duration_minutes = duration.total_seconds() / 60

        notification_window = tk.Toplevel(self.root)
        notification_window.title("事件计时提醒")
        notification_window.geometry("400x200")
        notification_window.configure(bg=self.bg_color)
        notification_window.attributes("-topmost", True)

        notification_window.update_idletasks()
        width = notification_window.winfo_width()
        height = notification_window.winfo_height()
        x = (notification_window.winfo_screenwidth() // 2) - (width // 2)
        y = (notification_window.winfo_screenheight() // 2) - (height // 2)
        notification_window.geometry(f'{width}x{height}+{x}+{y}')

        tk.Label(
            notification_window,
            text="⏰ 事件计时提醒",
            bg=self.bg_color,
            fg=self.accent_color,
            font=("Arial", 16, "bold")
        ).pack(pady=(20, 10))

        tk.Label(
            notification_window,
            text=f"事件 '{event_name}' 已计时 {self.notification_interval} 分钟",
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 12),
            wraplength=350
        ).pack(pady=(0, 20))

        tk.Label(
            notification_window,
            text="是否仍在继续这个事件？",
            bg=self.bg_color,
            fg=self.fg_color
        ).pack(pady=(0, 20))

        button_frame = tk.Frame(notification_window, bg=self.bg_color)
        button_frame.pack(pady=(0, 20))

        def continue_event():
            self.status_bar.config(text=f"已确认事件仍在继续: {event_name}")
            notification_window.destroy()

        def stop_event():
            self.stop_single_timing(event_name)
            notification_window.destroy()

        continue_button = tk.Button(
            button_frame,
            text="仍在继续",
            command=continue_event,
            bg=self.start_color,
            fg="white",
            width=12,
            activebackground=self.start_color,
            activeforeground="white",
            relief="flat"
        )
        continue_button.pack(side=tk.LEFT, padx=(0, 20))

        stop_button = tk.Button(
            button_frame,
            text="停止该事件",
            command=stop_event,
            bg=self.stop_color,
            fg="white",
            width=12,
            activebackground=self.stop_color,
            activeforeground="white",
            relief="flat"
        )
        stop_button.pack(side=tk.LEFT)

    def show_notification_settings(self):
        """显示通知设置"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("通知设置")
        settings_window.geometry("400x350")
        settings_window.configure(bg=self.bg_color)
        settings_window.transient(self.root)
        settings_window.grab_set()

        tk.Label(
            settings_window,
            text="通知设置",
            bg=self.bg_color,
            fg=self.accent_color,
            font=("Arial", 14, "bold")
        ).pack(pady=(20, 10))

        # 通知间隔设置
        interval_frame = tk.Frame(settings_window, bg=self.bg_color)
        interval_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        tk.Label(interval_frame, text="通知间隔:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value=str(self.notification_interval))
        interval_entry = tk.Entry(interval_frame, textvariable=self.interval_var, width=10, bg=self.entry_bg,
                                  fg=self.entry_fg)
        interval_entry.pack(side=tk.LEFT, padx=(5, 5))
        tk.Label(interval_frame, text="分钟", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT)

        # 通知启用复选框
        notification_var = tk.BooleanVar(value=self.notification_active)

        def toggle_notification():
            self.notification_active = notification_var.get()
            if self.notification_active:
                # 获取间隔值
                try:
                    interval = int(self.interval_var.get())
                    if interval < 1:
                        interval = 1
                    elif interval > 480:  # 8小时
                        interval = 480
                    self.notification_interval = interval
                except:
                    self.notification_interval = 30
                    self.interval_var.set("30")

                self.start_notification_checker()
                self.status_bar.config(text=f"已开启通知，间隔{self.notification_interval}分钟")
            else:
                self.status_bar.config(text="已关闭通知")

        notification_check = tk.Checkbutton(
            settings_window,
            text="启用通知提醒",
            variable=notification_var,
            command=toggle_notification,
            bg=self.bg_color,
            fg=self.fg_color,
            selectcolor=self.bg_color,
            activebackground=self.bg_color,
            activeforeground=self.fg_color,
            font=("Arial", 12)
        )
        notification_check.pack(pady=(10, 10))

        # 自动停止复选框
        auto_stop_var = tk.BooleanVar(value=self.auto_stop_on_notification)

        def toggle_auto_stop():
            self.auto_stop_on_notification = auto_stop_var.get()

        auto_stop_check = tk.Checkbutton(
            settings_window,
            text="通知出现时自动停止所有事件",
            variable=auto_stop_var,
            command=toggle_auto_stop,
            bg=self.bg_color,
            fg=self.fg_color,
            selectcolor=self.bg_color,
            activebackground=self.bg_color,
            activeforeground=self.fg_color,
            font=("Arial", 12)
        )
        auto_stop_check.pack(pady=(0, 10))

        tk.Label(
            settings_window,
            text="开启后，当通知出现时会自动停止所有计时事件。",
            bg=self.bg_color,
            fg=self.fg_color,
            wraplength=350,
            justify="left"
        ).pack(pady=(0, 20))

        # 保存设置按钮
        def save_settings():
            try:
                interval = int(self.interval_var.get())
                if interval < 1:
                    interval = 1
                elif interval > 480:
                    interval = 480
                self.notification_interval = interval

                # 重新启动通知检查器
                self.notification_active = False
                time.sleep(0.2)  # 等待线程停止
                self.notification_active = True
                self.start_notification_checker()

                self.save_settings()
                settings_window.destroy()
                self.status_bar.config(text=f"通知设置已保存，间隔{self.notification_interval}分钟")
            except:
                messagebox.showerror("错误", "请输入有效的数字")

        save_button = tk.Button(
            settings_window,
            text="保存设置",
            command=save_settings,
            bg=self.accent_color,
            fg="white",
            width=10,
            activebackground=self.accent_color,
            activeforeground="white",
            relief="flat"
        )
        save_button.pack(pady=(0, 10))

    # ===== 打开配置文件夹功能 =====

    def open_config_folder(self):
        """打开配置文件所在文件夹"""
        try:
            # 打开config文件夹
            if platform.system() == "Windows":
                os.startfile(self.config_dir)
            elif platform.system() == "Darwin":  # macOS
                import subprocess
                subprocess.Popen(["open", self.config_dir])
            else:  # Linux
                import subprocess
                subprocess.Popen(["xdg-open", self.config_dir])

            self.status_bar.config(text=f"已打开配置文件夹: {self.config_dir}")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {str(e)}")

    # ===== 设置保存和加载 =====

    def load_settings(self):
        """加载设置"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.notification_interval = settings.get("notification_interval", 30)
                    self.auto_stop_on_notification = settings.get("auto_stop_on_notification", False)
                    self.notification_active = settings.get("notification_active", True)
            except:
                self.notification_interval = 30
                self.auto_stop_on_notification = False
                self.notification_active = True
        else:
            self.notification_interval = 30
            self.auto_stop_on_notification = False
            self.notification_active = True

    def save_settings(self):
        """保存设置"""
        try:
            settings = {
                "notification_interval": self.notification_interval,
                "auto_stop_on_notification": self.auto_stop_on_notification,
                "notification_active": self.notification_active
            }
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except:
            pass

    # ===== 筛选功能 =====

    def on_filter_tag_selected(self, event):
        """标签筛选选择事件"""
        self.update_history_display()

    def on_filter_date_selected(self, event):
        """日期筛选选择事件"""
        self.update_history_display()

    def reset_filters(self):
        """重置筛选"""
        self.filter_tag_var.set("所有标签")
        self.filter_date_var.set("所有日期")
        self.update_history_display()
        self.status_bar.config(text="已重置所有筛选")

    # ===== 主要计时功能 =====

    def start_timing(self):
        """开始计时一个新事件"""
        event_name = self.event_entry.get().strip()

        if not event_name:
            messagebox.showwarning("输入错误", "请输入事件名称")
            self.event_entry.focus()
            return

        if event_name in self.current_events:
            messagebox.showwarning("事件已存在", f"事件 '{event_name}' 已经在计时中")
            self.event_entry.delete(0, tk.END)
            return

        start_time = datetime.now()
        tags = self.tag_entry.get().strip()

        self.current_events[event_name] = {
            "start_time": start_time,
            "tags": tags,
            "from_template": False
        }

        # 更新事件名称数据
        if event_name in self.event_names_data:
            self.event_names_data[event_name]["count"] += 1
        else:
            self.event_names_data[event_name] = {"count": 1}

        self.event_names_data[event_name]["last_used"] = start_time.strftime("%Y-%m-%d %H:%M:%S")
        self.save_event_names()

        # 更新标签数据
        parsed_tags = self.parse_tags(tags)
        for tag in parsed_tags:
            if tag in self.tags_data:
                self.tags_data[tag] += 1
            else:
                self.tags_data[tag] = 1

        self.save_tags()
        self.update_filter_tag_combo()

        # 清空输入框
        self.event_entry.delete(0, tk.END)

        # 隐藏下拉列表
        self.hide_dropdown()

        # 更新状态栏
        self.status_bar.config(text=f"开始计时: {event_name}")

        # 更新系统托盘图标提示
        self.update_tray_tooltip()

        # 添加计时器显示
        self.add_timer_display(event_name, start_time, parsed_tags)

        # 如果不是来自模板的事件，重置模板相关变量
        if self.current_template:
            # 检查是否还有模板事件需要执行
            if self.template_event_index >= len(self.template_events_queue):
                # 所有模板事件都完成了
                self.status_bar.config(text=f"模板 '{self.current_template['name']}' 的所有事件已完成")
                self.current_template = None
                self.template_event_index = 0
                self.template_events_queue = []

    def add_timer_display(self, event_name, start_time, tags):
        """为事件添加计时器显示"""
        timer_frame = tk.Frame(self.scrollable_frame, bg=self.bg_color)
        timer_frame.pack(fill=tk.X, pady=2)

        name_label = tk.Label(
            timer_frame,
            text=f"{event_name}:",
            bg=self.bg_color,
            fg=self.accent_color,
            width=25,
            anchor="w"
        )
        name_label.pack(side=tk.LEFT, padx=(0, 10))

        if tags:
            tag_text = " ".join([f"#{tag}" for tag in tags[:2]])
            if len(tags) > 2:
                tag_text += f" +{len(tags) - 2}"
            tag_label = tk.Label(
                timer_frame,
                text=tag_text,
                bg=self.bg_color,
                fg=self.tag_color,
                width=15,
                anchor="w"
            )
            tag_label.pack(side=tk.LEFT, padx=(0, 10))

        timer_label = tk.Label(
            timer_frame,
            text="0h00m",
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 10),
            width=15
        )
        timer_label.pack(side=tk.LEFT, padx=(0, 10))

        stop_button = tk.Button(
            timer_frame,
            text="停止",
            command=lambda e=event_name: self.stop_single_timing(e),
            bg=self.stop_color,
            fg="white",
            width=6,
            activebackground=self.stop_color,
            activeforeground="white",
            relief="flat",
            cursor="hand2"
        )
        stop_button.pack(side=tk.LEFT)

        self.timer_widgets[event_name] = {
            "frame": timer_frame,
            "label": timer_label,
            "button": stop_button,
            "start_time": start_time
        }

        self.update_single_timer_display(event_name)

    def update_single_timer_display(self, event_name):
        """更新单个计时器显示"""
        if event_name in self.timer_widgets:
            widget = self.timer_widgets[event_name]
            start_time = widget["start_time"]
            current_time = datetime.now()
            duration = current_time - start_time

            duration_str = self.format_duration(duration.total_seconds())
            widget["label"].config(text=duration_str)

            self.root.after(1000, lambda: self.update_single_timer_display(event_name))

    def stop_single_timing(self, event_name):
        """停止单个事件的计时"""
        if event_name not in self.current_events:
            return

        event_data = self.current_events[event_name]
        start_time = event_data["start_time"]
        tags = event_data.get("tags", "")
        from_template = event_data.get("from_template", False)
        end_time = datetime.now()
        duration = end_time - start_time

        duration_str = self.format_duration(duration.total_seconds())

        event_record = {
            "event": event_name,
            "tags": tags,
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": duration_str,
            "duration_seconds": int(duration.total_seconds())
        }

        self.events_history.append(event_record)
        self.save_history()

        del self.current_events[event_name]

        if event_name in self.timer_widgets:
            self.timer_widgets[event_name]["frame"].destroy()
            del self.timer_widgets[event_name]

        self.update_history_display()
        self.status_bar.config(text=f"事件完成: {event_name} - 持续时间: {duration_str}")
        self.update_tray_tooltip()

        # 如果事件来自模板，开始下一个模板事件
        if from_template and self.current_template:
            self.root.after(500, self.start_next_template_event)

    def update_time_display(self):
        """更新当前时间显示"""
        now = datetime.now()
        self.root.title(f"事件计时器-z17code - {now.strftime('%H:%M')} - 进行中: {len(self.current_events)}")
        self.root.after(1000, self.update_time_display)

    def update_history_display(self):
        """更新历史记录显示"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        selected_tag = self.filter_tag_var.get()
        selected_date = self.filter_date_var.get()

        filtered_history = []
        for event in self.events_history:
            if selected_tag != "所有标签":
                event_tags = self.parse_tags(event.get("tags", ""))
                if selected_tag not in event_tags:
                    continue

            if selected_date != "所有日期":
                event_date = datetime.strptime(event["start_time"], "%Y-%m-%d %H:%M:%S").date()
                today = datetime.now().date()

                if selected_date == "今天":
                    if event_date != today:
                        continue
                elif selected_date == "本周":
                    monday = today - timedelta(days=today.weekday())
                    if event_date < monday:
                        continue
                elif selected_date == "本月":
                    if event_date.year != today.year or event_date.month != today.month:
                        continue
                elif selected_date == "最近7天":
                    week_ago = today - timedelta(days=7)
                    if event_date < week_ago:
                        continue
                elif selected_date == "最近30天":
                    month_ago = today - timedelta(days=30)
                    if event_date < month_ago:
                        continue

            filtered_history.append(event)

        sorted_history = sorted(filtered_history,
                                key=lambda x: x.get("duration_seconds", 0),
                                reverse=True)

        for event in sorted_history:
            start_time_display = self.format_time_for_display(event["start_time"])
            end_time_display = self.format_time_for_display(event["end_time"])
            tags_display = event.get("tags", "")

            self.history_tree.insert(
                "",
                0,
                values=(
                    event["event"],
                    tags_display,
                    start_time_display,
                    end_time_display,
                    event["duration"]
                )
            )

    def load_history(self):
        """从文件加载历史记录"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.events_history = json.load(f)
            except:
                self.events_history = []
        else:
            self.events_history = []

    def load_event_names(self):
        """加载事件名称数据"""
        if os.path.exists(self.names_file):
            try:
                with open(self.names_file, 'r', encoding='utf-8') as f:
                    self.event_names_data = json.load(f)
            except:
                self.event_names_data = {}
        else:
            self.event_names_data = {}

    def load_templates(self):
        """加载事件模板"""
        if os.path.exists(self.templates_file):
            try:
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    self.event_templates = json.load(f)
            except:
                self.event_templates = []
        else:
            self.event_templates = []

    def load_tags(self):
        """加载标签数据"""
        if os.path.exists(self.tags_file):
            try:
                with open(self.tags_file, 'r', encoding='utf-8') as f:
                    self.tags_data = json.load(f)
            except:
                self.tags_data = {}
        else:
            self.tags_data = {}

        if not self.tags_data and self.events_history:
            for event in self.events_history:
                if "tags" in event:
                    tags = self.parse_tags(event["tags"])
                    for tag in tags:
                        if tag in self.tags_data:
                            self.tags_data[tag] += 1
                        else:
                            self.tags_data[tag] = 1

            self.save_tags()

    def save_history(self):
        """保存历史记录到文件"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.events_history, f, ensure_ascii=False, indent=2)
        except:
            messagebox.showerror("保存错误", "无法保存历史记录到文件")

    def save_event_names(self):
        """保存事件名称数据到文件"""
        try:
            with open(self.names_file, 'w', encoding='utf-8') as f:
                json.dump(self.event_names_data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def save_templates(self):
        """保存事件模板到文件"""
        try:
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(self.event_templates, f, ensure_ascii=False, indent=2)
        except:
            messagebox.showerror("保存错误", "无法保存事件模板到文件")

    def save_tags(self):
        """保存标签数据到文件"""
        try:
            with open(self.tags_file, 'w', encoding='utf-8') as f:
                json.dump(self.tags_data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def clear_history(self):
        """清空历史记录"""
        if not self.events_history:
            messagebox.showinfo("提示", "历史记录已经是空的")
            return

        if messagebox.askyesno("确认", "确定要清空所有历史记录吗？此操作不可撤销。"):
            self.events_history = []
            self.update_history_display()
            self.save_history()
            self.status_bar.config(text="历史记录已清空")

    # ===== 系统托盘功能 =====

    def create_system_tray(self):
        """创建系统托盘图标"""
        try:
            icon_image = self.load_tray_icon()

            menu = (
                pystray.MenuItem('显示主窗口', self.show_main_window),
                pystray.MenuItem('显示简易窗口', self.show_simple_window),
                pystray.MenuItem('---', None, enabled=False),
                pystray.MenuItem('退出', self.quit_app)
            )

            self.tray_icon = pystray.Icon(
                "event_timer",
                icon_image,
                "事件计时器",
                menu
            )

            threading.Thread(target=self.run_tray_icon, daemon=True).start()

        except Exception as e:
            print(f"创建系统托盘失败: {e}")

    def load_tray_icon(self):
        """加载托盘图标"""
        icon_paths = [
            "timer_icon.ico",
            "icon.ico",
            "resources/timer_icon.ico",
            "resources/icon.ico"
        ]

        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    image = Image.open(icon_path)
                    return image
                except:
                    continue

        return self.create_tray_image()

    def create_tray_image(self):
        """创建托盘图标图像"""
        image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        if self.is_dark_mode:
            icon_color = "#ffffff"
        else:
            icon_color = "#2196F3"

        draw.ellipse([12, 12, 52, 52], outline=icon_color, width=3)
        draw.line([32, 32, 32, 20], fill=icon_color, width=3)
        draw.line([32, 32, 44, 32], fill=icon_color, width=3)

        return image

    def run_tray_icon(self):
        """运行托盘图标"""
        if self.tray_icon:
            self.tray_icon.run()

    def show_main_window(self, icon=None, item=None):
        """显示主窗口"""
        if self.is_hidden_to_tray:
            self.show_from_tray()
        else:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

    def show_simple_window(self, icon=None, item=None):
        """显示简易窗口"""
        if self.current_events:
            self.simple_window.create_window()
        else:
            messagebox.showinfo("提示", "当前没有正在计时的事件")

    def toggle_window_visibility(self, icon=None, item=None):
        """切换窗口显示/隐藏（兼容旧代码）"""
        if self.is_hidden_to_tray:
            self.show_from_tray()
        else:
            self.hide_to_tray()

    def hide_to_tray(self):
        """隐藏窗口到系统托盘"""
        self.hide_dropdown()

        self.is_hidden_to_tray = True
        self.root.withdraw()

        # 如果有计时事件，显示简易窗口
        if self.current_events:
            self.simple_window.create_window()

        self.update_tray_tooltip()
        self.status_bar.config(text="程序已最小化到系统托盘，右键点击托盘图标选择'显示/隐藏窗口'")

    def show_from_tray(self):
        """从系统托盘显示窗口"""
        self.is_hidden_to_tray = False
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

        # 关闭简易窗口
        if self.simple_window.window:
            self.simple_window.window.destroy()
            self.simple_window.window = None

        self.update_tray_tooltip()

        if self.current_events:
            event_count = len(self.current_events)
            self.status_bar.config(text=f"正在计时 {event_count} 个事件")
        else:
            self.status_bar.config(text="就绪")

    def update_tray_tooltip(self):
        """更新系统托盘图标提示"""
        if self.tray_icon:
            tooltip = "事件计时器"
            if self.current_events:
                event_count = len(self.current_events)
                tooltip += f" - {event_count}个事件进行中"
            if self.is_hidden_to_tray:
                tooltip += " (已最小化到托盘)"
            self.tray_icon.title = tooltip

    def quit_app(self, icon=None, item=None):
        """退出应用程序"""
        self.save_history()
        self.save_event_names()
        self.save_templates()
        self.save_tags()
        self.save_settings()

        self.notification_active = False

        if self.tray_icon:
            self.tray_icon.stop()

        self.root.quit()
        self.root.destroy()
        os._exit(0)


def main():
    root = tk.Tk()
    app = EventTimerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()