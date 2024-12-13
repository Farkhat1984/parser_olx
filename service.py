import os
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from dataclasses import asdict, dataclass
from typing import List, Optional, Callable, Dict
import json
import time
import random
import logging
from datetime import datetime


@dataclass
class ProductDetails:
    id: str
    title: str
    price: str
    description: str
    images: List[str]
    location: str
    seller_name: str
    seller_since: str
    last_seen: str
    post_date: str


class OlxScraper:
    def __init__(self, base_url: str, output_file: str, item_limit: int,
                 progress_callback: Callable[[float], None],
                 stop_flag: threading.Event,
                 log_callback: Callable[[str], None],
                 page_limit: int = 100):
        self.base_url = base_url
        self.output_file = output_file
        self.item_limit = item_limit
        self.progress_callback = progress_callback
        self.stop_flag = stop_flag
        self.log = log_callback
        self.page_limit = page_limit
        self.products = self._load_existing_products()
        self.driver = None
        self.total_items_found = 0

        # Enhanced configuration
        self.max_retries = 3
        self.retry_delay = 5
        self.session_duration = random.randint(25, 35)  # minutes
        self.session_start_time = None

        # Randomization settings
        self.delays = {
            'page_load': (2, 5),
            'scroll': (0.5, 1.5),
            'action': (1, 3),
            'mouse_move': (0.1, 0.3)
        }

    def _setup_chrome_options(self) -> webdriver.ChromeOptions:
        options = webdriver.ChromeOptions()
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # Random user agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        ]
        options.add_argument(f'user-agent={random.choice(user_agents)}')
        return options

    def _initialize_driver(self):
        """Initialize or reinitialize the WebDriver with error handling."""
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass

        try:
            self.driver = webdriver.Chrome(options=self._setup_chrome_options())
            self.session_start_time = time.time()
            self.log("New WebDriver session initialized")
        except Exception as e:
            self.log(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def _should_refresh_session(self) -> bool:
        """Check if the current session should be refreshed."""
        if not self.session_start_time:
            return True
        elapsed_minutes = (time.time() - self.session_start_time) / 60
        return elapsed_minutes >= self.session_duration

    def _simulate_human_behavior(self):
        """Simulate realistic human browsing behavior with safer mouse movements."""
        try:
            # Random scrolling
            scroll_amount = random.randint(100, 500)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(0.5, 1.5))

            # Get actual viewport size for safe mouse movements
            viewport_width = self.driver.execute_script("return window.innerWidth;")
            viewport_height = self.driver.execute_script("return window.innerHeight;")

            # Safer mouse movements within viewport bounds
            actions = ActionChains(self.driver)
            for _ in range(random.randint(2, 4)):
                # Keep coordinates within 80% of viewport to avoid edge cases
                x = random.randint(10, int(viewport_width * 0.8))
                y = random.randint(10, int(viewport_height * 0.8))

                try:
                    actions.move_by_offset(x, y).perform()
                    actions.reset_actions()  # Reset action chains after each movement
                    time.sleep(random.uniform(0.1, 0.3))
                except:
                    # If movement fails, reset mouse position to (0,0) and try again
                    actions.move_to_element(self.driver.find_element(By.TAG_NAME, "body"))
                    actions.perform()
                    actions.reset_actions()

        except Exception as e:
            # Log error but don't raise it as mouse movement is not critical
            self.log(f"Mouse movement simulation skipped: {str(e)}")
            pass  # Continue execution even if mouse movement fails

    def wait_for_element(self, selector: str, by: By = By.CSS_SELECTOR,
                         timeout: int = 20, retries: int = 2) -> Optional[webdriver.remote.webelement.WebElement]:
        """Enhanced wait for element with retries and error handling."""
        for attempt in range(retries):
            try:
                return WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, selector))
                )
            except TimeoutException:
                if attempt < retries - 1:
                    self.log(f"Timeout waiting for {selector}, retrying...")
                    self._simulate_human_behavior()
                else:
                    self.log(f"Element not found after {retries} attempts: {selector}")
                    return None
            except Exception as e:
                self.log(f"Error finding element {selector}: {str(e)}")
                return None

    def get_product_links_from_page(self) -> List[str]:
        """Get product links from the current page with enhanced error handling."""
        links = []
        try:
            if self.wait_for_element("[data-cy='l-card']"):
                # Natural scrolling behavior
                viewport_height = self.driver.execute_script("return window.innerHeight")
                page_height = self.driver.execute_script("return document.body.scrollHeight")
                current_scroll = 0

                while current_scroll < page_height:
                    self.driver.execute_script(f"window.scrollTo(0, {current_scroll});")
                    current_scroll += viewport_height // 2
                    time.sleep(random.uniform(*self.delays['scroll']))

                cards = self.driver.find_elements(By.CSS_SELECTOR, "[data-cy='l-card']")
                links = [card.find_element(By.CSS_SELECTOR, "a").get_attribute('href')
                         for card in cards if card.find_element(By.CSS_SELECTOR, "a")]

                self.log(f"Found {len(links)} product links on current page")

        except Exception as e:
            self.log(f"Error getting product links: {str(e)}")

        return links

    def has_next_page(self) -> bool:
        """Check for next page with improved reliability."""
        try:
            next_button = self.wait_for_element("[data-testid='pagination-forward']", timeout=5)
            return next_button is not None and next_button.is_displayed()
        except Exception:
            return False

    def get_location(self) -> str:
        """Enhanced location extraction with multiple selectors."""
        location_selectors = [
            "p.css-1cju8pu",
            "[data-testid='location-date']",
            "p.css-b5m1rv",
            "span[data-testid='location-name']"
        ]

        for selector in location_selectors:
            if element := self.wait_for_element(selector, timeout=5):
                return element.text.strip()
        return ""

    def get_images(self) -> List[str]:
        """Enhanced image extraction with error handling."""
        images = []
        try:
            img_elements = self.driver.find_elements(By.CSS_SELECTOR, ".css-1bmvjcs")
            images = [img.get_attribute('src') for img in img_elements
                      if img.get_attribute('src') and 'frankfurt.apollo.olxcdn.com' in img.get_attribute('src')]

            # Remove duplicates while preserving order
            images = list(dict.fromkeys(images))

        except Exception as e:
            self.log(f"Error getting images: {str(e)}")

        return images

    def get_product_details(self, url: str) -> Optional[ProductDetails]:
        """Enhanced product details extraction with retry logic."""
        for attempt in range(self.max_retries):
            try:
                self.driver.get(url)
                time.sleep(random.uniform(*self.delays['page_load']))
                self._simulate_human_behavior()

                # Extract product ID
                id_elem = self.wait_for_element("span.css-12hdxwj")
                product_id = id_elem.text.replace('ID: ', '') if id_elem else url.split('ID')[-1].split('.')[0]

                if product_id in self.products:
                    self.log(f"Product {product_id} already exists, skipping...")
                    return None

                # Get all elements with improved error handling
                details = ProductDetails(
                    id=product_id,
                    title=self._get_element_text("h4.css-1kc83jo"),
                    price=self._get_element_text("h3.css-90xrc0"),
                    description=self._get_element_text("div.css-1o924a9"),
                    images=self.get_images(),
                    location=self.get_location(),
                    seller_name=self._get_element_text("h4.css-1lcz6o7"),
                    seller_since=self._get_element_text("p.css-23d1vy"),
                    last_seen=self._get_element_text("span.css-1p85e15"),
                    post_date=self._get_element_text("[data-cy='ad-posted-at']")
                )

                return details

            except WebDriverException:
                if attempt < self.max_retries - 1:
                    self.log(f"WebDriver error, reinitializing session (attempt {attempt + 1}/{self.max_retries})")
                    self._initialize_driver()
                else:
                    self.log(f"Failed to get product details after {self.max_retries} attempts")
                    return None

            except Exception as e:
                self.log(f"Error getting product details: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    return None

    def _get_element_text(self, selector: str) -> str:
        """Helper method to safely get element text."""
        element = self.wait_for_element(selector)
        return element.text.strip() if element else ""

    def get_product_links(self) -> List[str]:
        """Get all product links with enhanced pagination handling."""
        all_links = []
        page = 1
        current_url = self.base_url

        while (len(all_links) < self.item_limit and
               page <= self.page_limit and
               not self.stop_flag.is_set()):

            self.log(f"\nProcessing page {page}/{self.page_limit}")

            try:
                self.driver.get(current_url)
                time.sleep(random.uniform(*self.delays['page_load']))

                page_links = self.get_product_links_from_page()
                if not page_links:
                    self.log("No products found on current page")
                    break

                all_links.extend(page_links)
                self.total_items_found = len(all_links)

                # Update progress
                progress = min(0.5, (len(all_links) / self.item_limit) * 0.5)
                self.progress_callback(progress)

                self.log(f"Found {len(all_links)} products so far (target: {self.item_limit})")

                if len(all_links) >= self.item_limit:
                    self.log(f"Reached target number of items ({self.item_limit})")
                    break

                if not self.has_next_page():
                    self.log("No more pages available")
                    break

                page += 1
                current_url = f"{self.base_url}?page={page}"

            except WebDriverException:
                self.log("WebDriver error, reinitializing session...")
                self._initialize_driver()
                continue

            except Exception as e:
                self.log(f"Error processing page {page}: {str(e)}")
                break

        return all_links[:self.item_limit]

    def _load_existing_products(self) -> Dict:
        """Load existing products with error handling."""
        try:
            if os.path.exists(self.output_file):
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.log(f"Error loading existing products: {str(e)}")
        return {}

    def _save_products(self):
        """Save products with error handling."""
        try:
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.products, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"Error saving products: {str(e)}")

    def run(self):
        """Main execution method with enhanced error handling and session management."""
        try:
            self._initialize_driver()
            self.log(f"Starting scraping process for {self.base_url}")

            product_links = self.get_product_links()
            if not product_links:
                self.log("No products found!")
                return

            self.log(f"Processing {len(product_links)} products")

            for i, link in enumerate(product_links, 1):
                if self.stop_flag.is_set():
                    self.log("Stopping scraping process...")
                    break

                if self._should_refresh_session():
                    self.log("Refreshing session...")
                    self._initialize_driver()

                self.log(f"Processing product {i}/{len(product_links)}: {link}")
                if details := self.get_product_details(link):
                    self.products[details.id] = asdict(details)
                    self._save_products()

                    # Update progress
                    progress = 0.5 + (0.5 * i / len(product_links))
                    self.progress_callback(progress)
                    self.log(f"Successfully saved product: {details.title}")

                # Random delay between products
                time.sleep(random.uniform(*self.delays['action']))

        except Exception as e:
            self.log(f"Critical error: {str(e)}")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            self.log("Scraping process completed")

    def _validate_and_clean_product(self, details: ProductDetails) -> Optional[ProductDetails]:
        """Validate and clean product details before saving."""
        if not details.id or not details.title:
            return None

        # Clean and validate fields
        clean_details = ProductDetails(
            id=str(details.id).strip(),
            title=details.title.strip(),
            price=details.price.strip(),
            description=details.description.strip(),
            images=list(filter(None, details.images)),  # Remove empty URLs
            location=details.location.strip(),
            seller_name=details.seller_name.strip(),
            seller_since=details.seller_since.strip(),
            last_seen=details.last_seen.strip(),
            post_date=details.post_date.strip()
        )

        return clean_details

    def _handle_webdriver_error(self, error: WebDriverException, context: str):
        """Handle WebDriver errors with context."""
        self.log(f"WebDriver error during {context}: {str(error)}")
        try:
            if self.driver:
                self.driver.save_screenshot(f"error_{int(time.time())}.png")
        except:
            pass

        # Check if error is due to session being expired/invalid
        if any(msg in str(error).lower() for msg in ["invalid session", "session not created", "no such session"]):
            self.log("Session appears to be invalid, reinitializing...")
            self._initialize_driver()
        else:
            raise error

    def _extract_page_data(self) -> dict:
        """Extract all available data from current page with error handling."""
        try:
            return {
                'page_title': self.driver.title,
                'total_items': len(self.driver.find_elements(By.CSS_SELECTOR, "[data-cy='l-card']")),
                'current_url': self.driver.current_url,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.log(f"Error extracting page data: {str(e)}")
            return {}

    def _scroll_with_lazy_loading(self):
        """Implement smart scrolling to handle lazy-loaded content."""
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            retries = 3

            while retries > 0:
                # Scroll in smaller increments
                for i in range(10):
                    current_scroll = (i + 1) * (last_height // 10)
                    self.driver.execute_script(f"window.scrollTo(0, {current_scroll});")
                    time.sleep(random.uniform(0.3, 0.7))

                # Wait for possible lazy-loaded content
                time.sleep(random.uniform(1, 2))

                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    retries -= 1
                else:
                    last_height = new_height
                    retries = 3  # Reset retries if new content was loaded

                self._simulate_human_behavior()

        except Exception as e:
            self.log(f"Error during scrolling: {str(e)}")

    def _verify_page_loaded(self, timeout: int = 30) -> bool:
        """Verify that the page has fully loaded."""
        try:
            # Wait for the document to be ready
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )

            # Wait for any AJAX calls to complete
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return jQuery.active == 0")
            )

            # Check if main content container is present
            main_content = self.wait_for_element("[data-cy='l-card']", timeout=10)
            return main_content is not None

        except Exception as e:
            self.log(f"Error verifying page load: {str(e)}")
            return False

    def _handle_captcha(self) -> bool:
        """Handle potential CAPTCHA challenges."""
        captcha_indicators = [
            "captcha",
            "security check",
            "verify you're human"
        ]

        try:
            page_source = self.driver.page_source.lower()
            if any(indicator in page_source for indicator in captcha_indicators):
                self.log("CAPTCHA detected, waiting for manual resolution...")
                # Wait for manual intervention
                time.sleep(30)  # Adjust based on your needs
                return True
        except Exception as e:
            self.log(f"Error handling CAPTCHA: {str(e)}")
        return False

    def _retry_with_backoff(self, func, max_retries: int = 3, initial_delay: int = 5):
        """Execute a function with exponential backoff retry logic."""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e

                delay = initial_delay * (2 ** attempt)  # Exponential backoff
                self.log(f"Attempt {attempt + 1} failed, retrying in {delay} seconds...")
                time.sleep(delay)

    def _save_error_report(self, error: Exception, context: str):
        """Save detailed error reports for debugging."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"error_reports/error_{timestamp}.json"
            os.makedirs("error_reports", exist_ok=True)

            report = {
                "timestamp": timestamp,
                "context": context,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "url": self.driver.current_url if self.driver else None,
                "page_source_preview": self.driver.page_source[:1000] if self.driver else None
            }

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            self.log(f"Error report saved to {report_file}")

        except Exception as e:
            self.log(f"Error saving error report: {str(e)}")

    def cleanup(self):
        """Perform cleanup operations."""
        try:
            if self.driver:
                self.driver.quit()
            self._save_products()  # Final save of any remaining data
            self.log("Cleanup completed successfully")
        except Exception as e:
            self.log(f"Error during cleanup: {str(e)}")

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.cleanup()
        if exc_val:
            self._save_error_report(exc_val, "Context manager exit")