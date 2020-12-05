import time
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import json
import datetime
from trace import (
    get_web_driver_options, 
    get_chrome_web_driver,
    set_ignore_certificate_error,
    set_browser_as_incognito,
    NAME,
    CURRENCY,
    FILTERS,
    BASE_URL,
    DIRECTORY
)

# the numbers in each method are telling us the chronology in which we wrote the class
class GenerateReport:
    # 1
    def __init__(self, file_name, filters, base_link, currency, data):
        self.data = data
        self.file_name = file_name
        self.filters = filters
        self.base_link = base_link
        self.currency = currency
        report = {
            'title': self.file_name,
            'data': self.get_now(),
            'best_item': self.get_best_item(),
            'currency': self.currency,
            'filters': self.filters,
            'base_link': self.base_link,
            'products': self.data
        }
        print("Creating report ...")
        with open(f"{DIRECTORY}/{file_name}.json", 'w') as file_data:
            json.dump(report, file_data)
        print("Done ... :)")

    # 2
    def get_now(self):
        now = datetime.datetime.now()
        return now.strftime("%d/%m/%Y &H:%M:%S")

    # 3
    def get_best_item(self):
        try:
            # sorting a list of dictionary
            return sorted(self.data, key=lambda k: k['price'])[0]
        except Exception as er:
            print(er)
            print("Problem with sorting items")
            return None

# the numbers in each method are telling us the chronology in which we wrote the class
class AmazonAPI:
    # 1
    def __init__(self, search_term, filters, base_url, currency):
        self.base_url = base_url
        self.search_term = search_term
        options = get_web_driver_options()
        set_ignore_certificate_error(options)
        set_browser_as_incognito(options)
        self.driver = get_chrome_web_driver(options)
        self.currency = currency
        self.price_filter = f"&rh=p_36%3A{filters['min']}00-{filters['max']}00"
        
    # 2
    def run(self):
        print("Starting script....")
        print(f"Looking for {self.search_term} products...")
        links = self.get_product_links()
        time.sleep(1)
        if not links:
            print("Stopped script.")
            return
        print(f"Got {len(links)} links to products...")
        print("Getting info about products...")
        products = self.get_products_info(links)
        print(f"Got info about {len(products)} products ...")
        self.driver.quit()
        return products

    # 4
    def get_products_info(self, links):
        asins = self.get_asins(links)
        products = []
        for asin in asins:
            product = self.get_single_product_info(asin)
            if product:
                products.append(product)
        return products

    # 7
    def get_single_product_info(self, asin):
        print(f"Product ID {asin} - getting data ...")
        product_short_url = self.shorten_url(asin)
        self.driver.get(f'{product_short_url}?language=en_GB')
        time.sleep(2)
        title = self.get_title()
        seller = self.get_seller()
        price = self.get_price()
        if title and seller and price:
            product_info = {
                'Product ID': asin,
                'url': product_short_url,
                'title': title,
                'seller': seller,
                'price': price
            }
            return product_info
        return None

    # 9
    def get_title(self):
        try:
            return self.driver.find_element_by_id('productTitle').text
        except Exception as er:
            print(er)
            print(f"Can't get title of the product - {self.driver.current_url}")
            return None

    # 10
    def get_seller(self):
        try:
            return self.driver.find_element_by_id('bylineInfo').text
        except Exception as er:
            print(er)
            print(f"Can't get seller of the product - {self.driver.current_url}")
            return None

    # 11
    def get_price(self):
        price = None
        try:
            # usually the product price is on top centre right of webpage
            price = self.driver.find_element_by_id('priceblock_ourprice').text
            price = self.convert_price(price)
        except NoSuchElementException:
            try:
                # for some product the prices are in the bottom of product description 
                availability = self.driver.find_element_by_id('availability').text
                if 'Availability' in availability:
                    price = self.driver.find_element_by_class_name('old-padding-right').text
                    price = price[price.find(self.currency):]
                    price = self.convert_price(price)
        # for some product there is no price
            except Exception as er:
                print(er)
                print(f"Can't get price of the product - {self.driver.current_url}")
                return None
        except Exception as er:
            print(er)
            print(f"Can't get price of the product - {self.driver.current_url}")
            return None
        return price

    #12
    # converting price from string to float
    def convert_price(self, price):
        price = price.split(self.currency)[1]
        try:
            price = price.split("\n")[0] + "." + price.split("\n")[1]
        except:
            Exception()
        try:
            price = price.split(",")[0] + price.split(",")[1]
        except:
            Exception()
        return float(price)

    # 8
    # shortening the URL till the asin(product ID)
    def shorten_url(self, asin):
        return self.base_url + 'dp/' + asin

    # 5
    # this function shorten URL so we don't get tracked by amazon
    def get_asins(self, links):
        # slice links for specific number of product
        return [self.get_asin(link) for link in links[:4]]

    # 6
    # slicing the URL(for search product) and taking only upto /ref(after ref amazon will track us)
    # asin is the unique ID of the product
    def get_asin(self, product_link):
        # 4 is index of the string element after /dp/[/(/ index is 0)d(1)p(2)/(3)]
        return product_link[product_link.find('/dp/') + 4:product_link.find('/ref')]

    # 3
    def get_product_links(self):
        self.driver.get(self.base_url)
        # finding the div tag(inspect F12) of search bar(element)
        element = self.driver.find_element_by_id("twotabsearchtextbox")
        # typing the search term in search bar and pressing enter
        element.send_keys(self.search_term)
        element.send_keys(Keys.ENTER)
        time.sleep(2) # wait to load page
        self.driver.get(f'{self.driver.current_url}{self.price_filter}')
        time.sleep(2) # wait to load page
        result_list = self.driver.find_elements_by_class_name('s-result-list')

        links = []
        try:
            results = result_list[0].find_elements_by_xpath(
                "//div/span/div/div/div[2]/div[2]/div/div[1]/div/div/div[1]/h2/a")

            links = [link.get_attribute('href') for link in results]
            return links

        except Exception as er:
            print("Didn't get any products... :(")
            print(er)
            return links


if __name__ == "__main__":
    print('Heyyyyyy')
    amazon = AmazonAPI(NAME, FILTERS, BASE_URL, CURRENCY)
    data = amazon.run()
    GenerateReport(NAME, FILTERS, BASE_URL, CURRENCY, data)
    