#!/usr/bin/env python3
"""
Enhanced Livescore AI Agent - Detailed Match Extraction
Scrapes structured match data like the actual Livescore website
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import json
import time
import re

class EnhancedLivescoreAgent:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def scrape_matches(self):
        """Scrape detailed match data from multiple sources"""
        print("🤖 Enhanced Livescore AI Agent Starting...")
        print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        all_matches = []
        
        # Try multiple URLs and approaches
        sources = [
            {'name': 'Main Page', 'url': 'https://www.livescore.com'},
            {'name': 'Football', 'url': 'https://www.livescore.com/en/football'},
            {'name': 'Today Matches', 'url': 'https://www.livescore.com/en/football/live'},
        ]
        
        for source in sources:
            try:
                print(f"🔍 Scraping {source['name']}: {source['url']}")
                matches = self.scrape_source(source['url'])
                all_matches.extend(matches)
                print(f"✅ Found {len(matches)} matches from {source['name']}")
                time.sleep(3)  # Be respectful
                
            except Exception as e:
                print(f"⚠️ Error with {source['name']}: {e}")
                continue
        
        # Remove duplicates and enhance data
        unique_matches = self.process_and_deduplicate(all_matches)
        print(f"📊 Total unique matches processed: {len(unique_matches)}")
        
        return unique_matches
    
    def scrape_source(self, url):
        """Scrape a specific source URL"""
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try multiple parsing strategies
            matches = []
            matches.extend(self.parse_modern_structure(soup))
            matches.extend(self.parse_classic_structure(soup))
            matches.extend(self.parse_table_structure(soup))
            matches.extend(self.parse_list_structure(soup))
            
            return matches
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return []
    
    def parse_modern_structure(self, soup):
        """Parse modern JavaScript-heavy structure"""
        matches = []
        
        # Look for match containers with common class patterns
        selectors = [
            '[class*="match"]',
            '[class*="fixture"]', 
            '[class*="event"]',
            '[class*="game"]',
            '[data-match]',
            '[data-event]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements[:50]:  # Limit per selector
                match_data = self.extract_match_from_element(element)
                if match_data:
                    matches.append(match_data)
        
        return matches
    
    def parse_table_structure(self, soup):
        """Parse table-based structures"""
        matches = []
        
        # Find tables that might contain match data
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:  # Minimum for team1, score, team2
                    match_data = self.extract_match_from_row(cells)
                    if match_data:
                        matches.append(match_data)
        
        return matches
    
    def parse_list_structure(self, soup):
        """Parse list-based structures"""
        matches = []
        
        # Find lists that might contain matches
        lists = soup.find_all(['ul', 'ol', 'div'], class_=re.compile(r'match|fixture|event|game', re.I))
        
        for list_elem in lists:
            items = list_elem.find_all(['li', 'div'])
            for item in items:
                match_data = self.extract_match_from_element(item)
                if match_data:
                    matches.append(match_data)
        
        return matches
    
    def parse_classic_structure(self, soup):
        """Parse classic HTML structures"""
        matches = []
        
        # Look for elements containing team names and scores
        potential_matches = soup.find_all(['div', 'span', 'p'], string=re.compile(r'\d+\s*[-:]\s*\d+'))
        
        for element in potential_matches:
            match_data = self.extract_match_from_score_element(element)
            if match_data:
                matches.append(match_data)
        
        return matches
    
    def extract_match_from_element(self, element):
        """Extract match data from a DOM element"""
        try:
            text = element.get_text(strip=True)
            
            # Skip if not likely a match
            if not self.looks_like_match_element(element, text):
                return None
            
            # Extract basic info
            match_data = {
                'raw_text': text[:200],
                'home_team': 'Unknown',
                'away_team': 'Unknown', 
                'home_score': '',
                'away_score': '',
                'status': 'Unknown',
                'time': '',
                'league': 'Unknown',
                'scraped_at': datetime.now().isoformat(),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'source': 'livescore.com'
            }
            
            # Try to extract teams and scores
            self.extract_teams_and_scores(element, match_data)
            self.extract_status_and_time(element, match_data)
            self.extract_league_info(element, match_data)
            
            # Only return if we found meaningful data
            if (match_data['home_team'] != 'Unknown' and 
                match_data['away_team'] != 'Unknown' and
                match_data['home_team'] != match_data['away_team']):
                return match_data
                
        except Exception as e:
            pass
        
        return None
    
    def extract_match_from_row(self, cells):
        """Extract match data from table row cells"""
        try:
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            
            # Look for team names in cells
            teams = []
            scores = []
            times = []
            
            for text in cell_texts:
                if re.search(r'\d+\s*[-:]\s*\d+', text):
                    scores.append(text)
                elif re.search(r'\d{1,2}:\d{2}|FT|HT|LIVE|\d+\'', text):
                    times.append(text)
                elif len(text) > 2 and not text.isdigit():
                    teams.append(text)
            
            if len(teams) >= 2:
                return {
                    'home_team': teams[0][:50],
                    'away_team': teams[1][:50],
                    'home_score': scores[0].split('-')[0].strip() if scores else '',
                    'away_score': scores[0].split('-')[1].strip() if scores and '-' in scores[0] else '',
                    'status': times[0] if times else 'Unknown',
                    'time': times[0] if times else '',
                    'league': 'Table Data',
                    'raw_text': ' | '.join(cell_texts)[:200],
                    'scraped_at': datetime.now().isoformat(),
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'source': 'livescore.com'
                }
        except:
            pass
        
        return None
    
    def extract_match_from_score_element(self, element):
        """Extract match from element containing score"""
        try:
            # Get surrounding context
            parent = element.find_parent(['div', 'tr', 'li'])
            context_text = parent.get_text(strip=True) if parent else element.get_text(strip=True)
            
            # Find score pattern
            score_match = re.search(r'(\d+)\s*[-:]\s*(\d+)', context_text)
            if not score_match:
                return None
                
            home_score = score_match.group(1)
            away_score = score_match.group(2)
            
            # Try to find team names around the score
            text_parts = re.split(r'\d+\s*[-:]\s*\d+', context_text)
            
            home_team = 'Unknown'
            away_team = 'Unknown'
            
            if len(text_parts) >= 2:
                # Text before score is likely home team
                home_part = text_parts[0].strip()
                if home_part:
                    home_team = re.sub(r'[^\w\s]', '', home_part)[-30:]
                
                # Text after score is likely away team  
                away_part = text_parts[1].strip()
                if away_part:
                    away_team = re.sub(r'[^\w\s]', '', away_part)[:30]
            
            return {
                'home_team': home_team.strip(),
                'away_team': away_team.strip(),
                'home_score': home_score,
                'away_score': away_score,
                'status': 'Live' if 'live' in context_text.lower() else 'Unknown',
                'time': '',
                'league': 'Score Match',
                'raw_text': context_text[:200],
                'scraped_at': datetime.now().isoformat(),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'source': 'livescore.com'
            }
            
        except:
            pass
        
        return None
    
    def looks_like_match_element(self, element, text):
        """Check if element likely contains match data"""
        # Check text patterns
        if len(text) < 10 or len(text) > 300:
            return False
            
        # Look for match indicators
        match_indicators = [
            r'\d+\s*[-:]\s*\d+',  # Score
            r'\bvs?\b',  # versus
            r'\d{1,2}:\d{2}',  # Time
            r'\bFT\b|\bHT\b|\bLIVE\b',  # Status
        ]
        
        text_lower = text.lower()
        indicator_count = sum(1 for pattern in match_indicators if re.search(pattern, text, re.I))
        
        # Football terms
        football_terms = ['premier league', 'champions league', 'la liga', 'bundesliga', 
                         'serie a', 'ligue 1', 'uefa', 'match', 'fixture']
        
        has_football_terms = any(term in text_lower for term in football_terms)
        
        return indicator_count >= 1 or has_football_terms
    
    def extract_teams_and_scores(self, element, match_data):
        """Extract team names and scores from element"""
        text = element.get_text(strip=True)
        
        # Look for score pattern first
        score_match = re.search(r'(\d+)\s*[-:]\s*(\d+)', text)
        if score_match:
            match_data['home_score'] = score_match.group(1)
            match_data['away_score'] = score_match.group(2)
            
            # Split text around score to find teams
            parts = re.split(r'\d+\s*[-:]\s*\d+', text)
            if len(parts) >= 2:
                home_part = parts[0].strip()
                away_part = parts[1].strip()
                
                if home_part:
                    match_data['home_team'] = re.sub(r'[^\w\s]', '', home_part)[-50:].strip()
                if away_part:
                    match_data['away_team'] = re.sub(r'[^\w\s]', '', away_part)[:50].strip()
        
        # Try alternative patterns for team extraction
        if match_data['home_team'] == 'Unknown':
            # Look for team names in child elements
            team_elements = element.find_all(['span', 'div', 'a'], limit=10)
            potential_teams = []
            
            for elem in team_elements:
                elem_text = elem.get_text(strip=True)
                if (len(elem_text) > 2 and 
                    not re.match(r'^\d+$', elem_text) and
                    not re.match(r'^\d{1,2}:\d{2}$', elem_text)):
                    potential_teams.append(elem_text[:50])
            
            if len(potential_teams) >= 2:
                match_data['home_team'] = potential_teams[0]
                match_data['away_team'] = potential_teams[1]
    
    def extract_status_and_time(self, element, match_data):
        """Extract match status and time"""
        text = element.get_text(strip=True)
        
        # Time patterns
        time_patterns = [
            r'\b(\d{1,2}:\d{2})\b',  # 15:30
            r'\b(\d{1,2}\')\b',      # 45'
            r'\b(FT|HT|LIVE)\b',     # Status
            r'\b(Full Time|Half Time)\b'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                match_data['status'] = match.group(1)
                match_data['time'] = match.group(1)
                break
    
    def extract_league_info(self, element, match_data):
        """Extract league/competition information"""
        # Look in parent elements for league info
        current = element
        for _ in range(3):  # Check up to 3 levels up
            parent = current.find_parent(['div', 'section', 'article'])
            if parent:
                # Look for headings or league indicators
                league_elem = parent.find(['h1', 'h2', 'h3', 'h4'], string=re.compile(r'league|cup|championship', re.I))
                if league_elem:
                    match_data['league'] = league_elem.get_text(strip=True)[:50]
                    break
                current = parent
            else:
                break
    
    def process_and_deduplicate(self, matches):
        """Process and remove duplicate matches"""
        if not matches:
            return []
        
        # Remove duplicates based on teams and score
        seen = set()
        unique_matches = []
        
        for match in matches:
            # Create unique key
            key = f"{match['home_team'].lower()}-{match['away_team'].lower()}-{match['home_score']}-{match['away_score']}"
            
            if (key not in seen and 
                match['home_team'] != 'Unknown' and 
                match['away_team'] != 'Unknown' and
                len(match['home_team']) > 2 and
                len(match['away_team']) > 2):
                
                seen.add(key)
                unique_matches.append(match)
        
        # Sort by league and teams
        try:
            unique_matches.sort(key=lambda x: (x['league'], x['home_team']))
        except:
            pass
        
        return unique_matches
    
    def export_enhanced_data(self, matches):
        """Export enhanced match data with better formatting"""
        if not matches:
            print("⚠️ No matches to export")
            return []
        
        os.makedirs('exports', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        exported_files = []
        
        # Prepare data for export
        export_data = []
        for match in matches:
            export_data.append({
                'League': match['league'],
                'Home Team': match['home_team'],
                'Away Team': match['away_team'],
                'Home Score': match['home_score'],
                'Away Score': match['away_score'],
                'Final Score': f"{match['home_score']}-{match['away_score']}" if match['home_score'] and match['away_score'] else 'N/A',
                'Status': match['status'],
                'Time': match['time'],
                'Date': match['date'],
                'Scraped At': match['scraped_at'],
                'Raw Text': match['raw_text']
            })
        
        df = pd.DataFrame(export_data)
        
        try:
            # Excel export with formatting
            excel_file = f'exports/livescore_detailed_{timestamp}.xlsx'
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Matches', index=False)
                
                # Auto-adjust columns
                worksheet = writer.sheets['Matches']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            exported_files.append(excel_file)
            print(f"📋 Enhanced Excel exported: {excel_file}")
            
            # CSV export
            csv_file = f'exports/livescore_detailed_{timestamp}.csv'
            df.to_csv(csv_file, index=False)
            exported_files.append(csv_file)
            print(f"📄 Enhanced CSV exported: {csv_file}")
            
        except Exception as e:
            print(f"❌ Export error: {e}")
        
        return exported_files
    
    def create_detailed_summary(self, matches, exported_files):
        """Create detailed summary report"""
        if not matches:
            summary = {
                'timestamp': datetime.now().isoformat(),
                'total_matches': 0,
                'status': 'no_matches_found'
            }
        else:
            # Analyze matches
            leagues = {}
            statuses = {}
            
            for match in matches:
                league = match['league']
                status = match['status']
                
                leagues[league] = leagues.get(league, 0) + 1
                statuses[status] = statuses.get(status, 0) + 1
            
            summary = {
                'timestamp': datetime.now().isoformat(),
                'total_matches': len(matches),
                'leagues_found': len(leagues),
                'leagues_breakdown': leagues,
                'status_breakdown': statuses,
                'files_created': len(exported_files),
                'status': 'success'
            }
        
        # Save summary
        with open('exports/detailed_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print detailed summary
        print("\n" + "="*60)
        print("📊 ENHANCED LIVESCORE SUMMARY REPORT")
        print("="*60)
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"🏆 Total matches: {summary['total_matches']}")
        print(f"🏟️ Leagues found: {summary.get('leagues_found', 0)}")
        print(f"📁 Files created: {len(exported_files)}")
        
        if matches:
            print(f"\n🏆 League Breakdown:")
            for league, count in summary.get('leagues_breakdown', {}).items():
                print(f"   {league}: {count} matches")
                
            print(f"\n⏱️ Status Breakdown:")
            for status, count in summary.get('status_breakdown', {}).items():
                print(f"   {status}: {count} matches")
        
        print("="*60)
        return summary
    
    def run_enhanced_task(self):
        """Run the enhanced daily task"""
        try:
            print("🚀 Starting Enhanced Livescore AI Agent")
            print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
            
            # Scrape matches with enhanced methods
            matches = self.scrape_matches()
            
            # Export with better formatting
            exported_files = self.export_enhanced_data(matches)
            
            # Create detailed summary
            summary = self.create_detailed_summary(matches, exported_files)
            
            if matches:
                print("✅ Enhanced daily task completed successfully!")
                print(f"🎯 Found detailed data for {len(matches)} matches")
            else:
                print("⚠️ No detailed matches found - trying backup methods")
                
            return summary
            
        except Exception as e:
            print(f"❌ Enhanced task failed: {e}")
            
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
    """Main entry point for enhanced agent"""
    agent = EnhancedLivescoreAgent()
    result = agent.run_enhanced_task()
    
    # Print final status
    if result.get('status') == 'success':
        print(f"\n🎉 SUCCESS: Found {result['total_matches']} detailed matches!")
        print(f"🏟️ Covering {result.get('leagues_found', 0)} different leagues!")
    else:
        print(f"\n⚠️ COMPLETED: {result.get('status', 'unknown')}")

if __name__ == "__main__":
    main()
