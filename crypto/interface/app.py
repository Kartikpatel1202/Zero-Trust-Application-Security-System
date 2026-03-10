import sys
import os
import time
import threading
import requests
import io
import tkinter as tk
import tkinter.filedialog as filedialog

# --- AGGRESSIVE PATH FIX ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import customtkinter as ctk
from cryptography.hazmat.primitives import serialization
from network.server import ZTAServer
from network.client import SecureClient
from utils.key_store import save_private_key, load_private_key, has_key

# --- 🎨 CRYPTO DARK THEME CONSTANTS ---
C_BG      = "#0a0b0d"  # Deepest black
C_FRAME   = "#14171a"  # Dark navy/gray frame
C_ACCENT  = "#f0b90b"  # Crypto Gold (Binance-style)
C_TEXT    = "#f5f5f5"  # Off-white text
C_SUBTEXT = "#848e9c"  # Muted slate
C_SUCCESS = "#0ecb81"  # Vibrant green
C_DANGER  = "#f6465d"  # Vibrant red
C_BORDER  = "#2b2f36"  # Subtle border

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue") # We'll override mostly with hex anyway

# ─────────────────────────────────────────────
#  HELPER: pretty-print file size
# ─────────────────────────────────────────────
def _fmt_size(metadata: dict) -> str:
    size = metadata.get("metadata", {}) or {}
    size = size.get("size", None)
    if size is None:
        size = metadata.get("size", None)
    if size is None:
        return "—"
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


class ModernSecureGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Zero-Trust Secure Messenger (Pro)")
        self.geometry("1060x720")
        self.minsize(820, 520)

        print("[System] Connecting to Supabase Cloud...")
        self.server = ZTAServer()
        self.current_user = None

        # Cached list rows for click-to-download
        self._received_rows: list[dict] = []
        self._sent_rows: list[dict] = []

        self.build_login_screen()

    # ==========================================
    # 🔐 LOGIN & REGISTRATION SCREEN
    # ==========================================
    def build_login_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

        # Background gradient-ish frame
        outer = ctk.CTkFrame(self, fg_color=C_BG, corner_radius=0)
        outer.place(relx=0, rely=0, relwidth=1, relheight=1)

        login_frame = ctk.CTkFrame(outer, width=380, corner_radius=18,
                                   fg_color=C_FRAME,
                                   border_color=C_BORDER, border_width=1)
        login_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Logo / branding
        ctk.CTkLabel(login_frame, text="⚡ CRYPTO-ZTA",
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color=C_ACCENT).pack(pady=(40, 4))
        ctk.CTkLabel(login_frame, text="Quantum-Secure Decentralized Gateway",
                     text_color=C_SUBTEXT, font=ctk.CTkFont(size=12)).pack(pady=(0, 28))

        # Username
        self.username_entry = ctk.CTkEntry(login_frame,
                                           placeholder_text="⚡  Identity (Username)",
                                           width=290, height=42,
                                           corner_radius=8,
                                           fg_color=C_BG, border_color=C_BORDER)
        self.username_entry.pack(pady=6)

        # Password
        self.password_entry = ctk.CTkEntry(login_frame,
                                           placeholder_text="🔑  Master Password",
                                           show="★", width=290, height=42,
                                           corner_radius=8,
                                           fg_color=C_BG, border_color=C_BORDER)
        self.password_entry.pack(pady=6)

        # Confirm password (shown only during registration — hidden initially)
        self.confirm_frame = ctk.CTkFrame(login_frame, fg_color="transparent")
        self.confirm_frame.pack()
        self.confirm_entry = ctk.CTkEntry(self.confirm_frame,
                                          placeholder_text="🔑  Confirm Password",
                                          show="★", width=290, height=42,
                                          corner_radius=8,
                                          fg_color=C_BG, border_color=C_BORDER)

        # Mode toggle
        self._register_mode = False
        self.mode_label = ctk.CTkLabel(login_frame, text="", text_color=C_SUBTEXT,
                                       font=ctk.CTkFont(size=11))
        self.mode_label.pack(pady=(4, 0))

        # Primary action button
        self.action_btn = ctk.CTkButton(login_frame, text="Unlock Secure Node",
                                        command=self.handle_action,
                                        width=290, height=44,
                                        corner_radius=8,
                                        font=ctk.CTkFont(weight="bold"),
                                        fg_color=C_ACCENT, text_color=C_BG, 
                                        hover_color="#d6a509")
        self.action_btn.pack(pady=(18, 6))

        # Toggle register / login
        self.toggle_btn = ctk.CTkButton(login_frame,
                                        text="New Identity? Register Vault",
                                        command=self._toggle_register_mode,
                                        width=290, height=36,
                                        fg_color="transparent",
                                        border_width=1, border_color=C_BORDER,
                                        text_color=C_SUBTEXT,
                                        hover_color=C_BG,
                                        font=ctk.CTkFont(size=12))
        self.toggle_btn.pack(pady=4)

        self.status_label = ctk.CTkLabel(login_frame, text="",
                                         text_color=C_ACCENT, wraplength=290,
                                         font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=(10, 30))

    def _toggle_register_mode(self):
        self._register_mode = not self._register_mode
        if self._register_mode:
            self.confirm_entry.pack(pady=6, in_=self.confirm_frame)
            self.action_btn.configure(text="Initialize New Vault",
                                      fg_color=C_SUCCESS, hover_color="#0ba368")
            self.toggle_btn.configure(text="Already have a Vault? Access Node")
            self.mode_label.configure(text="📝 Secure Registration")
        else:
            self.confirm_entry.pack_forget()
            self.action_btn.configure(text="Unlock Secure Node",
                                      fg_color=C_ACCENT, hover_color="#d6a509")
            self.toggle_btn.configure(text="New Identity? Register Vault")
            self.mode_label.configure(text="")

    def handle_action(self):
        if self._register_mode:
            self.handle_register()
        else:
            self.handle_login()

    def handle_register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        confirm  = self.confirm_entry.get()

        if not username:
            self.status_label.configure(text="❌ Username is required!", text_color="red")
            return
        if not password:
            self.status_label.configure(text="❌ Password is required!", text_color="red")
            return
        if len(password) < 6:
            self.status_label.configure(text="❌ Password must be at least 6 characters!", text_color="red")
            return
        if password != confirm:
            self.status_label.configure(text="❌ Passwords do not match — try again!", text_color="red")
            return

        self.status_label.configure(text="⚙  Generating Keys & Encrypting Vault...", text_color="#f0883e")
        self.update()
        try:
            # Remove old cloud records for this username
            headers = self.server.db.headers
            url = self.server.db.url
            requests.delete(f"{url}/rest/v1/messages?sender_username=eq.{username}", headers=headers)
            requests.delete(f"{url}/rest/v1/messages?recipient_username=eq.{username}", headers=headers)
            requests.delete(f"{url}/rest/v1/connections?requester_username=eq.{username}", headers=headers)
            requests.delete(f"{url}/rest/v1/connections?receiver_username=eq.{username}", headers=headers)
            requests.delete(f"{url}/rest/v1/users?username=eq.{username}", headers=headers)

            self.current_user = SecureClient(username, self.server)
            self.current_user.register()

            raw_private_bytes = self.current_user.crypto_engine.get_private_bytes()
            key_path = save_private_key(username, raw_private_bytes, password)

            short_path = os.path.relpath(key_path, os.path.expanduser("~"))
            self.status_label.configure(
                text=f"✅ Vault Secured!\nKey saved to: ~/{short_path}\nYou may now Login.",
                text_color="#3fb950"
            )
        except Exception as e:
            self.status_label.configure(text=f"Error: {e}", text_color="red")

    def handle_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            self.status_label.configure(text="❌ Username and Password required!", text_color="red")
            return

        self.status_label.configure(text="🔓 Decrypting Local Vault...", text_color="#f0883e")
        self.update()

        device_context = {"is_rooted": False, "location": "Headquarters"}

        if not self.current_user or self.current_user.username != username:
            if not has_key(username):
                self.status_label.configure(
                    text="❌ No local vault found.\nPlease register first!",
                    text_color="red"
                )
                return

            private_key_bytes = load_private_key(username, password)

            if private_key_bytes is False:
                self.status_label.configure(
                    text="❌ Access Denied: Incorrect Master Password!",
                    text_color="red"
                )
                return
            elif private_key_bytes is None:
                self.status_label.configure(
                    text="❌ No local vault found.\nPlease register first!",
                    text_color="red"
                )
                return

            self.current_user = SecureClient(username, self.server)
            from core.crypto_utils import CryptoEngine
            self.current_user.crypto_engine = CryptoEngine(private_key_bytes=private_key_bytes)

            all_users = self.server.db.get_all_users()
            for u in all_users:
                if u.get("username") == username:
                    self.current_user.crypto_engine.public_key_hex = u.get("public_key_hex")
                    break

        if self.current_user.login(device_context):
            self.status_label.configure(text="✅ Authentication Success!", text_color="#3fb950")
            self.update()
            time.sleep(0.4)
            self.build_chat_dashboard()
        else:
            self.status_label.configure(text="🚫 Access Denied by Gatekeeper.", text_color="red")
            self.current_user = None

    # ==========================================
    # 💻 MODERN DASHBOARD
    # ==========================================
    def build_chat_dashboard(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.active_contact = None
        self.server._load_existing_users()

        # --- LEFT SIDEBAR ---
        sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=C_FRAME)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text="⚡ CRYPTO-ZTA",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=C_ACCENT).pack(pady=(22, 2))
        ctk.CTkLabel(sidebar, text=f"ID:  {self.current_user.username}",
                     font=ctk.CTkFont(size=12, family="Courier"),
                     text_color=C_SUBTEXT).pack(pady=(0, 16))
        
        # --- SIDEBAR SCROLLABLE CONTENT ---
        self.sidebar_scroll = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.sidebar_scroll.pack(fill="both", expand=True, padx=2, pady=5)

        # Pending Requests Section
        ctk.CTkLabel(self.sidebar_scroll, text="📥  PENDING REQUESTS",
                     text_color=C_ACCENT, font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(10, 5), padx=10, anchor="w")
        self.pending_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        self.pending_frame.pack(fill="x", padx=5)

        ctk.CTkFrame(self.sidebar_scroll, height=1, fg_color=C_BORDER).pack(fill="x", padx=10, pady=10)

        # Verified Contacts Section
        ctk.CTkLabel(self.sidebar_scroll, text="👥  VERIFIED CONTACTS",
                     text_color=C_ACCENT, font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 5), padx=10, anchor="w")
        self.contacts_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        self.contacts_frame.pack(fill="x", padx=5)

        # Status Label in Sidebar
        self.sidebar_status = ctk.CTkLabel(sidebar, text="", text_color=C_ACCENT,
                                           wraplength=240, font=ctk.CTkFont(size=11))
        self.sidebar_status.pack(pady=10, padx=10)

        # BOTTOM BUTTONS
        btn_container = ctk.CTkFrame(sidebar, fg_color="transparent")
        btn_container.pack(side="bottom", fill="x", pady=10, padx=10)

        ctk.CTkButton(btn_container, text="➕ Add Contact",
                      command=self.ui_show_add_contact, height=32,
                      corner_radius=6, fg_color=C_BG, border_width=1, border_color=C_BORDER,
                      hover_color=C_FRAME).pack(pady=4, fill="x")

        ctk.CTkButton(btn_container, text="🚪 Logout",
                      command=self._logout, height=32,
                      corner_radius=6, fg_color="transparent",
                      border_width=1, border_color=C_BORDER,
                      text_color=C_SUBTEXT, hover_color=C_BG).pack(pady=4, fill="x")

        # NOVELTY: Emergency Wipe Button
        ctk.CTkButton(btn_container, text="🔴 EMERGENCY WIPE",
                      command=self.ui_emergency_wipe, height=34,
                      corner_radius=6, fg_color=C_DANGER,
                      text_color=C_BG, hover_color="#c83648",
                      font=ctk.CTkFont(weight="bold")).pack(pady=(12, 4), fill="x")

        # --- RIGHT MAIN AREA ---
        main_area = ctk.CTkFrame(self, corner_radius=0, fg_color=C_BG)
        main_area.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        main_area.grid_rowconfigure(0, weight=1)
        main_area.grid_columnconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(main_area, fg_color=C_FRAME,
                                      segmented_button_fg_color=C_BG,
                                      segmented_button_selected_color=C_ACCENT,
                                      segmented_button_selected_hover_color="#d6a509",
                                      segmented_button_unselected_color=C_FRAME,
                                      text_color=C_TEXT)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # ── TAB 1: Encrypted Chat ──
        self.tab_chat = self.tabview.add("💬  Messenger")
        self.tab_chat.grid_columnconfigure(0, weight=1)
        self.tab_chat.grid_rowconfigure(1, weight=1) # Row 0 is header

        # Chat Header
        self.chat_header = ctk.CTkFrame(self.tab_chat, fg_color=C_BG, height=50, corner_radius=8)
        self.chat_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.chat_header.grid_propagate(False)
        self.chat_name_label = ctk.CTkLabel(self.chat_header, text="Select a contact to start chatting",
                                            font=ctk.CTkFont(size=14, weight="bold"),
                                            text_color=C_ACCENT)
        self.chat_name_label.place(relx=0.05, rely=0.5, anchor="w")

        self.chat_textbox = ctk.CTkTextbox(self.tab_chat, state="disabled",
                                           font=ctk.CTkFont(size=13),
                                           fg_color=C_BG,
                                           text_color=C_TEXT,
                                           border_width=1, border_color=C_BORDER)
        self.chat_textbox.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 8))

        self.msg_entry = ctk.CTkEntry(self.tab_chat,
                                      placeholder_text="Compose encrypted transmission...",
                                      height=42, corner_radius=8,
                                      fg_color=C_BG, border_color=C_BORDER)
        self.msg_entry.grid(row=2, column=0, sticky="ew", padx=(0, 8))
        self.msg_entry.bind("<Return>", lambda e: self.ui_send_message())

        # NOVELTY: Burn After Reading Toggle & Exit Button
        burn_container = ctk.CTkFrame(self.tab_chat, fg_color="transparent")
        burn_container.grid(row=3, column=0, sticky="w", pady=(4, 0))
        
        self.burn_var = ctk.BooleanVar(value=False)
        self.burn_checkbox = ctk.CTkCheckBox(burn_container, text="🔥 Burn Mode",
                                             variable=self.burn_var,
                                             command=self._on_burn_toggle,
                                             fg_color=C_DANGER, hover_color="#c83648",
                                             text_color=C_DANGER, font=ctk.CTkFont(weight="bold"))
        self.burn_checkbox.pack(side="left", padx=(0, 10))
        
        self.exit_burn_btn = ctk.CTkButton(burn_container, text="🛑 Exit & Wipe Chat",
                                           command=self.ui_exit_burn_mode,
                                           height=24, width=120, corner_radius=6,
                                           fg_color=C_DANGER, text_color=C_BG,
                                           hover_color="#c83648", font=ctk.CTkFont(size=11, weight="bold"))
        self.exit_burn_btn.pack(side="left")
        self.exit_burn_btn.pack_forget() # Hide initially

        btn_frame2 = ctk.CTkFrame(self.tab_chat, fg_color="transparent")
        btn_frame2.grid(row=2, column=1, rowspan=2, sticky="ne")
        ctk.CTkButton(btn_frame2, text="🔒 Send", width=88, height=42,
                      corner_radius=8, command=self.ui_send_message,
                      fg_color=C_ACCENT, text_color=C_BG, hover_color="#d6a509").pack(side="left", padx=3)
        ctk.CTkButton(btn_frame2, text="🔄", width=42, height=42,
                      corner_radius=8, command=self.ui_refresh_inbox,
                      fg_color=C_BG, border_width=1, border_color=C_BORDER,
                      hover_color=C_FRAME).pack(side="left")

        # ── TAB 2: Secure Vault ──
        self.tab_files = self.tabview.add("📂  Vault")
        self._build_vault_tab(self.tab_files)

        # ── TAB 3: Visualizer ──
        self.tab_viz = self.tabview.add("🔬  ZTA Core")
        self.tab_viz.grid_columnconfigure(0, weight=1)
        self.tab_viz.grid_rowconfigure(0, weight=1)

        self.viz_textbox = ctk.CTkTextbox(self.tab_viz, state="disabled",
                                          font=ctk.CTkFont(family="Courier New", size=12),
                                          text_color=C_SUCCESS,
                                          fg_color=C_BG,
                                          border_width=1, border_color=C_BORDER)
        self.viz_textbox.grid(row=0, column=0, sticky="nsew")

        # Start background refresh threads
        self.ui_refresh_sidebar()
        
        self.log_to_viz("=== ZERO TRUST ARCHITECTURE INITIALIZED ===")
        self.log_to_viz(f"Node Identity  : {self.current_user.username}")
        self.log_to_viz("ECDH Engine    : X25519 Active")
        self.log_to_viz("Symmetric Algo : AES-256-GCM Active")
        self.log_to_viz("Storage Bucket : secure_vault (Supabase)\n")

    def _logout(self):
        self.current_user = None
        self.build_login_screen()

    # ==========================================
    # 🚨 NOVELTY: EMERGENCY WIPE LOGIC
    # ==========================================
    def ui_emergency_wipe(self):
        # Create a custom confirmation dialog to match the theme
        dialog = ctk.CTkToplevel(self)
        dialog.title("CRITICAL WARNING")
        dialog.geometry("400x200")
        dialog.attributes('-topmost', True)
        dialog.configure(fg_color=C_BG)
        
        # Center dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text="⚠️ INITIATING EMERGENCY WIPE", 
                     text_color=C_DANGER, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))
        ctk.CTkLabel(dialog, text="This will permanently delete your local private key.\nYou will lose access to all encrypted data.\nProceed?",
                     text_color=C_TEXT).pack(pady=(0, 20))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)

        def _execute_wipe():
            dialog.destroy()
            self._perform_wipe()

        ctk.CTkButton(btn_frame, text="CANCEL", command=dialog.destroy,
                      fg_color=C_FRAME, hover_color=C_BORDER).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="CONFIRM WIPE", command=_execute_wipe,
                      fg_color=C_DANGER, text_color=C_BG, hover_color="#c83648").pack(side="right", expand=True, padx=5)

    def _perform_wipe(self):
        self.log_to_viz("\n[CRITICAL] EMERGENCY WIPE PROTOCOL INITIATED.")
        username = self.current_user.username
        
        # Determine path to key
        keys_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "keys"))
        key_path = os.path.join(keys_dir, f"{username}_private.pem")
        
        try:
            if os.path.exists(key_path):
                # Overwrite with garbage before deleting for "forensic security"
                with open(key_path, "wb") as f:
                    f.write(os.urandom(2048))
                os.remove(key_path)
                print(f"[SHREDDING] Key destroyed at {key_path}")
            
            # Force logout
            self.current_user = None
            self.build_login_screen()
            self.status_label.configure(text="🔴 EMERGENCY WIPE SUCCESSFUL. KEY DESTROYED.", text_color=C_DANGER)
            
        except Exception as e:
            self.sidebar_status.configure(text="Wipe failed!", text_color=C_DANGER)
            print(f"Wipe error: {e}")

    # ==========================================
    # 👥 CONTACT MANAGEMENT LOGIC
    # ==========================================
    def ui_show_add_contact(self):
        dialog = ctk.CTkInputDialog(text="Enter the target username to request a secure handshake:", 
                                    title="Connect to Node",
                                    fg_color=C_BG, button_fg_color=C_ACCENT,
                                    button_hover_color="#d6a509",
                                    button_text_color=C_BG)
        target = dialog.get_input()
        if target:
            self.ui_request_connection_by_name(target)

    def ui_refresh_sidebar(self):
        """Periodically refreshes the sidebar lists."""
        if not self.current_user: return

        def _worker():
            try:
                verified = self.current_user.get_verified_contacts()
                pending = self.current_user.get_pending_requests()
                self.after(0, lambda: self._update_sidebar_lists(verified, pending))
            except Exception as e:
                print(f"Sidebar refresh error: {e}")
            
            # Refresh every 10 seconds if still logged in
            if self.current_user:
                self.after(10000, self.ui_refresh_sidebar)

        threading.Thread(target=_worker, daemon=True).start()

    def _update_sidebar_lists(self, verified, pending):
        # Clear frames
        for child in self.pending_frame.winfo_children(): child.destroy()
        for child in self.contacts_frame.winfo_children(): child.destroy()

        # Update Pending
        if not pending:
            ctk.CTkLabel(self.pending_frame, text="No new requests", text_color=C_SUBTEXT, font=ctk.CTkFont(size=10)).pack(pady=5)
        for user in pending:
            row = ctk.CTkFrame(self.pending_frame, fg_color=C_BG, corner_radius=6, border_width=1, border_color=C_BORDER)
            row.pack(fill="x", pady=2, padx=2)
            ctk.CTkLabel(row, text=user, font=ctk.CTkFont(size=12)).pack(side="left", padx=10, pady=5)
            ctk.CTkButton(row, text="Accept", width=60, height=24, corner_radius=4,
                          fg_color=C_SUCCESS, hover_color="#0ba368",
                          command=lambda u=user: self.ui_accept_connection_by_name(u)).pack(side="right", padx=5)

        # Update Verified
        if not verified:
            ctk.CTkLabel(self.contacts_frame, text="No contacts yet", text_color=C_SUBTEXT, font=ctk.CTkFont(size=10)).pack(pady=5)
        for user in verified:
            is_active = (user == self.active_contact)
            row = ctk.CTkButton(self.contacts_frame, text=f"  ●  {user}" if is_active else f"     {user}",
                                anchor="w", height=36, corner_radius=6,
                                fg_color=C_FRAME if not is_active else C_BG,
                                border_width=1 if is_active else 0,
                                border_color=C_ACCENT if is_active else C_FRAME,
                                text_color=C_TEXT if not is_active else C_ACCENT,
                                hover_color=C_BG,
                                command=lambda u=user: self.ui_select_contact(u))
            row.pack(fill="x", pady=2, padx=2)

    def ui_select_contact(self, username):
        self.active_contact = username
        self.chat_name_label.configure(text=f"Secure Channel: {username}")
        
        # If a new contact is selected, uncheck burn box safely
        if hasattr(self, 'burn_checkbox'):
            self.burn_var.set(False)
            if hasattr(self, 'exit_burn_btn'):
                self.exit_burn_btn.pack_forget()
                
        self._refresh_contacts() # Update vault dropdown
        self.ui_refresh_sidebar() # Update selection highlighting
        
        # --- LOAD FULL CHAT HISTORY NATIVELY ---
        self.log_to_viz(f"\n[CHANNEL] Switched to {username}. Fetching full encrypted history...")
        self.chat_textbox.configure(state="normal")
        self.chat_textbox.delete("1.0", "end")
        
        history = self.current_user.fetch_chat_history(username)
        self.rendered_msg_ids = set()
        
        if history:
            for msg in history:
                self.rendered_msg_ids.add(msg["id"])
                sender = msg["sender"]
                text = msg["text"]
                
                # Render BURN messages differently in history
                if text.startswith("[BURN]"):
                    tag = f"burn_hist_{msg['id']}"
                    self.chat_textbox.insert("end", f"🔥 [MESSAGE INCINERATED]\n", tag)
                    self.chat_textbox.tag_config(tag, foreground=C_SUBTEXT, font=ctk.CTkFont(slant="italic"))
                else:
                    if sender == self.current_user.username:
                        self.chat_textbox.insert("end", f"You → {username}: {text}\n")
                    else:
                        self.chat_textbox.insert("end", f"{sender} → You: {text}\n")
        
        self.chat_textbox.configure(state="disabled")
        self.chat_textbox.yview("end")
        self.log_to_viz(f"[CHANNEL] History synchronized. ({len(history)} messages)")

    def ui_request_connection_by_name(self, target):
        self.log_to_viz(f"\n[HANDSHAKE] Initiating request for {target}...")
        self.server._load_existing_users()
        self.current_user.request_connection(target)
        self.sidebar_status.configure(text=f"Request sent to {target}.", text_color=C_ACCENT)
        self.log_to_viz("[HANDSHAKE] Request anchored to Supabase.")
        self.ui_refresh_sidebar()

    def ui_accept_connection_by_name(self, requester):
        self.sidebar_status.configure(text="Verifying Merkle proof...", text_color=C_ACCENT)
        self.update()
        self.log_to_viz(f"\n[VERIFICATION] Rebuilding Merkle Tree for {requester}...")

        self.server._load_existing_users()
        self.current_user.verify_and_accept_connection(requester)

        if self.server.db.check_connection_status(requester, self.current_user.username):
            self.sidebar_status.configure(text=f"✅ Connected with {requester}!", text_color=C_SUCCESS)
            self.log_to_viz("[VERIFICATION] ✅ Identity Verified. Keys mapped.")
            self.ui_refresh_sidebar()
            self._refresh_contacts()
        else:
            self.sidebar_status.configure(text="❌ Verification failed!", text_color=C_DANGER)
            self.log_to_viz("[VERIFICATION] ❌ FAILED. Connection blocked by Gatekeeper.")

    # ==========================================
    # 📂 VAULT TAB (WhatsApp-like File Transfer)
    # ==========================================
    def _build_vault_tab(self, parent: ctk.CTkFrame):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # ── Upload toolbar ──
        toolbar = ctk.CTkFrame(parent, fg_color=C_BG,
                               corner_radius=10, border_width=1,
                               border_color=C_BORDER)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(toolbar, text="📤  DISPATCH ENCRYPTED ASSET",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C_ACCENT).pack(side="left", padx=14, pady=10)

        # Recipient dropdown
        self.recipient_var = ctk.StringVar(value="Select Contact ▾")
        self.recipient_menu = ctk.CTkOptionMenu(toolbar,
                                                variable=self.recipient_var,
                                                values=["— refresh contacts —"],
                                                width=180, height=34,
                                                corner_radius=6,
                                                fg_color=C_FRAME,
                                                button_color=C_BORDER,
                                                button_hover_color=C_ACCENT,
                                                text_color=C_TEXT,
                                                command=None)
        self.recipient_menu.pack(side="left", padx=6, pady=10)

        ctk.CTkButton(toolbar, text="🔄", width=36, height=34,
                      corner_radius=6, fg_color=C_FRAME, hover_color=C_BG,
                      border_width=1, border_color=C_BORDER,
                      command=self._refresh_contacts,
                      font=ctk.CTkFont(size=14)).pack(side="left", padx=2, pady=10)

        ctk.CTkButton(toolbar, text="📤  UPLOAD ASSET",
                      command=self.ui_upload_file,
                      width=130, height=34, corner_radius=6,
                      fg_color=C_ACCENT, text_color=C_BG, hover_color="#d6a509").pack(side="right", padx=14, pady=10)

        # Progress bar (hidden until needed)
        self.vault_progress = ctk.CTkProgressBar(parent, height=6, corner_radius=3,
                                                  progress_color=C_ACCENT,
                                                  fg_color=C_BG)
        self.vault_progress.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        self.vault_progress.set(0)
        self.vault_progress.grid_remove()

        # ── Inner sub-tabs: Received / Sent ──
        self.vault_tabs = ctk.CTkTabview(parent,
                                         fg_color=C_FRAME,
                                         segmented_button_fg_color=C_BG,
                                         segmented_button_selected_color=C_ACCENT,
                                         segmented_button_selected_hover_color="#d6a509",
                                         text_color=C_TEXT)
        self.vault_tabs.grid(row=1, column=0, sticky="nsew")

        self.vtab_recv = self.vault_tabs.add("📥  Inbound")
        self.vtab_sent = self.vault_tabs.add("📤  Outbound")

        for vtab in [self.vtab_recv, self.vtab_sent]:
            vtab.grid_columnconfigure(0, weight=1)
            vtab.grid_rowconfigure(0, weight=1)

        # Received list
        self.recv_scroll = ctk.CTkScrollableFrame(self.vtab_recv,
                                                   fg_color=C_BG,
                                                   corner_radius=8)
        self.recv_scroll.grid(row=0, column=0, sticky="nsew")
        self.recv_scroll.grid_columnconfigure(0, weight=1)

        self.recv_empty_label = ctk.CTkLabel(self.recv_scroll,
                                              text="Vault empty. No incoming transmissions detected. 📡",
                                              text_color=C_SUBTEXT,
                                              font=ctk.CTkFont(size=13))

        # Sent list
        self.sent_scroll = ctk.CTkScrollableFrame(self.vtab_sent,
                                                   fg_color=C_BG,
                                                   corner_radius=8)
        self.sent_scroll.grid(row=0, column=0, sticky="nsew")
        self.sent_scroll.grid_columnconfigure(0, weight=1)

        self.sent_empty_label = ctk.CTkLabel(self.sent_scroll,
                                              text="No records of outbound transmissions. 📤",
                                              text_color=C_SUBTEXT,
                                              font=ctk.CTkFont(size=13))

        # Refresh button bar
        refresh_bar = ctk.CTkFrame(parent, fg_color="transparent")
        refresh_bar.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        ctk.CTkButton(refresh_bar, text="🔄  Sync Vault Records",
                      command=self.ui_refresh_files,
                      height=32, corner_radius=6,
                      fg_color=C_BG, border_width=1, border_color=C_BORDER,
                      hover_color=C_FRAME).pack(side="left")
        self.vault_status = ctk.CTkLabel(refresh_bar, text="",
                                          text_color=C_SUBTEXT,
                                          font=ctk.CTkFont(size=11))
        self.vault_status.pack(side="left", padx=10)

        # Auto-load contacts
        self._refresh_contacts()

    def _refresh_contacts(self):
        """Refresh the recipient dropdown with verified contacts."""
        try:
            contacts = self.current_user.get_verified_contacts()
            if contacts:
                self.recipient_menu.configure(values=contacts)
                self.recipient_var.set(contacts[0])
            else:
                self.recipient_menu.configure(values=["No verified contacts"])
                self.recipient_var.set("No verified contacts")
        except Exception:
            pass

    def _clear_frame(self, frame: ctk.CTkScrollableFrame):
        for widget in frame.winfo_children():
            widget.destroy()

    def _make_file_row(self, parent: ctk.CTkScrollableFrame, row_idx: int,
                       icon: str, label: str, sublabel: str, size_str: str,
                       date_str: str, btn_text: str, btn_cmd, btn_color: str):
        """Creates a single styled file row card inside a scrollable frame."""
        card = ctk.CTkFrame(parent, corner_radius=10,
                            fg_color=C_FRAME,
                            border_width=1, border_color=C_BORDER)
        card.grid(row=row_idx, column=0, sticky="ew", pady=4, padx=4)
        card.grid_columnconfigure(1, weight=1)

        # Icon
        ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=24),
                     width=44).grid(row=0, column=0, rowspan=2, padx=(12, 8), pady=10, sticky="w")

        # Main label (filename)
        ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=C_TEXT, anchor="w").grid(row=0, column=1, sticky="ew", padx=4, pady=(10, 0))

        # Sub-label (sender / recipient)
        ctk.CTkLabel(card, text=sublabel, font=ctk.CTkFont(size=11),
                     text_color=C_SUBTEXT, anchor="w").grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 10))

        # Size + date (right-side)
        meta_frame = ctk.CTkFrame(card, fg_color="transparent")
        meta_frame.grid(row=0, column=2, rowspan=2, padx=(4, 6), pady=4, sticky="ns")
        ctk.CTkLabel(meta_frame, text=size_str, text_color=C_SUBTEXT,
                     font=ctk.CTkFont(size=10)).pack(pady=(8, 0))
        ctk.CTkLabel(meta_frame, text=date_str, text_color=C_SUBTEXT,
                     font=ctk.CTkFont(size=10)).pack()

        # Action button
        ctk.CTkButton(card, text=btn_text, width=110, height=32,
                      corner_radius=6, fg_color=btn_color,
                      text_color=C_BG if btn_color == C_ACCENT else "#ffffff",
                      hover_color="#d6a509" if btn_color == C_ACCENT else "#0ba368",
                      command=btn_cmd).grid(row=0, column=3, rowspan=2,
                                            padx=(4, 12), pady=8)

    def _file_icon(self, filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower().replace("enc", "")
        icons = {
            "pdf": "📄", "doc": "📝", "docx": "📝", "xls": "📊", "xlsx": "📊",
            "png": "🖼", "jpg": "🖼", "jpeg": "🖼", "gif": "🎞",
            "mp4": "🎬", "avi": "🎬", "mov": "🎬",
            "mp3": "🎵", "wav": "🎵",
            "zip": "🗜", "rar": "🗜", "7z": "🗜",
            "py": "🐍", "js": "📜", "txt": "📃", "csv": "📋",
        }
        return icons.get(ext, "📁")

    def _parse_date(self, raw: str) -> str:
        if not raw:
            return "—"
        return raw.split("T")[0]

    # ── File list refresh ──
    def ui_refresh_files(self):
        self._show_progress()

        def _worker():
            try:
                recv_files = self.current_user.list_my_files()
                sent_files = self.current_user.list_sent_files()
            except Exception as e:
                recv_files, sent_files = [], []
                self.after(0, lambda: self.vault_status.configure(
                    text=f"❌ Error: {e}", text_color="red"))
            self._received_rows = recv_files
            self._sent_rows = sent_files
            self.after(0, self._populate_recv_list)
            self.after(0, self._populate_sent_list)
            self.after(0, self._hide_progress)
            self.after(0, lambda: self.vault_status.configure(
                text=f"📦 {len(recv_files)} received, {len(sent_files)} sent",
                text_color="#8b949e"))

        threading.Thread(target=_worker, daemon=True).start()

    def _populate_recv_list(self):
        self._clear_frame(self.recv_scroll)
        files = self._received_rows

        if not files:
            self.recv_empty_label = ctk.CTkLabel(
                self.recv_scroll,
                text="No encrypted files received yet.\nAsk a contact to send you a file! 📭",
                text_color="#8b949e", font=ctk.CTkFont(size=13))
            self.recv_empty_label.grid(row=0, column=0, pady=40)
            return

        for i, f in enumerate(files):
            name = f.get("name", "unknown")
            # remote path is {my_username}/{sender}_{filename}.enc
            remote_path = f"{self.current_user.username}/{name}"

            # Parse sender from filename: {sender}_{rest}
            parts = name.split("_", 1)
            sender = parts[0] if len(parts) > 1 else "unknown"
            original_name = parts[1] if len(parts) > 1 else name

            size_str = _fmt_size(f)
            date_str = self._parse_date(f.get("created_at", ""))
            icon = self._file_icon(original_name)

            # Capture for closure
            def make_dl(rp=remote_path, snd=sender):
                return lambda: self._download_file(rp, snd)

            self._make_file_row(
                self.recv_scroll, i,
                icon=icon,
                label=original_name,
                sublabel=f"From: {sender}",
                size_str=size_str,
                date_str=date_str,
                btn_text="⬇  Download",
                btn_cmd=make_dl(),
                btn_color=C_ACCENT
            )

    def _populate_sent_list(self):
        self._clear_frame(self.sent_scroll)
        files = self._sent_rows

        if not files:
            self.sent_empty_label = ctk.CTkLabel(
                self.sent_scroll,
                text="No files sent yet.\nUpload a file to a contact to get started! 📤",
                text_color="#8b949e", font=ctk.CTkFont(size=13))
            self.sent_empty_label.grid(row=0, column=0, pady=40)
            return

        for i, f in enumerate(files):
            name     = f.get("name", "unknown")
            recipient = f.get("_recipient", "unknown")
            remote_path = f.get("_remote_path", "")

            # Parse original name: strip {sender}_ prefix
            parts = name.split("_", 1)
            original_name = parts[1] if len(parts) > 1 else name

            size_str = _fmt_size(f)
            date_str = self._parse_date(f.get("created_at", ""))
            icon = self._file_icon(original_name)

            # Sent files: offer re-download (my own copy) — decrypt as myself
            def make_dl(rp=remote_path, rcpt=recipient):
                return lambda: self._download_file(rp, self.current_user.username)

            self._make_file_row(
                self.sent_scroll, i,
                icon=icon,
                label=original_name,
                sublabel=f"To: {recipient}",
                size_str=size_str,
                date_str=date_str,
                btn_text="⬇  Download",
                btn_cmd=make_dl(),
                btn_color=C_SUCCESS
            )

    # ── Upload ──
    def ui_upload_file(self):
        target = self.recipient_var.get()
        if not target or target in ("Select Contact ▾", "No verified contacts",
                                    "— refresh contacts —"):
            self.vault_status.configure(
                text="❌ Select a verified contact first!", text_color=C_DANGER)
            return

        file_path = filedialog.askopenfilename(
            title="Select file to encrypt and upload")
        if not file_path:
            return

        self._show_progress(indeterminate=True)
        self.vault_status.configure(
            text=f"🔒 Encrypting & uploading to {target}...", text_color=C_ACCENT)
        self.update()

        def _worker():
            try:
                ok = self.current_user.upload_secure_file(file_path, target)
            except Exception as e:
                ok = False
                self.after(0, lambda: self.vault_status.configure(
                    text=f"❌ Upload error: {e}", text_color=C_DANGER))
            self.after(0, self._hide_progress)
            if ok:
                self.after(0, lambda: self.vault_status.configure(
                    text=f"✅ File uploaded to {target}'s vault!", text_color=C_SUCCESS))
                self.after(100, self.ui_refresh_files)
            else:
                self.after(0, lambda: self.vault_status.configure(
                    text="❌ Upload failed. Check connection.", text_color=C_DANGER))

        threading.Thread(target=_worker, daemon=True).start()

    # ── Download (called from row button) ──
    def _download_file(self, remote_path: str, sender: str):
        self._show_progress(indeterminate=True)
        self.vault_status.configure(
            text=f"🔓 Decrypting {os.path.basename(remote_path)}...",
            text_color=C_ACCENT)
        self.update()

        def _worker():
            try:
                decrypted_bytes = self.current_user.download_secure_file(remote_path, sender)
            except Exception as e:
                decrypted_bytes = None
                self.after(0, lambda: self.vault_status.configure(
                    text=f"❌ Decryption error: {e}", text_color=C_DANGER))

            self.after(0, self._hide_progress)

            if decrypted_bytes:
                # Strip .enc from suggested filename
                base = os.path.basename(remote_path)
                # remove sender_ prefix
                parts = base.split("_", 1)
                suggested = parts[1].replace(".enc", "") if len(parts) > 1 else base.replace(".enc", "")
                self.after(0, lambda: self._save_decrypted(decrypted_bytes, suggested))
            else:
                self.after(0, lambda: self.vault_status.configure(
                    text="❌ Download/Decryption failed!", text_color=C_DANGER))

        threading.Thread(target=_worker, daemon=True).start()

    def _save_decrypted(self, data: bytes, suggested: str):
        save_path = filedialog.asksaveasfilename(
            title="Save decrypted file", initialfile=suggested)
        if save_path:
            with open(save_path, "wb") as fh:
                fh.write(data)
            self.vault_status.configure(
                text=f"✅ Saved: {os.path.basename(save_path)}", text_color=C_SUCCESS)

    # ── Progress bar helpers ──
    def _show_progress(self, indeterminate: bool = False):
        self.vault_progress.grid()
        if indeterminate:
            self.vault_progress.configure(mode="indeterminate")
            self.vault_progress.start()
        else:
            self.vault_progress.configure(mode="determinate")
            self.vault_progress.set(0)

    def _hide_progress(self):
        self.vault_progress.stop()
        self.vault_progress.set(0)
        self.vault_progress.grid_remove()

    # ==========================================
    # ⚙️ CHAT UI ACTIONS & LOGGING
    # ==========================================
    def log_to_chat(self, text):
        self.chat_textbox.configure(state="normal")
        self.chat_textbox.insert("end", text + "\n")
        self.chat_textbox.configure(state="disabled")
        self.chat_textbox.yview("end")

    def log_to_viz(self, text):
        self.viz_textbox.configure(state="normal")
        self.viz_textbox.insert("end", text + "\n")
        self.viz_textbox.configure(state="disabled")
        self.viz_textbox.yview("end")

    def ui_send_message(self):
        target = self.active_contact
        msg = self.msg_entry.get().strip()
        if not target:
            self.sidebar_status.configure(text="Select a contact first!", text_color=C_DANGER)
            return
        if not msg:
            return
            
        is_burn = self.burn_var.get()
        if is_burn:
            msg = f"[BURN]{msg}"
            self.log_to_chat(f"You (🔥) → {target}: {msg[6:]}")
        else:
            self.log_to_chat(f"You → {target}: {msg}")
            
        self.log_to_viz(f"\n[ENCRYPTION] Packaging payload for {target}...")
        
        # NOVELTY: Simulated Onion Routing Visuals
        import random
        nodes = ["Alpha [Zürich]", "Sigma [Tokyo]", "Omega [Reykjavik]", "Delta [Panama]", "Echo [Singapore]"]
        route = random.sample(nodes, 3)
        self.log_to_viz(f"[ROUTING] Relaying via {route[0]} -> {route[1]} -> {route[2]}")
        
        self.server._load_existing_users()
        self.current_user.send_message(target, msg)
        self.msg_entry.delete(0, "end")
        
        # Uncheck burn box after sending
        if is_burn:
            self.burn_checkbox.deselect()
            
        self.log_to_viz("[ENCRYPTION] AES-GCM Ciphertext anchored to Cloud.")

    def ui_refresh_inbox(self):
        if not self.active_contact:
            self.log_to_viz("\n[DECRYPTION] No active channel selected.")
            return

        self.log_to_viz(f"\n[DECRYPTION] Syncing channel with {self.active_contact}...")
        self.server._load_existing_users()
        
        if not hasattr(self, 'rendered_msg_ids'):
            self.rendered_msg_ids = set()
            
        history = self.current_user.fetch_chat_history(self.active_contact)
        new_msgs = [m for m in history if m["id"] not in self.rendered_msg_ids]
        
        if not new_msgs:
            self.log_to_viz("[DECRYPTION] No new encrypted packets found.")
            return
            
        self.log_to_viz(f"[DECRYPTION] {len(new_msgs)} new payloads received. Validating & decrypting...")
        
        for msg in new_msgs:
            self.rendered_msg_ids.add(msg["id"])
            sender = msg["sender"]
            text = msg["text"]
            
            if sender == self.current_user.username:
                continue # We already rendered this locally when we sent it
                
            if text.startswith("[BURN]"):
                clean_msg = text[6:]
                tag = f"burn_{time.time()}_{msg['id']}"
                
                self.chat_textbox.configure(state="normal")
                self.chat_textbox.insert("end", f"🔥 {sender} -> You: {clean_msg}\n", tag)
                self.chat_textbox.tag_config(tag, foreground=C_DANGER)
                self.chat_textbox.configure(state="disabled")
                self.chat_textbox.yview("end")
                
                self.log_to_viz(f" >> [BURN MESSAGE DETECTED] Auto-destruct initiated.")
                self._schedule_burn(tag, clean_msg)
            else:
                self.log_to_chat(f"{sender} → You: {text}")
                self.log_to_viz(f" >> {text[:50]}... [Decrypted]")
        
        # Notifying for other channels (unread indicator placeholder)
        # You could fetch all channels here, but to keep it fast we just sync active contact.

    def _schedule_burn(self, tag, message_text):
        """Deletes a message tagged with `tag` after 10 seconds."""
        def _burn_it():
            self.chat_textbox.configure(state="normal")
            
            # Find the start index of the tagged text
            start_index = self.chat_textbox.tag_ranges(tag)
            if start_index:
                self.chat_textbox.delete(start_index[0], start_index[1])
                self.chat_textbox.insert(start_index[0], "[MESSAGE INCINERATED]\n", f"{tag}_deleted")
                self.chat_textbox.tag_config(f"{tag}_deleted", foreground=C_SUBTEXT, font=ctk.CTkFont(slant="italic"))
            
            self.chat_textbox.configure(state="disabled")
        
        # Schedule after 10 seconds
        self.after(10000, _burn_it)

    def _on_burn_toggle(self):
        """Called when the burn checkbox is turned on or off."""
        if self.burn_var.get():
            self.exit_burn_btn.pack(side="left")
            self.sidebar_status.configure(text="🔥 Burn mode ACTIVATED.", text_color=C_DANGER)
            self.log_to_viz("\n[PROTOCOL] Burn Mode Activated. Messages will self-destruct.")
        else:
            self.exit_burn_btn.pack_forget()
            
    def ui_exit_burn_mode(self):
        """Permanently wipes Burn records and exits burn mode."""
        if not self.active_contact:
            return
            
        target = self.active_contact
        self.log_to_viz(f"\n[PROTOCOL] Exiting Burn Mode. Purging all [BURN] records with {target}...")
        
        # 1. Purge from Backend
        success = self.current_user.delete_burn_messages_with(target)
        
        # 2. selectively Purge Burn markers from UI
        self.chat_textbox.configure(state="normal")
        all_text = self.chat_textbox.get("1.0", "end").split("\n")
        # Keep lines that aren't burn-related
        filtered_text = [line for line in all_text if "🔥" not in line and "[MESSAGE INCINERATED]" not in line]
        
        self.chat_textbox.delete("1.0", "end")
        # remove empty strings at the end due to split
        while filtered_text and not filtered_text[-1].strip():
            filtered_text.pop()
            
        self.chat_textbox.insert("end", "\n".join(filtered_text) + "\n")
        self.chat_textbox.configure(state="disabled")
        self.chat_textbox.yview("end")
        
        # 3. Reset State
        self.burn_var.set(False)
        self.exit_burn_btn.pack_forget()
        
        if success:
            self.sidebar_status.configure(text=f"Burn traces with {target} wiped.", text_color=C_SUCCESS)
            self.log_to_viz(f"[PROTOCOL] Burn conversation history thoroughly scrubbed.")
        else:
            self.sidebar_status.configure(text="Wipe failed!", text_color=C_DANGER)

if __name__ == "__main__":
    app = ModernSecureGUI()
    app.mainloop()
