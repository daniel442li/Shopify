from colorama import init
from termcolor import colored
import datetime
import requests
import json
import time
from bs4 import BeautifulSoup as soup
import urllib3

def getprofile():
    with open('shopConfig.json') as f:
        profile = json.load(f)
    return profile
profile = getprofile()

def logFormat():
    now = str(datetime.datetime.now())
    now = now.split(' ')[1]
    printFormat = '[' + str(now) + ']' + ' ' + '[Shopify Bot] '
    return printFormat

class shopifyMain():
    def __init__(self):
        print(colored(logFormat() + "Shopify Bot Starting", "green"))
        session = requests.session()
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.checkoutProcess(session)

    def searchProduct(self, session):
        keywords = profile['keywords']
        size = profile['size']
        monitorDelay = profile['monitorDelay']
        while True:
            print(colored(logFormat() + "Searching for Product", "magenta"))
            #Can change the limit, but it slows down the higher you go
            link = 'http://' + profile['store'] + '.com/collections/all/products.json?limit=20'
            shopprofile = requests.get(link)
            shopprofile = shopprofile.json()
            products = (shopprofile['products'])
            print(colored(logFormat() + "Product Page Parsed", "cyan"))
            for item in products:
                itemName = item['title']
                if all(x in itemName for x in keywords):
                    productName = itemName
                    print(colored(logFormat() + "Product Found", "green"))
                    variants = item['variants']
                    for productVariant in variants:
                        if (size in productVariant['title']):
                            print(colored(logFormat() + "Size Found", "yellow"))
                            return productVariant['id']
                    print(colored(logFormat() + "Size Not Found", "red"))
            else:
                print(colored(logFormat() + "Product Not Found, Trying Another Endpoint", "red"))
            
            print(colored(logFormat() + "Retrying", "yellow"))
            time.sleep(monitorDelay)
    
    def addToCart(self, session):
        variant = self.searchProduct(session)
        link = "https://" + profile['store'] + ".com/cart/add.js?quantity=1&id=" + str(variant)
        print(colored(logFormat() + "Added to Cart", "cyan"))
        response = session.post(link)
        atcprofile = json.loads(response.text)
        
        checkID = (atcprofile['id'])
        
        cookies = session.cookies.get_dict()
        getToken = session.get('https://' + profile['store'] + '.com/cart.js', cookies= cookies)
        cartprofile = json.loads(getToken.text)
        token = cartprofile['token']
        
        '''
        At first, I was planning to use a PayPal checkout in order to skip almost the whole checkout process and likely have 
        a better shot at bot protection, but that would be better created later. 
        '''
        payLink = "https://" + profile['store'] + '.com/wallets/checkouts.json'
        payload = "{\"checkout\":{\"cart_token\":\"%s\",\"secret\":true,\"wallet_name\":\"PayPalV4\",\"is_upstream_button\":false,\"page_type\":\"\",\"presentment_currency\":\"USD\"}}" %(token)
        headers = {
        #This authorizaiton varys by site, in this example, it's Saint Alfreds
        'authorization': 'Basic ODQ5YWY2ZmEwNjVkZTE0YjAyMWUxMTlhNGFkMTJiYzA=',
        'content-type': 'application/json',
        }
        
        walletResponse = session.post(payLink, headers=headers, data = payload, cookies = cookies, allow_redirects=True)
        walletprofile = json.loads(walletResponse.text)
        #print(walletprofile)
        checkoutLink = (walletprofile['checkout']['web_url'])
        return checkoutLink
    
    def checkoutProcess(self, session):
        checkoutLink = self.addToCart(session)
        cookies = session.cookies.get_dict()
        response = session.get(checkoutLink, verify=False, allow_redirects=True)
        checkoutLink = (response.url)
        bs = soup(response.text, "html.parser")
        authToken = bs.find('input', {"name":"authenticity_token"})['value']
        
        while True:
            if 'stock_problems' in checkoutLink:
                print(colored(logFormat() + "Product OOS, Waiting for Restock", "red"))
                time.sleep(profile['monitorDelay'])
            else:
                print(colored(logFormat() + "Found Checkout URL, In-Stock", "magenta"))
                break
        
        
        if 'queue' in checkoutLink:
            while True:
                if 'queue' in checkoutLink:
                    time.sleep(0.1)
                else:
                    print(colored(logFormat() + "Through Queue", "cyan"))
                    break
        else:
            print(colored(logFormat() + "No Queue", "cyan"))

        
        #Note: Needs some sort of captcha checking or anywhere captchas usually pop up in order to have a chance on drop day

        headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
        }

        payload = {
        "utf8": u'\u2713',
        "_method": "patch",
        "authenticity_token": authToken,
        "previous_step": "contact_information",
        "step": "shipping_method",
        "checkout[email]": profile['email'],
        "checkout[buyer_accepts_marketing]": "0",
        "checkout[shipping_address][first_name]": profile['firstName'],
        "checkout[shipping_address][last_name]": profile['lastName'],
        "checkout[shipping_address][address1]": profile['addy'],
        "checkout[shipping_address][address2]": "",
        "checkout[shipping_address][city]": profile['city'],
        "checkout[shipping_address][country]": profile['country'],
        "checkout[shipping_address][province]": profile['state'],
        "checkout[shipping_address][zip]": profile['zipCode'],
        "checkout[shipping_address][phone]": profile['phoneNumber'],
        "checkout[remember_me]": "0",
        "checkout[client_details][browser_width]": "1920",
        "checkout[client_details][browser_height]": "1080",
        "checkout[client_details][javascript_enabled]": "1",
        }

        while True:
            response = session.post(checkoutLink, cookies=cookies, headers=headers, data=payload, verify=False)
            if response.status_code is 200:
                print(colored(logFormat() + "Customer Info Submitted", "green"))
                break
            else:
                print(colored(logFormat() + "Error Submitting Customer Info, Retrying", "yellow"))
                time.sleep(1)
        
        
        shipmentOptionLink = "http://" + profile['store'] + ".com" + "//cart/shipping_rates.json?shipping_address[zip]=" + profile['zipCode'] + "&shipping_address[country]=" + profile['country'] + "&shipping_address[province]=" + profile['state']
        shipmentOptionLink = shipmentOptionLink.replace(' ', '%20')

        response = session.get(shipmentOptionLink, cookies=cookies, verify=False)
        shipOptions = json.loads(response.text)
        shipRate = None

        try:
            shipmentOption = shipOptions["shipping_rates"][0]["name"].replace(' ', "%20")
            shipmentPrice = shipOptions["shipping_rates"][0]["price"]
            shipRate = "shopify-" + shipmentOption + "-" + shipmentPrice
        except:
            print(colored(logFormat() + "Shipping Token Error, Setting Shipping as None", "green"))

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
        }

        payload = {
            "utf8": u'\u2713',
            "_method": "patch",
            "authenticity_token": authToken,
            "previous_step": "shipping_method",
            "step": "payment_method",
            "checkout[shipping_rate][id]": shipRate,
        }

        while True:
            response = session.post(checkoutLink, data=payload, cookies=cookies, headers=headers, verify=False)
            if "payment_method" in response.url:
                print(colored(logFormat() + "Shipping Submitted", "yellow"))
                break
            else:
                print(colored(logFormat() + "Shipping Error, Retrying", "red"))
                time.sleep(1)

        link = checkoutLink + '?step=payment_method'
        response = session.get(link, cookies=cookies, verify=False)
        bs = soup(response.text, "html.parser")
        div = bs.find("div", {"class": "radio__input"})
        gateway = ""
        values = str(div.input).split('"')
        for value in values:
            if value.isnumeric():
                gateway = value
                break

        bs = soup(response.text, "html.parser")
        totalPrice = bs.find('input', {'name': 'checkout[total_price]'})['value']

        link = "https://elb.deposit.shopifycs.com/sessions"

        payload = {
            "credit_card": {
                "number": profile['cardNumber'],
                "name": profile['nameOnCard'],
                "month": profile['expMonth'],
                "year": profile['expYear'],
                "verification_value": profile['cvv']
            }
        }

        response = session.post(link, json=payload, verify=False)
        payment_token = json.loads(response.text)["id"]


        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36"
        }

        payload = {
            "utf8": u'\u2713',
            "_method": "patch",
            "authenticity_token": authToken,
            "previous_step": "payment_method",
            "step": "",
            'checkout[buyer_accepts_marketing]': '1', 
            "s": payment_token,
            "checkout[payment_gateway]": gateway,
            "checkout[different_billing_address]": "false",
            'checkout[credit_card][vault]': 'false',
            'checkout[total_price]': totalPrice,
            "complete": "1",
            "checkout[client_details][browser_width]": '1920',
            "checkout[client_details][browser_height]": '1080',
            "checkout[client_details][javascript_enabled]": "1",
        }

        response = session.post(checkoutLink, cookies=cookies, headers=headers, data=payload, verify=False)

        if response.status_code == 404:
            print(colored(logFormat() + "Payment Failed", "red"))
        elif response.status_code == 200:
            print(colored(logFormat() + "Checked Out", "green"))
