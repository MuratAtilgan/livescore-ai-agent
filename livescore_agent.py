#!/usr/bin/env python3
"""
Real Livescore Fixtures Extractor
Gets actual upcoming fixtures from Livescore website
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import time
import re

class RealLivescoreFixtures:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get_real_fixtures(self):
        """Get real fixtures from Livescore"""
        print("🤖 Extracting REAL fixtures from Livescore...")
        print(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        all_fixtures = []
        
        # Try different Livescore URLs for fixtures
        fixture_urls = [
            'https://www.livescore.com/en/football/fixtures',
            'https://www.livescore.com/en/football',
            'https://www.livescore.com',
        ]
        
        for url in fixture_urls:
            print(f"🔍 Trying to extract from: {url}")
            fixtures = self.extract_from_url(url)
            all_fixtures.extend(fixtures)
            
            if fixtures:
                print(f"✅ Extracted {len(fixtures)} fixtures from {url}")
                break
            else:
                print(f"⚠️ No fixtures found from {url}")
            
            time.sleep(3)
        
        # Remove duplicates
        unique_fixtures = self.remove_duplicates(all_fixtures)
        
        # If still no real fixtures, show what we tried
        if not unique_fixtures:
            print("❌ Could not extract real fixtures. Showing diagnostic info...")
            unique_fixtures = self.create_diagnostic_data()
        
        print(f"📊 Final result: {len(unique_fixtures)} fixtures")
        return unique_fixtures
    
    def extract_from_url(self, url):
        """Extract fixtures from a specific URL"""
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            print(f"   📄 Page loaded, size: {len(response.content)} bytes")
            
            fixtures = []
            
            # Strategy 1: Look for fixture-specific elements
            fixtures.extend(self.find_fixture_elements(soup))
            
            # Strategy 2: Look for time-based elements (upcoming times)
            fixtures.extend(self.find_time_elements(soup))
            
            # Strategy 3: Parse all text for fixture patterns
            fixtures.extend(self.parse_page_text(soup))
            
            # Strategy 4: Look for JavaScript data
            fixtures.extend(self.extract_js_data(soup))
            
            return fixtures
            
        except Exception as e:
            print(f"   ❌ Error accessing {url}: {e}")
            return []
    
    def find_fixture_elements(self, soup):
        """Find elements that look like fixtures"""
        fixtures = []
        
        # Look for common fixture container patterns
        selectors = [
            '[class*="fixture"]',
            '[class*="match"][class*="upcoming"]',
            '[class*="event"][class*="scheduled"]',
            '[data-fixture]',
            '[data-match-time]',
            '.fixture',
            '.match-fixture',
            '.upcoming-match'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            print(f"   🔍 Found {len(elements)} elements with selector: {selector}")
            
            for element in elements[:20]:  # Limit per selector
                fixture = self.parse_fixture_element(element)
                if fixture:
                    fixtures.append(fixture)
        
        return fixtures
    
    def find_time_elements(self, soup):
        """Find elements containing future times"""
        fixtures = []
        
        # Look for time patterns that suggest future matches
        time_elements = soup.find_all(string=re.compile(r'\d{1,2}:\d{2}'))
        
        print(f"   🕐 Found {len(time_elements)} time elements")
        
        for time_elem in time_elements[:30]:
            try:
                time_text = time_elem.strip()
                
                # Skip if it looks like a score (contains numbers around it)
                parent_text = time_elem.parent.get_text() if time_elem.parent else time_text
                
                # Skip if it contains score patterns
                if re.search(r'\d+\s*[-:]\s*\d+', parent_text):
                    continue
                
                # Try to extract fixture info from context
                fixture = self.parse_time_context(time_elem, time_text)
                if fixture:
                    fixtures.append(fixture)
                    
            except Exception as e:
                continue
        
        return fixtures
    
    def parse_page_text(self, soup):
        """Parse all page text for fixture patterns"""
        fixtures = []
        
        # Get all visible text
        text_content = soup.get_text()
        
        print(f"   📝 Analyzing {len(text_content)} characters of page text")
        
        # Look for patterns that suggest fixtures (not scores)
        lines = text_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if len(line) < 10 or len(line) > 200:
                continue
            
            # Look for time patterns without scores
            if re.search(r'\d{1,2}:\d{2}', line) and not re.search(r'\d+\s*[-:]\s*\d+', line):
                fixture = self.parse_fixture_line(line)
                if fixture:
                    fixtures.append(fixture)
        
        return fixtures
    
    def extract_js_data(self, soup):
        """Extract fixture data from JavaScript"""
        fixtures = []
        
        scripts = soup.find_all('script')
        print(f"   🔧 Analyzing {len(scripts)} script tags for data")
        
        for script in scripts:
            if script.string:
                script_content = script.string
                
                # Look for JSON-like fixture data
                if 'fixture' in script_content.lower() or 'match' in script_content.lower():
                    js_fixtures = self.parse_js_fixtures(script_content)
                    fixtures.extend(js_fixtures)
        
        return fixtures
    
    def parse_fixture_element(self, element):
        """Parse a fixture from an HTML element"""
        try:
            text = element.get_text(strip=True)
            
            # Skip if it looks like a completed match
            if any(status in text.upper() for status in ['FT', 'FINAL', 'RESULT']):
                return None
            
            # Look for time
            time_match = re.search(r'(\d{1,2}:\d{2})', text)
            if not time_match:
                return None
            
            match_time = time_match.group(1)
            
            # Extract teams
            teams = self.extract_teams_from_text(text)
            if not teams:
                return None
            
            home_team, away_team = teams
            
            # Get current date for fixture
            today = datetime.now()
            fixture_date = today.strftime('%A, %d %B %Y')
            
            # Try to get league info
            league = self.get_league_from_context(element)
            
            return {
                'date': fixture_date,
                'time': match_time,
                'home_team': home_team,
                'away_team': away_team,
                'league': league,
                'status': 'Scheduled',
                'tv_info': '',
                'source': 'livescore.com',
                'extraction_method': 'element_parse'
            }
            
        except Exception as e:
            return None
    
    def parse_time_context(self, time_elem, time_text):
        """Parse fixture from time element context"""
        try:
            if not time_elem.parent:
                return None
            
            # Get surrounding context
            context = time_elem.parent.get_text(strip=True)
            
            # Skip if it contains scores
            if re.search(r'\d+\s*[-:]\s*\d+', context):
                return None
            
            # Extract teams from context
            teams = self.extract_teams_from_text(context)
            if not teams:
                return None
            
            home_team, away_team = teams
            
            return {
                'date': datetime.now().strftime('%A, %d %B %Y'),
                'time': time_text,
                'home_team': home_team,
                'away_team': away_team,
                'league': 'Extracted from page',
                'status': 'Scheduled',
                'tv_info': '',
                'source': 'livescore.com',
                'extraction_method': 'time_context'
            }
            
        except:
            return None
    
    def parse_fixture_line(self, line):
        """Parse a single line for fixture info"""
        try:
            # Extract time
            time_match = re.search(r'(\d{1,2}:\d{2})', line)
            if not time_match:
                return None
            
            match_time = time_match.group(1)
            
            # Extract teams
            teams = self.extract_teams_from_text(line)
            if not teams:
                return None
            
            home_team, away_team = teams
            
            return {
                'date': datetime.now().strftime('%A, %d %B %Y'),
                'time': match_time,
                'home_team': home_team,
                'away_team': away_team,
                'league': 'Text extraction',
                'status': 'Scheduled',
                'tv_info': '',
                'source': 'livescore.com',
                'extraction_method': 'line_parse'
            }
            
        except:
            return None
    
    def parse_js_fixtures(self, script_content):
        """Parse fixtures from JavaScript content"""
        fixtures = []
        
        try:
            # Look for JSON-like patterns
            patterns = [
                r'"homeTeam":\s*"([^"]+)".*?"awayTeam":\s*"([^"]+)".*?"time":\s*"([^"]+)"',
                r'"home":\s*"([^"]+)".*?"away":\s*"([^"]+)".*?"kickoff":\s*"([^"]+)"'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, script_content)
                for home, away, time_str in matches:
                    fixtures.append({
                        'date': datetime.now().strftime('%A, %d %B %Y'),
                        'time': time_str,
                        'home_team': home,
                        'away_team': away,
                        'league': 'JavaScript data',
                        'status': 'Scheduled',
                        'tv_info': '',
                        'source': 'livescore.com',
                        'extraction_method': 'javascript'
                    })
        except:
            pass
        
        return fixtures
    
    def extract_teams_from_text(self, text):
        """Extract team names from text"""
        # Remove time and common words
        clean_text = re.sub(r'\d{1,2}:\d{2}', '', text)
        
        # Look for team separation patterns
        patterns = [
            r'([A-Za-z\s]+?)\s+vs?\s+([A-Za-z\s]+)',
            r'([A-Za-z\s]+?)\s+-\s+([A-Za-z\s]+)',
            r'([A-Za-z\s]+?)\s+v\s+([A-Za-z\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, clean_text, re.I)
            if match:
                home, away = match.groups()
                home = home.strip()[:40]
                away = away.strip()[:40]
                
                if len(home) > 2 and len(away) > 2 and home != away:
                    return (home, away)
        
        return None
    
    def get_league_from_context(self, element):
        """Get league info from element context"""
        try:
            # Look up the DOM tree for league info
            current = element
            for _ in range(5):
                parent = current.find_parent()
                if parent:
                    # Look for headings
                    heading = parent.find(['h1', 'h2', 'h3', 'h4'])
                    if heading:
                        heading_text = heading.get_text(strip=True)
                        if any(word in heading_text.lower() for word in ['league', 'cup', 'championship']):
                            return heading_text[:50]
                    current = parent
                else:
                    break
        except:
            pass
        
        return 'Unknown League'
    
    def remove_duplicates(self, fixtures):
        """Remove duplicate fixtures"""
        seen = set()
        unique = []
        
        for fixture in fixtures:
            key = f"{fixture['time']}-{fixture['home_team']}-{fixture['away_team']}"
            if key not in seen:
                seen.add(key)
                unique.append(fixture)
        
        return unique
    
    def create_diagnostic_data(self):
        """Create diagnostic data when real extraction fails"""
        print("🔍 Creating diagnostic data to show extraction attempt...")
        
        return [{
            'date': datetime.now().strftime('%A, %d %B %Y'),
            'time': 'N/A',
            'home_team': 'EXTRACTION FAILED',
            'away_team': 'NO REAL DATA FOUND',
            'league': 'Diagnostic Info',
            'status': 'Livescore website structure may have changed',
            'tv_info': 'Need to update scraping method',
            'source': 'diagnostic',
            'extraction_method': 'fallback'
        }]
    
    def export_real_fixtures(self, fixtures):
        """Export the extracted fixtures"""
        os.makedirs('exports', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Prepare data
        export_data = []
        for fixture in fixtures:
            export_data.append({
                'Date': fixture['date'],
                'Time': fixture['time'],
                'Match': f"{fixture['home_team']} vs {fixture['away_team']}",
                'Home Team': fixture['home_team'],
                'Away Team': fixture['away_team'],
                'League/Competition': fixture['league'],
                'Status': fixture['status'],
                'TV/Streaming': fixture['tv_info'],
                'Source': fixture['source'],
                'Extraction Method': fixture['extraction_method']
            })
        
        df = pd.DataFrame(export_data)
        
        # Export to Excel
        excel_file = f'exports/real_livescore_fixtures_{timestamp}.xlsx'
        df.to_excel(excel_file, index=False, sheet_name='Real Fixtures')
        
        print(f"✅ Real fixtures exported: {excel_file}")
        return [excel_file]
    
    def run_real_extraction(self):
        """Run the real fixtures extraction"""
        try:
            print("🚀 Starting REAL Livescore Fixtures Extraction")
            print(f"🎯 Target: Extract actual upcoming fixtures from Livescore")
            
            # Extract real fixtures
            fixtures = self.get_real_fixtures()
            
            # Export results
            exported_files = self.export_real_fixtures(fixtures)
            
            # Summary
            print("\n" + "="*60)
            print("📊 REAL FIXTURES EXTRACTION SUMMARY")
            print("="*60)
            print(f"✅ Fixtures extracted: {len(fixtures)}")
            print(f"📁 Files created: {len(exported_files)}")
            
            if fixtures and fixtures[0]['home_team'] != 'EXTRACTION FAILED':
                print("🎉 SUCCESS: Real fixtures extracted!")
            else:
                print("⚠️ NOTICE: Could not extract real fixtures")
                print("   Livescore may have anti-scraping protection")
                print("   or the website structure changed")
            
            print("="*60)
            
            return {'status': 'completed', 'fixtures_count': len(fixtures)}
            
        except Exception as e:
            print(f"❌ Real extraction failed: {e}")
            return {'status': 'failed', 'error': str(e)}

def main():
    """Main entry point"""
    extractor = RealLivescoreFixtures()
    result = extractor.run_real_extraction()
    
    print(f"\n🏁 Extraction completed with status: {result['status']}")

if __name__ == "__main__":
    main()
