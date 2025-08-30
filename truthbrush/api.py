from time import sleep
from typing import Any, Iterator, List, Optional
from loguru import logger
from dateutil import parser as date_parse
from datetime import datetime, timezone
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import logging
import os
from dotenv import load_dotenv, find_dotenv
import random

load_dotenv(find_dotenv())

logging.basicConfig(level=logging.INFO)

BASE_URL = "https://truthsocial.com"
API_BASE_URL = "https://truthsocial.com/api"

TRUTHSOCIAL_USERNAME = os.getenv("TRUTHSOCIAL_USERNAME")
TRUTHSOCIAL_PASSWORD = os.getenv("TRUTHSOCIAL_PASSWORD")

class LoginErrorException(Exception):
    pass

class Api:
    """
    A refactored API client that logs in only once and reuses the session.
    """
    def __init__(self, username=TRUTHSOCIAL_USERNAME, password=TRUTHSOCIAL_PASSWORD):
        self.__username = username
        self.__password = password
        self.auth_id = None
        self.driver = None
        
        if not self.__username:
            raise LoginErrorException("Username is missing. Please check your .env file.")
        if not self.__password:
            raise LoginErrorException("Password is missing. Please check your .env file.")
        
        self._browser_login()

    def _browser_login(self):
        logger.info("Launching browser for a single, persistent session...")
        options = uc.ChromeOptions()
        # options.headless = True 
        self.driver = uc.Chrome(options=options)
        try:
            self.driver.get(f"{BASE_URL}/login")
            WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Sign In']"))).click()
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(self.__username)
            self.driver.find_element(By.NAME, "password").send_keys(self.__password)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Home')]")))
            logger.info("Login successful! Session is now active.")
            token_data_str = self.driver.execute_script("return localStorage.getItem('truth:auth')")
            token_data = json.loads(token_data_str)
            self.auth_id = next(iter(token_data.get('tokens')))
            logger.success(f"Successfully retrieved auth token: {self.auth_id[:10]}...")
        except Exception as e:
            logger.error(f"An error occurred during automated login: {e}")
            self.quit()
            raise

    def quit(self):
        """Safely closes the browser session."""
        if self.driver:
            self.driver.quit()
            logger.info("Browser session closed.")

    def _get(self, url: str, params: dict = None) -> Any:
        if not self.driver or not self.auth_id:
            raise LoginErrorException("Session is not active. Please re-initialize the Api object.")

        full_url = API_BASE_URL + url
        if params:
            from urllib.parse import urlencode
            full_url += '?' + urlencode(params)
        
        js_script = f"""
        var callback = arguments[arguments.length - 1];
        fetch("{full_url}", {{ headers: {{ "Authorization": "Bearer {self.auth_id}" }} }})
        .then(response => {{
            if (!response.ok) {{
                return callback({{error: `HTTP error! status: ${{response.status}}`}});
            }}
            return response.json();
        }})
        .then(data => callback(data))
        .catch(error => callback({{error: error.toString()}}));
        """
        return self.driver.execute_async_script(js_script)

    def search(self, searchtype: str, query: str, limit: int, created_after: datetime = None, created_before: datetime = None, resolve: bool = False, include_comments: bool = False, comment_limit: int = 50, **kwargs):
        params = dict(q=query, limit=limit, type=searchtype, offset=0, resolve=resolve)
        MAX_ITEMS = 1000
        total_fetched = 0
        
        logger.info(f"Starting search for '{query}' with type '{searchtype}'...")

        while total_fetched < MAX_ITEMS:
            page = self._get("/v2/search", params)
            
            logger.debug(f"API response for search page: {page}")

            if not page or (isinstance(page, dict) and 'error' in page):
                logger.error(f"Received an error or empty page from API: {page}")
                break
            
            if not isinstance(page.get(searchtype), list) or not page.get(searchtype):
                if total_fetched == 0:
                    logger.warning(f"Search for '{query}' returned no results.")
                else:
                    logger.info("Search finished as no more results were found.")
                break
            
            items = sorted(page[searchtype], key=lambda p: p.get("created_at", ""), reverse=True)
            
            for item in items:
                if 'created_at' in item: 
                    post_at = date_parse.parse(item["created_at"]).replace(tzinfo=timezone.utc)
                    if created_after and post_at < created_after:
                        total_fetched = MAX_ITEMS
                        break
                    if created_before and post_at > created_before:
                        continue
                
                if searchtype == 'statuses' and include_comments:
                    post_id = item.get("id")
                    if post_id:
                        logger.info(f"Fetching up to {comment_limit} comments for post ID: {post_id}")
                        comments = list(self.pull_comments(post_id, includeall=False, top_num=comment_limit))
                        item['comments'] = comments

                yield item
                total_fetched += 1
                if total_fetched >= MAX_ITEMS: break
            
            if total_fetched >= MAX_ITEMS:
                logger.warning(f"Reached search limit of {MAX_ITEMS}. Stopping.")
                break

            params['offset'] += len(items)
            sleep(random.uniform(1.0, 2.0))

    def pull_statuses(self, username: str, replies: bool, created_after: datetime = None, created_before: datetime = None, pinned: bool = False):
        lookup_result = self.lookup(username)
        if not lookup_result or "id" not in lookup_result: return
        user_id = lookup_result["id"]
        params = {}
        if not replies: params['exclude_replies'] = 'true'
        if pinned: params['pinned'] = 'true'
        max_id = None
        while True:
            if max_id: params['max_id'] = max_id
            result = self._get(f"/v1/accounts/{user_id}/statuses", params=params)
            if not result or (isinstance(result, dict) and 'error' in result): break
            posts = sorted(result, key=lambda k: k.get("created_at", ""), reverse=True)
            if not posts: break
            max_id = posts[-1]["id"]
            for post in posts:
                post_at = date_parse.parse(post["created_at"]).replace(tzinfo=timezone.utc)
                if created_after and post_at < created_after: return
                if created_before and post_at > created_before: continue
                yield post
            if pinned: break
            sleep(random.uniform(1.0, 2.0))

    def lookup(self, user_handle: str = None):
        return self._get("/v1/accounts/lookup", params=dict(acct=user_handle))
        
    def trending(self):
        return self._get("/v1/trends")
        
    def pull_comments(
        self,
        post: str,
        includeall: bool = False,
        onlyfirst: bool = False,
        top_num: int = 40,
        sort: str = "oldest",
    ):
        """Pull comments for a given post."""
        
        max_id = None
        params = {"sort": sort}
        total_fetched = 0
        
        while True:
            if max_id:
                params['max_id'] = max_id

            comments = self._get(f"/v1/statuses/{post}/context/descendants", params=params)

            if not comments or (isinstance(comments, dict) and 'error' in comments):
                if total_fetched == 0:
                    logger.warning(f"Could not find comments for post {post}, or the post has no comments.")
                break

            if not isinstance(comments, list):
                logger.error(f"Unexpected API response for comments: {comments}")
                break
                
            if onlyfirst:
                comments = [comment for comment in comments if comment.get("in_reply_to_id") == post]

            if not comments:
                break

            for comment in comments:
                yield comment
                total_fetched += 1
                if not includeall and total_fetched >= top_num:
                    return
            
            if not includeall and total_fetched >= top_num:
                return

            max_id = comments[-1].get("id")
            if not max_id:
                break

            sleep(random.uniform(1.0, 2.0))
    
    def suggestions(self):
        return self._get("/v2/suggestions")

    def ads(self):
        return self._get("/v3/truth/ads")
        
    def user_likes(self, post_id: str, limit: int = 40):
        max_id = None
        while True:
            params = {"limit": limit}
            if max_id:
                params['max_id'] = max_id
            
            likers = self._get(f"/v1/statuses/{post_id}/favourited_by", params=params)
            if not likers or (isinstance(likers, dict) and 'error' in likers): break
            
            for liker in likers:
                yield liker
            
            if len(likers) < limit: break
            max_id = likers[-1]['id']
            sleep(random.uniform(1.0, 2.0))

    def groupposts(self, group_id: str, limit: int = 40):
        max_id = None
        while True:
            params = {"limit": limit}
            if max_id:
                params['max_id'] = max_id
            
            posts = self._get(f"/v1/timelines/group/{group_id}", params=params)
            if not posts: break
            
            for post in posts:
                yield post
            
            if len(posts) < limit: break
            max_id = posts[-1]['id']
            sleep(random.uniform(1.0, 2.0))
            
    def trending_truths(self):
        return self._get("/v1/truth/trending/truths")

    def tags(self):
        return self._get("/v1/trends")

    def group_tags(self):
        return self._get("/v1/groups/tags")

    def trending_groups(self):
        return self._get("/v1/truth/trends/groups")

    def suggested_groups(self):
        return self._get("/v1/truth/suggestions/groups")