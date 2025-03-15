from urllib.parse import urlparse
import re 

def extract_domain(url:str):
    if not url.startswith(('http://', 'https://', 'ftp://')):
        url = 'http://' + url
    
    parsed = urlparse(url)
    netloc = parsed.netloc
    
    if '@' in netloc:
        netloc = netloc.split('@')[-1]
    domain = netloc.split(':')[0]
    
    return domain

import re

def extract_html_from_markdown(md_text):
    pattern = re.compile(r'^```\s*html\s*$\n(.*?)^```\s*$', re.MULTILINE | re.DOTALL | re.IGNORECASE)
    matches = pattern.findall(md_text)
    return [match.strip() for match in matches]

md='''为了实现从Markdown中提取HTML代码块的功能，我们可以编写一个Python函数，利用正则表达式匹配Markdown中的HTML代码块。以下是实现这一功能的代码：
```html
<div class="test">
    <p>Hello</p>
</div>
```Another code block:
```
<span>Inline</span>
```
Not HTML:```
console.log("<div>");
```'''

def main():
    test_urls = [
        "https://www.example.com",
        "http://user:pass@sub.example.com:8080/path",
        "www.example.com/path?query=1",
        "ftp://example.com:2121",
        "mailto:user@example.com",  
        "[2001:db8::1]:8080"       
    ]
    # for url in test_urls:
    #     print(f"URL: {url.ljust(35)} →                      {extract_domain(url)}")
    print(extract_html_from_markdown(md))
if __name__ == "__main__":
    main()