from flask import Flask, jsonify, render_template, request,send_file

import os
import logging
import hashlib
import random
import json
import csv
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
)
import time
import re 
from datetime import datetime, timedelta
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
def scroll_and_click(driver, element, retries=3):
    """Scroll into view and click the element, with retry attempts."""
    for attempt in range(retries):
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(1)
            ActionChains(driver).move_to_element(element).click().perform()
            return True
        except StaleElementReferenceException:
            print(f"Element became stale, retrying {attempt + 1} of {retries}.")
            time.sleep(2)  # Wait and retry
            element = driver.find_element(By.XPATH, element.xpath)  # Re-find element
        except NoSuchElementException:
            print(f"Element not found, retrying {attempt + 1} of {retries}.")
            time.sleep(2)
    print(f"Failed to click the element after {retries} attempts.")
    return False

#chrome_options = Options()
#chrome_options.add_argument("--headless")

#chrome_options.add_argument("--window-size=2560,1440")
#chrome_options.add_argument("--disable-gpu")
#chrome_options.add_argument("--disable-extensions")
#chrome_options.add_argument("--disable-blink-features=AutomationControlled")
#chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
#chrome_options.add_argument("--proxy-server='direct://'")
#chrome_options.add_argument("--proxy-bypass-list=*")
#chrome_options.add_argument("--disable-dev-shm-usage")
#chrome_options.add_argument("--no-sandbox")
#chrome_options.add_argument("--start-maximized")

chrome_options = Options()
chrome_options.add_argument('--headless')  # Ensure headless mode
chrome_options.add_argument('--no-sandbox')  # Bypass OS security model, required in cloud environments
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.binary_location = "/opt/render/project/.render/chrome/opt/google/chrome/google-chrome"  # Path to the Chrome binary
chrome_options.add_argument("--window-size=2560,1440")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
chrome_options.add_argument("--proxy-server='direct://'")
chrome_options.add_argument("--proxy-bypass-list=*")
chrome_options.add_argument('--disable-software-rasterizer')
# Chrome flags to reduce memory consumption
chrome_options.add_argument('--disable-background-timer-throttling')
chrome_options.add_argument('--disable-backgrounding-occluded-windows')


service = Service(ChromeDriverManager().install(), port=0)  # Let OS pick an open port
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.set_page_load_timeout(120)
driver.implicitly_wait(30)
# Initialize WebDriver
# Initialize WebDriver
def human_typing(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(0.1)  # Delay between key presses


# Call this function to see all span elements and their details

def close_unexpected_popups():
    """Close any unexpected pop-ups that might interfere with scraping."""
    try:
        popups = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//div[@aria-label='Fermer']"))
        )
        for popup in popups:
            popup.click()
            print("Closed an unexpected popup")
    except Exception:
        # If no pop-ups are found, continue silently
        pass

def scroll_down():
    """Scroll down to load more posts."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(random.uniform(2, 4))  # Random sleep to mimic human behavior
    new_height = driver.execute_script("return document.body.scrollHeight")
    return new_height != last_height  # Returns True if new content is loaded

def get_unique_post_id(post_element):
    """Generate a unique identifier for a post."""
    try:
        post_id = post_element.get_attribute("data-testid")
        if post_id:
            return post_id
        else:
            post_html = post_element.get_attribute("outerHTML")
            return hashlib.md5(post_html.encode("utf-8")).hexdigest()
    except Exception:
        return None

def load_all_comments():
    """Scroll and load all comments in the current post's comment section."""
    while True:
        try:
            # Locate the 'View more comments' button and click it to load more comments
            view_more_comments = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.html-div.xdj266r.xat24cr.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x78zum5.x13a6bvl.x1d52u69.xktsk01"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", view_more_comments)
            time.sleep(1)  # Short delay to mimic human behavior
            view_more_comments.click()
            time.sleep(2)  # Wait for more comments to load
        except TimeoutException:
            print("No more 'View more comments' button found.")
            break
        except ElementClickInterceptedException:
            print("Could not click 'View more comments' button, possibly blocked by other elements.")
            break
