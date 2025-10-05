from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
import sys

def scrape_youtube_quiz_improved(url):
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = None
    try:
        # Initialize the driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(f"Loading YouTube page: {url}")
        driver.get(url)
        
        # Wait longer for YouTube to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        print("Page loaded, waiting for dynamic content...")
        time.sleep(5)
        
        # Try multiple approaches to find the elements
        
        # Approach 1: Look for the green circle (correct answer indicator)
        print("Searching for correct answer indicator...")
        
        # Try different selectors for the path element
        path_selectors = [
            "//path[@fill='rgb(43,166,64)']",
            "//path[contains(@fill, '43,166,64')]",
            "//*[name()='path' and contains(@fill, '43,166,64')]",
            "//path[contains(@d, 'M0,-20')]",
            "//*[local-name()='path' and contains(@d, 'M0,-20')]"
        ]
        
        target_path = None
        for selector in path_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    target_path = elements[0]
                    print(f"✓ Found target path using: {selector}")
                    break
            except:
                continue
        
        if not target_path:
            print("✗ Could not find the target path element")
            # Let's see what's actually on the page
            print("Debug: Searching for any path elements...")
            all_paths = driver.find_elements(By.TAG_NAME, "path")
            print(f"Found {len(all_paths)} path elements on page")
            for i, path in enumerate(all_paths[:5]):  # Show first 5
                try:
                    fill_attr = path.get_attribute('fill')
                    d_attr = path.get_attribute('d')
                    print(f"Path {i+1}: fill='{fill_attr}', d='{d_attr}'")
                except:
                    pass
            return None
        
        # Approach 2: Find answer choices
        print("Searching for answer choices...")
        
        # Try different selectors for answer elements
        answer_selectors = [
            "//a[@id='sign-in']",
            "//*[contains(@class, 'vote-choice')]",
            "//tp-yt-paper-item",
            "//*[contains(@class, 'backstage-quiz')]//*[contains(text(), 'Ljubljana')]",
            "//yt-formatted-string[contains(@class, 'choice-text')]"
        ]
        
        answer_elements = []
        for selector in answer_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    answer_elements = elements
                    print(f"✓ Found {len(elements)} answer elements using: {selector}")
                    break
            except:
                continue
        
        if not answer_elements:
            print("✗ Could not find answer elements")
            # Debug: look for any text that might be answer choices
            possible_answers = driver.find_elements(By.XPATH, "//*[contains(text(), 'Ljubljana') or contains(text(), 'Zagreb') or contains(text(), 'Sofia') or contains(text(), 'Bucharest')]")
            print(f"Found {len(possible_answers)} elements with city names")
            return None
        
        # Find which answer contains the target path
        print("Checking which answer contains the correct indicator...")
        matching_answers = []
        
        for i, answer_element in enumerate(answer_elements):
            try:
                # Get the answer text first
                choice_text = "Unknown"
                try:
                    text_elem = answer_element.find_element(By.XPATH, ".//yt-formatted-string[contains(@class, 'choice-text')]")
                    choice_text = text_elem.text
                except:
                    # Try to get text directly
                    choice_text = answer_element.text.split('\n')[0] if answer_element.text else "Unknown"
                
                # Check if this element contains the target path
                is_contained = driver.execute_script("""
                    var contains = false;
                    try {
                        contains = arguments[0].contains(arguments[1]);
                    } catch(e) {
                        // Try walking up the DOM tree
                        var parent = arguments[1];
                        while (parent && parent !== document.body) {
                            if (parent === arguments[0]) {
                                contains = true;
                                break;
                            }
                            parent = parent.parentElement;
                        }
                    }
                    return contains;
                """, answer_element, target_path)
                
                if is_contained:
                    matching_answers.append({
                        'index': i,
                        'text': choice_text,
                        'element': answer_element
                    })
                    print(f"✓ Target path found in answer: '{choice_text}'")
                    
            except Exception as e:
                print(f"Error checking answer {i}: {e}")
                continue
        
        if not matching_answers:
            print("✗ Could not find which answer contains the target path")
            print("Trying alternative approach...")
            
            # Alternative: Look for parent elements that contain both
            all_elements = driver.find_elements(By.XPATH, "//*[.//path[@fill='rgb(43,166,64)']]")
            for elem in all_elements:
                try:
                    if "choice" in elem.get_attribute('class') or "vote" in elem.get_attribute('class'):
                        text_elem = elem.find_element(By.XPATH, ".//yt-formatted-string[contains(@class, 'choice-text')]")
                        choice_text = text_elem.text if text_elem else "Unknown"
                        print(f"Alternative approach found: '{choice_text}'")
                        matching_answers.append({'index': 0, 'text': choice_text, 'element': elem})
                except:
                    continue
        
        return matching_answers
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if driver:
            driver.quit()

def main():
    # Check if URL is provided as command line argument
    if len(sys.argv) < 2:
        print("Usage: python youtubeQuizSolver.py <youtube_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    
    # Validate URL format
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    print("Scraping YouTube quiz page...")
    print("This may take a moment...")
    
    results = scrape_youtube_quiz_improved(url)
    
    if results:
        print("\n" + "="*60)
        print("🎯 RESULTS:")
        print("="*60)
        for result in results:
            print(f"✅ Correct Answer: {result['text']}")
    else:
        print("\n❌ No matching elements found.")
        print("\nPossible reasons:")
        print("1. The page structure may have changed")
        print("2. You need to be logged in to see the content")
        print("3. The quiz might not be available in your region")
        print("4. The post might have been removed or is private")

if __name__ == "__main__":
    main()