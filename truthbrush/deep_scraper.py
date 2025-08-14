"""
This script was implemented for the sole purpose of large-scale scraping of posts. It doesn't work as intended.
"""


import json
from truthbrush.api import Api
import logging
import time

# CONFIGURATION
TOPIC_TO_SCRAPE = "Ukraine"
OUTPUT_FILE = "Ukraine_deep_scrape.jsonl"

# Set your target number of posts.
POST_TARGET = 10000

# How many posts to get in each request. 40 is the API default and is a safe number.
POSTS_PER_REQUEST = 40
# How many seconds to pause between requests to be respectful to the API.
DELAY_BETWEEN_REQUESTS = 1.5


def main():
    logging.basicConfig(level=logging.WARNING)
    print(f"--- Deep Scraper for topic: '{TOPIC_TO_SCRAPE}' ---")
    print(f"Target: Scrape at least {POST_TARGET} posts.")
    
    # 1. Log in ONCE.
    try:
        api = Api()
        api._browser_login()
        print("Login successful!\n")
    except Exception as e:
        print(f"Fatal: Failed to log in. Error: {e}")
        return

    # 2. Open the output file.
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        total_posts_scraped = 0
        max_id = None # This will be our "cursor"

        # 3. Loop until the target is reached.
        while total_posts_scraped < POST_TARGET:
            print(f"-> Requesting next page of posts...")
            
            try:
                posts = list(api.search(
                    query=TOPIC_TO_SCRAPE,
                    searchtype="statuses",
                    limit=POSTS_PER_REQUEST,
                    max_id=max_id 
                ))

                if posts:
                    found_count = len(posts)
                    print(f"  <- Found {found_count} posts in this request.")
                    for post in posts:
                        f.write(json.dumps(post) + "\n")
                    total_posts_scraped += found_count
                    
                    
                    # Get the ID of the very last post and set it as our new cursor.
                    max_id = posts[-1]['id']
                    
                    print(f"  Total posts collected so far: {total_posts_scraped} / {POST_TARGET}")
                else:
                    # If the API returns no posts, we have reached the very beginning of the topic's history.
                    print("  <- No more posts found for this topic. Scrape complete.")
                    break # Exit the loop

            except Exception as e:
                print(f"  !! An error occurred: {e}")
                print("  ... Pausing for 60 seconds before retrying ...")
                time.sleep(60) # Wait longer if an error occurs
                continue

            # Pause briefly between successful requests.
            time.sleep(DELAY_BETWEEN_REQUESTS)

    print("\n--------------------------------------------------")
    print("DONE! Deep scrape is complete.")
    print(f"Scraped a total of {total_posts_scraped} posts.")
    print(f"All data saved to '{OUTPUT_FILE}'.")


if __name__ == "__main__":
    main()