from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec

from modules.log_manager import log


class BaseCrawler:
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        """
        Initialize the Selenium WebDriver with custom options.
        This method automatically installs the Chrome WebDriver if not already installed, using ChromeDriverManager.

        :param headless: If True, the browser is run in headless mode, which means it operates without a GUI.
        :param no_images: If True, the browser will not load images, which can speed up web page loading times.
        :param keep_window: If True, the browser window will not automatically close after execution.
        """
        self.headless = headless
        self.no_images = no_images
        self.keep_window = keep_window
        self.tab_handl_id = 0

        options = Options()
        if headless:
            options.add_argument("--headless")
        if no_images:
            options.add_argument("--blink-settings=imagesEnabled=false")
        if keep_window:
            options.add_experimental_option("detach", True)
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_driver()

    def close_driver(self) -> None:
        """
        quit the chrome driver
        :return: None
        """
        self.driver.quit()

    def close_current_tab(self) -> None:
        """
        Close the current tab unless it is the last tab
        If it is the last tab, go to home page
        :return: None
        """
        if len(self.driver.window_handles) > 1:
            self.driver.close()
        else:
            self.driver.get("about:blank")

    def switch_to_tab(self, tab_handle: str) -> None:
        """
        Switch to the tab with the given handle
        :param tab_handle: handle of the tab to switch to
        :return: None
        """
        self.driver.switch_to.window(tab_handle)

    def get_url_in_new_tab(self, url: str, tab_handle: str = None) -> str:
        """
        Get the url in a new tab
        :param url: url to get
        :return: handle of the new tab
        """
        if tab_handle is None:
            tab_handle = "t" + str(self.tab_handl_id)
        self.driver.execute_script(f"window.open('{url}', '{tab_handle}')")
        self.tab_handl_id += 1
        return tab_handle

    def get(self, url: str) -> None:
        """
        Get the url in the browser
        :param url: url to get
        :return: None
        """
        self.driver.get(url)

    def element_from_xpath(self, element_xpath: str, timeout: int = 10) -> WebElement:
        """
        Get the element object for selenium from the xpath
        :param element_xpath: xpath of the element to get
        :param timeout: timeout in seconds
        :return: element object for selenium
        """
        return WebDriverWait(self.driver, timeout).until(ec.presence_of_element_located((By.XPATH, element_xpath)))

    def element_from_xpath_exists(self, element_xpath: str) -> bool:
        """
        Check if the element exists right now
        :param element_xpath: xpath of the element to check
        :return: True if the element exists, False otherwise
        """
        try:
            elements = self.driver.find_elements(By.XPATH, element_xpath)
            return len(elements) > 0
        except Exception as e:
            # Handle any exceptions, such as invalid XPath or WebDriver exceptions
            log.error(f"Error checking elements existence: {e}")
            return False

    def click_by_xpath(self, element_xpath: str, timeout: int = 10, max_retries: int = 5) -> bool:
        """
        Click the element by xpath
        :param element_xpath: xpath of the element to click
        :param timeout: timeout in seconds
        :param max_retries: max retries to click the element
        :return: True if the element is clicked, False otherwise
        """

        for i in range(max_retries):
            try:
                element = self.element_from_xpath(element_xpath, timeout)
                element.click()
                return True
            except Exception as e:
                log.debug(f"URL: {self.driver.current_url}")
                log.debug(f"Element xpath: {element_xpath}")
                log.warning(f"(Attempt {i + 1}/{max_retries}) Failed to click the element: {e}")
                continue

        log.error(f"Failed to click the element after {max_retries} attempts.")
        return False
