#!/usr/bin/env python3
"""
Simple Livescore AI Agent - GitHub Actions Version
Scrapes sports data daily and exports to Excel/CSV
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import json
import time
import re

class LivescoreAgent:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def scrape_matches(self):
        """Scrape match data from Livescore"""
        print("🤖 Starting Livescore AI Agent...")
        print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        matches = []
        urls_to_try = [
            'https://www.livescore.com',
            'https://www.livescore.com/en/football'
        ]
        
        for url in urls_to_try:
            try:
                print(f"🔍 Scraping: {url}")
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                page_matches = self.parse_matches(soup)
                matches.extend(page_matches)
                
                print(f"✅ Found {len(page_matches)} matches from {url}")
                time.sleep(2)  # Be respectful
                
            except Exception as e:
                print(f"⚠️ Error scraping {url}: {e}")
                continue
        
        # Remove duplicates
        unique_matches = self.remove_duplicates(matches)
        print(f"📊 Total unique matches: {len(unique_matches)}")
        
        return unique_matches
    
    def parse_matches(self, soup):
        """Parse match data from HTML"""
        matches = []
        scraped_at = datetime.now().isoformat()
        
        # Look for potential match elements
        potential_elements = soup.find_all(['div', 'tr', 'li', 'span'], limit=500)
        
        for element in potential_elements:
            try:
                text = element.get_text(strip=True)
                
                # Skip if too short or too long
                if len(text) < 5 or len(text) > 200:
                    continue
                
                # Look for match patterns
                if self.looks_like_match(text):
                    match_data = self.extract_match_details(element, text, scraped_at)
                    if match_data:
                        matches.append(match_data)
                        
            except Exception:
                continue
        
        return matches[:100]  # Limit results
    
    def looks_like_match(self, text):
        """Check if text looks like a match"""
        # Common match indicators
        match_patterns = [
            r'\d+\s*-\s*\d+',  # Score pattern like "2-1"
            r'\w+\s+vs?\s+\w+',  # "Team vs Team"
            r'\w+\s+-\s+\w+',   # "Team - Team"
        ]
        
        # Check for match patterns
        for pattern in match_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Check for common football terms
        football_terms = ['premier league', 'champions league', 'la liga', 'bundesliga', 
                         'serie a', 'ligue 1', 'uefa', 'fifa', 'match', 'fixture']
        
        text_lower = text.lower()
        if any(term in text_lower for term in football_terms):
            return True
            
        return False
    
    def extract_match_details(self, element, text, scraped_at):
        """Extract detailed match information"""
        try:
            # Try to find parent containers for more context
            parent = element.find_parent(['div', 'tr', 'li'])
            parent_text = parent.get_text(strip=True) if parent else text
            
            # Look for time/status indicators
            time_patterns = [r'\d{1,2}:\d{2}', r'\d{1,2}\'', r'FT', r'HT', r'LIVE']
            status = 'Unknown'
            for pattern in time_patterns:
                match = re.search(pattern, parent_text)
                if match:
                    status = match.group()
                    break
            
            # Try to identify teams and score
            score_match = re.search(r'(\d+)\s*-\s*(\d+)', text)
            score = score_match.group() if score_match else 'N/A'
            
            return {
                'match_text': text[:100],
                'full_context': parent_text[:200] if parent_text != text else text[:200],
                'score': score,
                'status': status,
                'scraped_at': scraped_at,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'source': 'livescore.com'
            }
            
        except Exception:
            return {
                'match_text': text[:100],
                'full_context': text[:200],
                'score': 'N/A',
                'status': 'Unknown',
                'scraped_at': scraped_at,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'source': 'livescore.com'
            }
    
    def remove_duplicates(self, matches):
        """Remove duplicate matches"""
        seen = set()
        unique_matches = []
        
        for match in matches:
            # Create a simple key for deduplication
            key = match['match_text'].lower().strip()
            if key not in seen and len(key) > 5:
                seen.add(key)
                unique_matches.append(match)
                
        return unique_matches
    
    def export_data(self, matches):
        """Export match data to multiple formats"""
        if not matches:
            print("⚠️ No matches to export")
            return []
        
        # Create exports directory
        os.makedirs('exports', exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        exported_files = []
        
        # Convert to DataFrame
        df = pd.DataFrame(matches)
        
        try:
            # Excel export
            excel_file = f'exports/livescore_matches_{timestamp}.xlsx'
            df.to_excel(excel_file, index=False, sheet_name='Matches')
            exported_files.append(excel_file)
            print(f"📋 Excel exported: {excel_file}")
            
            # CSV export
            csv_file = f'exports/livescore_matches_{timestamp}.csv'
            df.to_csv(csv_file, index=False)
            exported_files.append(csv_file)
            print(f"📄 CSV exported: {csv_file}")
            
            # JSON export (for developers)
            json_file = f'exports/livescore_matches_{timestamp}.json'
            with open(json_file, 'w') as f:
                json.dump(matches, f, indent=2)
            exported_files.append(json_file)
            print(f"🔧 JSON exported: {json_file}")
            
        except Exception as e:
            print(f"❌ Export error: {e}")
        
        return exported_files
    
    def create_summary_report(self, matches, exported_files):
        """Create a summary report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_matches': len(matches),
            'files_created': len(exported_files),
            'status': 'success' if matches else 'no_data',
            'files': exported_files
        }
        
        # Save summary
        with open('exports/daily_summary.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*50)
        print("📊 DAILY SUMMARY REPORT")
        print("="*50)
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"🏆 Matches found: {len(matches)}")
        print(f"📁 Files created: {len(exported_files)}")
        
        if matches:
            # Analyze data
            statuses = {}
            for match in matches:
                status = match.get('status', 'Unknown')
                statuses[status] = statuses.get(status, 0) + 1
            
            print(f"\n📈 Match Status Breakdown:")
            for status, count in sorted(statuses.items()):
                print(f"   {status}: {count}")
        
        print("="*50)
        
        return report
    
    def run_daily_task(self):
        """Main daily task"""
        try:
            print("🚀 Starting Daily Livescore AI Agent")
            print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
            
            # Scrape matches
            matches = self.scrape_matches()
            
            # Export data
            exported_files = self.export_data(matches)
            
            # Create summary
            summary = self.create_summary_report(matches, exported_files)
            
            if matches:
                print("✅ Daily task completed successfully!")
            else:
                print("⚠️ No matches found - website might have changed")
            
            return summary
            
        except Exception as e:
            print(f"❌ Daily task failed: {e}")
            
            # Create error report
            os.makedirs('exports', exist_ok=True)
            error_report = {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'status': 'failed'
            }
            
            with open('exports/error_log.json', 'w') as f:
                json.dump(error_report, f, indent=2)
            
            return error_report

def main():
    """Main entry point"""
    agent = LivescoreAgent()
    result = agent.run_daily_task()
    
    # Print final status
    if result.get('status') == 'success':
        print(f"\n🎉 SUCCESS: Found {result['total_matches']} matches!")
    else:
        print(f"\n⚠️ COMPLETED: {result.get('status', 'unknown')}")

if __name__ == "__main__":
    main()
