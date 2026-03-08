import base64
import io
import os
import threading
from socket import socket, AF_INET, SOCK_STREAM

from customtkinter import *
from tkinter import filedialog
from PIL import Image

HOST = "127.0.0.1"
PORT = 80

set_appearance_mode("dark")
set_default_color_theme("blue")


class ChatApp(CTk):

    def __init__(self):
        super().__init__()

        self.geometry("760x660")
        self.title("💬 Online Chat")
        self.configure(fg_color="#141414")

        # СОКЕТ НЕ МІНЯЮ
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.sock.connect((HOST, PORT))

        self.username = None
        self.images_cache = []

        self.show_auth_screen()

    # ================= AUTH =================

    def show_auth_screen(self):
        self.auth_frame = CTkFrame(self, corner_radius=25)
        self.auth_frame.place(relx=0.5, rely=0.5, anchor="center")

        CTkLabel(self.auth_frame,
                 text="💬 Вхід у чат",
                 font=("Arial", 28, "bold")).pack(pady=(30, 20))

        self.login_entry = CTkEntry(
            self.auth_frame,
            placeholder_text="Логін",
            width=260,
            height=42,
            corner_radius=12
        )
        self.login_entry.pack(pady=10)

        self.pass_entry = CTkEntry(
            self.auth_frame,
            placeholder_text="Пароль",
            show="*",
            width=260,
            height=42,
            corner_radius=12
        )
        self.pass_entry.pack(pady=10)

        CTkButton(self.auth_frame,
                  text="Увійти",
                  width=260,
                  height=42,
                  corner_radius=12,
                  command=self.login).pack(pady=(20, 10))

        CTkButton(self.auth_frame,
                  text="Створити акаунт",
                  width=260,
                  height=38,
                  fg_color="transparent",
                  border_width=1,
                  corner_radius=12,
                  command=self.register).pack(pady=(0, 20))

        self.status_label = CTkLabel(self.auth_frame, text="")
        self.status_label.pack(pady=(0, 20))

    def login(self):
        username = self.login_entry.get()
        password = self.pass_entry.get()

        self.sock.send(f"LOGIN@{username}@{password}".encode())
        response = self.sock.recv(1024).decode().strip()

        if response == "LOGIN_OK":
            self.username = username
            self.auth_frame.destroy()
            self.build_chat()
            threading.Thread(target=self.receive_loop,
                             daemon=True).start()
        else:
            self.status_label.configure(text="❌ Невірні дані",
                                        text_color="red")

    def register(self):
        username = self.login_entry.get()
        password = self.pass_entry.get()

        self.sock.send(f"REGISTER@{username}@{password}".encode())
        response = self.sock.recv(1024).decode().strip()

        if response == "REGISTER_OK":
            self.status_label.configure(text="✅ Зареєстровано",
                                        text_color="green")
        else:
            self.status_label.configure(text="❌ Користувач існує",
                                        text_color="red")

    # ================= CHAT =================

    def build_chat(self):

        self.header = CTkFrame(self, height=60, fg_color="#0f0f0f")
        self.header.pack(fill="x")

        CTkLabel(self.header,
                 text=f"👤 {self.username}",
                 font=("Arial", 18, "bold")).pack(side="left",
                                                  padx=20,
                                                  pady=15)

        self.chat_frame = CTkScrollableFrame(
            self,
            fg_color="#141414"
        )
        self.chat_frame.pack(fill="both",
                             expand=True,
                             padx=15,
                             pady=10)

        bottom = CTkFrame(self,
                          height=70,
                          fg_color="#0f0f0f")
        bottom.pack(fill="x")

        self.entry = CTkEntry(
            bottom,
            placeholder_text="Напиши повідомлення...",
            height=44,
            corner_radius=25
        )
        self.entry.pack(side="left",
                        fill="x",
                        expand=True,
                        padx=15,
                        pady=15)

        CTkButton(bottom,
                  text="📷",
                  width=45,
                  height=44,
                  corner_radius=25,
                  command=self.send_image).pack(side="right",
                                                padx=5)

        CTkButton(bottom,
                  text="➤",
                  width=45,
                  height=44,
                  corner_radius=25,
                  command=self.send_message).pack(side="right",
                                                  padx=5)

    def add_message(self, text, author=None, image=None):

        is_me = author == self.username

        bubble = CTkFrame(
            self.chat_frame,
            fg_color="#2979ff" if is_me else "#262626",
            corner_radius=18
        )

        bubble.pack(anchor="e" if is_me else "w",
                    pady=6,
                    padx=10)

        if image:
            self.images_cache.append(image)
            CTkLabel(bubble,
                     text=text,
                     image=image,
                     compound="top",
                     wraplength=420,
                     text_color="white").pack(padx=14,
                                              pady=10)
        else:
            CTkLabel(bubble,
                     text=text,
                     wraplength=420,
                     text_color="white",
                     justify="left").pack(padx=14,
                                          pady=10)

    # ================= SEND =================

    def send_message(self):
        msg = self.entry.get().strip()
        if not msg:
            return

        self.sock.send(f"TEXT@{msg}".encode())
        self.add_message(msg, self.username)
        self.entry.delete(0, END)

    def send_image(self):
        file_name = filedialog.askopenfilename()
        if not file_name:
            return

        with open(file_name, "rb") as f:
            raw = f.read()

        b64_data = base64.b64encode(raw).decode()
        short_name = os.path.basename(file_name)

        self.sock.send(f"IMAGE@{short_name}@{b64_data}".encode())

        pil_img = Image.open(file_name)
        img = CTkImage(light_image=pil_img, size=(300, 300))
        self.add_message(short_name, self.username, img)

    # ================= RECEIVE =================

    def receive_loop(self):
        buffer = ""
        while True:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break

                buffer += chunk.decode()

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    self.handle_line(line.strip())

            except:
                break

    def handle_line(self, line):
        parts = line.split("@", 3)

        if parts[0] == "TEXT":
            self.after(0, self.add_message,
                       parts[2], parts[1])

        elif parts[0] == "SYSTEM":
            self.after(0, self.add_message,
                       f"🔔 {parts[1]}")

        elif parts[0] == "IMAGE":
            author = parts[1]
            filename = parts[2]
            img_data = base64.b64decode(parts[3])
            pil_img = Image.open(io.BytesIO(img_data))
            img = CTkImage(light_image=pil_img,
                           size=(300, 300))

            self.after(0, self.add_message,
                       filename, author, img)


if __name__ == "__main__":
    app = ChatApp()
    app.mainloop()