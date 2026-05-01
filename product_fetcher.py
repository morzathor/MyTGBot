
import requests as rq
import json
import re
import os
from rtl import rtl
from urllib.parse import urlparse
import tldextract




THIS_DIR = os.path.dirname(__file__)
FILE_PATH = os.path.join(THIS_DIR, 'file1.txt')


def get_product(user_link, file_path=FILE_PATH, write_file=False):

    response = rq.get(f'{user_link}')
    response_text = response.text

    # if write_file:
    #     # Create or overwrite the file with the latest HTML
    #     with open(file_path, 'w', encoding='utf-8') as f:
    #         f.write(response_text)

    #     # Read back the file content to preserve original flow
    #     with open(file_path, 'r', encoding='utf-8') as ff:
    #         target_text = ff.read()
    # else:
        # Run regex directly against the HTTP response (no file I/O)
    target_text = response_text

    sku_matches = re.findall(r'sku\\".*?\"(.*?)\\"', target_text)
    if not sku_matches:
        raise ValueError('Not valid product!!')
    return int(sku_matches[0])


def get_price(product_id):
    """    """
    # Accept either a product id (int/str of digits) or a product URL
    if isinstance(product_id, int) or (isinstance(product_id, str) and product_id.isdigit()):
        pid = int(product_id)
    else:
        # treat product_id as a URL and extract SKU using get_product
        pid = get_product(product_id, write_file=False)

    req = rq.get(
        f'https://api2.zoomit.ir/catalog/api/products/{pid}/stores?sort=Cheapest&searchQuery=&inStock=false'
    )

    try:
        data = json.loads(req.text)
    except json.JSONDecodeError:
        raise ValueError('API did not return valid JSON')

    # Use regex on raw response text to extract price and description reliably
    response_text = req.text
    price_matches = re.findall(r'"price"\s*:\s*([0-9.]+)', response_text)
    description_matches = re.findall(r'"description"\s*:\s*"([^"]+)"', response_text)
    
    if not price_matches:
        raise ValueError('Price not found in API response')
    
    price_val = price_matches[0]
    description = description_matches[0] if description_matches else ''
    
    # Ensure numeric conversion and formatted thousands separator
    price_int = int(float(price_val))
    price_desc = [price_int,description]
    return price_desc


# e = str(input('Give me a link: '))

def get_main_site(url):

    parsed = urlparse(url if "://" in url else "http://" + url)
    ext = tldextract.extract(parsed.hostname)
    if ext.domain == 'zoomit':
        #print('\nhah\n')
        return get_price(str(url))
    else:
        return 'نمیفهمم چی میگی'

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        print(get_main_site(sys.argv[1]))
    else:
        print('Usage: python product_fetcher.py <url>')