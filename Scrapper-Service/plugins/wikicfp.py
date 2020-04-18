import requests
import logging
from bs4 import BeautifulSoup
from commons import Scrapper,PageParsingError
from datamodels import Conference , Metadata
import datetime


class WikiCfpScrapper(Scrapper):
    def __init__(self , **kwargs):
        super().__init__( context_name = __name__ , **kwargs)
        self.base_address = "http://www.wikicfp.com"
        self.site_name = "wikicfp"
        self.logger.info("{} initialized !!!".format(__name__))

    def __del__(self):
        self.logger.info("{} done scrapping !!!".format(__name__))

    def extract_and_put(self ,linkSet:set , category:str , link:str):
        base_address= self.base_address
        for name , clink in self.iterate_links(category , link):
                if clink in linkSet:
                    continue
                try:
                    qlink = base_address + clink
                    req = self.get_page(qlink , "Page extracted for conference : {} , category : {} ,  link: {}  extracted".format(name ,category, clink))
                    try:
                        conference_data = self.parse_conference_page_info(req.content , qlink )
                        ## Error from DB insertion should not be handled
                        ## Since this means there is fault in data or connection
                        ## Process must be restarted
                        self.push_todb(conference_data)
                        linkSet.add(clink)
                        totalLink = len(linkSet)
                        self.logger.debug("Total unique conference links till now :{}".format(totalLink))
                        if totalLink % 500 == 0:
                            self.logger.info("Total unique conference links till now :{}".format(totalLink))
                            
                    except Exception as e:
                        self.logger.error("Error when parsing link: {} exception: {}".format(clink, e))
                except requests.HTTPError as e:
                    self.logger.error("Error when requesting html failed :{}".format(e))
                except requests.Timeout as e:
                    self.logger.error("Timeout when requesting html : {}".format(e))
                except Exception as e:
                    self.logger.error("Error occured where requesting html :{}".format(e))
                    
    

    def parse_action(self):
        linkSet = set()
        try:
            c_list = self.category_list()
            for category ,link in c_list:
                self.extract_and_put(linkSet , category , link)
        except Exception as e:
            self.logger.error("Failed at extracting category page of {} error: {}".format(self.base_address , e))


    def category_list(self ):
        base_address = self.base_address
        site_name = self.site_name 
        req = self.get_page("{}/cfp/allcat?sortby=1".format(base_address), "{} category page extracted".format(site_name)) # getting page listed in specific order

        page_dom = BeautifulSoup(req.content , 'html.parser')
        table_container = page_dom.find(attrs={"class":"contsec"}) ## table in the page
        if table_container is None:
            self.logger.error("{} no element contsec at category page".format(site_name))
            raise self.PageParsingError("{} no element contsec at category page".format(site_name))
        
        anchors = table_container.select("tr td a")
        if len(anchors) == 0:
            self.logger.error("{} no anchor found".format(site_name))
            raise self.PageParsingError("{} no anchor found".format(site_name))
        
        anchors = anchors[1:]    
        links = map(lambda anchor: (anchor.text, anchor["href"])  , anchors)
        links = sorted(links , key = lambda link: link[0])
        return links

    def next_anchor(self , base_address:str , category:str ,  link:str):
        """ Gives the next anchor from a particular page to the next page
            Also parses the page for relevant information and gives the table container

        Arguments:
            base_address {str} -- the anchor link to visit
            category {str} -- the category we are working with . used for logging
            link {str} -- the link used for extraction
        
        Raises:
            self.PageParsingError: When is fails to parse
        
        Returns:
            [(BeautifulSoup, str)]
        """
        
        req = self.get_page(base_address+link , "{} : {} page extracted".format(category , link))
        page_dom = BeautifulSoup(req.content , 'html.parser')
        page_dom = page_dom.find(attrs={"class":"contsec"})
        page_dom = page_dom.find(name = "center")
        
        table_container = page_dom.find(name = "form" , attrs={"name":"myform"} , recursive= False)
        table_container = table_container.find(name = "table" , recursive = False)
        if table_container is None:
            self.logger.error("{} no element form ".format(category))
            raise self.PageParsingError("{} no element form ".format(category))
        trs = table_container.find_all("tr" , recursive = False)
        content = trs[-2]
        tr = trs[-1]
        anchors = tr.find_all("a")
        anchor = list(filter(lambda x: x.text == "next"  ,anchors))[0]
        return (content,anchor)
        

    def iterate_pages(self, base_address:str , category:str , link:str):
        count = 0
        try:
            curr_table_container , next_a = self.next_anchor(base_address , category , link)
            count = count + 1
            self.logger.debug("{} category link \" {} \" extracted ".format(category , link))
        except Exception as e:
            self.logger.warn("No. of link extracted: {} , Could not extract anchor information for category {} page {} error:{}"
                            .format(count,category , link , e))
            return
        yield curr_table_container
        prev_link = link
        link = next_a["href"]

        while True:
            try:
                curr_table_container , next_a= self.next_anchor(base_address , category , link) 
                count = count + 1
                self.logger.debug("{} category link \" {} \" extracted ".format(category , link))
            except Exception as e:
                self.logger.warn("No. of link extracted: {} , Could not extract anchor information for category {} page {} error:{}"
                                .format(count,category , link , e))
                break
            yield curr_table_container
            link = next_a["href"]
            if prev_link == link and prev_link is not None:
                break
            prev_link = link

    def iterate_categories(self ,category:str , link:str ,  base_address:str):
        try: 
            self.logger.info("starting with {} category ".format(category))
            yield from self.iterate_pages(base_address , category , link)
            self.logger.info("done with {} category ".format(category))
        except Exception as e:
            self.logger.warn("Failed to extract complete data from {} starting at {} exception:{} "
                            .format(category , link , e))

    def iterate_links(self ,category:str , link:str):
        base_address = self.base_address
        for parsed_pages in self.iterate_categories(category , link , base_address):
            links = parsed_pages.select("a")
            links = map(lambda x: (x.text , x["href"]) , links)
            for link in links:
                yield link

    

    def extract_info(self , page_dom):
        info_table = page_dom.select("table.gglu")
        list_info_title = map(lambda x: x.text.strip() ,  info_table[0].select("th"))
        list_info_content = map(lambda x:x.text.strip() , info_table[0].select("td"))
        info = {"dateRange":"" , "location":"" , "deadline":"" , "notificationDue":"" , "finalDue":""}
        for title , content in zip(list_info_title , list_info_content):
            if title == "When":
                dates = list(map( lambda x: self.get_date(x) , content.split("-")))
                info["dateRange"] = dates
            elif title == "Where":
                info["location"] = content
            elif title == "Submission Deadline":
                info["deadline"] = self.get_date(content)
            elif title == "Notification Due":
                info["notificationDue"] =  self.get_date(content)
            elif title == "Final Version Due":
                info["finalDue"] = self.get_date(content)
        return info

    def extract_categories(self , page_dom:BeautifulSoup):
        anchor_list = page_dom.select("table.gglu tr td a")
        anchor_list = map(lambda x: x.text , anchor_list[1:])
        return list(anchor_list)

    def create_metadata(self, website_url , domain_url , domain_name , **kwargs):
        return Metadata(__name__ , datetime.datetime.now() , website_url , domain_url , domain_name , **kwargs)

    def parse_conference_page_info(self , page:str , qlink):
        page_dom = BeautifulSoup(page , 'html.parser')
        title = page_dom.find(name = "span" , attrs={"property":"v:description"}).text
        url = page_dom.find(name = "a" , attrs={"target":"_newtab"})["href"]
        info = self.extract_info(page_dom)
        if "deadline" not in info:
            raise ValueError("Deadline is a mandatory field, could not parse the page")
        categories = self.extract_categories(page_dom)
        bulk_text = ""
        try:
            qresult = page_dom.select("div.cfp")
            bulk_text = qresult[0].text
        except Exception as e:
            self.logger.warn("Failed to parse bulk text information css query result: {} error : {} ".format(qresult, e))
        
        metadata = self.create_metadata(qlink , self.base_address , self.site_name )

        return Conference( **{  "title":title , "url":url , 
                                        "categories":categories , "bulkText":bulk_text  , "metadata":metadata} , **info )

    


