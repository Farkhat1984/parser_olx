# Controller
import threading
from tkinter import filedialog
from model import ScraperModel
from view import ScraperView


class ScraperController:
    def __init__(self):
        self.model = ScraperModel()
        self.view = ScraperView()

        # Bind events
        self.view.path_button.configure(command=self.browse_path)
        self.view.start_button.configure(command=self.start_scraping)
        self.view.stop_button.configure(command=self.stop_scraping)

        # Start log checker
        self.check_logs()

    def check_logs(self):
        while not self.model.log_queue.empty():
            message = self.model.log_queue.get()
            self.view.add_log(message)
        self.view.after(100, self.check_logs)

    def browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.view.path_entry.delete(0, 'end')
            self.view.path_entry.insert(0, path)

    def update_progress(self, current: float):
        self.view.update_progress(current)

    def on_scraping_complete(self):
        self.view.after(0, self._handle_completion)

    def _handle_completion(self):
        self.model.log("Scraping completed!")
        self.view.set_controls_state(False)
        self.view.update_progress(1.0)

    def start_scraping(self):
        if not self.validate_inputs():
            self.model.log("Invalid inputs. Please check all fields.")
            return

        # Update model config
        self.model.config.url = self.view.url_entry.get()
        self.model.config.output_name = self.view.name_entry.get()
        self.model.config.output_path = self.view.path_entry.get()
        self.model.config.item_limit = int(self.view.limit_entry.get())
        self.model.config.page_limit = int(self.view.page_limit_entry.get())

        # Update UI state
        self.view.set_controls_state(True)
        self.view.update_progress(0)

        # Start scraping in a separate thread
        self.model.log("Starting scraping process...")
        thread = threading.Thread(
            target=self.model.start_scraping,
            args=(self.update_progress, self.on_scraping_complete)
        )
        thread.daemon = True
        thread.start()

    def stop_scraping(self):
        self.model.log("Stopping scraping process...")
        self.model.stop_scraping()
        self.view.set_controls_state(False)

    def validate_inputs(self) -> bool:
        if not self.view.url_entry.get():
            return False
        if not self.view.name_entry.get():
            return False
        if not self.view.path_entry.get():
            return False
        try:
            limit = int(self.view.limit_entry.get())
            page_limit = int(self.view.page_limit_entry.get())
            if limit <= 0 or page_limit <= 0:
                return False
        except ValueError:
            return False
        return True
    def run(self):
        self.view.mainloop()