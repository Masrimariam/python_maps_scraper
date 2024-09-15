from playwright.sync_api import  sync_playwright
from playwright.sync_api import Page
from dataclasses import  dataclass,asdict ,field
import pandas as pd
import argparse 


 

@dataclass
class Business:
   name: str=None
   address: str=None 
   website: str=None
   phone_nb: str=None
   links: list[str]=field(default_factory=list)


@dataclass
class BusinessList:
   business_list: list[Business]=field(default_factory=list) 


   def dataframe(self):
      return pd.json_normalize((asdict(business) for business in self.business_list),sep='_')
   
   def save_to_excel(self):
    
       self.dataframe().to_excel("data.xlsx",index=False)
   
   def save_to_csv(self):
    
      self.dataframe().to_csv("data.csv",index=False)


def scrape_data(page):
    detailed_panel = page.locator('div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde').nth(2)
    scroll_pause_time = 2  # seconds

    previous_height = detailed_panel.evaluate("element => element.scrollHeight")

    while True:
        detailed_panel.evaluate("element => element.scrollTop = element.scrollHeight")
        page.wait_for_timeout(scroll_pause_time * 1000)

        new_height = detailed_panel.evaluate("element => element.scrollHeight")
        if new_height == previous_height:
            print("No new content loaded, stopping scrolling.")
            break
        previous_height = new_height

    # Wait for the iframe to load
    page.wait_for_timeout(5000)
    page_frame = page.frame_locator('iframe')

    # Wait for the web results to appear
    try:
        page_frame.locator('div.HTomEb.P0BCpd.GLttn.wFAQK').wait_for(timeout=30000)
    except Exception as e:
        print("Timed out waiting for the web results to load:", e)

    # Locate all web result divs
    web_results_divs = page_frame.locator('div.HTomEb.P0BCpd.GLttn.wFAQK')
    length = web_results_divs.count()
    print(f"Found {length} web results.")

    urls = []

    for index in range(length):
        try:
            div = web_results_divs.nth(index)
            div.scroll_into_view_if_needed()
            div.click()

            page.context.wait_for_event("page", timeout=15000)
            # to get the last new one opend
            new_page = page.context.pages[-1]
            new_url = new_page.url
            urls.append(new_url)
            new_page.close()

            page_frame = page.frame_locator('iframe')

        except Exception as e:
            print(f"An error occurred while processing result {index + 1}: {e}")

    return urls

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", type=str)
    parser.add_argument("-t", "--total", type=int)
    parser.add_argument("-r","--rating",type=str)
    args = parser.parse_args()
   
    if args.search :
        search_for = args.search
    else:
        search_for = "hotel lebanon"

    if args.total:
        total=args.total
    else :
        total=10  
    if args.rating:
        desired_rating=args.rating
    else :
        desired_rating="4.0"              

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            page.goto("https://www.google.com/maps/?hl=en", timeout=60000)
            page.wait_for_timeout(5000)

            page.locator("//input[@id='searchboxinput']").fill(search_for)
            page.wait_for_timeout(1000)

            page.keyboard.press("Enter")
            page.wait_for_timeout(5000)
            # # # rating 
           
            page.wait_for_selector("button.e2moi", timeout=10000)
            page.evaluate("document.querySelectorAll('button.e2moi')[0].click()")

            page.wait_for_timeout(5000)


            page.wait_for_selector('//div[@role="menuitemradio"]')

            rating_options=page.locator('//div[@role="menuitemradio"]').all()
            if desired_rating:
                for option in rating_options:
                    option_text=option.text_content()
                    if option_text and desired_rating in option_text:
                        if option.is_visible():
                            option.click()
                            print("good")
                            
                            break
                        else:
                            print(f"option of rating {desired_rating} is not vivsible and cannot be clicked")
    
            listings =[]
            while len(listings) < total:

                page.mouse.wheel(0,10000)
                page.wait_for_timeout(3000)
                new_listings=page.locator('//div[contains(@class,"Nv2PK")]').all()
                
                listings=new_listings[:total]
                
                if len(listings) >= total:
                    break

            
            business_list = BusinessList()

            for listing in listings:
                
                try:
                    listing.click()
                    page.wait_for_timeout(10000)


                    name_css='h1.lfPIob'
                   
                    address_css='div.Io6YTe.fontBodyMedium.kR99db'
                   
                    website_css='a.CsEnBe'
                    
                    phonenb_css='div.Io6YTe'
                    


                    business = Business()
                    
                    name_locator= page.locator(name_css)
                    
                    if name_locator.count()>0:
                        business.name=name_locator.text_content()
                        
                    else:
                        business.name=""  
                    
                    address_locator=page.locator(address_css)
                   
                       

                    if address_locator.count() >0 :
                        
                      business.address=address_locator.nth(1).text_content()
                           
                       
                    else:
                        business.address=""  
                    try:  
                              
                  
                          
                         page.locator(website_css).wait_for(state='visible',timeout=5000)
                         
                         website_href = page.locator(website_css).get_attribute('href')

                           
                         if website_href:  
                                business.website = website_href 
                      
                         else :
                                business.website = ""
                    except Exception as e:
                              print(f"error {e}")
                   

                    
                       

                    

                    phone_locator = page.locator(phonenb_css)
                  
                    if phone_locator.count()>0:
                        business.phone_nb=page.locator(phonenb_css).nth(2).text_content()
                        
                        
                    else:
                        business.phone_nb=""  

                    business.links = scrape_data(page)
                      
                    business_list.business_list.append(business)

                except Exception as e:
                    print(f"Error processing listing: {e}")
            print(business_list)  

            # Save data and close browser 
           
            business_list.save_to_csv()
            business_list.save_to_excel()
            page.wait_for_timeout(5000)

            browser.close()

    except Exception as e:
        print(f"An error occurred in the main function: {e}")





if __name__ == "__main__":
   
    main()




