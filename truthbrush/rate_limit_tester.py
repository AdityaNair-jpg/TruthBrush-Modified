import json
from truthbrush.api import Api
import logging
import time

#TOPIC CONFIGURATION
TOPIC_TO_SCRAPE = "Ukraine"
OUTPUT_FILE = "expensive_search_results.jsonl"
# How many posts to ask for in this single, request
SEARCH_LIMIT = 500



def main():
    """
    Logs in once and performs a single, resource-intensive search
    to demonstrate an "expensive" API call.
    """
    logging.basicConfig(level=logging.WARNING)
    print(f"--- Expensive Request Tester ---")
    print(f"This will perform one large search for the topic: '{TOPIC_TO_SCRAPE}'")
    
    # 1. Log in ONCE
    try:
        api = Api()
        api._browser_login()
        print("Login successful!\n")
    except Exception as e:
        print(f"Fatal: Failed to log in. Error: {e}")
        return

    # 2. Perform the single search and time it
    print(f"-> Making one expensive request for up to {SEARCH_LIMIT} posts. Please wait...")
    start_time = time.time()
    
    try:
        posts = list(api.search(
            query=TOPIC_TO_SCRAPE,
            searchtype="statuses",
            limit=SEARCH_LIMIT
        ))
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 3. Save the results
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            for post in posts:
                f.write(json.dumps(post) + "\n")

        print("\n--- TEST FINISHED ---")
        print(f"Found {len(posts)} posts.")
        print(f"The single expensive request took {total_time:.2f} seconds to complete.")
        print(f"Data saved to '{OUTPUT_FILE}'.")

    except Exception as e:
        print(f"\n!! An error occurred during the search: {e}")


if __name__ == "__main__":
    main()