def extract_date_from_text(potential_date_texts):
    for text in potential_date_texts:
        # Adjust regex to match common date formats more robustly
        date_match = re.search(r'\d{1,2} \w{3,}|\w+ \d{1,2}', text) # e.g., "28 août" or "August 4"
        if date_match:
            return date_match.group(0)
    return "No valid date found"


def parse_relative_date(relative_text):
    """Parse relative dates like 'il y a 3 h', 'il y a 2 jours', '4 m'."""
    now = datetime.now()
    
    if 'h' in relative_text:
        hours_ago = int(re.search(r'\d+', relative_text).group())
        return now - timedelta(hours=hours_ago)
    elif 'jour' in relative_text or 'j' in relative_text:
        days_ago = int(re.search(r'\d+', relative_text).group())
        return now - timedelta(days=days_ago)
    elif 'm' in relative_text:
        minutes_ago = int(re.search(r'\d+', relative_text).group())
        return now - timedelta(minutes=minutes_ago)
    elif "il y a" in relative_text:
        if 'jours' in relative_text:
            days_ago = int(re.search(r'il y a (\d+) jours', relative_text).group(1))
            return now - timedelta(days=days_ago)
        elif 'heures' in relative_text or 'h' in relative_text:
            hours_ago = int(re.search(r'il y a (\d+) heures?', relative_text).group(1))
            return now - timedelta(hours=hours_ago)
    elif "hier" in relative_text:
        return now - timedelta(days=1)
    elif "aujourd'hui" in relative_text:
        return now
    else:
        return None

def normalize_date_text(date_text):
    """Normalize date text to a consistent format."""
    # Handle months in French
    month_conversion = {
        'janv': '01',
        'févr': '02',
        'mars': '03',
        'avr': '04',
        'mai': '05',
        'juin': '06',
        'juil': '07',
        'août': '08',
        'sept': '09',
        'oct': '10',
        'nov': '11',
        'déc': '12'
    }

    # Replace month names with numeric values
    for abbr, num in month_conversion.items():
        if abbr in date_text:
            date_text = date_text.replace(abbr, num)
            break

    # Replace common separators and ensure the text is in a format strptime can parse
    date_text = date_text.replace('sep', '09')  # Handle any custom month mappings

    return date_text

def parse_post_date(post_element):
    """Extract and parse the post date from the post element."""
    try:
        # Patterns for matching dates and relative times
        relative_date_patterns = [
            r'\d+ h',         # Hours
            r'\d+ m',         # Minutes
            r'\d+ jours',     # Days (French)
            r'\d+ j',         # Days (abbreviated French)
            r'\d+ heures'     # Hours (French)
        ]

        date_spans = post_element.find_elements(By.CSS_SELECTOR, 'span.x4k7w5x.x1h91t0o.x1h9r5lt.x1jfb8zj.xv2umb2.x1beo9mf')

        for span in date_spans:
            date_text = span.text.strip().lower()  # Convert to lowercase to match month names
            if not date_text:
                continue

            print(f"Potential date text: {date_text}")

            # Check for relative date formats
            for pattern in relative_date_patterns:
                if re.search(pattern, date_text):
                    relative_date = parse_relative_date(date_text)
                    if relative_date:
                        print(f"Parsed relative date: {relative_date}")
                        return relative_date

            # Normalize and parse absolute dates
            normalized_date_text = normalize_date_text(date_text)
            try:
                if 'aujourd\'hui' in normalized_date_text or 'hier' in normalized_date_text:
                    return datetime.now() if 'aujourd\'hui' in normalized_date_text else datetime.now() - timedelta(days=1)
                
                # Example for '31 08' format (day month)
                if re.search(r'\d{1,2} \d{2}', normalized_date_text):
                    possible_date = datetime.strptime(normalized_date_text, '%d %m')
                    possible_date = possible_date.replace(year=datetime.now().year)
                    print(f"Parsed absolute date: {possible_date}")
                    return possible_date
                
                # Example for '31 août' format (day month name)
                if re.search(r'\d{1,2} \w+', normalized_date_text):
                    possible_date = datetime.strptime(normalized_date_text, '%d %B')
                    possible_date = possible_date.replace(year=datetime.now().year)
                    print(f"Parsed absolute date: {possible_date}")
                    return possible_date

            except ValueError as ve:
                print(f"Date parsing error: {ve}")

        print("No valid date found.")
        return None
    except Exception as e:
        print(f"Error parsing post date: {e}")
        return None
