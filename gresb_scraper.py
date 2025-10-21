"""
GRESB Ratings Web Scraper for Data Centre Companies
Extracts GRESB ratings from company websites and sustainability reports
"""

import sys
import traceback

# Check for required packages
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
except ImportError as e:
    print(f"ERROR: Missing required package - {e}")
    print("\nPlease install required packages:")
    print("pip install selenium")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas not installed")
    print("Please install: pip install pandas")
    sys.exit(1)

import time
import re
from datetime import datetime
import os
import json

class GRESBScraper:
    def __init__(self, headless=True, debug=True):
        """
        Initialise the GRESB scraper with Chrome WebDriver
        
        Args:
            headless (bool): Run browser in headless mode
            debug (bool): Enable debug output
        """
        self.debug = debug
        if self.debug:
            print("[DEBUG] Initialising GRESBScraper...")
        
        self.options = Options()
        if headless:
            self.options.add_argument('--headless')
            if self.debug:
                print("[DEBUG] Running in headless mode")
        else:
            if self.debug:
                print("[DEBUG] Running with browser window visible")
                
        # Add more options for compatibility
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--disable-web-security')
        self.options.add_argument('--disable-features=VizDisplayCompositor')
        self.options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Enable logging
        self.options.add_argument('--enable-logging')
        self.options.add_argument('--v=1')
        
        self.driver = None
        self.results = []
        
        # Company data with their actual sustainability/ESG URLs
        self.companies = {
            'GDS GROUP': {
                'regions': ['China', 'Hong Kong', 'Malaysia', 'Indonesia'],
                'urls': [
                    'https://www.gds-services.com/esg2023/ESG.html',
                    'https://investors.gds-services.com/news-releases',
                    'https://www.gds-services.com/en/esg'
                ],
                'notes': 'MSCI ESG upgraded to A rating in 2024, Moody\'s NZA-2 rating'
            },
            'ST Telemedia Global Data Centres': {
                'regions': ['Singapore', 'London', 'Indonesia'],
                'urls': [
                    'https://www.sttelemediagdc.com/about-us/esg',
                    'https://www.sttelemediagdc.com/about-us/our-esg-progress',
                    'https://www.sttelemediagdc.com/resources/2023-esg-report'
                ],
                'notes': '78.5% renewable energy usage in 2024, 62.5% in 2023'
            },
            'AirTrunk': {
                'regions': ['Australia', 'Japan'],
                'urls': [
                    'https://airtrunk.com/sustainability/',
                    'https://airtrunk.com/insights/airtrunk-fy24-sustainability-report/',
                    'https://airtrunk.com/wp-content/uploads/2024/10/FY24-Sustainability-Report-by-AirTrunk.pdf'
                ],
                'notes': 'GRESB 5-star rating, 97/100 score, 1st in sector in 2023'
            },
            'Chindata Group': {
                'regions': ['China', 'Malaysia', 'India'],
                'urls': [
                    'https://www.chindatagroup.com/about/sustainability.html',
                    'https://www.chindatagroup.com/media/news/',
                    'https://ir.chindatagroup.com/news-releases'
                ],
                'notes': 'CDP Climate Change A- rating, 100% renewable energy target by 2030'
            },
            'Princeton Digital Group': {
                'regions': ['Asia Pacific'],
                'urls': [
                    'https://princetondg.com/esg/',
                    'https://princetondg.com/wp-content/uploads/2024/07/ESG-Report-2023-24.pdf',
                    'https://princetondg.com/newsroom/'
                ],
                'notes': 'Net Zero target for Scope 1&2 by 2030, 15% carbon offset achieved'
            },
            'Digital Bridge Group': {
                'regions': ['Global'],
                'urls': [
                    'https://www.digitalbridge.com/about/esg',
                    'https://www.digitalbridge.com/news',
                    'https://ir.digitalbridge.com/sustainability'
                ],
                'notes': 'Infrastructure investment firm focused on digital infrastructure'
            },
            'QTS Group': {
                'regions': ['United States'],
                'urls': [
                    'https://www.qtsdatacenters.com/sustainability',
                    'https://www.qtsdatacenters.com/company/esg',
                    'https://www.qtsdatacenters.com/resources'
                ],
                'notes': 'Part of Blackstone Infrastructure Partners'
            },
            'Stack Infrastructure Group': {
                'regions': ['Global'],
                'urls': [
                    'https://www.stackinfra.com/sustainability',
                    'https://www.stackinfra.com/about-us/esg',
                    'https://www.stackinfra.com/newsroom'
                ],
                'notes': 'IPI Partners portfolio company'
            },
            'Kuok Group': {
                'regions': ['Asia Pacific'],
                'urls': [
                    'https://www.kuokgroup.com/sustainability',
                    'https://www.ppl.my/sustainability',
                    'https://www.shangri-la.com/group/esg/'
                ],
                'notes': 'Diversified conglomerate with data centre investments'
            },
            'Mapletree': {
                'regions': ['Asia Pacific'],
                'urls': [
                    'https://www.mapletree.com.sg/sustainability',
                    'https://www.mapletree.com.sg/sustainability/reports',
                    'https://www.mapletree.com.sg/newsroom'
                ],
                'notes': 'Real estate development including data centre properties'
            },
            'Digital Realty': {
                'regions': ['Global'],
                'urls': [
                    'https://www.digitalrealty.com/about/esg',
                    'https://s29.q4cdn.com/106493612/files/doc_financials/2023/ar/report_digital_realty_2406_2023_esg_report.pdf',
                    'https://www.digitalrealty.com/resources/reports'
                ],
                'notes': '75% renewable energy in 2024, 69% US ENERGY STAR certified'
            },
            'Keppel DC REIT': {
                'regions': ['Asia Pacific'],
                'urls': [
                    'https://www.keppeldcreit.com/en/sustainability/',
                    'https://www.keppeldcreit.com/en/sustainability/sustainability-report/',
                    'https://www.keppeldcreit.com/en/investor-relations/publications/'
                ],
                'notes': 'First pure-play data centre REIT in Asia'
            },
            'BDX Group': {
                'regions': ['Asia Pacific'],
                'urls': [
                    'https://www.bridgedatacentres.com/sustainability',
                    'https://www.bridgedatacentres.com/esg',
                    'https://www.bdx-data.com/sustainability'
                ],
                'notes': 'Part of Chindata Group (Bridge Data Centres brand)'
            },
            'NextDC': {
                'regions': ['Australia'],
                'urls': [
                    'https://www.nextdc.com/about-us/environmental-sustainability',
                    'https://www.nextdc.com/hubfs/ASX%20Announcements/NextDC_ESG_Report.pdf',
                    'https://www.nextdc.com/investors/reports'
                ],
                'notes': '100% carbon neutral, Climate Active certified, NABERS 5-star'
            },
            'CDC Group': {
                'regions': ['Asia Pacific'],
                'urls': [
                    'https://www.cdcdata.com.cn/sustainability',
                    'https://www.cdcdata.com.cn/esg',
                    'https://www.cdc-group.com/sustainability'
                ],
                'notes': 'China-based data centre operator'
            },
            'Wintrix': {
                'regions': ['Asia Pacific'],
                'urls': [
                    'https://www.wintrix.com/sustainability',
                    'https://www.wintrix.com/about',
                    'https://www.wintrix.com/news'
                ],
                'notes': 'Data centre solutions provider'
            },
            'Sify Technologies': {
                'regions': ['India'],
                'urls': [
                    'https://www.sify.com/about-us/sustainability/',
                    'https://www.sify.com/investors/',
                    'https://www.sify.com/resources/'
                ],
                'notes': 'Indian ICT service provider with data centre operations'
            },
            'Singtel': {
                'regions': ['Singapore', 'Asia Pacific'],
                'urls': [
                    'https://www.singtel.com/sustainability',
                    'https://www.singtel.com/about-us/sustainability/sustainability-reports',
                    'https://www.singtel.com/about-us/investor-relations'
                ],
                'notes': 'Telecommunications company with data centre investments'
            }
        }
        
    def check_chrome_driver(self):
        """Check if Chrome and ChromeDriver are properly installed"""
        if self.debug:
            print("[DEBUG] Checking Chrome/ChromeDriver installation...")
        
        try:
            # Try to find Chrome
            chrome_paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable',
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium',
                'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
                'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
            ]
            
            chrome_found = False
            for path in chrome_paths:
                if os.path.exists(path):
                    if self.debug:
                        print(f"[DEBUG] Chrome found at: {path}")
                    chrome_found = True
                    break
            
            if not chrome_found:
                print("[WARNING] Chrome browser not found in standard locations")
                print("Please ensure Google Chrome is installed")
            
            # Try to check ChromeDriver
            try:
                from selenium.webdriver.chrome.service import Service
                from selenium import webdriver
                
                # Try default ChromeDriver
                test_driver = webdriver.Chrome(options=self.options)
                test_driver.quit()
                if self.debug:
                    print("[DEBUG] ChromeDriver is working correctly")
                return True
                
            except Exception as e:
                print(f"[ERROR] ChromeDriver issue: {str(e)}")
                print("\nTo fix this:")
                print("1. Download ChromeDriver from: https://chromedriver.chromium.org/")
                print("2. Make sure ChromeDriver version matches your Chrome version")
                print("3. Add ChromeDriver to your PATH or specify its location")
                return False
                
        except Exception as e:
            print(f"[ERROR] Error checking Chrome/ChromeDriver: {str(e)}")
            return False
    
    def start_driver(self):
        """Start the Chrome WebDriver with error handling"""
        if self.debug:
            print("[DEBUG] Starting Chrome WebDriver...")
            
        if not self.driver:
            try:
                # Try different methods to start the driver
                try:
                    # Method 1: Default
                    self.driver = webdriver.Chrome(options=self.options)
                    if self.debug:
                        print("[DEBUG] ChromeDriver started successfully (default method)")
                except Exception as e1:
                    if self.debug:
                        print(f"[DEBUG] Default method failed: {str(e1)}")
                    
                    # Method 2: With Service
                    try:
                        from selenium.webdriver.chrome.service import Service
                        service = Service()
                        self.driver = webdriver.Chrome(service=service, options=self.options)
                        if self.debug:
                            print("[DEBUG] ChromeDriver started successfully (service method)")
                    except Exception as e2:
                        if self.debug:
                            print(f"[DEBUG] Service method failed: {str(e2)}")
                        
                        # Method 3: Try Firefox as alternative
                        try:
                            from selenium.webdriver.firefox.options import Options as FirefoxOptions
                            firefox_options = FirefoxOptions()
                            if self.options.arguments and '--headless' in str(self.options.arguments):
                                firefox_options.add_argument('--headless')
                            self.driver = webdriver.Firefox(options=firefox_options)
                            print("[INFO] Using Firefox as Chrome is not available")
                        except Exception as e3:
                            print(f"[ERROR] Could not start any browser driver")
                            print(f"Chrome error: {str(e1)}")
                            print(f"Firefox error: {str(e3)}")
                            raise Exception("No browser driver available")
                
            except Exception as e:
                print(f"[ERROR] Failed to start WebDriver: {str(e)}")
                print("\nTroubleshooting steps:")
                print("1. Ensure Chrome or Firefox is installed")
                print("2. Install/update ChromeDriver: https://chromedriver.chromium.org/")
                print("3. For Firefox, install geckodriver: https://github.com/mozilla/geckodriver/releases")
                print("4. Make sure the driver is in your PATH")
                raise
            
    def close_driver(self):
        """Close the Chrome WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                if self.debug:
                    print("[DEBUG] WebDriver closed successfully")
            except Exception as e:
                print(f"[WARNING] Error closing driver: {str(e)}")
            finally:
                self.driver = None
            
    def extract_gresb_rating(self, text):
        """
        Extract GRESB rating from text using regex patterns
        
        Args:
            text (str): Text to search for GRESB ratings
            
        Returns:
            dict: Extracted GRESB information
        """
        if self.debug:
            print(f"[DEBUG] Searching for ratings in {len(text)} characters of text")
            
        gresb_info = {
            'score': None,
            'stars': None,
            'year': None,
            'ranking': None,
            'other_ratings': []
        }
        
        # Pattern for GRESB score (0-100)
        score_patterns = [
            r'GRESB\s*(?:score|rating)[\s:]*(\d{1,3})',
            r'scored?\s*(\d{1,3})\s*(?:out of 100)?\s*in\s*GRESB',
            r'(\d{1,3})/100\s*GRESB',
            r'GRESB.*?(\d{1,3})\s*(?:points|score)',
            r'achieved?\s*(\d{1,3})\s*in\s*(?:the\s*)?GRESB'
        ]
        
        # Pattern for GRESB stars (1-5)
        star_patterns = [
            r'(\d)\s*(?:star|★)\s*GRESB',
            r'GRESB\s*(\d)\s*(?:star|★)',
            r'achieved?\s*(\d)\s*stars?\s*in\s*GRESB',
            r'(\d)-star\s*(?:GRESB\s*)?rating'
        ]
        
        # Search for patterns
        for pattern in score_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                if 0 <= score <= 100:
                    gresb_info['score'] = score
                    if self.debug:
                        print(f"[DEBUG] Found GRESB score: {score}")
                    break
                
        for pattern in star_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                stars = int(match.group(1))
                if 1 <= stars <= 5:
                    gresb_info['stars'] = stars
                    if self.debug:
                        print(f"[DEBUG] Found GRESB stars: {stars}")
                    break
                
        return gresb_info
    
    def scrape_page(self, url):
        """
        Scrape a single page for GRESB ratings
        
        Args:
            url (str): URL to scrape
            
        Returns:
            dict: Extracted GRESB information
        """
        try:
            if self.debug:
                print(f"[DEBUG] Loading URL: {url}")
                
            self.driver.get(url)
            time.sleep(3)  # Wait for page to load
            
            # Wait for body element to be present
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get page text
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            if self.debug:
                print(f"[DEBUG] Page loaded, text length: {len(page_text)}")
            
            # Extract GRESB rating
            return self.extract_gresb_rating(page_text)
            
        except TimeoutException:
            print(f"[ERROR] Timeout loading page: {url}")
            return None
        except Exception as e:
            print(f"[ERROR] Error scraping {url}: {str(e)}")
            if self.debug:
                traceback.print_exc()
            return None
    
    def scrape_company(self, company_name):
        """
        Scrape GRESB ratings for a specific company
        
        Args:
            company_name (str): Name of the company
            
        Returns:
            dict: Company results
        """
        print(f"\n[INFO] Processing {company_name}...")
        
        company_data = self.companies.get(company_name)
        if not company_data:
            print(f"[WARNING] Company {company_name} not found in database")
            return None
            
        result = {
            'company': company_name,
            'regions': ', '.join(company_data['regions']),
            'gresb_score': None,
            'gresb_stars': None,
            'gresb_year': None,
            'gresb_ranking': None,
            'other_ratings': [],
            'notes': company_data.get('notes', ''),
            'source_url': None,
            'scrape_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Try each URL for the company
        for url in company_data['urls']:
            print(f"[INFO] Trying URL: {url}")
            gresb_info = self.scrape_page(url)
            
            if gresb_info and any([gresb_info.get('score'), gresb_info.get('stars')]):
                # Found GRESB data
                result['gresb_score'] = gresb_info['score']
                result['gresb_stars'] = gresb_info['stars']
                result['gresb_year'] = gresb_info.get('year')
                result['gresb_ranking'] = gresb_info.get('ranking')
                result['source_url'] = url
                print(f"[SUCCESS] Found ratings for {company_name}")
                break
        else:
            print(f"[INFO] No GRESB ratings found on websites for {company_name}")
        
        return result
    
    def scrape_all(self):
        """
        Scrape GRESB ratings for all companies
        
        Returns:
            list: List of company results
        """
        print("\n[INFO] Starting web scraping process...")
        print(f"[INFO] Total companies to process: {len(self.companies)}")
        
        # Check Chrome/ChromeDriver first
        if not self.check_chrome_driver():
            print("[ERROR] Chrome/ChromeDriver setup issues detected")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                return []
        
        try:
            self.start_driver()
            
            for i, company_name in enumerate(self.companies.keys(), 1):
                print(f"\n{'='*60}")
                print(f"[PROGRESS] Company {i}/{len(self.companies)}")
                result = self.scrape_company(company_name)
                if result:
                    self.results.append(result)
                    
                # Brief pause between companies
                time.sleep(2)
                
        except Exception as e:
            print(f"\n[ERROR] Fatal error during scraping: {str(e)}")
            if self.debug:
                traceback.print_exc()
        finally:
            self.close_driver()
            
        return self.results
    
    def export_results(self, filename='gresb_ratings.csv'):
        """
        Export results to CSV file
        
        Args:
            filename (str): Output filename
        """
        if not self.results:
            print("[WARNING] No results to export")
            return
            
        try:
            df = pd.DataFrame(self.results)
            df.to_csv(filename, index=False)
            print(f"\n[SUCCESS] Results exported to {filename}")
            
            # Also save as JSON for debugging
            json_filename = filename.replace('.csv', '.json')
            with open(json_filename, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"[SUCCESS] Results also saved to {json_filename}")
            
        except Exception as e:
            print(f"[ERROR] Failed to export results: {str(e)}")
        
        # Display summary
        print("\n" + "="*80)
        print("GRESB RATINGS SUMMARY")
        print("="*80)
        
        for result in self.results:
            print(f"\n{result['company']} ({result['regions']})")
            if result['notes']:
                print(f"  Notes: {result['notes']}")
            if result['gresb_score']:
                print(f"  GRESB Score: {result['gresb_score']}/100")
            if result['gresb_stars']:
                print(f"  GRESB Stars: {result['gresb_stars']}/5")
            if not any([result['gresb_score'], result['gresb_stars']]):
                print("  No GRESB ratings found on website")

def test_setup():
    """Test if all required components are installed"""
    print("\n" + "="*60)
    print("TESTING SETUP")
    print("="*60)
    
    # Test imports
    print("\n[TEST] Checking required packages...")
    required_packages = {
        'selenium': False,
        'pandas': False,
        'Chrome/Firefox': False
    }
    
    try:
        import selenium
        required_packages['selenium'] = True
        print(f"✓ selenium version: {selenium.__version__}")
    except ImportError:
        print("✗ selenium not installed")
    
    try:
        import pandas
        required_packages['pandas'] = True
        print(f"✓ pandas version: {pandas.__version__}")
    except ImportError:
        print("✗ pandas not installed")
    
    # Test browser driver
    print("\n[TEST] Checking browser drivers...")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        try:
            driver = webdriver.Chrome(options=options)
            driver.quit()
            print("✓ ChromeDriver is working")
            required_packages['Chrome/Firefox'] = True
        except Exception as chrome_error:
            print(f"✗ ChromeDriver error: {str(chrome_error)[:100]}...")
            
            # Try Firefox
            try:
                from selenium.webdriver.firefox.options import Options as FirefoxOptions
                ff_options = FirefoxOptions()
                ff_options.add_argument('--headless')
                driver = webdriver.Firefox(options=ff_options)
                driver.quit()
                print("✓ Firefox/GeckoDriver is working")
                required_packages['Chrome/Firefox'] = True
            except Exception as firefox_error:
                print(f"✗ Firefox error: {str(firefox_error)[:100]}...")
    
    except Exception as e:
        print(f"✗ Browser driver test failed: {str(e)}")
    
    # Summary
    print("\n" + "="*60)
    if all(required_packages.values()):
        print("✓ ALL TESTS PASSED - Ready to run scraper")
        return True
    else:
        print("✗ SETUP INCOMPLETE - Please install missing components")
        print("\nTo fix issues:")
        print("1. pip install selenium pandas")
        print("2. Download ChromeDriver: https://chromedriver.chromium.org/")
        print("3. Or download GeckoDriver: https://github.com/mozilla/geckodriver/releases")
        return False

def main():
    """Main execution function"""
    # Clear screen for better visibility
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("\n" + "="*80)
    print(" "*25 + "GRESB RATINGS WEB SCRAPER")
    print("="*80)
    
    # Run setup test first
    print("\n[STEP 1] Checking system requirements...")
    if not test_setup():
        response = input("\n⚠ Setup issues detected. Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting...")
            sys.exit(1)
    
    print("\n" + "="*80)
    print("[STEP 2] Starting web scraper...")
    print("="*80)
    
    try:
        # Create scraper instance
        # Set debug=False to reduce output clutter
        scraper = GRESBScraper(headless=True, debug=False)
        
        # Scrape all companies
        results = scraper.scrape_all()
        
        # Export results
        if results:
            scraper.export_results('gresb_ratings.csv')
            print(f"\n✓ Successfully processed {len(results)} companies")
        else:
            print("\n⚠ No results were collected")
            print("This could mean:")
            print("  1. The websites don't publicly display GRESB ratings")
            print("  2. The pages require login/authentication")
            print("  3. The ratings are in PDF documents that need downloading")
        
        print("\n" + "="*80)
        print("SCRAPING COMPLETE")
        print("="*80)
        print("\nNotes:")
        print("• Some companies may not publicly disclose GRESB ratings")
        print("• GRESB ratings are often only available to members/investors")
        print("• Check the CSV and JSON files for any data that was found")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Scraping interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ ERROR: Unexpected error occurred")
        print(f"Details: {str(e)}")
        print("\nFor debugging, try:")
        print("  1. Run with headless=False to see the browser")
        print("  2. Run with debug=True for verbose output")
        traceback.print_exc()

if __name__ == "__main__":
    main()