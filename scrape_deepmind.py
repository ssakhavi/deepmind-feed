import requests
from bs4 import BeautifulSoup
from rfeed import *
import datetime
import re
import xml.etree.ElementTree as ET
import time

def scrape_deepmind_publications():
    url = "https://deepmind.google/research/publications/"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching DeepMind URL: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    publications = []
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '/research/publications/' in href and href != '/research/publications/' and '/page/' not in href:
            title = link.get_text(strip=True)
            
            if not title or title.lower() == "learn more":
                continue
                
            if href.startswith('/'):
                full_url = f"https://deepmind.google{href}"
            else:
                full_url = href
            
            # Extract date if present in title
            date_match = re.search(r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})', title)
            pub_date = datetime.datetime.now()
            
            if date_match:
                date_str = date_match.group(1)
                try:
                    pub_date = datetime.datetime.strptime(date_str, "%d %B %Y")
                    title = title.replace(date_str, "").strip()
                except ValueError:
                    pass
            
            if not title:
                continue

            publications.append({
                'title': title,
                'link': full_url,
                'description': f"New publication from Google DeepMind: {title}",
                'author': "Google DeepMind",
                'pubDate': pub_date,
                'source': 'DeepMind' # Marker for deduplication preference
            })

    return publications

def scrape_arxiv_papers():
    # Broad query for recent papers in relevant categories
    # cs.AI: Artificial Intelligence
    # cs.LG: Machine Learning
    # cs.CV: Computer Vision
    # cs.RO: Robotics
    # stat.ML: Machine Learning (Stats)
    query = 'cat:cs.AI OR cat:cs.LG OR cat:cs.CV OR cat:cs.RO OR cat:stat.ML'
    
    print(f"Querying ArXiv for recent papers: {query}")
    base_url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": query,
        "start": 0,
        "max_results": 100,  # Fetch last 100 papers
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching ArXiv: {e}")
        return []

    root = ET.fromstring(response.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    
    papers = []
    
    for entry in root.findall('atom:entry', ns):
        link_elem = entry.find('atom:id', ns)
        if link_elem is not None and link_elem.text is not None:
            link = link_elem.text
        else:
            link = ""
        
        title_elem = entry.find('atom:title', ns)
        title = title_elem.text.strip().replace('\n', ' ') if title_elem is not None and title_elem.text else "No Title"

        # Check metadata first
        is_deepmind = False
        
        # Check title/summary for "DeepMind" (sometimes listed in text)
        summary_elem = entry.find('atom:summary', ns)
        summary = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""
        
        if "DeepMind" in summary or "DeepMind" in title:
            is_deepmind = True
            
        # Check authors/affiliations if available in metadata (ArXiv API often lacks explicit affiliation fields but check likely places)
        # Note: default ArXiv API doesn't always return affiliation. 
        # But if "Google DeepMind" is in the author list string (unlikely in standard Atom, but checks just in case)
        for author in entry.findall('atom:author', ns):
            name = author.find('atom:name', ns)
            if name is not None and name.text and "DeepMind" in name.text:
                is_deepmind = True
                break
        
        # If not found in metadata, check HTML content
        if not is_deepmind and link:
            # Extract ID from link (http://arxiv.org/abs/2602.XXXXX)
            # HTML URL format: https://arxiv.org/html/2602.XXXXX
            try:
                arxiv_id = link.split("/abs/")[-1]
                # specific version might be included in ID (v1), usually link has it.
                html_url = f"https://arxiv.org/html/{arxiv_id}"
                
                print(f"Checking HTML content for: {title} ({html_url})")
                try:
                    # Timeout to prevent hanging
                    html_response = requests.get(html_url, timeout=10)
                    if html_response.status_code == 200:
                        # Check first 50KB or so to be safe/fast, usually affiliation is at top
                        content_sample = html_response.text[:50000]
                        if "Google DeepMind" in content_sample or "DeepMind" in content_sample:
                            print(f"Found DeepMind in HTML content for: {title}")
                            is_deepmind = True
                except Exception as e:
                    print(f"Failed to check HTML for {arxiv_id}: {e}")
            except Exception as e:
                print(f"Error parsing link {link}: {e}")

        if is_deepmind:
            published_elem = entry.find('atom:published', ns)
            published_str = published_elem.text if published_elem is not None else ""
            
            pub_date = datetime.datetime.now()
            if published_str:
                try:
                    pub_date = datetime.datetime.strptime(published_str, "%Y-%m-%dT%H:%M:%SZ")
                except ValueError:
                    pass
            
            papers.append({
                'title': title,
                'link': link,
                'description': summary,
                'author': "Google DeepMind (ArXiv)",
                'pubDate': pub_date,
                'source': 'ArXiv'
            })
            
    return papers

def normalize_title(title):
    return re.sub(r'\W+', '', title.lower())

def deduplicate_and_merge(dm_papers, arxiv_papers):
    merged = []
    seen_titles = set()
    
    # Add DeepMind papers first (priority)
    for p in dm_papers:
        norm_title = normalize_title(p['title'])
        merged.append(p)
        seen_titles.add(norm_title)
        
    # Add ArXiv papers if not duplicate
    for p in arxiv_papers:
        norm_title = normalize_title(p['title'])
        if norm_title not in seen_titles:
            merged.append(p)
            seen_titles.add(norm_title)
        else:
            # Optional: Determine if ArXiv version is "newer" or has different info?
            # For now, we prefer the official site presence if it exists.
            print(f"Skipping duplicate/existing paper from ArXiv: {p['title']}")
            
    # Sort by date descending
    merged.sort(key=lambda x: x['pubDate'], reverse=True)
    return merged

def generate_rss_feed(items_data):
    rss_items = []
    for data in items_data:
        item = Item(
            title = data['title'],
            link = data['link'],
            description = data['description'],
            author = data['author'],
            guid = Guid(data['link']),
            pubDate = data['pubDate']
        )
        rss_items.append(item)

    feed = Feed(
        title = "Google DeepMind Publications",
        link = "https://deepmind.google/research/publications/",
        description = "Latest research publications from Google DeepMind (Official + ArXiv)",
        language = "en-US",
        lastBuildDate = datetime.datetime.now(),
        items = rss_items
    )
    return feed.rss()

if __name__ == "__main__":
    print("Scraping DeepMind website...")
    dm_papers = scrape_deepmind_publications()
    print(f"Found {len(dm_papers)} papers on DeepMind website.")
    
    print("Scraping ArXiv...")
    arxiv_papers = scrape_arxiv_papers()
    print(f"Found {len(arxiv_papers)} papers on ArXiv.")
    
    print("Merging and deduplicating...")
    all_papers = deduplicate_and_merge(dm_papers, arxiv_papers)
    print(f"Total unique papers: {len(all_papers)}")
    
    rss_xml = generate_rss_feed(all_papers)
    
    with open("feed.xml", "w", encoding='utf-8') as f:
        f.write(rss_xml)
    
    print(f"Generated RSS feed with {len(all_papers)} items.")
