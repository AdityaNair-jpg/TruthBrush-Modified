import json
from truthbrush.api import Api
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

#CONFIGURATION
TOPICS_FILE = "topics.txt"
OUTPUT_FILE = "all_topics_parallel_data.jsonl"
SEARCH_TYPE = "statuses"
SEARCH_LIMIT_PER_TOPIC = 100 
MAX_WORKERS = 5 

def scrape_topic(api_session, topic):
    """
    This function runs in a separate thread for each topic, searching
    based on default relevance.
    """
    try:
        print(f"  -> Starting search for: {topic}")
        posts = list(api_session.search(
            query=topic,
            searchtype=SEARCH_TYPE,
            limit=SEARCH_LIMIT_PER_TOPIC
        ))
        print(f"  <- Finished search for: {topic}, found {len(posts)} posts.")
        return posts
    except Exception as e:
        print(f"  !! Error searching for topic '{topic}': {e}")
        return []

def main():
    
    # Logs in once, then uses a pool of threads to search multiple topics in parallel.
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger("truthbrush.api")
    logger.setLevel(logging.WARNING)

    print("Logging in to Truth Social once... (this may take a moment)")
    
    try:
        api = Api()
        api._browser_login()
        print("Login successful! Auth token is ready to be shared.")
    except Exception as e:
        print(f"Fatal: Failed to log in. Error: {e}")
        return

    try:
        with open(TOPICS_FILE, "r") as f:
            topics_to_scrape = [line.strip() for line in f if line.strip()]
        print(f"Found {len(topics_to_scrape)} topics to scrape. Starting parallel execution...")
    except FileNotFoundError:
        print(f"Error: Could not find '{TOPICS_FILE}'. Please make sure it exists.")
        return

    all_posts = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_topic = {executor.submit(scrape_topic, api, topic): topic for topic in topics_to_scrape}
        
        for future in as_completed(future_to_topic):
            topic_posts = future.result()
            if topic_posts:
                all_posts.extend(topic_posts)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for post in all_posts:
            f.write(json.dumps(post) + "\n")

    print("\n--------------------------------------------------")
    print(f"DONE! Scraped a total of {len(all_posts)} posts from all topics.")
    print(f"All data saved to '{OUTPUT_FILE}'.")


if __name__ == "__main__":
    main()