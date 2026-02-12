import calendar
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
    """简易计时窗口（支持置顶、关闭、按钮状态）"""
    def __init__(self, main_app):
        self.main_app = main_app
        self.window = None
        self.topmost_var = tk.BooleanVar(value=True)

    def create_window(self):
        if self.window is not None:
            try:
                self.window.destroy()
            except:
                pass
            self.window = None

        self.window = tk.Toplevel()
        self.window.title("事件计时器 - 简易模式")
        self.window.geometry("340x260")
        self.window.configure(bg=self.main_app.bg_color)
        self.window.attributes("-topmost", self.topmost_var.get())
        self.window.protocol('WM_DELETE_WINDOW', self.on_close)
        self.main_app.center_window(self.window)

        title_frame = tk.Frame(self.window, bg=self.main_app.bg_color)
        title_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(title_frame, text="正在计时的事件", bg=self.main_app.bg_color,
                 fg=self.main_app.accent_color, font=("Arial", 12, "bold")).pack(side=tk.LEFT)

        topmost_cb = tk.Checkbutton(title_frame, text="置顶", variable=self.topmost_var,
                                    command=self.toggle_topmost, bg=self.main_app.bg_color,
                                    fg=self.main_app.fg_color, selectcolor=self.main_app.bg_color,
                                    activebackground=self.main_app.bg_color)
        topmost_cb.pack(side=tk.RIGHT)

        self.events_frame = tk.Frame(self.window, bg=self.main_app.bg_color)
        self.events_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.update_events_list()

        btn_frame = tk.Frame(self.window, bg=self.main_app.bg_color)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(btn_frame, text="显示主窗口", command=self.show_main_window,
                  bg=self.main_app.accent_color, fg="white", width=12, relief="flat").pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="停止所有", command=self.stop_all_events,
                  bg=self.main_app.stop_color, fg="white", width=12, relief="flat").pack(side=tk.LEFT, padx=2)

        self.update_timer()
        return self.window

    def toggle_topmost(self):
        if self.window:
            self.window.attributes("-topmost", self.topmost_var.get())

    def update_events_list(self):
        for widget in self.events_frame.winfo_children():
            widget.destroy()

        if not self.main_app.current_events:
            tk.Label(self.events_frame, text="当前没有正在计时的事件",
                     bg=self.main_app.bg_color, fg=self.main_app.fg_color).pack(pady=20)
            return

        canvas = tk.Canvas(self.events_frame, bg=self.main_app.bg_color, height=150)
        scrollbar = tk.Scrollbar(self.events_frame, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=self.main_app.bg_color)
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for name, data in self.main_app.current_events.items():
            frame = tk.Frame(scrollable, bg=self.main_app.bg_color)
            frame.pack(fill=tk.X, pady=2)

            tk.Label(frame, text=f"{name[:15]}{'...' if len(name)>15 else ''}:",
                     bg=self.main_app.bg_color, fg=self.main_app.accent_color,
                     width=18, anchor="w").pack(side=tk.LEFT)

            dur = self.main_app.get_event_display_duration(name)
            time_label = tk.Label(frame, text=dur, bg=self.main_app.bg_color,
                                  fg=self.main_app.fg_color, width=8)
            time_label.pack(side=tk.LEFT, padx=(0,5))
            data["simple_time_label"] = time_label

            # 暂停/恢复按钮（统一根据主程序模式）
            if data["status"] == "running":
                pause_text = "暂停"
                pause_cmd = lambda n=name: self.main_app.pause_event_by_mode(n)
                pause_color = self.main_app.clear_color
            elif data["status"] in ("paused_a", "paused_b"):
                pause_text = "恢复"
                pause_cmd = lambda n=name: self.main_app.resume_event_by_mode(n)
                pause_color = self.main_app.start_color
            else:
                pause_text = "暂停"
                pause_cmd = None
                pause_color = self.main_app.button_bg

            pause_btn = tk.Button(frame, text=pause_text, command=pause_cmd,
                                  bg=pause_color, fg="white", width=5, relief="flat")
            pause_btn.pack(side=tk.RIGHT, padx=2)

            stop_btn = tk.Button(frame, text="停止",
                                 command=lambda n=name: self.main_app.stop_single_timing(n),
                                 bg=self.main_app.stop_color, fg="white", width=4, relief="flat")
            stop_btn.pack(side=tk.RIGHT, padx=2)

    def update_timer(self):
        if self.window and self.window.winfo_exists():
            for name, data in self.main_app.current_events.items():
                if "simple_time_label" in data:
                    dur = self.main_app.get_event_display_duration(name)
                    data["simple_time_label"].config(text=dur)
            self.window.after(1000, self.update_timer)

    def stop_all_events(self):
        for name in list(self.main_app.current_events.keys()):
            self.main_app.stop_single_timing(name)
        self.update_events_list()

    def show_main_window(self):
        if self.window:
            self.window.destroy()
            self.window = None
        self.main_app.show_from_tray()

    def on_close(self):
        if self.window:
            self.window.destroy()
            self.window = None


