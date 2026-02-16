# DeepMind Papers RSS Feed

This repository hosts a Python script that scrapes the [Google DeepMind Research Publications](https://deepmind.google/research/publications/) page and generates an RSS feed (`feed.xml`).

## Features
- **Automated Scraping**: Fetches the latest publications from DeepMind.
- **RSS Generation**: Creates a standard RSS 2.0 feed.
- **GitHub Actions**: Automatically updates the feed daily.

## Usage

### Local Execution
1.  Clone the repository.
2.  Install dependencies using [uv](https://github.com/astral-sh/uv):
    ```bash
    uv sync
    ```
3.  Run the script:
    ```bash
    uv run scrape_deepmind.py
    ```
4.  The `feed.xml` file will be generated in the root directory.

### Hosting with GitHub Pages
1.  Fork this repository.
2.  Go to **Settings** -> **Pages**.
3.  Select the `main` branch as the source.
4.  Your RSS feed will be available at: `https://<your-username>.github.io/<repo-name>/feed.xml`.

### Data Source
The feed is scraped from:
1.  [Google DeepMind Research Publications](https://deepmind.google/research/publications/) (Official Website)
2.  [ArXiv API](http://export.arxiv.org/api/query?search_query=all:%22Google+DeepMind%22) (For early access papers)

Deduplication logic prefers the official website version if a paper appears on both. All credit for the research goes to Google DeepMind and the respective authors.
