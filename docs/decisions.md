Data source: https://dividendhistory.org/
- Reason: has data I'm looking for as well as a metrics table; robots.txt checked and scraping is allowed

Scraping tool: Selenium + Beautiful Soup
- Reason: Selenium is the tool I'm most familiar with and Beautiful Soup is an excellent HTML parser, ontop of that, the pages dividendhistory.org are loaded in using Javascript and so using Beautiful Soup alone is not viable

Data staleness thresholds:
- <7 days: fresh
  - returns from cache
- 7 - 30 days: stale
  - immediately returns from cache but triggers a background refresh
- \>30: expired
  - trigger re-scrape; does not return anything except for signal to user that they may have to wait awhile until the re-scrape has finished  
- Reason: dividends are announced at most quarterly, so a 30-day refresh gaurantees that at least one refresh per accounement cycle

Deployment target: Fly.io
- Reason: ease of use