def clean_comments(comments):
   
    cleaned_comments = []
    for comment in comments:
        # Remove unwanted characters and escape sequences
        cleaned_comment = comment.strip().replace('\n', ' ').replace('\r', '')
        if cleaned_comment:
            cleaned_comments.append(cleaned_comment)
    return cleaned_comments

def decode_comments(json_string):
    """Decode JSON-encoded comments with proper handling of Unicode escapes."""
    try:
            # Decode the JSON string
            comments_list = json.loads(json_string)
            # Return the list as is; json.loads handles Unicode escapes
            return comments_list
    except json.JSONDecodeError:
            print(f"JSON decoding error: {json_string}")
            return json_string  # Return the original string if decoding fails
def scrap_group(group_url, search_term, max_posts):
    try:
        # Open Facebook login page
        driver.get('https://www.facebook.com/login')
        time.sleep(5)  # Wait for the page to load

        # Log in (replace with your own credentials)
        username_field = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, 'email'))
        )
        password_field = driver.find_element(By.ID, 'pass')
        login_button = driver.find_element(By.NAME, 'login')

        human_typing(username_field, 'edwardswan721@gmail.com')  # Replace with your email
        human_typing(password_field, 'edwardswan123')  # Replace with your password
        login_button.click()
        time.sleep(5)
        # Wait for login to complete
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
            )
            print("Logged in successfully and on home page")
            driver.save_screenshot('home_page.png')
        except Exception as e:
            print("Failed to find home page:", str(e))
            driver.save_screenshot('home_page_failed.png')

        # Navigate to the group URL
        driver.get(group_url)
        time.sleep(6)
        # Perform search in the group
        search_button_xpath =  driver.find_element(By.XPATH,"//div[@aria-label='Rechercher' and @role='button']")
        driver.execute_script("arguments[0].scrollIntoView(true);", search_button_xpath)
        driver.execute_script("arguments[0].click();", search_button_xpath)

        

        search_input_xpath = "//input[@aria-label='Rechercher dans ce groupe']"
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, search_input_xpath))
        )
        search_input.send_keys(search_term)
        search_input.send_keys(Keys.ENTER)

        # Scrape posts and comments
        processed_posts = set()
        scraped_data = []
        post_count = 0

        # Define the maximum number of posts to scrape
        while post_count < max_posts:
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(5)
            
            # Locate posts
            posts = driver.find_elements(By.CSS_SELECTOR, 'div.x1yztbdb.x1n2onr6.xh8yej3.x1ja2u2z')
            for post in posts:
                post_id = post.text[:30]  # Unique identifier
                if post_id in processed_posts:
                    continue
                processed_posts.add(post_id)
                post_count += 1
                if post_count > max_posts:
                    break
                
                # Get post content
                post_text = post.text
                cleaned_post = post_text.strip().replace('\n', ' ')
                driver.save_screenshot(f'post_{post_count}.png')

                # Click the post
                scroll_and_click(driver, post)
                time.sleep(5)
                post_url = driver.current_url

                # Extract comments
                load_all_comments()
                comments = driver.find_elements(By.CSS_SELECTOR, 'div.x1y1aw1k.xn6708d.xwib8y2.x1ye3gou')
                comments_text = [comment.text for comment in comments]
                cleaned_comments = clean_comments(comments_text)

                # Save scraped data
                scraped_data.append({
                    'post_id': post_id,
                    'post_text': cleaned_post,
                    'post_url': post_url,
                    'comments': json.dumps(cleaned_comments),
                    'scraped_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

                # Close the post or the popup
                try:
                    close_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Fermer']"))
                    )
                    driver.execute_script("arguments[0].click();", close_button)
                except Exception as e:
                    print(f"Failed to close popup: {e}")

        # Save scraped data to DataFrame
        df = pd.DataFrame(scraped_data)
        df['comments'] = df['comments'].apply(lambda x: ' | '.join(json.loads(x)))
        df.to_csv('scraped_data.csv', index=False, encoding='utf-8')
        print("Data saved to 'scraped_data.csv'")
        return df.to_dict(orient='records')

    finally:
        driver.quit()
def scrape_facebook_page(hours):
    
    try:
        # Log in to Facebook
        driver.get('https://www.facebook.com/')
        time.sleep(5)
       

        # Navigate to the Facebook page
        driver.get('https://www.facebook.com/orange.tn/')
        print("Navigated to the Facebook page")
        time.sleep(10)  # Wait for the page to load
        driver.save_screenshot('navigated_page.png')
        close_unexpected_popups()
        # Verify navigation
        current_url = driver.current_url
        print("Current URL:", current_url)
        if 'orange.tn' not in current_url:
            raise Exception("Navigation to the specified page failed")
        print("Verified navigation to the specified page")
       
        # Set the target date based on the number of hours entered by the user
        target_date = datetime.now() - timedelta(hours=hours)
        print(f"Target date set to: {target_date}")
        close_unexpected_popups()
        processed_posts = set()
        scraped_data = []
        target_reached = False

        while not target_reached:
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(5)

            posts = driver.find_elements(By.CSS_SELECTOR, 'div.x1yztbdb.x1n2onr6.xh8yej3.x1ja2u2z')
            for post in posts:
                post_id = post.text[:30]
                if post_id in processed_posts:
                    continue
                processed_posts.add(post_id)

                post_date = parse_post_date(post)
                if post_date and post_date < target_date:
                    print("Reached posts older than target date. Stopping.")
                    target_reached = True
                    break

                post_text = post.text.strip().replace('\n', ' ')
                if not scroll_and_click(driver, post):
                    continue

                post_url = driver.current_url
                load_all_comments()
                comments = driver.find_elements(By.CSS_SELECTOR, 'div.x1y1aw1k.xn6708d.xwib8y2.x1ye3gou')
                comments_text = [comment.text for comment in comments]
                cleaned_comments = clean_comments(comments_text)

                scraped_data.append({
                    'post_id': post_id,
                    'post_text': post_text,
                    'post_url': post_url,
                    'comments': json.dumps(cleaned_comments)
                })

                try:
                    close_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Fermer']"))
                    )
                    driver.execute_script("arguments[0].click();", close_button)
                except Exception as e:
                    print(f"Failed to close popup: {e}")

        # Save data to CSV
        df = pd.DataFrame(scraped_data)
        df['comments'] = df['comments'].apply(lambda x: ' | '.join(json.loads(x)))
        df.to_csv('scraped_data.csv', index=False, encoding='utf-8')
        print("Data saved to 'scraped_data.csv'")
        return df.to_dict(orient='records')
   

    finally:
        driver.quit()

# Flask route to trigger scraping
@app.route('/scrap_groupe', methods=['GET'])
def scrap_groupe():
    group_url = request.args.get('group_url')
    search_term = request.args.get('search_term', 'default search')
    max_posts = int(request.args.get('max_posts', 5))  # Default to 5 posts if not provided
    scraped_data = scrap_group(group_url, search_term, max_posts)
    return jsonify(scraped_data)
@app.route('/scrap_page', methods=['GET'])
def scrap_page():
    hours = int(request.args.get('hours'))
    # Call the page scraping function with the number of hours
    scraped_data = scrape_facebook_page(hours)
    # Return a success message after scraping
    return jsonify(scraped_data)
@app.route('/')
def home():
    return render_template('home.html')
@app.route('/groups')
def groups():
    return render_template('index.html')
@app.route('/pages')
def pages():
    return render_template('pages_form.html')
@app.route('/download_csv')
def download_csv():
    file_path = 'scraped_data.csv'
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name='scraped_data.csv', mimetype='text/csv')
    else:
        return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':

    port = int(os.environ.get('PORT', 5000))  # Get the port from environment or default to 5000
    app.run(host='0.0.0.0', port=port)
