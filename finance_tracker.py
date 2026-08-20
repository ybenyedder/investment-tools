import argparse
import requests
import json
from bs4 import BeautifulSoup
import sqlite3
import pandas as pd
import chromadb
import os

DB_PATH = 'finance_history.db'
CHROMA_PATH = 'chroma_db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_code INTEGER,
            company_name TEXT,
            company_full_name TEXT,
            net_sales REAL,
            net_profit REAL,
            eps REAL,
            result_date TEXT,
            UNIQUE(company_name, result_date)
        )
    ''')
    conn.commit()
    conn.close()

def init_chroma():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name="financial_results")
    return collection

def scrape_and_store():
    url = "https://www.business-standard.com/companies/results/latest-results-list"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    print("Fetching data from Business Standard...")
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    script_tag = soup.find('script', id='__NEXT_DATA__')
    if not script_tag:
        print("Could not find data payload in the page.")
        return
        
    data = json.loads(script_tag.string)
    
    try:
        results_list = data['props']['pageProps']['response2']['data']
    except KeyError:
        print("Data structure changed, could not extract latestResultList.")
        return
        
    print(f"Extracted {len(results_list)} results. Updating databases...")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    collection = init_chroma()
    
    added = 0
    for res in results_list:
        comp_code = res.get('company_code')
        comp_name = res.get('company_name')
        comp_full = res.get('company_full_name')
        net_sales = res.get('net_sales')
        net_profit = res.get('net_profit')
        eps = res.get('eps')
        try:
            eps_val = float(eps) if eps else None
        except ValueError:
            eps_val = None
        result_date = res.get('result_date')
        
        # Insert into SQLite
        try:
            c.execute('''
                INSERT INTO results (company_code, company_name, company_full_name, net_sales, net_profit, eps, result_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (comp_code, comp_name, comp_full, net_sales, net_profit, eps_val, result_date))
            
            added += 1
            
            # If successfully added to SQLite (not a duplicate), add to ChromaDB vector DB
            doc_text = f"Company {comp_full} ({comp_name}) reported quarterly results on {result_date}. Net Sales: {net_sales} Cr. Net Profit: {net_profit} Cr. EPS: {eps}."
            doc_id = f"{comp_name}_{result_date}"
            metadata = {
                "company_name": str(comp_name),
                "result_date": str(result_date),
                "net_sales": float(net_sales) if net_sales else 0.0,
                "net_profit": float(net_profit) if net_profit else 0.0
            }
            
            collection.add(
                documents=[doc_text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
        except sqlite3.IntegrityError:
            # Duplicate entry, ignore to avoid saving redundant history
            pass
            
    conn.commit()
    conn.close()
    print(f"Scraping complete. Added {added} new records to SQLite and Chroma Vector DB.")

def query_company(company_name):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query('SELECT * FROM results WHERE company_name LIKE ? OR company_full_name LIKE ? ORDER BY result_date ASC', conn, params=(f'%{company_name}%', f'%{company_name}%'))
    conn.close()
    
    if df.empty:
        print(f"No history found for company: {company_name}")
        
        print("\nChecking Vector Database for semantically similar matches...")
        collection = init_chroma()
        results = collection.query(
            query_texts=[company_name],
            n_results=3
        )
        if results['documents'] and results['documents'][0]:
            print("Did you mean one of these?")
            for doc in results['documents'][0]:
                print(f" - {doc}")
        
        return
        
    print(f"\nTime Series History for {df['company_name'].iloc[0]} ({df['company_full_name'].iloc[0]}):")
    display_df = df[['result_date', 'net_sales', 'net_profit', 'eps']].copy()
    print(display_df.to_string(index=False))
    
    try:
        import matplotlib.pyplot as plt
        df['parsed_date'] = pd.to_datetime(df['result_date'], format='%d/%m/%Y', errors='coerce')
        df = df.dropna(subset=['parsed_date']).sort_values('parsed_date')
        
        if not df.empty:
            plt.figure(figsize=(10, 5))
            plt.plot(df['parsed_date'], df['net_sales'], marker='o', label='Net Sales')
            plt.plot(df['parsed_date'], df['net_profit'], marker='x', label='Net Profit')
            plt.title(f"Financial Time Series: {df['company_name'].iloc[0]}")
            plt.xlabel("Date")
            plt.ylabel("Amount")
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            plot_path = f"{df['company_name'].iloc[0]}_timeseries.png"
            plt.savefig(plot_path)
            print(f"\nGenerated time series plot: {plot_path}")
    except ImportError:
        pass

if __name__ == "__main__":
    init_db()
    
    parser = argparse.ArgumentParser(description="Financial Results Tracker")
    parser.add_argument('--scrape', action='store_true', help="Scrape latest results and update DB")
    parser.add_argument('--company', type=str, help="Search for a company and view its time series history")
    
    args = parser.parse_args()
    
    if args.scrape:
        scrape_and_store()
        
    if args.company:
        query_company(args.company)
        
    if not args.scrape and not args.company:
        parser.print_help()
