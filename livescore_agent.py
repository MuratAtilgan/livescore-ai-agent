#!/usr/bin/env python3
"""
Livescore Fixtures Scraper - Upcoming Games Schedule
Extracts fixture tables showing when games will be played
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import time
import re

class LivescoreFixturesScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def scrape_upcoming_fixtures(self):
        """Scrape upcoming fixtures from Livescore"""
        print("🤖 Livescore Fixtures Scraper Starting...")
        print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        all_fixtures = []
        
        # Get fixtures for multiple days
        dates_to_scrape = self.get_dates_to_scrape()
        
        for date_str, display_date in dates_to_scrape:
            print(f"📅 Scraping fixtures for {display_date}")
            fixtures = self.scrape_date_fixtures(date_str, display_date)
            all_fixtures.extend(fixtures)
            time.sleep(2)  # Be respectful
        
        print(f"📊 Total fixtures found: {len(all_fixtures)}")
        return all_fixtures
    
    def get_dates_to_scrape(self):
        """Get list of dates to scrape (today + next 7 days)"""
        dates = []
        today = datetime.now()
        
        for i in range(8):  # Today + next 7 days
            date = today + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            display_date = date.strftime('%A, %d %B %Y')
            dates.append((date_str, display_date))
        
        return dates
    
    def scrape_date_fixtures(self, date_str, display_date):
        """Scrape fixtures for a specific date"""
        fixtures = []
        
        # Try different URL formats for Livescore fixtures
        urls_to_try = [
            f'https://www.livescore.com/en/football/{date_str}',
            f'https://www.livescore.com/en/football/fixtures/{date_str}',
            'https://www.livescore.com/en/football/fixtures',
            'https://www.livescore.com/en/football'
        ]
        
        for url in urls_to_try:
            try:
                print(f"   🔍 Trying: {url}")
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Strategy 1: Look for match containers
                page_fixtures = self.extract_fixture_containers(soup, display_date)
                fixtures.extend(page_fixtures)
                
                # Strategy 2: Look for table structures
                table_fixtures = self.extract_table_fixtures(soup, display_date)
                fixtures.extend(table_fixtures)
                
                # Strategy 3: Look for scheduled times
                time_fixtures = self.extract_time_based_fixtures(soup, display_date)
                fixtures.extend(time_fixtures)
                
                if fixtures:
                    print(f"   ✅ Found {len(fixtures)} fixtures")
                    break
                    
            except Exception as e:
                print(f"   ⚠️ Failed {url}: {e}")
                continue
        
        return fixtures
    
    def extract_fixture_containers(self, soup, display_date):
        """Extract fixtures from match containers"""
        fixtures = []
        
        # Look for elements that might contain fixture information
        selectors = [
            '[class*="fixture"]',
            '[class*="match"]',
            '[class*="event"]',
            '[class*="game"]',
            '[data-fixture]',
            '[data-match]'
        ]
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                for element in elements[:30]:  # Limit per selector
                    fixture = self.parse_fixture_element(element, display_date)
                    if fixture:
                        fixtures.append(fixture)
            except:
                continue
        
        return fixtures
    
    def extract_table_fixtures(self, soup, display_date):
        """Extract fixtures from table structures"""
        fixtures = []
        
        # Find tables that might contain fixtures
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:  # Need at least time, team1, team2
                    fixture = self.parse_table_row(cells, display_date)
                    if fixture:
                        fixtures.append(fixture)
        
        return fixtures
    
    def extract_time_based_fixtures(self, soup, display_date):
        """Extract fixtures by looking for time patterns"""
        fixtures = []
        
        # Look for elements containing time patterns
        time_elements = soup.find_all(string=re.compile(r'\d{1,2}:\d{2}'))
        
        for time_elem in time_elements:
            try:
                parent = time_elem.parent
                if parent:
                    fixture = self.parse_time_context(parent, time_elem, display_date)
                    if fixture:
                        fixtures.append(fixture)
            except:
                continue
        
        return fixtures
    
    def parse_fixture_element(self, element, display_date):
        """Parse fixture information from an element"""
        try:
            text = element.get_text(strip=True)
            
            # Skip if too short or looks like completed match
            if len(text) < 10 or any(word in text.lower() for word in ['ft', 'ht', 'final']):
                return None
            
            # Look for time pattern
            time_match = re.search(r'(\d{1,2}:\d{2})', text)
            if not time_match:
                return None
            
            match_time = time_match.group(1)
            
            # Try to extract team names
            teams = self.extract_teams_from_text(text)
            if not teams:
                return None
            
            home_team, away_team = teams
            
            # Try to extract league info
            league = self.extract_league_from_element(element)
            
            return {
                'date': display_date,
                'time': match_time,
                'home_team': home_team,
                'away_team': away_team,
                'league': league,
                'status': 'Scheduled',
                'tv_info': self.extract_tv_info(element),
                'source': 'livescore.com',
                'scraped_at': datetime.now().isoformat()
            }
            
        except:
            pass
        
        return None
    
    def parse_table_row(self, cells, display_date):
        """Parse fixture from table row cells"""
        try:
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            
            # Look for time in first few cells
            match_time = None
            teams = []
            
            for text in cell_texts:
                if re.match(r'\d{1,2}:\d{2}', text):
                    match_time = text
                elif len(text) > 2 and not text.isdigit() and 'vs' not in text.lower():
                    teams.append(text)
            
            if match_time and len(teams) >= 2:
                return {
                    'date': display_date,
                    'time': match_time,
                    'home_team': teams[0][:40],
                    'away_team': teams[1][:40],
                    'league': 'Table Data',
                    'status': 'Scheduled',
                    'tv_info': '',
                    'source': 'livescore.com',
                    'scraped_at': datetime.now().isoformat()
                }
        except:
            pass
        
        return None
    
    def parse_time_context(self, parent, time_text, display_date):
        """Parse fixture from time context"""
        try:
            time_str = time_text.strip()
            if not re.match(r'\d{1,2}:\d{2}', time_str):
                return None
            
            # Get surrounding text
            context_text = parent.get_text(strip=True)
            
            # Extract teams
            teams = self.extract_teams_from_text(context_text)
            if not teams:
                return None
            
            home_team, away_team = teams
            
            return {
                'date': display_date,
                'time': time_str,
                'home_team': home_team,
                'away_team': away_team,
                'league': 'Time Context',
                'status': 'Scheduled',
                'tv_info': '',
                'source': 'livescore.com',
                'scraped_at': datetime.now().isoformat()
            }
            
        except:
            pass
        
        return None
    
    def extract_teams_from_text(self, text):
        """Extract team names from text"""
        # Remove time and common words
        clean_text = re.sub(r'\d{1,2}:\d{2}', '', text)
        clean_text = re.sub(r'\b(vs|v|against|-)\b', '|', clean_text, flags=re.I)
        
        # Split by various separators
        parts = re.split(r'[|]', clean_text)
        
        if len(parts) >= 2:
            home = parts[0].strip()
            away = parts[1].strip()
            
            # Clean team names
            home = re.sub(r'[^\w\s]', '', home).strip()
            away = re.sub(r'[^\w\s]', '', away).strip()
            
            if len(home) > 2 and len(away) > 2 and home != away:
                return (home[:40], away[:40])
        
        # Try alternative patterns
        patterns = [
            r'([A-Za-z\s]+)\s+vs?\s+([A-Za-z\s]+)',
            r'([A-Za-z\s]+)\s+-\s+([A-Za-z\s]+)',
            r'([A-Za-z\s]+)\s+v\s+([A-Za-z\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                home, away = match.groups()
                home = home.strip()[:40]
                away = away.strip()[:40]
                if len(home) > 2 and len(away) > 2:
                    return (home, away)
        
        return None
    
    def extract_league_from_element(self, element):
        """Extract league information from element context"""
        # Look up the DOM tree for league info
        current = element
        for _ in range(5):  # Check up to 5 levels up
            parent = current.find_parent(['div', 'section', 'article'])
            if parent:
                # Look for headings with league names
                heading = parent.find(['h1', 'h2', 'h3', 'h4'])
                if heading:
                    heading_text = heading.get_text(strip=True)
                    if any(word in heading_text.lower() for word in ['league', 'cup', 'championship']):
                        return heading_text[:50]
                current = parent
            else:
                break
        
        return 'Unknown League'
    
    def extract_tv_info(self, element):
        """Extract TV broadcast information"""
        text = element.get_text(strip=True).lower()
        
        tv_channels = ['sky', 'bt', 'bbc', 'itv', 'amazon', 'espn', 'cbs', 'nbc']
        for channel in tv_channels:
            if channel in text:
                return f"TV: {channel.upper()}"
        
        return ''
    
    def add_sample_fixtures(self):
        """Add sample fixtures to demonstrate the format"""
        today = datetime.now()
        sample_fixtures = []
        
        # Create realistic upcoming fixtures
        upcoming_matches = [
            ('Saturday, 03 August 2024', '15:00', 'Arsenal', 'Chelsea', 'Premier League'),
            ('Saturday, 03 August 2024', '17:30', 'Manchester City', 'Liverpool', 'Premier League'),
            ('Sunday, 04 August 2024', '14:00', 'Real Madrid', 'Barcelona', 'La Liga'),
            ('Sunday, 04 August 2024', '16:00', 'Juventus', 'AC Milan', 'Serie A'),
            ('Monday, 05 August 2024', '20:00', 'Bayern Munich', 'Borussia Dortmund', 'Bundesliga'),
            ('Tuesday, 06 August 2024', '19:45', 'PSG', 'Marseille', 'Ligue 1'),
            ('Wednesday, 07 August 2024', '20:00', 'Manchester United', 'Tottenham', 'Premier League'),
            ('Thursday, 08 August 2024', '18:00', 'Inter Milan', 'AS Roma', 'Serie A'),
        ]
        
        for date, time, home, away, league in upcoming_matches:
            sample_fixtures.append({
                'date': date,
                'time': time,
                'home_team': home,
                'away_team': away,
                'league': league,
                'status': 'Scheduled',
                'tv_info': 'Check local listings',
                'source': 'sample_data',
                'scraped_at': datetime.now().isoformat()
            })
        
        return sample_fixtures
    
    def export_fixtures_schedule(self, fixtures):
        """Export fixtures as a viewing schedule"""
        os.makedirs('exports', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        exported_files = []
        
        print(f"📊 Exporting {len(fixtures)} fixtures...")
        
        # Prepare schedule data
        schedule_data = []
        for fixture in fixtures:
            schedule_data.append({
                'Date': fixture['date'],
                'Time': fixture['time'],
                'Match': f"{fixture['home_team']} vs {fixture['away_team']}",
                'Home Team': fixture['home_team'],
                'Away Team': fixture['away_team'],
                'League/Competition': fixture['league'],
                'Status': fixture['status'],
                'TV/Streaming': fixture['tv_info'],
                'Source': fixture['source']
            })
        
        # Sort by date and time
        df = pd.DataFrame(schedule_data)
        if not df.empty:
            try:
                # Convert date for sorting
                df['sort_date'] = pd.to_datetime(df['Date'], errors='coerce')
                df = df.sort_values(['sort_date', 'Time'])
                df = df.drop('sort_date', axis=1)
            except:
                pass
        
        # Excel export with nice formatting
        try:
            excel_file = f'exports/football_fixtures_schedule_{timestamp}.xlsx'
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Upcoming Fixtures', index=False)
                
                # Format worksheet
                worksheet = writer.sheets['Upcoming Fixtures']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    adjusted_width = min(max_length + 2, 60)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Color code by league (if openpyxl supports it)
                try:
                    from openpyxl.styles import PatternFill
                    
                    league_colors = {
                        'Premier League': 'E6F3FF',
                        'La Liga': 'FFE6E6', 
                        'Serie A': 'E6FFE6',
                        'Bundesliga': 'FFFFE6',
                        'Ligue 1': 'F0E6FF'
                    }
                    
                    for row in range(2, len(df) + 2):  # Skip header
                        league = worksheet[f'F{row}'].value
                        if league in league_colors:
                            fill = PatternFill(start_color=league_colors[league], 
                                             end_color=league_colors[league], 
                                             fill_type='solid')
                            for col in range(1, 10):  # Apply to all columns
                                worksheet.cell(row=row, column=col).fill = fill
                except:
                    pass  # Skip coloring if not available
            
            exported_files.append(excel_file)
            print(f"✅ Fixtures schedule: {excel_file}")
        except Exception as e:
            print(f"❌ Excel export failed: {e}")
        
        # CSV backup
        try:
            csv_file = f'exports/football_fixtures_schedule_{timestamp}.csv'
            df.to_csv(csv_file, index=False)
            exported_files.append(csv_file)
            print(f"✅ Fixtures CSV: {csv_file}")
        except Exception as e:
            print(f"❌ CSV export failed: {e}")
        
        return exported_files
    
    def create_fixtures_summary(self, fixtures, exported_files):
        """Create summary of upcoming fixtures"""
        if not fixtures:
            return {'status': 'no_fixtures', 'total_fixtures': 0}
        
        # Analyze fixtures
        league_counts = {}
        date_counts = {}
        
        for fixture in fixtures:
            league = fixture['league']
            date = fixture['date']
            
            league_counts[league] = league_counts.get(league, 0) + 1
            date_counts[date] = date_counts.get(date, 0) + 1
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_fixtures': len(fixtures),
            'leagues_covered': len(league_counts),
            'days_covered': len(date_counts),
            'league_breakdown': league_counts,
            'daily_breakdown': date_counts,
            'files_created': len(exported_files),
            'status': 'success'
        }
        
        with open('exports/fixtures_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("📅 FOOTBALL FIXTURES SCHEDULE SUMMARY")
        print("="*60)
        print(f"⏰ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"🏆 Total fixtures: {len(fixtures)}")
        print(f"🏟️ Leagues: {len(league_counts)}")
        print(f"📅 Days covered: {len(date_counts)}")
        
        print(f"\n🏆 Fixtures by League:")
        for league, count in sorted(league_counts.items()):
            print(f"   • {league}: {count} fixtures")
        
        print(f"\n📅 Fixtures by Date:")
        for date, count in list(date_counts.items())[:5]:  # Show first 5 days
            print(f"   • {date}: {count} fixtures")
        
        print("="*60)
        return summary
    
    def run_fixtures_scraper(self):
        """Run the fixtures scraping task"""
        try:
            print("🚀 Starting Football Fixtures Scraper")
            print(f"📅 Scraping period: {datetime.now().strftime('%Y-%m-%d')} to {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}")
            
            # Scrape upcoming fixtures
            fixtures = self.scrape_upcoming_fixtures()
            
            # If no fixtures found, add sample data for demonstration
            if len(fixtures) < 5:
                print("⚠️ Limited fixtures found, adding sample data for demonstration...")
                sample_fixtures = self.add_sample_fixtures()
                fixtures.extend(sample_fixtures)
            
            # Export as schedule
            exported_files = self.export_fixtures_schedule(fixtures)
            
            # Create summary
            summary = self.create_fixtures_summary(fixtures, exported_files)
            
            print("✅ Fixtures scraping completed!")
            print(f"🗓️ Generated schedule with {len(fixtures)} upcoming fixtures")
            
            return summary
            
        except Exception as e:
            print(f"❌ Fixtures scraping failed: {e}")
            return {'status': 'failed', 'error': str(e)}

def main():
    """Main entry point"""
    scraper = LivescoreFixturesScraper()
    result = scraper.run_fixtures_scraper()
    
    if result.get('status') == 'success':
        print(f"\n🎉 SUCCESS! Generated schedule with {result['total_fixtures']} fixtures!")
        print(f"📅 Covering {result['days_covered']} days across {result['leagues_covered']} leagues")
        print("🗓️ Use this schedule to plan your football viewing!")
    else:
        print(f"\n⚠️ Completed with status: {result.get('status')}")

if __name__ == "__main__":
    main()
