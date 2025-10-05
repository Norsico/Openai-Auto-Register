import customtkinter as ctk
import json
import random
import string
import imaplib
import email
from email.header import decode_header
import time
from datetime import datetime
import threading
import os
import re

# 设置主题
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# 全局配置
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 680

class ConfigManager:
    def __init__(self):
        self.config_file = "config.json"
        self.config = self.load_config()
    
    def load_config(self):
        """从本地文件加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self.get_default_config()
        return self.get_default_config()
    
    def get_default_config(self):
        """获取默认配置"""
        return {
            'domain': '',
            'imap_server': 'imap.qq.com',
            'imap_email': '',
            'imap_password': '',
            'port': 993
        }
    
    def save_config(self, config_data):
        """保存配置到本地"""
        self.config = config_data
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def get_config(self):
        """获取当前配置"""
        return self.config

class AccountManager:
    def __init__(self):
        self.accounts_file = "accounts.json"
        self.accounts = self.load_accounts()
        
    def load_accounts(self):
        """从本地文件加载账号"""
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_account(self, account_data):
        """保存账号到本地"""
        self.accounts.append(account_data)
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(self.accounts, f, ensure_ascii=False, indent=2)
    
    def get_all_accounts(self):
        """获取所有账号"""
        return self.accounts

class EmailReceiver:
    def __init__(self, imap_server, email_address, password, port=993):
        self.imap_server = imap_server
        self.email_address = email_address
        self.password = password
        self.port = port
    
    def get_verification_code(self, target_email, timeout=120):
        """获取验证码"""
        try:
            # 连接到IMAP服务器
            mail = imaplib.IMAP4_SSL(self.imap_server, self.port)
            mail.login(self.email_address, self.password)
            mail.select('INBOX')
            
            start_time = time.time()
            
            # 轮询检查新邮件
            while time.time() - start_time < timeout:
                # 搜索最近的邮件
                status, messages = mail.search(None, 'TO', target_email)
                
                if status == 'OK' and messages[0]:
                    email_ids = messages[0].split()
                    # 获取最新的邮件
                    if email_ids:
                        latest_email_id = email_ids[-1]
                        status, msg_data = mail.fetch(latest_email_id, '(RFC822)')
                        
                        if status == 'OK':
                            email_body = msg_data[0][1]
                            email_message = email.message_from_bytes(email_body)
                            
                            # 提取邮件内容
                            code = self._extract_code_from_email(email_message)
                            if code:
                                mail.close()
                                mail.logout()
                                return code
                
                time.sleep(3)  # 每3秒检查一次
            
            mail.close()
            mail.logout()
            return None
            
        except Exception as e:
            print(f"邮件接收错误: {str(e)}")
            return None
    
    def _extract_code_from_email(self, email_message):
        """从邮件中提取验证码"""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode()
                        break
                    except:
                        pass
        else:
            try:
                body = email_message.get_payload(decode=True).decode()
            except:
                pass
        
        # 使用正则表达式提取验证码（通常是4-8位数字或字母数字组合）
        patterns = [
            r'验证码[：:]\s*([A-Za-z0-9]{4,8})',
            r'code[：:]\s*([A-Za-z0-9]{4,8})',
            r'Code[：:]\s*([A-Za-z0-9]{4,8})',
            r'\b([A-Z0-9]{6})\b',
            r'\b(\d{4,8})\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body)
            if match:
                return match.group(1)
        
        return None

class AccountManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 配置管理器
        self.config_manager = ConfigManager()
        self.email_config = self.config_manager.get_config()
        
        # 账号管理器
        self.account_manager = AccountManager()
        
        # 邮件接收器（如果配置完整则初始化）
        self.email_receiver = None
        if self.is_config_complete():
            self.init_email_receiver()
        
        # 当前注册流程的数据
        self.current_registration = {}
        
        # 窗口配置
        self.title("账号管理工具")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        
        # 窗口置顶变量
        self.is_topmost = False
        
        # 创建主容器
        self.create_main_interface()
    
    def is_config_complete(self):
        """检查配置是否完整"""
        required_fields = ['domain', 'imap_server', 'imap_email', 'imap_password', 'port']
        return all(self.email_config.get(field) for field in required_fields)
    
    def init_email_receiver(self):
        """初始化邮件接收器"""
        self.email_receiver = EmailReceiver(
            self.email_config['imap_server'],
            self.email_config['imap_email'],
            self.email_config['imap_password'],
            self.email_config['port']
        )
        
    def create_main_interface(self):
        """创建主界面"""
        # 顶部工具栏
        toolbar = ctk.CTkFrame(self, height=50, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=(10, 0))
        
        # 窗口置顶按钮
        self.topmost_btn = ctk.CTkButton(
            toolbar,
            text="📌 窗口置顶",
            width=120,
            height=35,
            command=self.toggle_topmost,
            fg_color="gray30",
            hover_color="gray40"
        )
        self.topmost_btn.pack(side="right", padx=5)
        
        # 创建Tab视图
        self.tabview = ctk.CTkTabview(self, width=WINDOW_WIDTH-20, height=WINDOW_HEIGHT-70)
        self.tabview.pack(padx=10, pady=(5, 10), fill="both", expand=True)
        
        # 添加标签页
        self.tabview.add("注册账号")
        self.tabview.add("账号列表")
        self.tabview.add("设置")
        
        # 创建注册页面（页面切换式）
        self.create_registration_pages()
        
        # 创建账号列表页面
        self.create_accounts_list_tab()
        
        # 创建设置页面
        self.create_settings_tab()
    
    def toggle_topmost(self):
        """切换窗口置顶状态"""
        self.is_topmost = not self.is_topmost
        self.attributes('-topmost', self.is_topmost)
        
        if self.is_topmost:
            self.topmost_btn.configure(fg_color="#1f6aa5", text="📌 已置顶")
        else:
            self.topmost_btn.configure(fg_color="gray30", text="📌 窗口置顶")
        
    def create_registration_pages(self):
        """创建注册页面（页面切换式）"""
        tab = self.tabview.tab("注册账号")
        
        # 主容器
        self.reg_container = ctk.CTkFrame(tab, fg_color="transparent")
        self.reg_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 创建三个页面
        self.pages = []
        
        # 页面1: 生成账号和密码
        self.page1 = self.create_page1()
        self.pages.append(self.page1)
        
        # 页面2: 验证码
        self.page2 = self.create_page2()
        self.pages.append(self.page2)
        
        # 页面3: 用户名和生日
        self.page3 = self.create_page3()
        self.pages.append(self.page3)
        
        # 当前页面索引
        self.current_page = 0
        
        # 显示第一个页面
        self.show_page(0)
    
    def create_page1(self):
        """创建第1页：生成账号和密码"""
        page = ctk.CTkFrame(self.reg_container, fg_color="transparent")
        
        # 标题
        title = ctk.CTkLabel(
            page,
            text="步骤 1: 生成账号和密码",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        title.pack(pady=(40, 30))
        
        # 内容区域
        content_frame = ctk.CTkFrame(page, fg_color="#2b2b2b", corner_radius=15)
        content_frame.pack(pady=20, padx=50, fill="both", expand=True)
        
        # 垂直居中容器
        center_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # 邮箱账号
        email_label = ctk.CTkLabel(center_frame, text="邮箱账号", font=ctk.CTkFont(size=14, weight="bold"))
        email_label.pack(pady=(0, 5))
        
        email_container = ctk.CTkFrame(center_frame, fg_color="transparent")
        email_container.pack(pady=(0, 25))
        
        self.email_entry = ctk.CTkEntry(
            email_container,
            width=400,
            height=40,
            font=ctk.CTkFont(size=14),
            border_width=2
        )
        self.email_entry.pack(side="left", padx=(0, 10))
        
        copy_email_btn = ctk.CTkButton(
            email_container,
            text="复制",
            width=80,
            height=40,
            command=lambda: self.copy_to_clipboard(self.email_entry.get())
        )
        copy_email_btn.pack(side="left")
        
        # 密码
        password_label = ctk.CTkLabel(center_frame, text="密码", font=ctk.CTkFont(size=14, weight="bold"))
        password_label.pack(pady=(0, 5))
        
        password_container = ctk.CTkFrame(center_frame, fg_color="transparent")
        password_container.pack(pady=(0, 30))
        
        self.password_entry = ctk.CTkEntry(
            password_container,
            width=400,
            height=40,
            font=ctk.CTkFont(size=14),
            border_width=2
        )
        self.password_entry.pack(side="left", padx=(0, 10))
        
        copy_password_btn = ctk.CTkButton(
            password_container,
            text="复制",
            width=80,
            height=40,
            command=lambda: self.copy_to_clipboard(self.password_entry.get())
        )
        copy_password_btn.pack(side="left")
        
        # 按钮区域
        btn_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="❌ 取消",
            width=120,
            height=45,
            font=ctk.CTkFont(size=15),
            command=self.cancel_registration,
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        cancel_btn.pack(side="left", padx=5)
        
        generate_btn = ctk.CTkButton(
            btn_frame,
            text="🎲 重新生成",
            width=130,
            height=45,
            font=ctk.CTkFont(size=15),
            command=self.generate_account_password,
            fg_color="gray40",
            hover_color="gray50"
        )
        generate_btn.pack(side="left", padx=5)
        
        next_btn = ctk.CTkButton(
            btn_frame,
            text="下一步 →",
            width=130,
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.next_to_verification
        )
        next_btn.pack(side="left", padx=5)
        
        # 自动生成
        self.after(100, self.generate_account_password)
        
        return page
    
    def create_page2(self):
        """创建第2页：验证码"""
        page = ctk.CTkFrame(self.reg_container, fg_color="transparent")
        
        # 标题
        title = ctk.CTkLabel(
            page,
            text="步骤 2: 等待验证码",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        title.pack(pady=(40, 20))
        
        # 内容区域
        content_frame = ctk.CTkFrame(page, fg_color="#2b2b2b", corner_radius=15)
        content_frame.pack(pady=20, padx=50, fill="both", expand=True)
        
        # 垂直居中容器
        center_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # 状态提示
        self.verification_status_label = ctk.CTkLabel(
            center_frame,
            text="⏳ 正在自动接收验证码，请稍候...",
            font=ctk.CTkFont(size=15),
            text_color="#4a9eff"
        )
        self.verification_status_label.pack(pady=(0, 30))
        
        # 验证码显示
        code_label = ctk.CTkLabel(center_frame, text="验证码", font=ctk.CTkFont(size=14, weight="bold"))
        code_label.pack(pady=(0, 5))
        
        code_container = ctk.CTkFrame(center_frame, fg_color="transparent")
        code_container.pack(pady=(0, 30))
        
        self.verification_code_entry = ctk.CTkEntry(
            code_container,
            width=400,
            height=40,
            font=ctk.CTkFont(size=14),
            border_width=2,
            placeholder_text="等待接收..."
        )
        self.verification_code_entry.pack(side="left", padx=(0, 10))
        
        copy_code_btn = ctk.CTkButton(
            code_container,
            text="复制",
            width=80,
            height=40,
            command=lambda: self.copy_to_clipboard(self.verification_code_entry.get())
        )
        copy_code_btn.pack(side="left")
        
        # 按钮区域
        btn_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="❌ 取消",
            width=110,
            height=45,
            font=ctk.CTkFont(size=15),
            command=self.cancel_registration,
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        cancel_btn.pack(side="left", padx=5)
        
        receive_btn = ctk.CTkButton(
            btn_frame,
            text="🔄 重新接收",
            width=140,
            height=45,
            font=ctk.CTkFont(size=15),
            command=self.start_receiving_verification,
            fg_color="gray40",
            hover_color="gray50"
        )
        receive_btn.pack(side="left", padx=5)
        
        next_btn = ctk.CTkButton(
            btn_frame,
            text="下一步 →",
            width=130,
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.next_to_userinfo
        )
        next_btn.pack(side="left", padx=5)
        
        # 底部提示
        hint_label = ctk.CTkLabel(
            center_frame,
            text="💡 提示：验证码已自动开始接收，等待时间最长120秒\n如未收到可点击重新接收或手动输入",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        hint_label.pack(pady=(20, 0))
        
        return page
    
    def create_page3(self):
        """创建第3页：用户名"""
        page = ctk.CTkFrame(self.reg_container, fg_color="transparent")
        
        # 标题
        title = ctk.CTkLabel(
            page,
            text="步骤 3: 设置用户名",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        title.pack(pady=(40, 30))
        
        # 内容区域
        content_frame = ctk.CTkFrame(page, fg_color="#2b2b2b", corner_radius=15)
        content_frame.pack(pady=20, padx=50, fill="both", expand=True)
        
        # 垂直居中容器
        center_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # 用户名
        username_label = ctk.CTkLabel(center_frame, text="用户名", font=ctk.CTkFont(size=14, weight="bold"))
        username_label.pack(pady=(0, 5))
        
        username_container = ctk.CTkFrame(center_frame, fg_color="transparent")
        username_container.pack(pady=(0, 40))
        
        self.username_entry = ctk.CTkEntry(
            username_container,
            width=400,
            height=40,
            font=ctk.CTkFont(size=14),
            border_width=2
        )
        self.username_entry.pack(side="left", padx=(0, 10))
        
        copy_username_btn = ctk.CTkButton(
            username_container,
            text="复制",
            width=80,
            height=40,
            command=lambda: self.copy_to_clipboard(self.username_entry.get())
        )
        copy_username_btn.pack(side="left")
        
        # 按钮区域
        btn_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="❌ 取消",
            width=120,
            height=45,
            font=ctk.CTkFont(size=15),
            command=self.cancel_registration,
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        cancel_btn.pack(side="left", padx=5)
        
        regenerate_btn = ctk.CTkButton(
            btn_frame,
            text="🎲 重新生成",
            width=130,
            height=45,
            font=ctk.CTkFont(size=15),
            command=self.generate_user_info,
            fg_color="gray40",
            hover_color="gray50"
        )
        regenerate_btn.pack(side="left", padx=5)
        
        complete_btn = ctk.CTkButton(
            btn_frame,
            text="✓ 完成注册",
            width=130,
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="green",
            hover_color="darkgreen",
            command=self.complete_registration
        )
        complete_btn.pack(side="left", padx=5)
        
        # 底部提示
        hint_label = ctk.CTkLabel(
            center_frame,
            text="💡 提示：用户名仅包含字母，已自动生成",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        hint_label.pack(pady=(30, 0))
        
        return page
    
    def show_page(self, page_index):
        """显示指定页面"""
        # 隐藏所有页面
        for page in self.pages:
            page.pack_forget()
        
        # 显示指定页面
        if 0 <= page_index < len(self.pages):
            self.pages[page_index].pack(fill="both", expand=True)
            self.current_page = page_index
        
    def create_settings_tab(self):
        """创建设置标签页"""
        tab = self.tabview.tab("设置")
        
        # 标题
        title_label = ctk.CTkLabel(
            tab,
            text="⚙️ 邮箱配置",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(30, 20))
        
        # 内容区域
        content_frame = ctk.CTkFrame(tab, fg_color="#2b2b2b", corner_radius=15)
        content_frame.pack(pady=10, padx=50, fill="both", expand=True)
        
        # 配置表单容器
        form_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        form_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # IMAP服务器
        imap_label = ctk.CTkLabel(form_frame, text="IMAP 服务器", font=ctk.CTkFont(size=14, weight="bold"))
        imap_label.grid(row=0, column=0, sticky="w", pady=(0, 5), padx=(0, 20))
        
        self.imap_server_entry = ctk.CTkEntry(
            form_frame,
            width=350,
            height=35,
            font=ctk.CTkFont(size=13),
            placeholder_text="imap.qq.com"
        )
        self.imap_server_entry.grid(row=1, column=0, pady=(0, 15))
        self.imap_server_entry.insert(0, self.email_config.get('imap_server', 'imap.qq.com'))
        
        # 端口
        port_label = ctk.CTkLabel(form_frame, text="端口", font=ctk.CTkFont(size=14, weight="bold"))
        port_label.grid(row=2, column=0, sticky="w", pady=(0, 5))
        
        self.port_entry = ctk.CTkEntry(
            form_frame,
            width=350,
            height=35,
            font=ctk.CTkFont(size=13),
            placeholder_text="993"
        )
        self.port_entry.grid(row=3, column=0, pady=(0, 15))
        self.port_entry.insert(0, str(self.email_config.get('port', 993)))
        
        # IMAP邮箱
        email_label = ctk.CTkLabel(form_frame, text="IMAP 邮箱", font=ctk.CTkFont(size=14, weight="bold"))
        email_label.grid(row=4, column=0, sticky="w", pady=(0, 5))
        
        self.imap_email_entry = ctk.CTkEntry(
            form_frame,
            width=350,
            height=35,
            font=ctk.CTkFont(size=13),
            placeholder_text="your_email@qq.com"
        )
        self.imap_email_entry.grid(row=5, column=0, pady=(0, 15))
        self.imap_email_entry.insert(0, self.email_config.get('imap_email', ''))
        
        # IMAP密码/令牌
        password_label = ctk.CTkLabel(form_frame, text="IMAP 密码/令牌", font=ctk.CTkFont(size=14, weight="bold"))
        password_label.grid(row=6, column=0, sticky="w", pady=(0, 5))
        
        self.imap_password_entry = ctk.CTkEntry(
            form_frame,
            width=350,
            height=35,
            font=ctk.CTkFont(size=13),
            placeholder_text="授权码或密码",
            show="●"
        )
        self.imap_password_entry.grid(row=7, column=0, pady=(0, 15))
        self.imap_password_entry.insert(0, self.email_config.get('imap_password', ''))
        
        # 邮箱域名
        domain_label = ctk.CTkLabel(form_frame, text="邮箱域名", font=ctk.CTkFont(size=14, weight="bold"))
        domain_label.grid(row=8, column=0, sticky="w", pady=(0, 5))
        
        self.domain_entry = ctk.CTkEntry(
            form_frame,
            width=350,
            height=35,
            font=ctk.CTkFont(size=13),
            placeholder_text="example.com"
        )
        self.domain_entry.grid(row=9, column=0, pady=(0, 20))
        self.domain_entry.insert(0, self.email_config.get('domain', ''))
        
        # 按钮区域
        btn_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_frame.grid(row=10, column=0, pady=10)
        
        save_btn = ctk.CTkButton(
            btn_frame,
            text="💾 保存配置",
            width=150,
            height=40,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.save_settings,
            fg_color="green",
            hover_color="darkgreen"
        )
        save_btn.pack(side="left", padx=5)
        
        reset_btn = ctk.CTkButton(
            btn_frame,
            text="🔄 重置默认",
            width=150,
            height=40,
            font=ctk.CTkFont(size=15),
            command=self.reset_settings,
            fg_color="gray40",
            hover_color="gray50"
        )
        reset_btn.pack(side="left", padx=5)
        
        # 提示信息
        hint_label = ctk.CTkLabel(
            form_frame,
            text="💡 提示：修改配置后需保存才能生效\n使用QQ邮箱需要使用授权码而不是登录密码",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        hint_label.grid(row=11, column=0, pady=(10, 0))
    
    def save_settings(self):
        """保存设置"""
        # 获取输入值
        config = {
            'imap_server': self.imap_server_entry.get().strip(),
            'port': int(self.port_entry.get().strip()) if self.port_entry.get().strip().isdigit() else 993,
            'imap_email': self.imap_email_entry.get().strip(),
            'imap_password': self.imap_password_entry.get().strip(),
            'domain': self.domain_entry.get().strip()
        }
        
        # 验证必填项
        if not config['imap_email'] or not config['imap_password'] or not config['domain']:
            self.show_message("❌ 请填写所有必填项！\n\nIMAP邮箱、密码和域名不能为空")
            return
        
        # 保存配置
        self.config_manager.save_config(config)
        self.email_config = config
        
        # 重新初始化邮件接收器
        self.init_email_receiver()
        
        self.show_message("✅ 配置保存成功！")
    
    def reset_settings(self):
        """重置为默认设置"""
        default_config = self.config_manager.get_default_config()
        
        self.imap_server_entry.delete(0, 'end')
        self.imap_server_entry.insert(0, default_config['imap_server'])
        
        self.port_entry.delete(0, 'end')
        self.port_entry.insert(0, str(default_config['port']))
        
        self.imap_email_entry.delete(0, 'end')
        self.imap_password_entry.delete(0, 'end')
        self.domain_entry.delete(0, 'end')
        
        self.show_message("已重置为默认值\n请填写邮箱、密码和域名后保存")
    
    def create_accounts_list_tab(self):
        """创建账号列表标签页"""
        tab = self.tabview.tab("账号列表")
        
        # 顶部区域
        header_frame = ctk.CTkFrame(tab, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=20)
        
        # 标题
        title_label = ctk.CTkLabel(
            header_frame, 
            text="📋 所有账号信息", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left")
        
        # 刷新按钮
        refresh_btn = ctk.CTkButton(
            header_frame,
            text="🔄 刷新列表",
            font=ctk.CTkFont(size=14),
            width=120,
            height=35,
            command=self.refresh_accounts_list,
            fg_color="#1f6aa5",
            hover_color="#1e5a8e"
        )
        refresh_btn.pack(side="right", padx=5)
        
        # 创建可滚动的框架显示账号卡片
        self.accounts_scroll_frame = ctk.CTkScrollableFrame(
            tab,
            width=WINDOW_WIDTH-60,
            height=WINDOW_HEIGHT-180,
            fg_color="transparent"
        )
        self.accounts_scroll_frame.pack(padx=20, pady=(0, 20), fill="both", expand=True)
        
        # 初始加载账号列表
        self.refresh_accounts_list()
        
    def generate_account_password(self):
        """生成随机账号和密码"""
        # 生成随机邮箱前缀（8-12位字母数字组合）
        email_prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(8, 12)))
        email = f"{email_prefix}@{self.email_config['domain']}"
        
        # 生成随机密码（12-16位，包含大小写字母、数字和特殊字符）
        password_length = random.randint(12, 16)
        password = ''.join(random.choices(
            string.ascii_letters + string.digits + "!@#$%^&*", 
            k=password_length
        ))
        
        # 显示在输入框
        self.email_entry.delete(0, 'end')
        self.email_entry.insert(0, email)
        
        self.password_entry.delete(0, 'end')
        self.password_entry.insert(0, password)
        
        # 保存到当前注册数据
        self.current_registration['email'] = email
        self.current_registration['password'] = password
        
    def copy_to_clipboard(self, text):
        """复制到剪贴板"""
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        
    def next_to_verification(self):
        """进入验证码步骤"""
        if not self.current_registration.get('email') or not self.current_registration.get('password'):
            self.show_message("请先生成账号和密码！")
            return
        
        # 切换到第2页
        self.show_page(1)
        
        # 自动开始接收验证码
        self.after(500, self.start_receiving_verification)
        
    def start_receiving_verification(self):
        """开始接收验证码"""
        if not self.current_registration.get('email'):
            self.show_message("请先生成账号！")
            return
        
        # 检查配置是否完整
        if not self.is_config_complete():
            self.show_message("❌ 邮箱配置未完成！\n\n请先到 [设置] 标签页配置邮箱信息")
            return
        
        # 检查邮件接收器是否已初始化
        if not self.email_receiver:
            self.show_message("❌ 邮件接收器初始化失败！\n\n请检查邮箱配置")
            return
        
        self.verification_status_label.configure(
            text="⏳ 正在等待验证码，请稍候...",
            text_color="#4a9eff"
        )
        
        # 在新线程中接收验证码
        thread = threading.Thread(target=self.receive_verification_code)
        thread.daemon = True
        thread.start()
        
    def receive_verification_code(self):
        """接收验证码（在后台线程中运行）"""
        target_email = self.current_registration.get('email')
        
        code = self.email_receiver.get_verification_code(target_email, timeout=120)
        
        if code:
            self.after(0, lambda: self.on_verification_received(code))
        else:
            self.after(0, lambda: self.verification_status_label.configure(
                text="❌ 未收到验证码，请重试或手动输入",
                text_color="#ff6b6b"
            ))
    
    def on_verification_received(self, code):
        """收到验证码后的处理"""
        self.verification_code_entry.delete(0, 'end')
        self.verification_code_entry.insert(0, code)
        self.verification_status_label.configure(
            text=f"✅ 已成功接收验证码: {code}",
            text_color="#51cf66"
        )
        self.current_registration['verification_code'] = code
        
    def next_to_userinfo(self):
        """进入用户信息步骤"""
        # 切换到第3页
        self.show_page(2)
        # 自动生成用户名
        self.after(100, self.generate_user_info)
        
    def generate_user_info(self):
        """生成随机用户名"""
        # 生成随机用户名（6-10位纯字母）
        username = ''.join(random.choices(string.ascii_lowercase, k=random.randint(6, 10)))
        username = 'user_' + username
        
        # 显示在输入框
        self.username_entry.delete(0, 'end')
        self.username_entry.insert(0, username)
        
        # 保存到当前注册数据
        self.current_registration['username'] = username
        
    def complete_registration(self):
        """完成注册"""
        if not all(key in self.current_registration for key in ['email', 'password', 'username']):
            self.show_message("请完成所有步骤！")
            return
        
        # 添加创建时间
        self.current_registration['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 保存账号
        self.account_manager.save_account(self.current_registration.copy())
        
        self.show_message("账号创建成功！")
        
        # 重置注册流程
        self.reset_registration()
        
    def cancel_registration(self):
        """取消注册"""
        # 确认对话框
        dialog = ctk.CTkToplevel(self)
        dialog.title("确认取消")
        dialog.geometry("450x220")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (220 // 2)
        dialog.geometry(f"450x220+{x}+{y}")
        
        # 如果窗口置顶，对话框也置顶
        if self.is_topmost:
            dialog.attributes('-topmost', True)
        
        # 消息内容
        content_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        label = ctk.CTkLabel(
            content_frame,
            text="确定要取消当前注册吗？\n所有填写的信息将被清空",
            font=ctk.CTkFont(size=15),
            wraplength=360
        )
        label.pack(pady=(20, 30))
        
        # 按钮区域
        btn_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        btn_frame.pack()
        
        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="确定取消",
            width=120,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color="#dc3545",
            hover_color="#c82333",
            command=lambda: [dialog.destroy(), self.reset_registration()]
        )
        confirm_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="继续注册",
            width=120,
            height=40,
            font=ctk.CTkFont(size=14),
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", padx=5)
    
    def reset_registration(self):
        """重置注册流程"""
        self.current_registration = {}
        
        # 清空所有输入框
        self.email_entry.delete(0, 'end')
        self.password_entry.delete(0, 'end')
        self.verification_code_entry.delete(0, 'end')
        self.username_entry.delete(0, 'end')
        
        # 重置验证码状态
        self.verification_status_label.configure(text="⏳ 正在自动接收验证码，请稍候...", text_color="#4a9eff")
        
        # 切换回第1页并自动生成
        self.show_page(0)
        self.after(100, self.generate_account_password)
        
    def refresh_accounts_list(self):
        """刷新账号列表"""
        # 清空现有内容
        for widget in self.accounts_scroll_frame.winfo_children():
            widget.destroy()
        
        accounts = self.account_manager.get_all_accounts()
        
        if not accounts:
            # 显示空状态
            empty_label = ctk.CTkLabel(
                self.accounts_scroll_frame,
                text="📭 暂无账号信息\n\n点击 [注册账号] 标签页开始创建账号",
                font=ctk.CTkFont(size=16),
                text_color="gray60"
            )
            empty_label.pack(pady=100)
            return
        
        # 为每个账号创建卡片
        for i, account in enumerate(accounts, 1):
            self.create_account_card(i, account)
    
    def create_account_card(self, index, account):
        """创建单个账号卡片"""
        # 卡片主容器
        card = ctk.CTkFrame(
            self.accounts_scroll_frame,
            fg_color="#2b2b2b",
            corner_radius=10,
            border_width=2,
            border_color="#3b3b3b"
        )
        card.pack(pady=10, padx=5, fill="x")
        
        # 卡片内容
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=15)
        
        # 标题行
        title_frame = ctk.CTkFrame(content, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 15))
        
        title_label = ctk.CTkLabel(
            title_frame,
            text=f"账号 #{index}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#4a9eff"
        )
        title_label.pack(side="left")
        
        # 创建时间
        time_label = ctk.CTkLabel(
            title_frame,
            text=f"📅 {account.get('created_at', 'N/A')}",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        time_label.pack(side="right")
        
        # 邮箱行
        self.create_field_row(
            content,
            "📧 邮箱账号",
            account.get('email', 'N/A')
        )
        
        # 密码行
        self.create_field_row(
            content,
            "🔑 密码",
            account.get('password', 'N/A')
        )
        
        # 用户名行
        self.create_field_row(
            content,
            "👤 用户名",
            account.get('username', 'N/A')
        )
    
    def create_field_row(self, parent, label_text, value):
        """创建字段行（带复制按钮）"""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=5)
        
        # 标签
        label = ctk.CTkLabel(
            row,
            text=label_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            width=100,
            anchor="w"
        )
        label.pack(side="left", padx=(0, 10))
        
        # 值输入框（只读效果）
        value_entry = ctk.CTkEntry(
            row,
            font=ctk.CTkFont(size=13),
            height=35,
            border_width=1
        )
        value_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        value_entry.insert(0, value)
        value_entry.configure(state="readonly")
        
        # 复制按钮
        copy_btn = ctk.CTkButton(
            row,
            text="📋 复制",
            width=80,
            height=35,
            font=ctk.CTkFont(size=12),
            command=lambda v=value: self.copy_to_clipboard(v),
            fg_color="#1f6aa5",
            hover_color="#1e5a8e"
        )
        copy_btn.pack(side="left")
        
    def show_message(self, message):
        """显示消息对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("提示")
        dialog.geometry("450x220")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (220 // 2)
        dialog.geometry(f"450x220+{x}+{y}")
        
        # 如果窗口置顶，对话框也置顶
        if self.is_topmost:
            dialog.attributes('-topmost', True)
        
        # 消息内容
        content_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        label = ctk.CTkLabel(
            content_frame,
            text=message,
            font=ctk.CTkFont(size=16),
            wraplength=360
        )
        label.pack(pady=(20, 30))
        
        button = ctk.CTkButton(
            content_frame,
            text="确定",
            command=dialog.destroy,
            width=120,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        button.pack(pady=10)

if __name__ == "__main__":
    app = AccountManagerApp()
    app.mainloop()

