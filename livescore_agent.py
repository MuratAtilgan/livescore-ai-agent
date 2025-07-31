name: Daily Livescore AI Agent

on:
  schedule:
    # Run every day at 8:00 AM UTC (adjust time as needed)
    - cron: '0 8 * * *'
  workflow_dispatch: # Allows manual trigger for testing

jobs:
  scrape-livescore:
    runs-on: ubuntu-latest
    
    steps:
    - name: 📥 Checkout repository
      uses: actions/checkout@v4
    
    - name: 🐍 Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: 📦 Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: 📁 Create export directory
      run: mkdir -p exports
    
    - name: 🤖 Run Livescore AI Agent
      run: python livescore_agent.py
    
    - name: 📊 Upload results
      uses: actions/upload-artifact@v4
      if: always() # Upload even if scraping partially failed
      with:
        name: livescore-data-${{ github.run_number }}
        path: exports/
        retention-days: 30
    
    - name: 📝 Display summary
      if: always()
      run: |
        echo "🎉 Daily scraping completed!"
        echo "📁 Files created:"
        ls -la exports/ || echo "No exports directory found"
        
        if [ -f exports/daily_summary.json ]; then
          echo "📊 Summary:"
          cat exports/daily_summary.json
        fi
    
    - name: 🚨 Notify on failure
      if: failure()
      run: |
        echo "❌ Scraping failed! Check the logs above."
        echo "💡 This might happen if the website structure changed."
