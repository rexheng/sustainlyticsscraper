#!/usr/bin/env python3
"""
Company Logo Extractor
Fetches transparent company logos from various API services
and saves them as PNG files for PowerPoint presentations.
"""

import os
import sys
import time
import requests
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from PIL import Image
from io import BytesIO
import json
import argparse
from urllib.parse import quote, urlparse
import re

class LogoExtractor:
    """Main class for extracting company logos from various sources."""
    
    def __init__(self, output_dir: str = "company_logos"):
        """
        Initialise the Logo Extractor.
        
        Args:
            output_dir: Directory to save the downloaded logos
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Headers for requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Track successful downloads
        self.downloaded = []
        self.failed = []
    
    def clean_filename(self, name: str) -> str:
        """
        Clean company name for use as filename.
        
        Args:
            name: Company name
            
        Returns:
            Cleaned filename-safe string
        """
        # Remove special characters and replace spaces with underscores
        cleaned = re.sub(r'[^\w\s-]', '', name)
        cleaned = re.sub(r'[-\s]+', '_', cleaned)
        return cleaned.lower()
    
    def fetch_from_clearbit(self, company_name: str, domain: Optional[str] = None) -> Optional[bytes]:
        """
        Fetch logo from Clearbit Logo API.
        Free tier available, no API key required for basic usage.
        
        Args:
            company_name: Name of the company
            domain: Optional company domain
            
        Returns:
            Logo image bytes or None if failed
        """
        if not domain:
            # Try to guess domain (works for many major companies)
            domain = f"{company_name.lower().replace(' ', '').replace('&', '')}.com"
        
        # Clearbit Logo API endpoint
        url = f"https://logo.clearbit.com/{domain}"
        
        try:
            print(f"  → Trying Clearbit for {company_name} (domain: {domain})...")
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.content
            else:
                print(f"    ✗ Clearbit returned status {response.status_code}")
                return None
                
        except Exception as e:
            print(f"    ✗ Clearbit error: {str(e)}")
            return None
    
    def fetch_from_brandfetch(self, company_name: str, domain: Optional[str] = None) -> Optional[bytes]:
        """
        Fetch logo from Brandfetch (formerly Brand.fetch).
        Note: Brandfetch now requires API key for most endpoints.
        Using their CDN endpoint which may work for some brands.
        
        Args:
            company_name: Name of the company
            domain: Optional company domain
            
        Returns:
            Logo image bytes or None if failed
        """
        if not domain:
            domain = f"{company_name.lower().replace(' ', '').replace('&', '')}.com"
        
        # Brandfetch CDN endpoint (may work for some popular brands)
        url = f"https://cdn.brandfetch.io/{domain}/w/512/h/512"
        
        try:
            print(f"  → Trying Brandfetch for {company_name}...")
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.content
            else:
                print(f"    ✗ Brandfetch returned status {response.status_code}")
                return None
                
        except Exception as e:
            print(f"    ✗ Brandfetch error: {str(e)}")
            return None
    
    def fetch_from_logo_dev(self, company_name: str, domain: Optional[str] = None) -> Optional[bytes]:
        """
        Fetch logo from Logo.dev (free tier available).
        
        Args:
            company_name: Name of the company
            domain: Optional company domain
            
        Returns:
            Logo image bytes or None if failed
        """
        if not domain:
            domain = f"{company_name.lower().replace(' ', '').replace('&', '')}.com"
        
        # Logo.dev API endpoint
        url = f"https://img.logo.dev/{domain}?token=pk_demo&size=512"
        
        try:
            print(f"  → Trying Logo.dev for {company_name}...")
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.content
            else:
                print(f"    ✗ Logo.dev returned status {response.status_code}")
                return None
                
        except Exception as e:
            print(f"    ✗ Logo.dev error: {str(e)}")
            return None
    
    def fetch_from_google_favicon(self, company_name: str, domain: Optional[str] = None) -> Optional[bytes]:
        """
        Fetch logo from Google's favicon service (fallback option).
        Lower quality but widely available.
        
        Args:
            company_name: Name of the company
            domain: Optional company domain
            
        Returns:
            Logo image bytes or None if failed
        """
        if not domain:
            domain = f"{company_name.lower().replace(' ', '').replace('&', '')}.com"
        
        # Google favicon service
        url = f"https://www.google.com/s2/favicons?domain={domain}&sz=256"
        
        try:
            print(f"  → Trying Google Favicons for {company_name}...")
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200 and len(response.content) > 1000:
                return response.content
            else:
                print(f"    ✗ Google Favicons failed or returned default icon")
                return None
                
        except Exception as e:
            print(f"    ✗ Google Favicons error: {str(e)}")
            return None
    
    def process_image(self, image_data: bytes, company_name: str) -> Optional[str]:
        """
        Process and save the image as PNG with transparency.
        
        Args:
            image_data: Raw image data
            company_name: Name of the company
            
        Returns:
            Path to saved file or None if failed
        """
        try:
            # Open image with PIL
            img = Image.open(BytesIO(image_data))
            
            # Convert to RGBA for transparency support
            if img.mode != 'RGBA':
                # If image has no alpha channel, create one
                if img.mode == 'RGB':
                    img = img.convert('RGBA')
                elif img.mode == 'P':
                    img = img.convert('RGBA')
            
            # Generate filename
            filename = f"{self.clean_filename(company_name)}_logo.png"
            filepath = self.output_dir / filename
            
            # Save as PNG
            img.save(filepath, 'PNG', optimize=True)
            
            # Get file size for reporting
            file_size = filepath.stat().st_size / 1024  # in KB
            
            print(f"    ✓ Saved: {filename} ({file_size:.1f} KB)")
            return str(filepath)
            
        except Exception as e:
            print(f"    ✗ Error processing image: {str(e)}")
            return None
    
    def extract_logo(self, company_name: str, domain: Optional[str] = None) -> bool:
        """
        Try to extract logo for a company using multiple services.
        
        Args:
            company_name: Name of the company
            domain: Optional company domain (e.g., 'apple.com')
            
        Returns:
            True if successful, False otherwise
        """
        print(f"\n🔍 Searching for: {company_name}")
        
        # Try different services in order of preference
        services = [
            ("Clearbit", self.fetch_from_clearbit),
            ("Logo.dev", self.fetch_from_logo_dev),
            ("Brandfetch", self.fetch_from_brandfetch),
            ("Google Favicons", self.fetch_from_google_favicon),
        ]
        
        for service_name, fetch_function in services:
            try:
                image_data = fetch_function(company_name, domain)
                
                if image_data:
                    filepath = self.process_image(image_data, company_name)
                    if filepath:
                        self.downloaded.append({
                            'company': company_name,
                            'path': filepath,
                            'service': service_name
                        })
                        return True
                
                # Small delay between API calls
                time.sleep(0.5)
                
            except Exception as e:
                print(f"    ✗ Error with {service_name}: {str(e)}")
                continue
        
        print(f"  ❌ Failed to find logo for {company_name}")
        self.failed.append(company_name)
        return False
    
    def extract_multiple(self, companies: List[Dict[str, str]]) -> None:
        """
        Extract logos for multiple companies.
        
        Args:
            companies: List of company dictionaries with 'name' and optional 'domain'
        """
        print(f"\n{'='*60}")
        print(f"Starting logo extraction for {len(companies)} companies")
        print(f"Output directory: {self.output_dir.absolute()}")
        print(f"{'='*60}")
        
        for company_info in companies:
            if isinstance(company_info, str):
                # Handle simple string input
                self.extract_logo(company_info)
            else:
                # Handle dictionary input with name and optional domain
                self.extract_logo(
                    company_info.get('name'),
                    company_info.get('domain')
                )
            
            # Delay between companies to avoid rate limiting
            time.sleep(1)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self) -> None:
        """Print extraction summary."""
        print(f"\n{'='*60}")
        print("📊 EXTRACTION SUMMARY")
        print(f"{'='*60}")
        
        print(f"\n✅ Successfully downloaded: {len(self.downloaded)} logos")
        for item in self.downloaded:
            print(f"  • {item['company']} ({item['service']})")
        
        if self.failed:
            print(f"\n❌ Failed to download: {len(self.failed)} logos")
            for company in self.failed:
                print(f"  • {company}")
        
        print(f"\n📁 Logos saved to: {self.output_dir.absolute()}")
        print(f"{'='*60}\n")


def load_companies_from_file(filepath: str) -> List[Dict[str, str]]:
    """
    Load company list from a text or JSON file.
    
    Args:
        filepath: Path to the input file
        
    Returns:
        List of company dictionaries
    """
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    companies = []
    
    if path.suffix == '.json':
        # Load JSON file
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                companies = data
            else:
                raise ValueError("JSON file must contain a list of companies")
    else:
        # Load text file (one company per line)
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Check if line contains domain info (separated by comma)
                    if ',' in line:
                        name, domain = line.split(',', 1)
                        companies.append({
                            'name': name.strip(),
                            'domain': domain.strip()
                        })
                    else:
                        companies.append({'name': line})
    
    return companies


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description='Extract company logos for PowerPoint presentations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract logos for specific companies
  python logo_extractor.py -c "Apple" "Microsoft" "Google"
  
  # Extract logos with custom domains
  python logo_extractor.py -c "S&P:spglobal.com" "Moody's:moodys.com"
  
  # Load companies from file
  python logo_extractor.py -f companies.txt
  
  # Specify output directory
  python logo_extractor.py -c "Apple" "Google" -o my_logos
        """
    )
    
    parser.add_argument(
        '-c', '--companies',
        nargs='+',
        help='Company names (optionally with domain using format "Name:domain.com")'
    )
    
    parser.add_argument(
        '-f', '--file',
        help='Path to file containing company names (one per line or JSON)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='company_logos',
        help='Output directory for logos (default: company_logos)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.companies and not args.file:
        print("Error: Please provide company names (-c) or input file (-f)")
        parser.print_help()
        sys.exit(1)
    
    # Prepare company list
    companies = []
    
    if args.file:
        try:
            companies.extend(load_companies_from_file(args.file))
        except Exception as e:
            print(f"Error loading file: {e}")
            sys.exit(1)
    
    if args.companies:
        for company_str in args.companies:
            if ':' in company_str:
                name, domain = company_str.split(':', 1)
                companies.append({'name': name, 'domain': domain})
            else:
                companies.append({'name': company_str})
    
    # Extract logos
    extractor = LogoExtractor(output_dir=args.output)
    extractor.extract_multiple(companies)


if __name__ == "__main__":
    # If running without arguments, use default examples
    if len(sys.argv) == 1:
        print("Running with example companies...")
        print("Use -h flag to see all options\n")
        
        example_companies = [
            {'name': 'S&P', 'domain': 'spglobal.com'},
            {'name': 'Fitch', 'domain': 'fitchratings.com'},
            {'name': "Moody's", 'domain': 'moodys.com'},
            {'name': 'Microsoft'},
            {'name': 'Apple'},
            {'name': 'Google'},
            {'name': 'Amazon'},
            {'name': 'Meta', 'domain': 'meta.com'},
            {'name': 'Tesla'},
            {'name': 'Netflix'}
        ]
        
        extractor = LogoExtractor()
        extractor.extract_multiple(example_companies)
    else:
        main()