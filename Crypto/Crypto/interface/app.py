import sys
import os
import time
import requests
import io

# --- AGGRESSIVE PATH FIX ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import customtkinter as ctk
from network.server import ZTAServer
from network.client import SecureClient
from utils.key_store import save_private_key, load_private_key

# --- 🎨 THEME SETUP ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green") 

class SecureChatGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Zero-Trust Secure Messenger")
        self.geometry("400x400")
        self.resizable(False, False)

        print("[System] Connecting to Supabase Cloud...")
        self.server = ZTAServer()
        self.current_user = None

        self.build_login_screen()

    def build_login_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.geometry("400x400")

        title = ctk.CTkLabel(self, text="SECURE NODE", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=(40, 10))

        subtitle = ctk.CTkLabel(self, text="End-to-End Identity Bound Encryption", text_color="gray")
        subtitle.pack(pady=(0, 30))

        self.username_entry = ctk.CTkEntry(self, placeholder_text="Enter Username", width=250)
        self.username_entry.pack(pady=10)

        login_btn = ctk.CTkButton(self, text="Zero-Trust Login", command=self.handle_login, width=250)
        login_btn.pack(pady=10)

        register_btn = ctk.CTkButton(self, text="Register Identity", command=self.handle_register, width=250, fg_color="transparent", border_width=1)
        register_btn.pack(pady=10)

        self.status_label = ctk.CTkLabel(self, text="", text_color="yellow")
        self.status_label.pack(pady=20)

    def handle_register(self):
        username = self.username_entry.get().strip()
        if not username: return
        self.status_label.configure(text="Generating Keys & Anchoring to Cloud...", text_color="yellow")
        self.update() 
        try:
            # 🔥 FIX 1: Strict CASCADE Deletion to destroy Ghost Clones
            headers = self.server.db.headers
            url = self.server.db.url
            
            # Must delete messages and connections BEFORE the user, or the DB blocks it!
            requests.delete(f"{url}/rest/v1/messages?sender_username=eq.{username}", headers=headers)
            requests.delete(f"{url}/rest/v1/messages?recipient_username=eq.{username}", headers=headers)
            requests.delete(f"{url}/rest/v1/connections?requester=eq.{username}", headers=headers)
            requests.delete(f"{url}/rest/v1/connections?target=eq.{username}", headers=headers)
            requests.delete(f"{url}/rest/v1/users?username=eq.{username}", headers=headers)
            
            # Now register the fresh identity safely
            self.current_user = SecureClient(username, self.server)
            self.current_user.register()
            # Persist private key locally so decryption works on next login
            save_private_key(username, self.current_user.crypto_engine.get_private_bytes())
            self.status_label.configure(text="Identity Registered! You may now Login.", text_color="green")
        except Exception as e:
            self.status_label.configure(text=f"Error: {e}", text_color="red")

    def handle_login(self):
        username = self.username_entry.get().strip()
        if not username: return
        self.status_label.configure(text="Running Zero-Trust Checks...", text_color="yellow")
        self.update()

        device_context = {"is_rooted": False, "location": "Headquarters"}
        
        # Use existing client if just registered; otherwise load stored key for decryption
        if not self.current_user or self.current_user.username != username:
            private_key_bytes = load_private_key(username)
            if private_key_bytes is None:
                self.status_label.configure(
                    text="No key found. Register first, or restore keys from this machine.",
                    text_color="red"
                )
                return
            self.current_user = SecureClient(username, self.server, private_key_bytes=private_key_bytes)
        
        if self.current_user.login(device_context):
            self.status_label.configure(text="Authentication Success!", text_color="green")
            self.update()
            time.sleep(0.5)
            self.build_chat_dashboard()
        else:
            self.status_label.configure(text="Access Denied by Gatekeeper.", text_color="red")
            self.current_user = None

    # --- 💻 THE MAIN DASHBOARD ---
    def build_chat_dashboard(self):
        for widget in self.winfo_children():
            widget.destroy()
            
        self.geometry("800x500")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # --- LEFT PANEL: Handshake & Identity ---
        left_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        left_frame.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(left_frame, text=f"👤 {self.current_user.username}", font=ctk.CTkFont(size=20, weight="bold"), text_color="#00FF41").pack(pady=20)
        
        ctk.CTkLabel(left_frame, text="--- 🤝 Handshake ---", text_color="gray").pack(pady=(10,5))
        
        self.target_user_entry = ctk.CTkEntry(left_frame, placeholder_text="Target Username")
        self.target_user_entry.pack(pady=5, padx=20)
        
        ctk.CTkButton(left_frame, text="Request Connection", command=self.ui_request_connection).pack(pady=5, padx=20)
        
        ctk.CTkLabel(left_frame, text="Verify Incoming:", text_color="gray").pack(pady=(20,5))
        self.incoming_user_entry = ctk.CTkEntry(left_frame, placeholder_text="Requester Username")
        self.incoming_user_entry.pack(pady=5, padx=20)
        
        ctk.CTkButton(left_frame, text="✅ Verify Identity", command=self.ui_accept_connection, fg_color="transparent", border_width=1).pack(pady=5, padx=20)

        self.ui_status_label = ctk.CTkLabel(left_frame, text="", text_color="yellow", wraplength=200)
        self.ui_status_label.pack(pady=20)

        # --- RIGHT PANEL: Encrypted Chat ---
        right_frame = ctk.CTkFrame(self, corner_radius=0)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        self.chat_textbox = ctk.CTkTextbox(right_frame, state="disabled", font=ctk.CTkFont(size=14))
        self.chat_textbox.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0,10))

        self.msg_entry = ctk.CTkEntry(right_frame, placeholder_text="Type encrypted message...")
        self.msg_entry.grid(row=1, column=0, sticky="ew", padx=(0,10))

        ctk.CTkButton(right_frame, text="🔒 Send", width=80, command=self.ui_send_message).grid(row=1, column=1)
        ctk.CTkButton(right_frame, text="🔄 Fetch Inbox", width=80, command=self.ui_refresh_inbox, fg_color="#333333").grid(row=2, column=1, pady=10)

        self.log_to_chat("[System] Node initialized. Zero Trust Network active.\n")

    # --- UI ACTIONS ---
    def log_to_chat(self, text):
        self.chat_textbox.configure(state="normal")
        self.chat_textbox.insert("end", text + "\n")
        self.chat_textbox.configure(state="disabled")
        self.chat_textbox.yview("end")

    def ui_request_connection(self):
        target = self.target_user_entry.get().strip()
        if not target: return
        self.current_user.request_connection(target)
        self.ui_status_label.configure(text=f"Connection request sent to {target}.", text_color="yellow")

    def ui_accept_connection(self):
        requester = self.incoming_user_entry.get().strip()
        if not requester: return
        
        self.ui_status_label.configure(text="Verifying cryptographic proof...", text_color="yellow")
        self.update()

        # Sync the local Blockchain before doing the math!
        self.server._load_existing_users()
        self.current_user.verify_and_accept_connection(requester)
        
        if self.server.db.check_connection_status(requester, self.current_user.username):
            self.ui_status_label.configure(text=f"Verified & Connected with {requester}!", text_color="#00FF41")
        else:
            self.ui_status_label.configure(text=f"Verification failed! Check terminal.", text_color="red")

    def ui_send_message(self):
        target = self.target_user_entry.get().strip()
        msg = self.msg_entry.get().strip()
        if not target or not msg: return
        
        # Force the local Blockchain to sync with the Cloud before encrypting
        self.server._load_existing_users() 
        
        self.log_to_chat(f"\nYou -> {target}: {msg}")
        self.current_user.send_message(target, msg)
        self.msg_entry.delete(0, 'end')

    def ui_refresh_inbox(self):
        # Force the local Blockchain to sync
        self.server._load_existing_users()
        
        # 🔥 FIX 2: Hijack the terminal output to use your flawless core engine!
        captured_output = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output  # Temporarily mute the terminal
        
        try:
            # Run the EXACT same function that works perfectly in main.py
            self.current_user.check_inbox()
        except Exception as e:
            print(f"🚨 Terminal Error: {e}")
        finally:
            sys.stdout = old_stdout  # Give the terminal its print power back
            
        output = captured_output.getvalue().strip()
        
        if not output or "empty" in output.lower() or "0 new" in output.lower():
            self.ui_status_label.configure(text="Inbox empty.", text_color="gray")
        else:
            # Clean up the terminal logs and inject them right into the UI chat box
            self.log_to_chat("\n📥 Fetched from Cloud:")
            for line in output.split('\n'):
                if line.strip():  # Ignore empty blank lines
                    self.log_to_chat(line.strip())

if __name__ == "__main__":
    app = SecureChatGUI()
    app.mainloop()