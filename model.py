from dataclasses import dataclass
from typing import Callable, List
import threading
import os
from datetime import datetime
from queue import Queue
from service import OlxScraper



@dataclass
class ScraperConfig:
    url: str = ""
    output_name: str = ""
    output_path: str = ""
    item_limit: int = 0
    page_limit: int = 100
    current_progress: int = 0

class ScraperModel:
    def __init__(self):
        self.config = ScraperConfig()
        self.is_running = False
        self.stop_flag = threading.Event()
        self._scraper = None
        self.log_queue = Queue()
        self.completion_callback = None

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {message}")

    def start_scraping(self, progress_callback: Callable[[float], None], completion_callback: Callable[[], None]):
        self.stop_flag.clear()
        self.is_running = True
        self.completion_callback = completion_callback
        try:
            self._scraper = OlxScraper(
                base_url=self.config.url,
                output_file=os.path.join(self.config.output_path, f"{self.config.output_name}.json"),
                item_limit=self.config.item_limit,
                progress_callback=progress_callback,
                stop_flag=self.stop_flag,
                log_callback=self.log,
                page_limit=self.config.page_limit  # Added this line
            )
            self._scraper.run()
        except Exception as e:
            self.log(f"Error during scraping: {str(e)}")
        finally:
            self.is_running = False
            if self.completion_callback:
                self.completion_callback()

    def stop_scraping(self):
        self.stop_flag.set()