from urllib.parse import urlparse

def extract_domain(url:str):
    if not url.startswith(('http://', 'https://', 'ftp://')):
        url = 'http://' + url
    
    parsed = urlparse(url)
    netloc = parsed.netloc
    
    if '@' in netloc:
        netloc = netloc.split('@')[-1]
    domain = netloc.split(':')[0]
    
    return domain

def main():
    test_urls = [
        "https://www.example.com",
        "http://user:pass@sub.example.com:8080/path",
        "www.example.com/path?query=1",
        "ftp://example.com:2121",
        "mailto:user@example.com",  
        "[2001:db8::1]:8080"       
    ]
    for url in test_urls:
        print(f"URL: {url.ljust(35)} →                      {extract_domain(url)}")

if __name__ == "__main__":
    main()