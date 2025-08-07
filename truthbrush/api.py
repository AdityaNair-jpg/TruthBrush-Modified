from time import sleep
from typing import Any, Iterator, List, Optional
from loguru import logger
from dateutil import parser as date_parse
from datetime import datetime, timezone, date
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import logging
import os
from dotenv import load_dotenv
import random

load_dotenv()
logging.basicConfig(level=logging.INFO)

BASE_URL = "https://truthsocial.com"
API_BASE_URL = "https://truthsocial.com/api"

TRUTHSOCIAL_USERNAME = os.getenv("TRUTHSOCIAL_USERNAME")
TRUTHSOCIAL_PASSWORD = os.getenv("TRUTHSOCIAL_PASSWORD")

class LoginErrorException(Exception):
    pass

class Api:
    def __init__(
        self,
        username=TRUTHSOCIAL_USERNAME,
        password=TRUTHSOCIAL_PASSWORD,
        token=None,
    ):
        self.__username = username
        self.__password = password
        self.auth_id = token
        self.driver = None

    def __del__(self):
        if self.driver:
            self.driver.quit()

    def __check_login(self):
        if self.driver is None or self.auth_id is None:
            if self.__username is None:
                raise LoginErrorException("Username is missing. Please set it in your .env file.")
            if self.__password is None:
                raise LoginErrorException("Password is missing. Please set it in your .env file.")
            self._browser_login()

    def _browser_login(self):
        logger.info("Launching browser for automated login...")
        options = uc.ChromeOptions()
        # To see the process, keep headless=False. To run in the background, set headless=True.
        # options.headless = True 
        self.driver = uc.Chrome(options=options)

        try:
            # Navigate directly to the login page
            self.driver.get(f"{BASE_URL}/login")

            # --- AUTO-FILL USERNAME ---
            # Wait for the username field to be visible and then type into it
            logger.info("Entering username...")
            username_field = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            username_field.send_keys(self.__username)

            # --- AUTO-FILL PASSWORD ---
            # Find the password field and type into it
            logger.info("Entering password...")
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.send_keys(self.__password)

            # --- AUTO-CLICK SIGN IN ---
            # Find the sign-in button and click it
            logger.info("Clicking Sign In...")
            signin_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            signin_button.click()

            # --- WAIT FOR LOGIN SUCCESS ---
            # Wait for the 'Home' landmark to appear on the timeline page
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Home')]"))
            )
            logger.info("Login successful! Session is now active.")

            # --- EXTRACT TOKEN ---
            token_data_str = self.driver.execute_script("return localStorage.getItem('truth:auth')") 
            if not token_data_str:
                raise LoginErrorException("Could not find 'truth:auth' key after login.")
            token_data = json.loads(token_data_str)
            tokens_dict = token_data.get('tokens')
            if not tokens_dict:
                raise LoginErrorException("'tokens' object not found in auth data.")
            self.auth_id = next(iter(tokens_dict))
            if not self.auth_id:
                 raise LoginErrorException("Access token could not be extracted.")

            logger.success(f"Successfully retrieved auth token: {self.auth_id[:10]}...")
        except Exception as e:
            logger.error(f"An error occurred during automated browser login: {e}")
            if self.driver:
                self.driver.quit()
            raise

    def _get(self, url: str, params: dict = None) -> Any:
        self.__check_login()
        full_url = API_BASE_URL + url
        if params:
            from urllib.parse import urlencode
            full_url += '?' + urlencode(params)

        js_script = f"""
        var callback = arguments[arguments.length - 1];
        fetch("{full_url}", {{
            "headers": {{
                "Authorization": "Bearer {self.auth_id}"
            }}
        }}).then(response => response.json())
           .then(data => callback(data))
           .catch(error => callback({{error: error.toString()}}));
        """

        try:
            result = self.driver.execute_async_script(js_script)
            return result
        except Exception as e:
            logger.error(f"In-browser API request failed: {e}")
            return None

    # This is the CORRECT line
    def search(self, searchtype: str = None, query: str = None, limit: int = 40, resolve: bool = False, created_after: datetime = None, created_before: datetime = None, **kwargs):
        """Search and yield individual items, with optional date filtering."""
        if searchtype != "statuses":
            logger.error("This version only supports searching for 'statuses'.")
            return

        params = dict(q=query, limit=limit, type=searchtype, offset=0, resolve=resolve)
        total_fetched = 0
        MAX_STATUSES = 10000 # Increased limit for date-range searches

        while total_fetched < MAX_STATUSES:
            page = self._get("/v2/search", params)
            if not page or not isinstance(page.get('statuses'), list) or not page.get('statuses'):
                logger.info("Search finished or no more results found.")
                break

            # Sort posts by date (newest first) to efficiently handle date ranges
            statuses = sorted(page['statuses'], key=lambda p: p.get("created_at", ""), reverse=True)

            for status in statuses:
                post_at = date_parse.parse(status["created_at"]).replace(tzinfo=timezone.utc)

                # --- DATE FILTERING LOGIC ---
                if created_after and post_at < created_after:
                    # If we find a post that is older than our start date, we can stop the entire search.
                    logger.info(f"Stopping search as post date {post_at.date()} is before the start date {created_after.date()}.")
                    total_fetched = MAX_STATUSES # Set to max to break the outer loop
                    break
                if created_before and post_at > created_before:
                    # If the post is newer than our end date, skip it and continue to the next (older) post.
                    continue

                yield status
                total_fetched += 1
                if total_fetched >= MAX_STATUSES:
                    break

            if total_fetched >= MAX_STATUSES:
                logger.warning(f"Reached search limit of {MAX_STATUSES} statuses or finished date range. Stopping.")
                break

            params['offset'] += len(statuses)
            sleep(random.uniform(1.5, 3.5))

    def pull_statuses(self, username: str, **kwargs):
        lookup_result = self.lookup(username)
        if not lookup_result or "id" not in lookup_result:
            logger.error(f"Could not find user ID for {username}")
            return
        user_id = lookup_result["id"]

        params = {}
        max_id = None
        while True:
            if max_id:
                params['max_id'] = max_id

            result = self._get(f"/v1/accounts/{user_id}/statuses", params=params)
            if not result or (isinstance(result, dict) and "error" in result):
                break

            posts = sorted(result, key=lambda k: k["id"], reverse=True)
            if not posts:
                break
            max_id = posts[-1]["id"]

            for post in posts:
                yield post

            sleep(random.uniform(1.5, 3.5))

    def lookup(self, user_handle: str = None):
        return self._get("/v1/accounts/lookup", params=dict(acct=user_handle))