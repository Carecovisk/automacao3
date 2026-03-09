import tkinter as tk


class SplashScreen:
    def __init__(self, url: str):
        self.url = url
        self.root = tk.Tk()
        self._build()

    def _build(self):
        root = self.root
        root.title("Iniciando aplicação")
        root.resizable(False, False)
        root.configure(bg="#1e1e2e")
        root.attributes("-topmost", True)

        frame = tk.Frame(root, bg="#1e1e2e", padx=48, pady=36)
        frame.pack()

        tk.Label(
            frame,
            text="Iniciando servidor...",
            font=("Segoe UI", 15, "bold"),
            bg="#1e1e2e",
            fg="#cdd6f4",
        ).pack(pady=(0, 10))

        tk.Label(
            frame,
            text="Aguarde enquanto o servidor web é iniciado.\nEsta janela será fechada automaticamente.",
            font=("Segoe UI", 10),
            bg="#1e1e2e",
            fg="#a6adc8",
            justify="center",
        ).pack(pady=(0, 20))

        tk.Label(
            frame,
            text="URL da aplicação:",
            font=("Segoe UI", 9),
            bg="#1e1e2e",
            fg="#6c7086",
        ).pack()

        tk.Label(
            frame,
            text=self.url,
            font=("Segoe UI", 11, "bold"),
            bg="#1e1e2e",
            fg="#89b4fa",
            cursor="hand2",
        ).pack(pady=(2, 0))

        # Center on screen
        root.update_idletasks()
        w = root.winfo_reqwidth()
        h = root.winfo_reqheight()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def close(self):
        """Thread-safe: schedules window destruction from any thread."""
        self.root.after(0, self.root.destroy)

    def run(self):
        """Start the tkinter event loop (blocks until the window is closed)."""
        self.root.mainloop()
