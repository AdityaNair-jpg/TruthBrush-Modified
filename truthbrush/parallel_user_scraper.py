import json
from truthbrush.api import Api
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

#CONFIGURATION 
USERS_FILE = "users.txt"
OUTPUT_FILE = "all_users_parallel_data.jsonl"
# How many users to scrape at the same time
MAX_WORKERS = 5 
CREATED_AFTER_DATE = datetime(2025, 8, 1, tzinfo=timezone.utc)
CREATED_BEFORE_DATE = datetime(2025, 8, 10, tzinfo=timezone.utc)

def scrape_user(api_session, username):                                 #This function runs in a separate thread for each user.
    #It uses the shared, pre-authenticated API session to scrape posts.
    try:
        print(f"  -> Starting scrape for: {username}")
        posts = list(api_session.pull_statuses(
            username, 
            replies=False, 
            pinned=False, 
            created_after=CREATED_AFTER_DATE, 
            created_before=CREATED_BEFORE_DATE
        ))
        print(f"  <- Finished scrape for: {username}, found {len(posts)} posts.")
        return posts
    except Exception as e:
        print(f"  !! Error scraping user '{username}': {e}")
        return [] # Return an empty list on error

def main():
    """
    Logs in once, then uses a pool of threads to scrape multiple users in parallel.
    """
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger("truthbrush.api")
    logger.setLevel(logging.WARNING)

    print("Logging in to Truth Social once... (this may take a moment)")
    
    # 1. Log in ONCE in the main thread
    try:
        api = Api()
        api._browser_login()
        print("Login successful! Auth token is ready to be shared.")
    except Exception as e:
        print(f"Fatal: Failed to log in. Error: {e}")
        return

    # 2. Read the list of users
    try:
        with open(USERS_FILE, "r") as f:
            users_to_scrape = [line.strip() for line in f if line.strip()]
        print(f"Found {len(users_to_scrape)} users to scrape. Starting parallel execution...")
    except FileNotFoundError:
        print(f"Error: Could not find '{USERS_FILE}'. Please make sure it exists.")
        return

    # 3. Scrape all users in parallel using a ThreadPool
    all_posts = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Create a future for each user 
        future_to_user = {executor.submit(scrape_user, api, user): user for user in users_to_scrape}
        
        # As each future completes, process the results
        for future in as_completed(future_to_user):
            user_posts = future.result()
            if user_posts:
                all_posts.extend(user_posts)

    # 4. Write all collected results to the output file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for post in all_posts:
            f.write(json.dumps(post) + "\n")

    print("\n--------------------------------------------------")
    print(f"DONE! Scraped a total of {len(all_posts)} posts from all users.")
    print(f"All data saved to '{OUTPUT_FILE}'.")


if __name__ == "__main__":
    main()