import requests
from io import StringIO
from bs4 import BeautifulSoup
import pandas as pd

url = "https://www.business-standard.com/companies/results/latest-results-list"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.content, 'html.parser')

tables = soup.find_all('table')
print(f"Found {len(tables)} tables.")

for i, table in enumerate(tables):
    print(f"\nTable {i}:")
    df = pd.read_html(StringIO(str(table)))[0]
    print(df.head())
