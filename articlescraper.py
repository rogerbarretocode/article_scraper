import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import time
import random
from openai import OpenAI
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Hardcoded API keys
SERP_API_KEY = ""
OPENAI_API_KEY = ""

def search_articles(query, article_type, num_results=5):
    url = "https://serpapi.com/search.json"
    params = {
        "q": query,
        "api_key": SERP_API_KEY,
        "num": num_results
    }
    
    if article_type == "News":
        params["tbm"] = "nws"
    
    response = requests.get(url, params=params)
    results = json.loads(response.text)
    
    if article_type == "News":
        return results.get('news_results', [])
    else:
        return results.get('organic_results', [])

def scrape_article(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    title = soup.find('h1').text.strip() if soup.find('h1') else "No title found"
    
    content_tags = soup.find_all(['p', 'article', 'div'], class_=['content', 'article-content', 'story-content'])
    content = ' '.join([tag.text.strip() for tag in content_tags])
    
    if not content:
        content = ' '.join([p.text.strip() for p in soup.find_all('p') if len(p.text.strip()) > 50])
    
    return {
        'title': title,
        'content': content,
        'url': url
    }

def format_content_with_openai(content):
    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        prompt = f"Summarize the following article content in plain text format, with clear paragraph breaks:\n\n{content[:4000]}"  # Limit to 4000 characters
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes articles."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            n=1,
            temperature=0.7,
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error in OpenAI API call: {str(e)}")
        return None

def main():
    st.set_page_config(page_title="Article Scraper", layout="wide")
    st.title("Article Scraper")

    article_type = st.radio("Select article type:", ("News", "General"))
    topic = st.text_input("Enter the topic you want to search for:")
    num_articles = st.slider("Number of articles to scrape:", 1, 10, 5)

    if st.button("Scrape Articles"):
        if not topic:
            st.warning("Please enter a topic to search for.")
            return

        with st.spinner("Scraping articles..."):
            article_results = search_articles(topic, article_type, num_articles)

            st.info(f"Found {len(article_results)} articles")

            scraped_articles = []
            for article in article_results:
                try:
                    url = article.get('link') or article.get('url')  # Handle both News and General results
                    if not url:
                        st.warning(f"No URL found for article: {article}")
                        continue

                    full_article = scrape_article(url)
                    full_article['source'] = article.get('source') or article.get('displayed_link', 'Unknown')
                    full_article['date'] = article.get('date') or article.get('snippet', 'Unknown')

                    formatted_content = format_content_with_openai(full_article['content'])
                    if formatted_content:
                        full_article['formatted_content'] = formatted_content
                    else:
                        st.warning(f"OpenAI formatting failed for {full_article['title']}. Using fallback.")
                        full_article['formatted_content'] = full_article['content'][:1000] + "..."

                    scraped_articles.append(full_article)
                    st.success(f"Scraped and processed: {full_article['title']}")

                    time.sleep(random.uniform(1, 3))
                except Exception as e:
                    st.error(f"Error processing {url}: {str(e)}")

            for article in scraped_articles:
                st.markdown("---")
                st.subheader(article['title'])
                st.write(f"Source: {article['source']} | Date: {article['date']}")
                st.markdown(f"[Read original article]({article['url']})")
                
                st.markdown(article['formatted_content'])

if __name__ == "__main__":
    main()