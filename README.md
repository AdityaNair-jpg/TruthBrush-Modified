
# TruthBrush-Modified

`TruthBrush-Modified` is a significantly re-engineered version of the original `truthbrush` API client for Truth Social, which was built and maintained by the Stanford Internet Observatory.

This version has been completely overhauled to bypass advanced anti-bot measures by using a full browser automation engine, enabling reliable and fully automated data collection for academic research, open source intelligence, and archival purposes.

## Key Modifications from the Original

The core of this program was re-written to solve the challenge of modern anti-bot security systems. The key changes are:

1.  **New Scraping Engine:** The original networking libraries have been replaced with **Selenium** and the **`undetected-chromedriver`** library. This allows the script to operate out of a real, patched Chrome browser, making its behavior appear more human and avoiding blocks.

2.  **Fully Automated Login:** The script no longer requires any manual intervention. It automatically launches a browser, navigates to the login page, enters the user's credentials from the `.env` file, and submits the form to authenticate a session.

3.  **Enhanced Reliability:** All subsequent API calls are made from within the authenticated browser session. This ensures that every request has the correct cookies and headers, making the script's traffic indistinguishable from a normal user and preventing `403 Forbidden` errors.

4.  **New Date Filtering Feature:** Functionality has been added to filter topic searches by a specific date range, allowing for more precise data collection.

5.  **Built-in Anti-Ban Measures:** The script includes randomized delays between requests and a hard-coded limit on the number of posts fetched per search to ensure the tool is used responsibly and to minimize the risk of IP bans.

---

## Setup and Installation

### Prerequisites

* **Python 3.9 or higher.**
* **Google Chrome** browser installed on your system.

### 1. Installation

Clone the project repository to your local machine. Navigate to the project directory in your terminal and run the pip installer. This will install `truthbrush` and all its dependencies, including Selenium.

```bash
pip install .
````

This makes `truthbrush` available as a command in your terminal.

### 2\. Configuration (Crucial Step)

To enable the automated login, you must provide your Truth Social credentials in a `.env` file.

1.  In the root of your project folder (`D:\truthbrush`), create a new text file.
2.  Name the file exactly **`.env`**
3.  Open the file and add your username and password in the following format:
    ```
    TRUTHSOCIAL_USERNAME="your_username"
    TRUTHSOCIAL_PASSWORD="your_password"
    ```
4.  Save the file. The script will automatically read these credentials every time it runs.

**Security Note:** The `.env` file is included in the `.gitignore` and should never be shared or uploaded to public repositories.

-----

## Usage

All commands should be run from your project directory in the terminal (e.g., PowerShell or Command Prompt). The script will automatically launch a browser, log in, and perform the requested task.

### Scrape a User's Posts

This command scrapes all posts from a specific user's timeline.

```bash
truthbrush statuses [USERNAME]
```

**Example:**

```bash
# Scrape all posts from gordonsimons and save to a file
truthbrush statuses [USERNAME} > [USERNAME].jsonl
```

### Scrape a User's Posts After a Specific Date

Use the `--created-after` flag to get posts created on or after a certain date.

```bash
truthbrush statuses [USERNAME] --created-after YYYY-MM-DD
```

**Example:**

```bash
truthbrush statuses realDonaldTrump --created-after 2025-08-01 > trump_posts_after_august.jsonl
```

### Search for Posts by Topic/Keyword

This command searches for all posts containing a specific word, phrase, or hashtag.

```bash
truthbrush search --searchtype statuses "YOUR QUERY"
```

**Example:**

```bash
# Scrape all posts containing the hashtag #republicans
truthbrush search --searchtype statuses "#republicans" > republicans_posts.jsonl

# Scrape all posts containing the word "india"
truthbrush search --searchtype statuses "india" > india_posts.jsonl
```

### Search for Posts Within a Date Range

You can combine the search command with the date filtering flags to get posts on a specific topic within a precise timeframe.

```bash
truthbrush search --searchtype statuses "YOUR QUERY" --created-after YYYY-MM-DD --created-before YYYY-MM-DD
```

**Example:**

```bash
# Scrape posts about "elections" from January 2025
truthbrush search --searchtype statuses "elections" --created-after 2025-01-01 --created-before 2025-01-31 > elections_jan_posts.jsonl
```

-----

## Acknowledgements

This project is a modification of the original `truthbrush` tool created by the **Stanford Internet Observatory**. Full credit and thanks go to them for their foundational work. This version was re-engineered to adapt to new security challenges while building upon the excellent command-line interface they designed.

```
```
