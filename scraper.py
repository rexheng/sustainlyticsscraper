#!/usr/bin/env python3
"""
Simple Sustainalytics ESG Risk Rating Scraper
Auto-installs ChromeDriver - no manual setup needed!
"""

import pandas as pd
import time
import re

def setup_selenium():
    """Setup Selenium with automatic ChromeDriver installation"""
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        
        print("✓ Selenium packages imported successfully")
        
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Ask user if they want to see the browser
        user_input = input("\nShow browser window? (y/n, default=y): ").strip().lower()
        if user_input == 'n':
            chrome_options.add_argument('--headless')
            print("Running in headless mode (no browser window)...")
        else:
            print("Browser window will open - don't close it during scraping...")
        
        # Auto-install and setup ChromeDriver
        print("\nSetting up ChromeDriver (will auto-download if needed)...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✓ Chrome driver ready!\n")
        return driver, By
        
    except ImportError as e:
        print(f"✗ Missing required package: {e}")
        print("\nPlease install required packages:")
        print("pip install selenium webdriver-manager pandas openpyxl")
        return None, None
    except Exception as e:
        print(f"✗ Error setting up driver: {e}")
        return None, None

def scrape_sustainalytics():
    """Main scraping function"""
    
    # Setup Selenium
    driver, By = setup_selenium()
    if not driver:
        return
    
    # List of companies to scrape
    companies = [
        {
            'name': 'Digital Realty Trust',
            'url': 'https://www.sustainalytics.com/esg-rating/digital-realty-trust-inc/1018920106'
        },
        {
            'name': 'DigitalBridge Group',
            'url': 'https://www.sustainalytics.com/esg-rating/digitalbridge-group-inc/1068717454'
        },
        {
            'name': 'Stack Infrastructure Inc',
            'url': 'https://www.sustainalytics.com/esg-rating/stack-infrastructure-inc/2006754006'
        },
        {
            'name': 'NextDC Ltd',
            'url': 'https://www.sustainalytics.com/esg-rating/nextdc-ltd/1123246430'
        },
        {
            'name': 'Keppel DC REIT',
            'url': 'https://www.sustainalytics.com/esg-rating/keppel-dc-reit/1287847576'
        },
        {
            'name': 'Keppel REIT',
            'url': 'https://www.sustainalytics.com/esg-rating/keppel-reit/1034566043'
        },
        {
            'name': 'Singapore Telecommunications',
            'url': 'https://www.sustainalytics.com/esg-rating/singapore-telecommunications-ltd/1007990630'
        },
        {
            'name': 'Mapletree Industrial Trust',
            'url': 'https://www.sustainalytics.com/esg-rating/mapletree-industrial-trust/1121344589'
        },
        {
            'name': 'Mapletree Logistics Trust',
            'url': 'https://www.sustainalytics.com/esg-rating/mapletree-logistics-trust/1030897891'
        },
        {
            'name': 'Mapletree Pan Asia Commercial Trust',
            'url': 'https://www.sustainalytics.com/esg-rating/mapletree-pan-asia-commercial-trust/2011664923'
        },
        {
            'name': 'GDS Holdings',
            'url': 'https://www.sustainalytics.com/esg-rating/gds-holdings-ltd/1411629733'
        }
    ]
    
    results = []
    
    print("=" * 60)
    print("Starting to scrape Sustainalytics ESG Ratings...")
    print("=" * 60)
    
    for i, company in enumerate(companies, 1):
        print(f"\n[{i}/{len(companies)}] Processing: {company['name']}")
        print("-" * 40)
        
        try:
            # Load the page
            driver.get(company['url'])
            print("  Loading page...")
            
            # Wait for page to fully load
            time.sleep(5)
            
            # Get page text
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            # Initialize result
            result = {
                'Company': company['name'],
                'ESG_Score': None,
                'Risk_Level': None,
                'Management': None,
                'URL': company['url']
            }
            
            # Method 1: Look for the score directly
            # Try to find elements with class containing 'risk' and 'score'
            try:
                score_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='risk'][class*='score']")
                for element in score_elements:
                    text = element.text.strip()
                    if text and re.match(r'^\d+\.?\d*$', text):
                        result['ESG_Score'] = float(text)
                        print(f"  ✓ Found ESG Score: {result['ESG_Score']}")
                        break
            except:
                pass
            
            # Method 2: Search for score pattern in page text
            if not result['ESG_Score']:
                # Look for patterns like "ESG Risk Rating: 16.8" or just standalone numbers
                score_patterns = [
                    r'ESG Risk Rating[:\s]+(\d+\.?\d*)',
                    r'Risk Rating[:\s]+(\d+\.?\d*)',
                    r'Score[:\s]+(\d+\.?\d*)',
                    r'\b((?:[0-4]?[0-9]|50)(?:\.\d{1,2})?)\b'  # Numbers 0-50 with up to 2 decimals
                ]
                
                for pattern in score_patterns:
                    matches = re.findall(pattern, page_text)
                    if matches:
                        # Filter to reasonable ESG score range (0-100, typically 0-50)
                        for match in matches:
                            score = float(match)
                            if 0 <= score <= 100:
                                result['ESG_Score'] = score
                                print(f"  ✓ Found ESG Score: {result['ESG_Score']}")
                                break
                    if result['ESG_Score']:
                        break
            
            # Look for risk level
            risk_patterns = ['Negligible', 'Low', 'Medium', 'High', 'Severe']
            for risk in risk_patterns:
                if risk in page_text:
                    result['Risk_Level'] = risk
                    break
            
            # Look for management level
            if "Management of ESG Material Risk is" in page_text:
                mgmt_match = re.search(r"Management of ESG Material Risk is (\w+)", page_text)
                if mgmt_match:
                    result['Management'] = mgmt_match.group(1)
            
            # Print what we found
            if not result['ESG_Score']:
                print(f"  ✗ Could not find ESG score")
                # Debug: show some numbers found on page
                numbers = re.findall(r'\b\d{1,2}\.?\d*\b', page_text)[:10]
                if numbers:
                    print(f"    Debug - Numbers found on page: {numbers}")
            
            results.append(result)
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                'Company': company['name'],
                'ESG_Score': None,
                'Risk_Level': None,
                'Management': None,
                'URL': company['url']
            })
        
        # Wait between requests
        if i < len(companies):
            time.sleep(2)
    
    # Close the browser
    print("\nClosing browser...")
    driver.quit()
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Display results
    print("\n" + "=" * 60)
    print("SCRAPING COMPLETE")
    print("=" * 60)
    
    print("\nResults Summary:")
    print(df.to_string(index=False))
    
    # Statistics
    found = df['ESG_Score'].notna().sum()
    total = len(df)
    print(f"\n✓ Found scores for {found}/{total} companies")
    
    # Save to files
    csv_file = 'sustainalytics_scores.csv'
    excel_file = 'sustainalytics_scores.xlsx'
    
    df.to_csv(csv_file, index=False)
    print(f"\n✓ Saved to {csv_file}")
    
    try:
        df.to_excel(excel_file, index=False, sheet_name='ESG Scores')
        print(f"✓ Saved to {excel_file}")
    except:
        print(f"✗ Could not save Excel file")
    
    print("\nDone!")
    
    # If no scores were found, provide troubleshooting
    if found == 0:
        print("\n" + "=" * 60)
        print("TROUBLESHOOTING - No scores were found")
        print("=" * 60)
        print("\nPossible reasons:")
        print("1. Sustainalytics may be blocking automated access")
        print("2. The page structure may have changed")
        print("3. Geographic restrictions or rate limiting")
        print("\nTry:")
        print("1. Run the script again with browser window visible")
        print("2. Manually check if scores are visible when pages load")
        print("3. Use a VPN if you're outside certain regions")
        print("4. Manually copy the scores from the website")

if __name__ == "__main__":
    print("=" * 60)
    print("SUSTAINALYTICS ESG RISK RATING SCRAPER")
    print("Simple Version with Auto-ChromeDriver")
    print("=" * 60)
    
    # Check packages
    print("\nChecking required packages...")
    packages_ok = True
    
    try:
        import selenium
        print("✓ selenium installed")
    except ImportError:
        print("✗ selenium not installed")
        packages_ok = False
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        print("✓ webdriver-manager installed")
    except ImportError:
        print("✗ webdriver-manager not installed")
        packages_ok = False
    
    try:
        import pandas
        print("✓ pandas installed")
    except ImportError:
        print("✗ pandas not installed")
        packages_ok = False
    
    if not packages_ok:
        print("\n⚠ Missing packages! Install them with:")
        print("pip install selenium webdriver-manager pandas openpyxl")
    else:
        print("\n✓ All packages ready!")
        print("\nNote: ChromeDriver will be auto-downloaded if needed")
        print("Make sure you have Chrome browser installed")
        print("-" * 60)
        
        # Run the scraper
        scrape_sustainalytics()