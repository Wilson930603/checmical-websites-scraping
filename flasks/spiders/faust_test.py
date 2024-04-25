from xml.dom.minidom import parseString
import scrapy
from bs4 import BeautifulSoup as BS
import json
from datetime import datetime
import math
import re
import sys
import html
from latest_user_agents import get_latest_user_agents,get_random_user_agent

class faustTestSpider(scrapy.Spider):
    regionConfig = 'ch' # please check https://www.faust.co.uk/gb/en/change-country.html for 'regionConfig' & langConfig
    langConfig = 'en'  # example : belgium -> faust.be/be/fr/home.html meaning regionConfig = be, langConfig = fr .
                       # example : United Kingdom -> faust.co.uk/gb/en meaning regionConfig = gb, langConfig = en . 
                       # for langConfig, please check the website for availabilities, sometimes it have fr,it,en in one region.
    #######################################################

    if(langConfig == 'en'):
        baseUrl = 'https://www.faust.ch/shop/tree_an_alpha_lang_uk.htm'
    else:
        baseUrl = 'https://www.faust.ch/shop/tree_an_alpha_lang_de.htm'
    name = 'faustTest'
    pages = []

    # allowed_domains = ['faust.com']
    start_urls = [baseUrl]
    history = []
    custom_settings={
        'USER_AGENT':''
    }
    headers_normal = {
        'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-encoding':'gzip, deflate, br',
        'Accept-language':'en-US,en;q=0.9',
        # 'cache-control':'max-age=0',
        # 'cookie':'locale='+lang+'_'+locale.upper()+';',
        # 'Host':'www.faust.ch',
        # 'sec-ch-ua':'"Chromium";v="97", "Opera GX";v="83", ";Not A Brand";v="99"',
        'sec-ch-ua-mobile':'?0',
        'sec-ch-ua-platform':'"Windows"',
        'Sec-Fetch-Dest':'document',
        'Sec-Fetch-Mode':'navigate',
        'Sec-Fetch-Site':'same-origin',
        'Sec-Fetch-User':'?1',
        'Upgrade-Insecure-Requests':'1',
        # 'User-Agent':'PostmanRuntime/7.29.0',
        'User-Agent':get_random_user_agent()
    }

    def parse(self, response):
        respUrl = response.url
        yield scrapy.Request(respUrl, callback = self.parseProducts, headers=self.headers_normal,dont_filter=True)
        

    def parseProducts(self, response):
        try:
            groupUrl = response.meta['group']
        except:
            groupUrl = ''
        products = response.xpath("//*[contains(@class,'DbD Col')]/*[@class='DbL']/@href").getall()
        if(len(products)>0):
            for product in products:
                if('/shop/' in product):
                    urlProduct = 'https://www.faust.ch'+product
                else:
                    urlProduct = 'https://www.faust.ch/shop/'+product
                try:
                    urlProduct = re.findall(r"([^>]*)\?UID",urlProduct)[0]
                    # print(urlProduct)
                    urlProduct = urlProduct.replace("?UID","")
                except Exception as e:pass
                yield scrapy.Request(urlProduct, callback = self.parseProducts, headers=self.headers_normal, meta={'group':response.url},dont_filter=True)
                # break
        else:
            #do normal parse
            print(re.findall(r"SetUserStatus(.*?);",response.text))
            respUrl = response.url
            images = []
            try:
                temp = response.xpath("//*[@id='ProdImageTag']/@src").getall()
                for te in temp:
                    images.append(te)
            except:pass
            
            data = {
                'URL':respUrl,
                'groupURL':groupUrl,
                'productName':response.xpath("//*[@class='SEGHEADTEXT']/*[@itemprop='name']/text()").get().strip(),
                'productDescription':response.xpath("//*[@itemprop='description']").getall(),#html
                'productCodes':'',
                'brand':'',#empty
                'breadcrumb':'>'.join(response.xpath("//*[@id='WR_BREADCRUMB']//*[@itemprop='name']/text()").getall()).strip(), 
                'price':'', #array of dict
                'stock':'',
                'imageURLs':images, 
                'documents':'',#empty
                'productAttributes':'',
            }
            # print(data)
            currency = ''
            unit = ''
            tableHeaders = response.xpath("//*[@class='DBTable SEGTABLE']//th")
            theHeaders = []
            headersClass = []
            for tableHeader in tableHeaders:
                tableClass = tableHeader.xpath("./@class").get()
                headersClass.append(tableClass)
                tableTexts = tableHeader.xpath(".//text()").getall()
                try:
                    if('ITEMPRICE' in tableClass):
                        currency = tableTexts[1].strip()
                    if('Unit' in tableClass):
                        unit = tableTexts[0].strip()
                except:pass
                theHeaders.append(' '.join(tableTexts).strip())
            # print(theHeaders)
            subProducts = response.xpath("//*[@class='DBTable SEGTABLE']//tr[contains(@class,'DataTableRow')]")
            
            for subProduct in subProducts:
                productCodes = []
                productAttributes = []
                price = []
                stock = '' #for p['stock']
                unitSize = ''
                bulkQty = ''
                p = data.copy()
                tds = subProduct.xpath("./td")
                count = 0
                for td in tds:
                    # tdClass = td.xpath("./@class").get()
                    # print(tdClass)
                    tdClass = headersClass[count]
                    # print(tdClass)
                    tdValue=''
                    try:
                        tdValue = td.xpath("./text()").get().strip()
                    except:pass
                    # print(tdValue)
                    if(tdValue!='' or tdValue is not None):
                        try:
                            if('Unit' in tdClass):
                                unitSize = tdValue
                            elif('Itemno' in tdClass):
                                productCodes.append({'codeType':theHeaders[count],'code':tdValue})
                            elif('StockCol' in tdClass):
                                stock = td.xpath("./@title").get()
                            elif('ITEMPRICE' in tdClass):
                                price.append({'quantity':1, 'price': tdValue, 'currency':currency,'unitSize':str(unitSize)+" "+unit})
                            elif('GRADQTY' in tdClass):
                                bulkQty = tdValue
                            elif('GRADPRICE' in tdClass):
                                if(bulkQty.strip()!=''):
                                    price.append({'quantity':str(bulkQty), 'price': tdValue, 'currency':currency,'unitSize':str(unitSize)+" "+unit})
                            else:
                                if(theHeaders[count]!=''):
                                    productAttributes.append({'name':theHeaders[count],'value':tdValue})
                        except Exception as e:print(e)
                    count+=1
                p['productAttributes']=productAttributes
                p['price'] = price
                p['stock'] = stock
                p['productCodes'] = productCodes
                yield({'price':p['price']})

            
        
