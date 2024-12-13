# View
import customtkinter as ctk


class ScraperView(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("OLX Scraper")
        self.geometry("800x600")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)

        # URL Input
        self.url_entry = ctk.CTkEntry(self, width=400, placeholder_text="Category URL:")
        self.url_entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        # Output File Name
        self.name_entry = ctk.CTkEntry(self, width=400, placeholder_text="Output File Name:")
        self.name_entry.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")

        # Output Path Selection
        self.path_frame = ctk.CTkFrame(self)
        self.path_frame.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        self.path_frame.grid_columnconfigure(0, weight=1)

        self.path_entry = ctk.CTkEntry(self.path_frame, placeholder_text="Save File Path:")
        self.path_entry.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.path_button = ctk.CTkButton(self.path_frame, text="Browse", width=100)
        self.path_button.grid(row=0, column=1, padx=(0, 0))

        # Combined Limits Frame
        self.limits_frame = ctk.CTkFrame(self)
        self.limits_frame.grid(row=5, column=0, padx=10, pady=5, sticky="ew")
        self.limits_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Item Limit Controls
        self.limit_label = ctk.CTkLabel(self.limits_frame, text="Item Limit:")
        self.limit_label.grid(row=0, column=0, padx=5)

        self.limit_entry = ctk.CTkEntry(self.limits_frame, width=100)
        self.limit_entry.grid(row=0, column=1, padx=5)
        self.limit_entry.insert(0, "10")

        # Page Limit Controls
        self.page_limit_label = ctk.CTkLabel(self.limits_frame, text="Max Pages:")
        self.page_limit_label.grid(row=0, column=2, padx=5)

        self.page_limit_entry = ctk.CTkEntry(self.limits_frame, width=100)
        self.page_limit_entry.grid(row=0, column=3, padx=5)
        self.page_limit_entry.insert(0, "100")

        # Log Window
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=6, column=0, padx=10, pady=5, sticky="nsew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(self.log_frame)
        self.log_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=7, column=0, padx=10, pady=10, sticky="ew")
        self.progress_bar.set(0)

        # Control Buttons
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=8, column=0, padx=10, pady=10)

        self.start_button = ctk.CTkButton(self.button_frame, text="Start Parsing", width=120)
        self.start_button.grid(row=0, column=0, padx=5)

        self.stop_button = ctk.CTkButton(self.button_frame, text="Stop Parsing", width=120, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5)

    def update_progress(self, value: float):
        self.progress_bar.set(value)

    def add_log(self, message: str):
        self.log_text.insert('end', message + '\n')
        self.log_text.see('end')

    def set_controls_state(self, is_running: bool):
        state = "disabled" if is_running else "normal"
        reverse_state = "normal" if is_running else "disabled"

        self.url_entry.configure(state=state)
        self.name_entry.configure(state=state)
        self.path_entry.configure(state=state)
        self.path_button.configure(state=state)
        self.limit_entry.configure(state=state)
        self.page_limit_entry.configure(state=state)  # Added this line
        self.start_button.configure(state=state)
        self.stop_button.configure(state=reverse_state)

    def on_closing(self):
        self.quit()