class EventTimerApp:
    def __init__(self, root):
        self.root = root
        self.is_dark_mode = self.detect_system_theme()

        if getattr(sys, 'frozen', False):
            program_dir = os.path.dirname(sys.executable)
        else:
            program_dir = os.path.dirname(os.path.abspath(__file__))

        config_dir = os.path.join(program_dir, "config")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        self.setup_theme()

        # ---------- 数据变量 ----------
        self.current_events = {}
        self.events_history = []
        self.event_names_data = {}
        self.event_templates = []
        self.tags_data = {}

        self.config_dir = config_dir
        self.data_file = os.path.join(config_dir, "events_history.json")
        self.names_file = os.path.join(config_dir, "event_names.json")
        self.templates_file = os.path.join(config_dir, "event_templates.json")
        self.tags_file = os.path.join(config_dir, "event_tags.json")
        self.settings_file = os.path.join(config_dir, "settings.json")

        self.tray_icon = None
        self.is_hidden_to_tray = False
        self.dropdown_visible = False
        self.notification_thread = None
        self.notification_active = False
        self.notification_interval = 30
        self.auto_stop_on_notification = False

        # 暂停模式（A 或 B）
        self.pause_mode = 'A'

        # 模板执行状态
        self.current_template = None
        self.template_event_index = 0
        self.template_events_queue = []

        self.simple_window = SimpleTimerWindow(self)

        # 历史记录显示设置
        self.show_full_datetime = False
        self.selected_tags_filter = set()   # 标签多选筛选

        # 加载数据
        self.load_history()
        self.load_event_names()
        self.load_templates()
        self.load_tags()
        self.load_settings()

        # 创建UI
        self.create_widgets()
        self.update_time_display()
        self.root.protocol('WM_DELETE_WINDOW', self.hide_to_tray)
        self.create_system_tray()
        self.root.after(100, self.ensure_window_visibility)
        self.bind_events()
        self.start_notification_checker()

    # ---------- 工具方法 ----------
    def ensure_window_visibility(self):
        if platform.system() == "Windows":
            hwnd = self.root.winfo_id()
            ctypes.windll.user32.ShowWindow(hwnd, 1)

    def detect_system_theme(self):
        try:
            if platform.system() == "Windows":
                import winreg
                reg = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(reg, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return val == 0
            elif platform.system() == "Darwin":
                import subprocess
                res = subprocess.run(['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                                     capture_output=True, text=True)
                return "Dark" in res.stdout
        except:
            pass
        return False

    def setup_theme(self):
        if self.is_dark_mode:
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

        self.root.configure(bg=self.bg_color)
        self.root.title("事件计时器")
        self.root.geometry("1000x700")

    def center_window(self, win):
        """将窗口居中显示"""
        win.update_idletasks()
        w = win.winfo_width()
        h = win.winfo_height()
        x = (win.winfo_screenwidth() // 2) - (w // 2)
        y = (win.winfo_screenheight() // 2) - (h // 2)
        win.geometry(f'{w}x{h}+{x}+{y}')

    def create_default_icon(self):
        try:
            img = Image.new('RGB', (32, 32), color=self.accent_color)
            draw = ImageDraw.Draw(img)
            draw.ellipse([4, 4, 28, 28], outline='white', width=2)
            draw.line([16, 16, 16, 10], fill='white', width=2)
            draw.line([16, 16, 22, 16], fill='white', width=2)
            temp = "temp_icon.ico"
            img.save(temp)
            self.root.iconbitmap(temp)
        except:
            pass
    # ---------- UI 构建 ----------
    def create_widgets(self):
        main = tk.Frame(self.root, bg=self.bg_color)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 顶部控制栏
        top = tk.Frame(main, bg=self.bg_color)
        top.pack(fill=tk.X, pady=(0,10))

        # 左：事件名称、标签、开始
        left = tk.Frame(top, bg=self.bg_color)
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(left, text="事件名称:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT)
        self.entry_container = tk.Frame(left, bg=self.bg_color)
        self.entry_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5,5))
        self.event_entry = tk.Entry(self.entry_container, width=30, bg=self.entry_bg, fg=self.entry_fg,
                                    insertbackground=self.fg_color, relief="flat")
        self.event_entry.pack(fill=tk.X, expand=True)

        tag_frame = tk.Frame(left, bg=self.bg_color)
        tag_frame.pack(side=tk.LEFT, padx=(5,5))
        tk.Label(tag_frame, text="标签:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT)
        self.tag_entry = tk.Entry(tag_frame, width=15, bg=self.entry_bg, fg=self.entry_fg, relief="flat")
        self.tag_entry.pack(side=tk.LEFT, padx=(2,2))
        # 一键清空标签
        tk.Button(tag_frame, text="×", command=self.clear_tag_entry,
                  bg=self.stop_color, fg="white", width=2, relief="flat",
                  activebackground=self.stop_color).pack(side=tk.LEFT, padx=(2,0))

        self.start_btn = tk.Button(left, text="开始计时", command=self.start_timing,
                                   bg=self.start_color, fg="white", width=8, relief="flat")
        self.start_btn.pack(side=tk.LEFT, padx=(5,0))

        # 右：模板、标签管理、模板选择、窗口置顶
        right = tk.Frame(top, bg=self.bg_color)
        right.pack(side=tk.RIGHT)

        tk.Button(right, text="模板管理", command=self.show_template_manager,
                  bg=self.template_color, fg="white", width=10, relief="flat").pack(side=tk.LEFT, padx=2)
        tk.Button(right, text="标签管理", command=self.show_tag_manager,
                  bg=self.tag_color, fg="white", width=10, relief="flat").pack(side=tk.LEFT, padx=2)

        self.template_combo = ttk.Combobox(right, values=[t["name"] for t in self.event_templates],
                                           width=12, state="readonly")
        self.template_combo.set("选择模板")
        self.template_combo.pack(side=tk.LEFT, padx=2)
        self.template_combo.bind("<<ComboboxSelected>>", self.on_template_selected)

        self.topmost_var = tk.BooleanVar(value=False)
        tk.Checkbutton(right, text="窗口置顶", variable=self.topmost_var,
                       command=self.toggle_topmost, bg=self.bg_color, fg=self.fg_color,
                       selectcolor=self.bg_color).pack(side=tk.LEFT, padx=2)

        # ---------- 历史事件补全下拉框 ----------
        self.dropdown_frame = tk.Frame(self.root, bg=self.dropdown_border, relief="solid", borderwidth=1)
        self.dropdown_frame.place_forget()
        self.dropdown_listbox = tk.Listbox(self.dropdown_frame, bg=self.dropdown_bg, fg=self.dropdown_fg,
                                           selectbackground=self.dropdown_sel_bg, height=8, relief="flat",
                                           activestyle="none", exportselection=False, highlightthickness=0)
        dscroll = tk.Scrollbar(self.dropdown_frame, orient="vertical", bg=self.dropdown_bg)
        self.dropdown_listbox.config(yscrollcommand=dscroll.set)
        dscroll.config(command=self.dropdown_listbox.yview)
        self.dropdown_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # ---------- 当前计时事件区域 ----------
        cur_frame = tk.LabelFrame(main, text="当前正在计时的事件", bg=self.bg_color, fg=self.fg_color)
        cur_frame.pack(fill=tk.X, pady=(0,10))

        canvas = tk.Canvas(cur_frame, bg=self.bg_color, height=150)
        scrollbar = tk.Scrollbar(cur_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=self.bg_color)
        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.timer_widgets = {}

        # ---------- 历史记录区域 ----------
        hist_frame = tk.LabelFrame(main, text="历史记录", bg=self.bg_color, fg=self.fg_color)
        hist_frame.pack(fill=tk.BOTH, expand=True)

        # ---------- 历史记录筛选栏（修复日期输入框 + 日历按钮）----------
        filter_bar = tk.Frame(hist_frame, bg=self.bg_color)
        filter_bar.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(filter_bar, text="筛选:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT)

        # 标签多选筛选按钮
        self.tag_filter_btn = tk.Button(filter_bar, text="标签筛选", command=self.show_tag_filter_dialog,
                                        bg=self.tag_color, fg="white", relief="flat", width=10)
        self.tag_filter_btn.pack(side=tk.LEFT, padx=5)

        # 当前筛选标签显示（固定宽度，不扩展）
        self.filter_tags_label = tk.Label(filter_bar, text="", bg=self.bg_color, fg=self.tag_color,
                                          font=("Arial", 9), anchor="w", width=20)
        self.filter_tags_label.pack(side=tk.LEFT, padx=(10, 0))

        # ---------- 日期筛选区域（输入框 + 日历按钮）----------
        date_frame = tk.Frame(filter_bar, bg=self.bg_color)
        date_frame.pack(side=tk.LEFT, padx=(10, 2))

        tk.Label(date_frame, text="日期:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT)

        self.specific_date_var = tk.StringVar()
        self.specific_date_entry = tk.Entry(
            date_frame,
            textvariable=self.specific_date_var,
            width=12,
            bg=self.entry_bg,
            fg=self.entry_fg,
            relief="sunken",
            bd=2,
            state=tk.NORMAL,
            takefocus=1
        )
        self.specific_date_entry.pack(side=tk.LEFT, padx=2)
        self.specific_date_entry.bind("<Return>", lambda e: self.apply_specific_date_filter())
        self.specific_date_entry.bind("<FocusIn>", lambda e: self.specific_date_entry.select_range(0, tk.END))
        self.specific_date_entry.config(state=tk.NORMAL)  # 强制启用

        # 📅 日历选择按钮
        calendar_btn = tk.Button(
            date_frame,
            text="📅",
            command=self.show_calendar,
            bg=self.accent_color,
            fg="white",
            width=3,
            relief="flat"
        )
        calendar_btn.pack(side=tk.LEFT, padx=2)

        # 确定按钮
        tk.Button(filter_bar, text="确定", command=self.apply_specific_date_filter,
                  bg=self.accent_color, fg="white", relief="flat", width=5).pack(side=tk.LEFT, padx=2)
        # 重置按钮
        tk.Button(filter_bar, text="重置", command=self.reset_filters,
                  bg=self.button_bg, fg=self.button_fg, relief="flat", width=5).pack(side=tk.LEFT, padx=2)

        # Treeview
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", background=self.tree_bg, foreground=self.tree_fg,
                        fieldbackground=self.tree_bg, borderwidth=0)
        style.configure("Treeview.Heading", background=self.button_bg, foreground=self.fg_color, relief="flat")
        style.map('Treeview', background=[('selected', self.tree_sel_bg)])

        cols = ("事件名称", "标签", "开始时间", "结束时间", "持续时间")
        self.history_tree = ttk.Treeview(hist_frame, columns=cols, show="headings", style="Treeview")
        for col in cols:
            self.history_tree.heading(col, text=col, anchor="center")
            if col == "事件名称":
                self.history_tree.column(col, width=200, anchor="center")
            elif col == "标签":
                self.history_tree.column(col, width=120, anchor="center")
            else:
                self.history_tree.column(col, width=150, anchor="center")

        self.history_tree.heading("开始时间", command=lambda: self.toggle_datetime_format("start"))
        self.history_tree.heading("结束时间", command=lambda: self.toggle_datetime_format("end"))

        hist_scroll = ttk.Scrollbar(hist_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=hist_scroll.set)
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hist_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.create_history_context_menu()

        # 底部状态栏
        bottom = tk.Frame(main, bg=self.bg_color)
        bottom.pack(fill=tk.X, pady=(10,0))

        tk.Button(bottom, text="清空历史", command=self.clear_history,
                  bg=self.clear_color, fg="white", width=15, relief="flat").pack(side=tk.LEFT, padx=(0,10))
        tk.Button(bottom, text="设置", command=self.show_settings_window,
                  bg=self.accent_color, fg="white", width=15, relief="flat").pack(side=tk.LEFT, padx=(0,10))
        tk.Button(bottom, text="打开配置文件夹", command=self.open_config_folder,
                  bg=self.accent_color, fg="white", width=15, relief="flat").pack(side=tk.LEFT, padx=(0,10))

        self.status_bar = tk.Label(bottom, text="就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W,
                                   bg=self.button_bg, fg=self.fg_color)
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.update_history_display()

    # ---------- 标签一键清空 ----------
    def clear_tag_entry(self):
        self.tag_entry.delete(0, tk.END)

    # ---------- 日期格式切换 ----------
    def toggle_datetime_format(self, col_type):
        self.show_full_datetime = not self.show_full_datetime
        self.update_history_display()

    # ---------- 特定日期筛选 ----------
    def apply_specific_date_filter(self):
        self.update_history_display()

    # ---------- 标签多选筛选对话框 ----------
    def show_tag_filter_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("标签筛选")
        win.geometry("300x400")
        win.configure(bg=self.bg_color)
        win.transient(self.root)
        win.grab_set()
        self.center_window(win)

        tk.Label(win, text="选择要显示的标签（可多选）:", bg=self.bg_color, fg=self.fg_color).pack(pady=10)

        lb = tk.Listbox(win, selectmode=tk.MULTIPLE, bg=self.entry_bg, fg=self.entry_fg,
                        selectbackground=self.dropdown_sel_bg, height=15)
        lb.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        all_tags = sorted(self.tags_data.keys())
        for tag in all_tags:
            lb.insert(tk.END, tag)

        for i, tag in enumerate(all_tags):
            if tag in self.selected_tags_filter:
                lb.selection_set(i)

        btnf = tk.Frame(win, bg=self.bg_color)
        btnf.pack(fill=tk.X, pady=10)

        def select_all():
            lb.selection_set(0, tk.END)

        def clear_all():
            lb.selection_clear(0, tk.END)

        tk.Button(btnf, text="全选", command=select_all,
                  bg=self.button_bg, fg=self.button_fg).pack(side=tk.LEFT, padx=5)
        tk.Button(btnf, text="全不选", command=clear_all,
                  bg=self.button_bg, fg=self.button_fg).pack(side=tk.LEFT, padx=5)
        tk.Button(btnf, text="确定",
                  command=lambda: self.apply_tag_filter(lb, win),
                  bg=self.accent_color, fg="white").pack(side=tk.RIGHT, padx=5)
        tk.Button(btnf, text="取消", command=win.destroy,
                  bg=self.button_bg, fg=self.button_fg).pack(side=tk.RIGHT, padx=5)

    def apply_tag_filter(self, listbox, win):
        sel = listbox.curselection()
        self.selected_tags_filter = {listbox.get(i) for i in sel}
        win.destroy()
        if self.selected_tags_filter:
            self.filter_tags_label.config(text=f"筛选标签: {', '.join(sorted(self.selected_tags_filter))}")
        else:
            self.filter_tags_label.config(text="")
        self.update_history_display()

    # ---------- 集中设置窗口 ----------
    def show_settings_window(self):
        win = tk.Toplevel(self.root)
        win.title("设置")
        win.geometry("450x450")
        win.configure(bg=self.bg_color)
        win.transient(self.root)
        win.grab_set()
        self.center_window(win)

        tk.Label(win, text="设置", bg=self.bg_color, fg=self.accent_color,
                 font=("Arial", 14, "bold")).pack(pady=10)

        # --- 通知设置 ---
        noti_frame = tk.LabelFrame(win, text="通知设置", bg=self.bg_color, fg=self.fg_color)
        noti_frame.pack(fill=tk.X, padx=10, pady=5)

        intv_frame = tk.Frame(noti_frame, bg=self.bg_color)
        intv_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(intv_frame, text="通知间隔(分钟):", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT)
        interval_var = tk.StringVar(value=str(self.notification_interval))
        tk.Entry(intv_frame, textvariable=interval_var, width=10,
                 bg=self.entry_bg, fg=self.entry_fg).pack(side=tk.LEFT, padx=5)

        notify_enable_var = tk.BooleanVar(value=self.notification_active)
        tk.Checkbutton(noti_frame, text="启用通知提醒", variable=notify_enable_var,
                       bg=self.bg_color, fg=self.fg_color, selectcolor=self.bg_color).pack(anchor="w", padx=10)

        auto_stop_var = tk.BooleanVar(value=self.auto_stop_on_notification)
        tk.Checkbutton(noti_frame, text="通知出现时自动停止所有事件", variable=auto_stop_var,
                       bg=self.bg_color, fg=self.fg_color, selectcolor=self.bg_color).pack(anchor="w", padx=10)

        # --- 暂停模式设置 ---
        pause_frame = tk.LabelFrame(win, text="暂停模式", bg=self.bg_color, fg=self.fg_color)
        pause_frame.pack(fill=tk.X, padx=10, pady=5)

        self.pause_mode_var = tk.StringVar(value=self.pause_mode)
        tk.Radiobutton(pause_frame, text="模式A - 暂停/恢复（累计计时）", variable=self.pause_mode_var,
                       value='A', bg=self.bg_color, fg=self.fg_color, selectcolor=self.bg_color,
                       activebackground=self.bg_color).pack(anchor="w", padx=10, pady=2)
        tk.Radiobutton(pause_frame, text="模式B - 分段计时（每段记录历史）", variable=self.pause_mode_var,
                       value='B', bg=self.bg_color, fg=self.fg_color, selectcolor=self.bg_color,
                       activebackground=self.bg_color).pack(anchor="w", padx=10, pady=2)

        # --- 简易窗口设置 ---
        simple_frame = tk.LabelFrame(win, text="简易窗口", bg=self.bg_color, fg=self.fg_color)
        simple_frame.pack(fill=tk.X, padx=10, pady=5)

        simple_topmost_var = tk.BooleanVar(value=self.simple_window.topmost_var.get())
        def on_simple_topmost():
            self.simple_window.topmost_var.set(simple_topmost_var.get())
            if self.simple_window.window:
                self.simple_window.toggle_topmost()
        tk.Checkbutton(simple_frame, text="简易窗口默认置顶", variable=simple_topmost_var,
                       command=on_simple_topmost,
                       bg=self.bg_color, fg=self.fg_color, selectcolor=self.bg_color).pack(anchor="w", padx=10)

        # --- 历史记录显示 ---
        hist_frame = tk.LabelFrame(win, text="历史记录显示", bg=self.bg_color, fg=self.fg_color)
        hist_frame.pack(fill=tk.X, padx=10, pady=5)

        full_dt_var = tk.BooleanVar(value=self.show_full_datetime)
        def on_full_dt():
            self.show_full_datetime = full_dt_var.get()
            self.update_history_display()
        tk.Checkbutton(hist_frame, text="默认显示完整日期时间", variable=full_dt_var,
                       command=on_full_dt,
                       bg=self.bg_color, fg=self.fg_color, selectcolor=self.bg_color).pack(anchor="w", padx=10)

        # --- 保存按钮 ---
        def save_all():
            try:
                iv = int(interval_var.get())
                if iv < 1: iv = 1
                if iv > 480: iv = 480
                self.notification_interval = iv
            except:
                self.notification_interval = 30

            was_active = self.notification_active
            self.notification_active = notify_enable_var.get()
            self.auto_stop_on_notification = auto_stop_var.get()
            self.pause_mode = self.pause_mode_var.get()

            if self.notification_active and not was_active:
                self.start_notification_checker()
            elif not self.notification_active and was_active:
                self.notification_active = False

            self.save_settings()
            win.destroy()
            self.status_bar.config(text="设置已保存")

        tk.Button(win, text="保存", command=save_all,
                  bg=self.accent_color, fg="white", width=10, relief="flat").pack(pady=10)

    # ---------- 事件绑定 ----------
    def bind_events(self):
        self.event_entry.bind("<KeyRelease>", self.on_entry_keyrelease)
        self.event_entry.bind("<FocusIn>", self.on_entry_focus_in)
        self.event_entry.bind("<FocusOut>", self.on_entry_focus_out)
        self.event_entry.bind("<Return>", lambda e: self.start_timing())
        self.event_entry.bind("<Escape>", lambda e: self.lose_focus())
        self.tag_entry.bind("<FocusIn>", lambda e: self.hide_dropdown())
        self.dropdown_listbox.bind("<ButtonRelease-1>", self.on_dropdown_select)
        self.dropdown_listbox.bind("<Return>", self.on_dropdown_select)
        self.dropdown_listbox.bind("<Escape>", lambda e: self.hide_dropdown())
        self.dropdown_listbox.bind("<Motion>", self.on_dropdown_motion)
        self.root.bind("<Button-1>", self.global_click_handler)
        self.root.bind("<Escape>", lambda e: self.lose_focus())
        self.history_tree.bind("<Button-3>", self.show_history_context_menu)

    def lose_focus(self):
        self.root.focus_set()
        self.hide_dropdown()
        return "break"

    def global_click_handler(self, event):
        w = event.widget
        if w in (self.event_entry, self.tag_entry, self.dropdown_listbox, self.dropdown_frame):
            return
        path = []
        cur = w
        while cur:
            path.append(str(cur))
            cur = cur.master
        path_str = ' '.join(path)
        if any(x in path_str for x in ('scrollable_frame', 'history_tree', 'current_timers_frame')):
            return
        self.hide_dropdown()
        self.lose_focus()

    # ---------- 下拉框 ----------
    def on_dropdown_motion(self, event):
        idx = self.dropdown_listbox.nearest(event.y)
        self.dropdown_listbox.selection_clear(0, tk.END)
        if idx >= 0:
            self.dropdown_listbox.selection_set(idx)

    def update_dropdown_list(self):
        text = self.event_entry.get().strip()
        items = []
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
                last = data.get("last_used", "1970-01-01 00:00:00")
                try:
                    days = (datetime.now() - datetime.strptime(last, "%Y-%m-%d %H:%M:%S")).days
                    if days < 30:
                        score += (30 - days) * 5
                except:
                    pass
                if score > 0:
                    matches.append((name, score))
            matches.sort(key=lambda x: x[1], reverse=True)
            items = [m[0] for m in matches[:20]]
        else:
            if self.event_names_data:
                items = sorted(self.event_names_data.items(),
                               key=lambda x: (x[1].get("count", 0), x[1].get("last_used", "")),
                               reverse=True)[:20]
                items = [i[0] for i in items]

        self.dropdown_listbox.delete(0, tk.END)
        if items:
            for it in items:
                self.dropdown_listbox.insert(tk.END, it)
        else:
            self.dropdown_listbox.insert(tk.END, "暂无历史事件")

        if self.dropdown_listbox.size() > 0:
            self.show_dropdown()
        else:
            self.hide_dropdown()

    def show_dropdown(self):
        x = self.event_entry.winfo_rootx() - self.root.winfo_rootx()
        y = self.event_entry.winfo_rooty() - self.root.winfo_rooty() + self.event_entry.winfo_height()
        w = self.event_entry.winfo_width()
        h = min(8, self.dropdown_listbox.size()) * 20 + 4
        self.dropdown_frame.place(x=x, y=y, width=w, height=h)
        self.dropdown_frame.lift()
        self.dropdown_visible = True
        self.event_entry.focus_set()

    def hide_dropdown(self):
        self.dropdown_frame.place_forget()
        self.dropdown_visible = False
        self.dropdown_listbox.selection_clear(0, tk.END)

    def on_dropdown_select(self, event=None):
        sel = self.dropdown_listbox.curselection()
        if sel:
            txt = self.dropdown_listbox.get(sel[0])
            if txt == "暂无历史事件":
                return
            self.event_entry.delete(0, tk.END)
            self.event_entry.insert(0, txt)
            self.hide_dropdown()
            self.event_entry.focus()

    def on_entry_keyrelease(self, event):
        if event.keysym not in ('Up', 'Down', 'Left', 'Right', 'Return'):
            self.update_dropdown_list()

    def on_entry_focus_in(self, event):
        self.update_dropdown_list()

    def on_entry_focus_out(self, event):
        self.root.after(50, self.check_and_hide_dropdown)

    def check_and_hide_dropdown(self):
        if not self.event_entry.focus_get() and not self.is_mouse_over_dropdown():
            self.hide_dropdown()

    def is_mouse_over_dropdown(self):
        try:
            mx = self.root.winfo_pointerx() - self.root.winfo_rootx()
            my = self.root.winfo_pointery() - self.root.winfo_rooty()
            dx = self.dropdown_frame.winfo_x()
            dy = self.dropdown_frame.winfo_y()
            dw = self.dropdown_frame.winfo_width()
            dh = self.dropdown_frame.winfo_height()
            return dx <= mx <= dx+dw and dy <= my <= dy+dh
        except:
            return False

    def toggle_topmost(self):
        self.root.attributes("-topmost", self.topmost_var.get())

    # ---------- 标签系统 ----------
    def parse_tags(self, tag_str):
        if not tag_str:
            return []
        tags = set()
        for part in tag_str.split(','):
            for sub in part.split():
                t = sub.strip()
                if t:
                    if t.startswith('#'):
                        t = t[1:]
                    tags.add(t)
        return list(tags)

    def show_tag_manager(self):
        """标签管理器（多选、批量添加）"""
        win = tk.Toplevel(self.root)
        win.title("标签管理")
        win.geometry("450x400")
        win.configure(bg=self.bg_color)
        win.transient(self.root)
        win.grab_set()
        self.center_window(win)

        list_frame = tk.Frame(win, bg=self.bg_color)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(list_frame, text="标签列表（可多选，双击或点击按钮添加到输入框）:",
                 bg=self.bg_color, fg=self.fg_color).pack(anchor="w")

        lb = tk.Listbox(list_frame, selectmode=tk.MULTIPLE,
                        bg=self.entry_bg, fg=self.entry_fg,
                        selectbackground=self.dropdown_sel_bg,
                        selectforeground="white", height=12)
        lb.pack(fill=tk.BOTH, expand=True, pady=5)

        for tag, cnt in sorted(self.tags_data.items(), key=lambda x: x[1], reverse=True):
            lb.insert(tk.END, f"{tag} ({cnt}次)")

        def on_double(event):
            sel = lb.curselection()
            if not sel:
                return
            selected = []
            for idx in sel:
                full = lb.get(idx)
                tag_name = full.split(' (')[0]
                selected.append(tag_name)
            current = self.tag_entry.get().strip()
            new = []
            if current:
                existing = [t.strip('#') for t in current.replace(',', ' ').split()]
                new.extend(existing)
            new.extend(selected)
            new = list(set(new))
            formatted = ", ".join([f"#{t}" for t in new])
            self.tag_entry.delete(0, tk.END)
            self.tag_entry.insert(0, formatted)
            self.status_bar.config(text=f"已添加 {len(selected)} 个标签")
            win.destroy()

        lb.bind("<Double-Button-1>", on_double)

        btn_frame = tk.Frame(win, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        def add_selected():
            sel = lb.curselection()
            if not sel:
                messagebox.showwarning("提示", "请至少选择一个标签")
                return
            selected = []
            for idx in sel:
                full = lb.get(idx)
                tag_name = full.split(' (')[0]
                selected.append(tag_name)
            current = self.tag_entry.get().strip()
            new = []
            if current:
                existing = [t.strip('#') for t in current.replace(',', ' ').split()]
                new.extend(existing)
            new.extend(selected)
            new = list(set(new))
            formatted = ", ".join([f"#{t}" for t in new])
            self.tag_entry.delete(0, tk.END)
            self.tag_entry.insert(0, formatted)
            self.status_bar.config(text=f"已添加 {len(selected)} 个标签")
            win.destroy()

        tk.Button(btn_frame, text="添加到输入框", command=add_selected,
                  bg=self.tag_color, fg="white", width=15, relief="flat").pack(side=tk.LEFT, padx=5)

        add_frame = tk.Frame(btn_frame, bg=self.bg_color)
        add_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(add_frame, text="添加标签:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT)
        new_entry = tk.Entry(add_frame, bg=self.entry_bg, fg=self.entry_fg, width=15)
        new_entry.pack(side=tk.LEFT, padx=5)

        def add_tag():
            t = new_entry.get().strip()
            if t:
                if t not in self.tags_data:
                    self.tags_data[t] = 0
                else:
                    self.tags_data[t] += 1
                self.save_tags()
                lb.delete(0, tk.END)
                for tag, cnt in sorted(self.tags_data.items(), key=lambda x: x[1], reverse=True):
                    lb.insert(tk.END, f"{tag} ({cnt}次)")
                new_entry.delete(0, tk.END)
                self.status_bar.config(text=f"已添加标签: {t}")

        tk.Button(add_frame, text="添加", command=add_tag,
                  bg=self.start_color, fg="white", width=6, relief="flat").pack(side=tk.LEFT)

        def del_tag():
            sel = lb.curselection()
            if not sel:
                messagebox.showwarning("提示", "请先选择要删除的标签")
                return
            to_del = []
            for idx in sel:
                full = lb.get(idx)
                tag = full.split(' (')[0]
                to_del.append(tag)
            if messagebox.askyesno("确认", f"删除选中的 {len(to_del)} 个标签？"):
                for tag in to_del:
                    if tag in self.tags_data:
                        del self.tags_data[tag]
                self.save_tags()
                lb.delete(0, tk.END)
                for tag, cnt in sorted(self.tags_data.items(), key=lambda x: x[1], reverse=True):
                    lb.insert(tk.END, f"{tag} ({cnt}次)")
                self.status_bar.config(text=f"已删除 {len(to_del)} 个标签")

        tk.Button(btn_frame, text="删除选中", command=del_tag,
                  bg=self.stop_color, fg="white", width=10, relief="flat").pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="关闭", command=win.destroy,
                  bg=self.button_bg, fg=self.button_fg, width=8, relief="flat").pack(side=tk.RIGHT)

    def update_filter_tag_combo(self):
        # 保留空方法，兼容旧调用
        pass

    # ---------- 核心计时逻辑 ----------
    def start_timing(self):
        name = self.event_entry.get().strip()
        if not name:
            messagebox.showwarning("输入错误", "请输入事件名称")
            return
        if name in self.current_events:
            messagebox.showwarning("事件已存在", f"事件 '{name}' 已在计时中")
            self.event_entry.delete(0, tk.END)
            return

        start = datetime.now()
        tags = self.tag_entry.get().strip()

        self.current_events[name] = {
            "start_time": start,
            "original_start_time": start,
            "tags": tags,
            "from_template": False,
            "status": "running",
            "accumulated_seconds": 0,
            "paused_time": None
        }

        if name in self.event_names_data:
            self.event_names_data[name]["count"] += 1
        else:
            self.event_names_data[name] = {"count": 1}
        self.event_names_data[name]["last_used"] = start.strftime("%Y-%m-%d %H:%M:%S")
        self.save_event_names()

        parsed = self.parse_tags(tags)
        for t in parsed:
            self.tags_data[t] = self.tags_data.get(t, 0) + 1
        self.save_tags()

        self.event_entry.delete(0, tk.END)
        self.hide_dropdown()
        self.status_bar.config(text=f"开始计时: {name}")
        self.update_tray_tooltip()
        self.add_timer_display(name, start, parsed)

        if self.current_template and self.template_event_index >= len(self.template_events_queue):
            self.current_template = None
            self.template_event_index = 0
            self.template_events_queue = []

    def start_timing_from_template(self):
        name = self.event_entry.get().strip()
        if not name or name in self.current_events:
            return
        start = datetime.now()
        tags = self.tag_entry.get().strip()
        self.current_events[name] = {
            "start_time": start,
            "original_start_time": start,
            "tags": tags,
            "from_template": True,
            "status": "running",
            "accumulated_seconds": 0,
            "paused_time": None
        }
        if name in self.event_names_data:
            self.event_names_data[name]["count"] += 1
        else:
            self.event_names_data[name] = {"count": 1}
        self.event_names_data[name]["last_used"] = start.strftime("%Y-%m-%d %H:%M:%S")
        self.save_event_names()
        parsed = self.parse_tags(tags)
        for t in parsed:
            self.tags_data[t] = self.tags_data.get(t, 0) + 1
        self.save_tags()
        self.event_entry.delete(0, tk.END)
        self.hide_dropdown()
        self.add_timer_display(name, start, parsed)
        self.update_tray_tooltip()

    def add_timer_display(self, name, start, tags):
        frame = tk.Frame(self.scrollable_frame, bg=self.bg_color)
        frame.pack(fill=tk.X, pady=2)

        tk.Label(frame, text=f"{name}:", bg=self.bg_color, fg=self.accent_color,
                 width=25, anchor="w").pack(side=tk.LEFT, padx=(0,5))

        if tags:
            tag_text = " ".join([f"#{t}" for t in tags[:2]])
            if len(tags) > 2:
                tag_text += f" +{len(tags)-2}"
            tk.Label(frame, text=tag_text, bg=self.bg_color, fg=self.tag_color,
                     width=15, anchor="w").pack(side=tk.LEFT, padx=(0,5))

        timer_label = tk.Label(frame, text="0h00m", bg=self.bg_color, fg=self.fg_color,
                               font=("Arial", 10), width=12)
        timer_label.pack(side=tk.LEFT, padx=(0,5))

        # 统一暂停按钮（根据模式）
        pause_btn = tk.Button(frame, text="暂停",
                              command=lambda n=name: self.pause_event_by_mode(n),
                              bg=self.clear_color, fg="white", width=6, relief="flat")
        pause_btn.pack(side=tk.RIGHT, padx=2)

        stop_btn = tk.Button(frame, text="停止",
                             command=lambda n=name: self.stop_single_timing(n),
                             bg=self.stop_color, fg="white", width=5, relief="flat")
        stop_btn.pack(side=tk.RIGHT, padx=2)

        self.timer_widgets[name] = {
            "frame": frame,
            "label": timer_label,
            "pause_btn": pause_btn,
            "stop": stop_btn,
            "start_time": start
        }
        self.update_single_timer_display(name)

    def update_single_timer_display(self, name):
        if name not in self.timer_widgets or name not in self.current_events:
            return
        w = self.timer_widgets[name]
        d = self.current_events[name]

        dur = self.get_event_display_duration(name)
        w["label"].config(text=dur)

        if d["status"] == "running":
            w["pause_btn"].config(text="暂停", command=lambda n=name: self.pause_event_by_mode(n),
                                  bg=self.clear_color, state=tk.NORMAL)
            w["stop"].config(state=tk.NORMAL)
        elif d["status"] in ("paused_a", "paused_b"):
            w["pause_btn"].config(text="恢复", command=lambda n=name: self.resume_event_by_mode(n),
                                  bg=self.start_color, state=tk.NORMAL)
            w["stop"].config(state=tk.NORMAL)

        self.root.after(1000, lambda: self.update_single_timer_display(name))

    def get_event_display_duration(self, name):
        if name not in self.current_events:
            return "0h00m"
        d = self.current_events[name]
        if d["status"] == "running":
            now = datetime.now()
            el = (now - d["start_time"]).total_seconds()
            total = d["accumulated_seconds"] + el
        else:
            total = d["accumulated_seconds"]
        return self.format_duration(total)

    # ---------- 暂停模式统一接口 ----------
    def pause_event_by_mode(self, name):
        if self.pause_mode == 'A':
            self.pause_event_a(name)
        else:
            self.pause_event_b(name)

    def resume_event_by_mode(self, name):
        if self.pause_mode == 'A':
            self.resume_event_a(name)
        else:
            self.resume_event_b(name)

    def pause_event_a(self, name):
        if name not in self.current_events:
            return
        d = self.current_events[name]
        if d["status"] != "running":
            return
        now = datetime.now()
        el = (now - d["start_time"]).total_seconds()
        d["accumulated_seconds"] += el
        d["status"] = "paused_a"
        d["paused_time"] = now
        self.status_bar.config(text=f"事件已暂停(A): {name}")
        if self.simple_window.window:
            self.simple_window.update_events_list()

    def resume_event_a(self, name):
        if name not in self.current_events:
            return
        d = self.current_events[name]
        if d["status"] != "paused_a":
            return
        d["start_time"] = datetime.now()
        d["status"] = "running"
        d["paused_time"] = None
        self.status_bar.config(text=f"事件已恢复: {name}")
        if self.simple_window.window:
            self.simple_window.update_events_list()

    def pause_event_b(self, name):
        if name not in self.current_events:
            return
        d = self.current_events[name]
        if d["status"] != "running":
            return
        now = datetime.now()
        el = (now - d["start_time"]).total_seconds()
        d["accumulated_seconds"] += el
        dur_str = self.format_duration(el)
        rec = {
            "event": name,
            "tags": d["tags"],
            "start_time": d["start_time"].strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": dur_str,
            "duration_seconds": int(el)
        }
        self.events_history.append(rec)
        self.save_history()
        d["status"] = "paused_b"
        d["start_time"] = None
        self.status_bar.config(text=f"事件已暂停(B): {name} (段已记录)")
        self.update_history_display()
        if self.simple_window.window:
            self.simple_window.update_events_list()

    def resume_event_b(self, name):
        if name not in self.current_events:
            return
        old = self.current_events[name]
        if old["status"] != "paused_b":
            return
        start = datetime.now()
        tags = old["tags"]
        self.current_events[name] = {
            "start_time": start,
            "original_start_time": old["original_start_time"],
            "tags": tags,
            "from_template": old.get("from_template", False),
            "status": "running",
            "accumulated_seconds": old["accumulated_seconds"],
            "paused_time": None
        }
        if name in self.event_names_data:
            self.event_names_data[name]["count"] += 1
        else:
            self.event_names_data[name] = {"count": 1}
        self.event_names_data[name]["last_used"] = start.strftime("%Y-%m-%d %H:%M:%S")
        self.save_event_names()
        self.status_bar.config(text=f"事件已恢复(分段): {name}")
        if name in self.timer_widgets:
            self.update_single_timer_display(name)
        if self.simple_window.window:
            self.simple_window.update_events_list()
    # ---------- 停止事件 ----------
    def stop_single_timing(self, name):
        if name not in self.current_events:
            return
        d = self.current_events[name]
        if d["status"] == "running":
            end = datetime.now()
            el = (end - d["start_time"]).total_seconds()
            total = d["accumulated_seconds"] + el
        elif d["status"] == "paused_a":
            end = d["paused_time"] or datetime.now()
            total = d["accumulated_seconds"]
        else:  # paused_b
            end = datetime.now()
            total = d["accumulated_seconds"]

        dur_str = self.format_duration(total)
        start_dt = d.get("original_start_time", d["start_time"] or d["paused_time"] or datetime.now())

        rec = {
            "event": name,
            "tags": d["tags"],
            "start_time": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": dur_str,
            "duration_seconds": int(total)
        }
        self.events_history.append(rec)
        self.save_history()

        del self.current_events[name]
        if name in self.timer_widgets:
            self.timer_widgets[name]["frame"].destroy()
            del self.timer_widgets[name]

        self.update_history_display()
        self.status_bar.config(text=f"事件完成: {name} - {dur_str}")
        self.update_tray_tooltip()

        if d.get("from_template") and self.current_template:
            self.root.after(500, self.start_next_template_event)

        if self.simple_window.window and not self.current_events:
            self.simple_window.window.destroy()
            self.simple_window.window = None

    def format_duration(self, sec):
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        return f"{h}h{m:02d}m"

    def format_time_for_display(self, dt_str):
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            if self.show_full_datetime:
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return dt.strftime("%H:%M")
        except:
            return dt_str

    def update_history_display(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        filtered = []
        for ev in self.events_history:
            if self.selected_tags_filter:
                ev_tags = set(self.parse_tags(ev.get("tags", "")))
                if not ev_tags & self.selected_tags_filter:
                    continue
            date_str = self.specific_date_var.get().strip()
            if date_str:
                try:
                    fd = datetime.strptime(date_str, "%Y-%m-%d").date()
                    evd = datetime.strptime(ev["start_time"], "%Y-%m-%d %H:%M:%S").date()
                    if evd != fd:
                        continue
                except:
                    pass
            filtered.append(ev)

        sorted_ev = sorted(filtered, key=lambda x: x.get("duration_seconds", 0), reverse=True)
        for ev in sorted_ev:
            self.history_tree.insert("", 0, values=(
                ev["event"],
                ev.get("tags", ""),
                self.format_time_for_display(ev["start_time"]),
                self.format_time_for_display(ev["end_time"]),
                ev["duration"]
            ))

    # ---------- 历史记录右键菜单 ----------
    def create_history_context_menu(self):
        self.history_menu = tk.Menu(self.root, tearoff=0, bg=self.button_bg, fg=self.fg_color)
        self.history_menu.add_command(label="删除选中项", command=self.delete_selected_history)
        self.history_menu.add_command(label="编辑标签", command=self.edit_selected_tag)

    def show_history_context_menu(self, event):
        item = self.history_tree.identify_row(event.y)
        if item:
            self.history_tree.selection_set(item)
            self.history_menu.post(event.x_root, event.y_root)

    def delete_selected_history(self):
        sel = self.history_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择要删除的历史记录")
            return
        if messagebox.askyesno("确认", f"删除选中的 {len(sel)} 条记录？"):
            for item in sel:
                vals = self.history_tree.item(item, 'values')
                if vals:
                    name = vals[0]
                    start_disp = vals[2]
                    for i, ev in enumerate(self.events_history):
                        if ev["event"] == name and self.format_time_for_display(ev["start_time"]) == start_disp:
                            del self.events_history[i]
                            break
            self.update_history_display()
            self.save_history()
            self.status_bar.config(text=f"已删除 {len(sel)} 条历史记录")

    def edit_selected_tag(self):
        sel = self.history_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择要编辑标签的记录")
            return
        if len(sel) > 1:
            messagebox.showwarning("提示", "只能编辑单条记录")
            return
        item = sel[0]
        vals = self.history_tree.item(item, 'values')
        if not vals:
            return
        name, old_tags, start_disp = vals[0], vals[1], vals[2]
        for i, ev in enumerate(self.events_history):
            if ev["event"] == name and self.format_time_for_display(ev["start_time"]) == start_disp:
                new = simpledialog.askstring("编辑标签", f"事件: {name}\n当前标签: {old_tags}\n新标签:",
                                             initialvalue=old_tags)
                if new is not None:
                    ev["tags"] = new
                    for t in self.parse_tags(new):
                        self.tags_data[t] = self.tags_data.get(t, 0) + 1
                    self.save_history()
                    self.save_tags()
                    self.update_history_display()
                    self.status_bar.config(text=f"已更新标签: {name}")
                break

    # ---------- 数据持久化 ----------
    def load_history(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.events_history = json.load(f)
            except:
                self.events_history = []
        else:
            self.events_history = []

    def save_history(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.events_history, f, ensure_ascii=False, indent=2)
        except:
            messagebox.showerror("保存错误", "无法保存历史记录")

    def load_event_names(self):
        if os.path.exists(self.names_file):
            try:
                with open(self.names_file, 'r', encoding='utf-8') as f:
                    self.event_names_data = json.load(f)
            except:
                self.event_names_data = {}
        else:
            self.event_names_data = {}

    def save_event_names(self):
        try:
            with open(self.names_file, 'w', encoding='utf-8') as f:
                json.dump(self.event_names_data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def load_templates(self):
        if os.path.exists(self.templates_file):
            try:
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    self.event_templates = json.load(f)
            except:
                self.event_templates = []
        else:
            self.event_templates = []

    def save_templates(self):
        try:
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(self.event_templates, f, ensure_ascii=False, indent=2)
        except:
            messagebox.showerror("保存错误", "无法保存模板")

    def load_tags(self):
        if os.path.exists(self.tags_file):
            try:
                with open(self.tags_file, 'r', encoding='utf-8') as f:
                    self.tags_data = json.load(f)
            except:
                self.tags_data = {}
        else:
            self.tags_data = {}
        if not self.tags_data and self.events_history:
            for ev in self.events_history:
                for t in self.parse_tags(ev.get("tags", "")):
                    self.tags_data[t] = self.tags_data.get(t, 0) + 1
            self.save_tags()

    def save_tags(self):
        try:
            with open(self.tags_file, 'w', encoding='utf-8') as f:
                json.dump(self.tags_data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    s = json.load(f)
                    self.notification_interval = s.get("notification_interval", 30)
                    self.auto_stop_on_notification = s.get("auto_stop_on_notification", False)
                    self.notification_active = s.get("notification_active", True)
                    self.pause_mode = s.get("pause_mode", 'A')
            except:
                pass
        else:
            self.notification_interval = 30
            self.auto_stop_on_notification = False
            self.notification_active = True
            self.pause_mode = 'A'

    def save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "notification_interval": self.notification_interval,
                    "auto_stop_on_notification": self.auto_stop_on_notification,
                    "notification_active": self.notification_active,
                    "pause_mode": self.pause_mode
                }, f, ensure_ascii=False, indent=2)
        except:
            pass

    # ---------- 模板管理 ----------
    def show_template_manager(self):
        win = tk.Toplevel(self.root)
        win.title("模板管理")
        win.geometry("500x400")
        win.configure(bg=self.bg_color)
        win.transient(self.root)
        win.grab_set()
        self.center_window(win)

        list_frame = tk.Frame(win, bg=self.bg_color)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(list_frame, text="模板列表:", bg=self.bg_color, fg=self.fg_color).pack(anchor="w")

        lb = tk.Listbox(list_frame, bg=self.entry_bg, fg=self.entry_fg,
                        selectbackground=self.dropdown_sel_bg,
                        selectforeground="white", height=10)
        lb.pack(fill=tk.BOTH, expand=True, pady=(5,10))

        for i, tmpl in enumerate(self.event_templates):
            cnt = len(tmpl.get("events", []))
            lb.insert(tk.END, f"{tmpl['name']} ({cnt}个事件)")

        btnf = tk.Frame(win, bg=self.bg_color)
        btnf.pack(fill=tk.X, padx=10, pady=(0,10))

        def create_new():
            cwin = tk.Toplevel(win)
            cwin.title("创建新模板")
            cwin.geometry("400x350")
            cwin.configure(bg=self.bg_color)
            cwin.transient(win)
            cwin.grab_set()
            self.center_window(cwin)

            tk.Label(cwin, text="模板名称:", bg=self.bg_color, fg=self.fg_color).pack(anchor="w", padx=10, pady=(10,5))
            name_entry = tk.Entry(cwin, bg=self.entry_bg, fg=self.entry_fg, width=30)
            name_entry.pack(fill=tk.X, padx=10, pady=(0,10))

            tk.Label(cwin, text="事件列表 (每行一个):", bg=self.bg_color, fg=self.fg_color).pack(anchor="w", padx=10, pady=(0,5))
            ev_text = tk.Text(cwin, bg=self.entry_bg, fg=self.entry_fg, height=8)
            ev_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

            tk.Label(cwin, text="默认标签 (可选):", bg=self.bg_color, fg=self.fg_color).pack(anchor="w", padx=10, pady=(0,5))
            tags_entry = tk.Entry(cwin, bg=self.entry_bg, fg=self.entry_fg, width=30)
            tags_entry.pack(fill=tk.X, padx=10, pady=(0,10))

            def save():
                name = name_entry.get().strip()
                if not name:
                    messagebox.showwarning("提示", "请输入模板名称")
                    return
                content = ev_text.get("1.0", tk.END).strip()
                if not content:
                    messagebox.showwarning("提示", "请至少添加一个事件")
                    return
                default_tags = tags_entry.get().strip()
                events = []
                for line in content.split('\n'):
                    line = line.strip()
                    if line:
                        events.append({"name": line, "tags": default_tags})
                self.event_templates.append({"name": name, "events": events})
                self.save_templates()
                self.template_combo['values'] = [t["name"] for t in self.event_templates]
                lb.delete(0, tk.END)
                for i, tmpl in enumerate(self.event_templates):
                    cnt = len(tmpl.get("events", []))
                    lb.insert(tk.END, f"{tmpl['name']} ({cnt}个事件)")
                cwin.destroy()
                self.status_bar.config(text=f"已创建模板: {name}")

            tk.Button(cwin, text="保存模板", command=save,
                      bg=self.template_color, fg="white", width=15, relief="flat").pack(side=tk.LEFT, padx=10, pady=(0,10))
            tk.Button(cwin, text="取消", command=cwin.destroy,
                      bg=self.button_bg, fg=self.button_fg, width=10, relief="flat").pack(side=tk.RIGHT, padx=10, pady=(0,10))

        def use_selected():
            sel = lb.curselection()
            if not sel:
                messagebox.showwarning("提示", "请先选择要使用的模板")
                return
            idx = sel[0]
            tmpl = self.event_templates[idx]
            if messagebox.askyesno("使用模板", f"使用模板 '{tmpl['name']}' 吗？\n包含 {len(tmpl['events'])} 个事件，将依次开始计时。"):
                self.current_template = tmpl
                self.template_event_index = 0
                self.template_events_queue = tmpl["events"].copy()
                self.event_entry.delete(0, tk.END)
                self.tag_entry.delete(0, tk.END)
                self.start_next_template_event()
                win.destroy()

        def delete_selected():
            sel = lb.curselection()
            if not sel:
                messagebox.showwarning("提示", "请先选择要删除的模板")
                return
            idx = sel[0]
            name = self.event_templates[idx]["name"]
            if messagebox.askyesno("确认", f"删除模板 '{name}' 吗？"):
                del self.event_templates[idx]
                self.save_templates()
                self.template_combo['values'] = [t["name"] for t in self.event_templates]
                lb.delete(0, tk.END)
                for i, tmpl in enumerate(self.event_templates):
                    cnt = len(tmpl.get("events", []))
                    lb.insert(tk.END, f"{tmpl['name']} ({cnt}个事件)")
                self.status_bar.config(text=f"已删除模板: {name}")

        tk.Button(btnf, text="新建模板", command=create_new,
                  bg=self.template_color, fg="white", width=15, relief="flat").pack(side=tk.LEFT, padx=(0,10))
        tk.Button(btnf, text="使用选中模板", command=use_selected,
                  bg=self.start_color, fg="white", width=15, relief="flat").pack(side=tk.LEFT, padx=(0,10))
        tk.Button(btnf, text="删除选中模板", command=delete_selected,
                  bg=self.stop_color, fg="white", width=15, relief="flat").pack(side=tk.LEFT, padx=(0,10))
        tk.Button(btnf, text="关闭", command=win.destroy,
                  bg=self.button_bg, fg=self.button_fg, width=10, relief="flat").pack(side=tk.RIGHT)

    def on_template_selected(self, event):
        name = self.template_combo.get()
        if name == "选择模板":
            return
        for tmpl in self.event_templates:
            if tmpl["name"] == name:
                self.current_template = tmpl
                self.template_event_index = 0
                self.template_events_queue = tmpl["events"].copy()
                self.event_entry.delete(0, tk.END)
                self.tag_entry.delete(0, tk.END)
                self.start_next_template_event()
                break

    def start_next_template_event(self):
        if not self.current_template or not self.template_events_queue:
            return
        if self.template_event_index >= len(self.template_events_queue):
            self.status_bar.config(text=f"模板 '{self.current_template['name']}' 所有事件已完成")
            self.current_template = None
            self.template_event_index = 0
            self.template_events_queue = []
            return

        evd = self.template_events_queue[self.template_event_index]
        ev_name = evd["name"]
        ev_tags = evd.get("tags", "")

        if ev_name in self.current_events:
            messagebox.showwarning("事件已存在", f"事件 '{ev_name}' 已在计时中，跳过")
            self.template_event_index += 1
            self.root.after(100, self.start_next_template_event)
            return

        self.event_entry.delete(0, tk.END)
        self.event_entry.insert(0, ev_name)
        self.tag_entry.delete(0, tk.END)
        self.tag_entry.insert(0, ev_tags)

        self.start_timing_from_template()

        self.template_event_index += 1
        remain = len(self.template_events_queue) - self.template_event_index
        if remain > 0:
            self.status_bar.config(text=f"模板 '{self.current_template['name']}' 进行中: {ev_name} (剩余 {remain} 个)")
        else:
            self.status_bar.config(text=f"模板 '{self.current_template['name']}' 已完成")
        self.template_combo.set("选择模板")

    # ---------- 打开配置文件夹 ----------
    def open_config_folder(self):
        try:
            if platform.system() == "Windows":
                os.startfile(self.config_dir)
            elif platform.system() == "Darwin":
                import subprocess
                subprocess.Popen(["open", self.config_dir])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", self.config_dir])
            self.status_bar.config(text=f"已打开配置文件夹: {self.config_dir}")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {str(e)}")

    # ---------- 系统托盘 ----------
    def create_system_tray(self):
        try:
            img = self.load_tray_icon()
            menu = (
                pystray.MenuItem('显示主窗口', self.show_main_window),
                pystray.MenuItem('显示简易窗口', self.show_simple_window),
                pystray.MenuItem('---', None, enabled=False),
                pystray.MenuItem('退出', self.quit_app)
            )
            self.tray_icon = pystray.Icon("event_timer", img, "事件计时器", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            print("托盘创建失败:", e)

    def load_tray_icon(self):
        paths = ["timer_icon.ico", "icon.ico", "resources/timer_icon.ico", "resources/icon.ico"]
        for p in paths:
            if os.path.exists(p):
                try:
                    return Image.open(p)
                except:
                    continue
        return self.create_tray_image()

    def create_tray_image(self):
        img = Image.new('RGBA', (64,64), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        color = "#ffffff" if self.is_dark_mode else "#2196F3"
        draw.ellipse([12,12,52,52], outline=color, width=3)
        draw.line([32,32,32,20], fill=color, width=3)
        draw.line([32,32,44,32], fill=color, width=3)
        return img

    def show_main_window(self, icon=None, item=None):
        if self.is_hidden_to_tray:
            self.show_from_tray()
        else:
            self.root.deiconify()
            self.root.lift()

    def show_simple_window(self, icon=None, item=None):
        if self.current_events:
            self.simple_window.create_window()
        else:
            messagebox.showinfo("提示", "当前没有正在计时的事件")

    def hide_to_tray(self):
        self.hide_dropdown()
        self.is_hidden_to_tray = True
        self.root.withdraw()
        if self.current_events:
            self.simple_window.create_window()
        self.update_tray_tooltip()
        self.status_bar.config(text="程序已最小化到系统托盘")

    def show_from_tray(self):
        self.is_hidden_to_tray = False
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        if self.simple_window.window:
            self.simple_window.window.destroy()
            self.simple_window.window = None
        self.update_tray_tooltip()
        self.status_bar.config(text=f"正在计时 {len(self.current_events)} 个事件" if self.current_events else "就绪")

    def update_tray_tooltip(self):
        if self.tray_icon:
            tip = "事件计时器"
            if self.current_events:
                tip += f" - {len(self.current_events)}个事件进行中"
            if self.is_hidden_to_tray:
                tip += " (最小化)"
            self.tray_icon.title = tip

    def quit_app(self, icon=None, item=None):
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

    # ---------- 通知系统 ----------
    def start_notification_checker(self):
        if not self.notification_active:
            return
        if self.notification_thread and self.notification_thread.is_alive():
            self.notification_active = False
            time.sleep(0.1)
        self.notification_active = True

        def loop():
            last = {}
            while self.notification_active:
                now = time.time()
                for name, data in self.current_events.items():
                    if data["status"] != "running":
                        continue
                    elapsed = data["accumulated_seconds"] + (datetime.now() - data["start_time"]).total_seconds()
                    mins = elapsed / 60
                    if mins >= self.notification_interval:
                        if name not in last or now - last[name] >= self.notification_interval * 60:
                            last[name] = now
                            self.root.after(0, lambda n=name, m=mins: self.show_single_event_notification(n, m))
                for n in list(last.keys()):
                    if n not in self.current_events:
                        del last[n]
                time.sleep(30)
        self.notification_thread = threading.Thread(target=loop, daemon=True)
        self.notification_thread.start()

    def show_single_event_notification(self, name, mins):
        if name not in self.current_events:
            return
        if self.auto_stop_on_notification:
            self.stop_single_timing(name)
            return
        try:
            winsound.Beep(1000, 500)
        except:
            pass
        win = tk.Toplevel(self.root)
        win.title("事件计时提醒")
        win.geometry("400x200")
        win.configure(bg=self.bg_color)
        win.attributes("-topmost", True)
        win.transient(self.root)
        self.center_window(win)

        tk.Label(win, text="⏰ 事件计时提醒", bg=self.bg_color, fg=self.accent_color,
                 font=("Arial",16,"bold")).pack(pady=(20,10))
        tk.Label(win, text=f"事件 '{name}' 已计时 {int(mins)} 分钟",
                 bg=self.bg_color, fg=self.fg_color, font=("Arial",12)).pack(pady=(0,20))
        tk.Label(win, text="是否仍在继续？", bg=self.bg_color, fg=self.fg_color).pack()

        btnf = tk.Frame(win, bg=self.bg_color)
        btnf.pack(pady=20)
        tk.Button(btnf, text="仍在继续", command=win.destroy,
                  bg=self.start_color, fg="white", width=12, relief="flat").pack(side=tk.LEFT, padx=10)
        tk.Button(btnf, text="停止该事件",
                  command=lambda: [self.stop_single_timing(name), win.destroy()],
                  bg=self.stop_color, fg="white", width=12, relief="flat").pack(side=tk.LEFT)

    # ---------- 筛选重置 ----------
    def reset_filters(self):
        self.specific_date_var.set("")
        self.selected_tags_filter = set()
        self.filter_tags_label.config(text="")
        self.update_history_display()
        self.status_bar.config(text="已重置所有筛选")
    # ---------- 日历选择对话框 ----------
    def show_calendar(self):
        """弹出简易日历选择窗口"""
        win = tk.Toplevel(self.root)
        win.title("选择日期")
        win.geometry("300x250")
        win.configure(bg=self.bg_color)
        win.transient(self.root)
        win.grab_set()
        self.center_window(win)

        # 获取当前日期
        now = datetime.now()
        year = now.year
        month = now.month

        top_frame = tk.Frame(win, bg=self.bg_color)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        # 年月选择
        year_var = tk.IntVar(value=year)
        month_var = tk.IntVar(value=month)

        tk.Label(top_frame, text="年:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT)
        year_spin = tk.Spinbox(top_frame, from_=1900, to=2100, textvariable=year_var,
                               width=6, bg=self.entry_bg, fg=self.entry_fg, relief="flat")
        year_spin.pack(side=tk.LEFT, padx=2)

        tk.Label(top_frame, text="月:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=(10,2))
        month_spin = tk.Spinbox(top_frame, from_=1, to=12, textvariable=month_var,
                                width=4, bg=self.entry_bg, fg=self.entry_fg, relief="flat")
        month_spin.pack(side=tk.LEFT, padx=2)

        # 日历显示区域
        cal_frame = tk.Frame(win, bg=self.bg_color)
        cal_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        def refresh_calendar(*args):
            # 清除现有日历
            for widget in cal_frame.winfo_children():
                widget.destroy()

            y = year_var.get()
            m = month_var.get()
            cal = calendar.monthcalendar(y, m)
            days = ['一', '二', '三', '四', '五', '六', '日']

            # 星期标题
            for i, day in enumerate(days):
                tk.Label(cal_frame, text=day, bg=self.button_bg, fg=self.fg_color,
                         width=3, relief="flat", font=("Arial", 9, "bold")).grid(row=0, column=i, padx=1, pady=1)

            # 日期按钮
            for r, week in enumerate(cal, start=1):
                for c, day in enumerate(week):
                    if day == 0:
                        tk.Label(cal_frame, text="", bg=self.bg_color, width=3).grid(row=r, column=c)
                    else:
                        btn = tk.Button(cal_frame, text=str(day), width=3, relief="flat",
                                        bg=self.entry_bg, fg=self.entry_fg,
                                        command=lambda d=day: select_date(d))
                        btn.grid(row=r, column=c, padx=1, pady=1)

        def select_date(day):
            y = year_var.get()
            m = month_var.get()
            date_str = f"{y:04d}-{m:02d}-{day:02d}"
            self.specific_date_var.set(date_str)
            win.destroy()
            self.apply_specific_date_filter()  # 自动应用筛选

        refresh_calendar()
        # 绑定年月变化刷新日历
        year_spin.config(command=refresh_calendar)
        month_spin.config(command=refresh_calendar)

        # 底部按钮
        btn_frame = tk.Frame(win, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(btn_frame, text="今天", command=lambda: select_date(now.day),
                  bg=self.accent_color, fg="white", width=8, relief="flat").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", command=win.destroy,
                  bg=self.button_bg, fg=self.button_fg, width=8, relief="flat").pack(side=tk.RIGHT, padx=5)
    # ---------- 时间显示更新 ----------
    def update_time_display(self):
        now = datetime.now()
        self.root.title(f"事件计时器 - {now.strftime('%H:%M')} - 进行中: {len(self.current_events)}")
        self.root.after(1000, self.update_time_display)

    # ---------- 清空历史 ----------
    def clear_history(self):
        if not self.events_history:
            messagebox.showinfo("提示", "历史记录已是空的")
            return
        if messagebox.askyesno("确认", "清空所有历史记录？此操作不可撤销。"):
            self.events_history = []
            self.update_history_display()
            self.save_history()
            self.status_bar.config(text="历史记录已清空")


def main():
    root = tk.Tk()
    app = EventTimerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
