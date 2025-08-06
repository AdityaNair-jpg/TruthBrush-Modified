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

load_dotenv()
logging.basicConfig(level=logging.INFO)

BASE_URL = "https://truthsocial.com"
API_BASE_URL = "https://truthsocial.com/api"

TRUTHSOCIAL_USERNAME = os.getenv("TRUTHSOCIAL_USERNAME")
TRUTHSOCIAL_PASSWORD = os.getenv("TRUTHSOCIAL_PASSWORD")
TRUTHSOCIAL_TOKEN = os.getenv("TRUTHSOCIAL_TOKEN")

class LoginErrorException(Exception):
    pass

class Api:
    def __init__(
        self,
        username=TRUTHSOCIAL_USERNAME,
        password=TRUTHSOCIAL_PASSWORD,
        token=TRUTHSOCIAL_TOKEN,
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
                raise LoginErrorException("Username is missing.")
            if self.__password is None:
                raise LoginErrorException("Password is missing.")
            self._browser_login()

    def _browser_login(self):
        logger.info("Launching browser for authentication...")
        options = uc.ChromeOptions()
        # options.headless = True 
        self.driver = uc.Chrome(options=options)

        try:
            self.driver.get(f"{BASE_URL}/explore")
            logger.info("Please complete the login in the browser window.")
            WebDriverWait(self.driver, timeout=300).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Home')]"))
            )
            logger.info("Login successful! Session is now active.")

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
            logger.error(f"An error occurred during browser login: {e}")
            if self.driver:
                self.driver.quit()
            raise

    def _get(self, url: str, params: dict = None) -> Any:
        """Performs an API GET request from within the authenticated browser session."""
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

    # --- CORRECTED SEARCH FUNCTION ---
    def search(self, searchtype: str = None, query: str = None, limit: int = 40, resolve: bool = False, offset: int = 0, **kwargs):
        """Search and yield individual items (statuses, accounts, etc.)."""
        if searchtype != "statuses":
            logger.error("This version of the script currently only supports searching for 'statuses'.")
            return

        params = dict(q=query, resolve=resolve, limit=limit, type=searchtype, offset=offset)

        total_fetched = 0
        # Set a limit for the total number of statuses to fetch to avoid very long runs
        MAX_STATUSES = 1000 

        while total_fetched < MAX_STATUSES:
            page = self._get("/v2/search", params)

            if not page or not isinstance(page.get('statuses'), list) or not page.get('statuses'):
                logger.info("Search finished or no more results found.")
                break

            statuses = page['statuses']
            for status in statuses:
                yield status
                total_fetched += 1
                if total_fetched >= MAX_STATUSES:
                    break

            if total_fetched >= MAX_STATUSES:
                logger.warning(f"Reached search limit of {MAX_STATUSES} statuses. Stopping.")
                break

            # Prepare for the next page
            offset += len(statuses)
            params['offset'] = offset
            sleep(1) # Add a small delay to be polite to the server


    def pull_statuses(self, username: str, replies=False, verbose=False, created_after: datetime = None, since_id=None, pinned=False):
        lookup_result = self.lookup(username)
        if not lookup_result or "id" not in lookup_result:
            logger.error(f"Could not find user ID for {username}")
            return
        user_id = lookup_result["id"]

        params = {}
        if pinned:
            params['pinned'] = 'true'
        elif not replies:
            params['exclude_replies'] = 'true'

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

            keep_going = True
            for post in posts:
                post_at = date_parse.parse(post["created_at"]).replace(tzinfo=timezone.utc)
                if (created_after and post_at <= created_after) or (since_id and post["id"] <= since_id):
                    keep_going = False
                    break
                yield post

            if not keep_going or pinned:
                break

    def lookup(self, user_handle: str = None):
        return self._get("/v1/accounts/lookup", params=dict(acct=user_handle))