import os
import platform
try:
    from urllib.request import urlopen
except ImportError: # python 2
    from urllib2 import urlopen
import ssl
import zipfile
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
import base64
import time
import sys
import re
import random



class Driver:
    WEB_DEVICE                  = 0
    MOBILE_DEVICE               = 1

    # Microsoft Edge user agents for additional points
    __WEB_USER_AGENT            = "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.10240"
    __MOBILE_USER_AGENT         = "Mozilla/5.0 (Linux; Android 8.0; Pixel XL Build/OPP3.170518.006) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.0 Mobile Safari/537.36 EdgA/41.1.35.1"


    def __init__(self, path, device, headless):
        self.driver = self.__get_driver(path, device, headless)

    def __download_driver(self, driver_path, system):
        # determine latest chromedriver version
        response = urlopen("https://sites.google.com/a/chromium.org/chromedriver/downloads").read()
        latest_version = max([float("{}.{}".format(version[0].decode(), version[1].decode())) 
                              for version in re.findall(b"ChromeDriver (\d+).(\d+)", response)])

        if system == "Windows":
            url = "https://chromedriver.storage.googleapis.com/{}/chromedriver_win32.zip".format(latest_version)
        elif system == "Darwin":
            url = "https://chromedriver.storage.googleapis.com/{}/chromedriver_mac64.zip".format(latest_version)

        response = urlopen(url, context=ssl.SSLContext(ssl.PROTOCOL_TLSv1)) # context args for mac
        zip_file_path = os.path.join(os.path.dirname(driver_path), os.path.basename(url))
        with open(zip_file_path, 'wb') as zip_file:
            while True:
                chunk = response.read(1024)
                if not chunk:
                    break
                zip_file.write(chunk)

        extracted_dir = os.path.splitext(zip_file_path)[0]
        with zipfile.ZipFile(zip_file_path, "r") as zip_file:
            zip_file.extractall(extracted_dir)
        os.remove(zip_file_path)

        driver = os.listdir(extracted_dir)[0]
        os.rename(os.path.join(extracted_dir, driver), driver_path)
        os.rmdir(extracted_dir)

        os.chmod(driver_path, 0o755)
    def __get_driver(self, path, device, headless):
        system = platform.system()
        if system == "Windows":
            if not path.endswith(".exe"):
                path += ".exe"
        if not os.path.exists(path):
            self.__download_driver(path, system)

        options = webdriver.ChromeOptions()
        options.add_argument("--disable-extensions")
        options.add_argument("--window-size=1280,1024")
        options.add_argument("--log-level=3")
        if headless:
            options.add_argument("--headless")
        
        if device == self.WEB_DEVICE:
            options.add_argument("user-agent=" + self.__WEB_USER_AGENT)
        else:
            options.add_argument("user-agent=" + self.__MOBILE_USER_AGENT)
        
        driver = webdriver.Chrome(path, chrome_options=options)
        #if not headless:
        #    driver.set_window_position(-2000, 0)
        return driver

    def close(self):
        # close open tabs
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            self.driver.close()

class Completion:
    def __init__(self):
        self.web_search         = False
        self.mobile_search      = False
        self.offers             = False

    def is_web_search_completed(self):
        return self.web_search
    def is_mobile_search_completed(self):
        return self.mobile_search
    def is_both_searches_completed(self):
        return self.web_search and self.mobile_search
    def is_any_searches_completed(self):
        return self.web_search or self.mobile_search
    def is_offers_completed(self):
        return self.offers
    def is_all_completed(self):
        return self.web_search and self.mobile_search and self.offers
    def is_any_completed(self):
        return self.web_search or self.mobile_search or self.offers

    def update(self, completion):
        self.web_search = max(self.web_search, completion.web_search)
        self.mobile_search = max(self.mobile_search, completion.mobile_search)
        self.offers = max(self.offers, completion.offers)

class Rewards:
    __LOGIN_URL                 = "https://login.live.com"
    __BING_URL                  = "https://bing.com"
    __DASHBOARD_URL             = "https://account.microsoft.com/rewards/dashboard"
    __POINTS_URL                = "https://account.microsoft.com/rewards/pointsbreakdown"

    __WEB_DRIVER_WAIT_LONG      = 15
    __WEB_DRIVER_WAIT_SHORT     = 5

    __SYS_OUT_TAB_LEN           = 8
    __SYS_OUT_PROGRESS_BAR_LEN  = 30


    def __init__(self, path, email, password, debug=True, headless=True):
        self.path               = path
        self.email              = email
        self.password           = password
        self.debug              = debug
        self.headless           = headless
        self.__completion       = Completion()


    def __get_sys_out_prefix(self, lvl, end):
        prefix = " "*(self.__SYS_OUT_TAB_LEN*(lvl-1)-(lvl-1))
        if not end:
            return prefix + ">"*lvl + " "
        else:
            return prefix + " "*int(self.__SYS_OUT_TAB_LEN/2) + "<"*lvl + " "
    def __sys_out(self, msg, lvl, end=False, flush=False):
        if self.debug:
            if flush: # because of progress bar
                print("")
            print("{0}{1}{2}".format(self.__get_sys_out_prefix(lvl, end), msg, "\n" if lvl==1 and end else ""))
    def __sys_out_progress(self, current_progress, complete_progress, lvl):
        if self.debug:
            ratio = float(current_progress)/complete_progress
            current_bars = int(ratio*self.__SYS_OUT_PROGRESS_BAR_LEN)
            needed_bars = self.__SYS_OUT_PROGRESS_BAR_LEN-current_bars
            sys.stdout.write("\r{0}Progress: [{1}] {2}/{3} ({4}%)".format(self.__get_sys_out_prefix(lvl, False), "#"*current_bars + " "*needed_bars, 
                                                                          current_progress, complete_progress, int(ratio*100)))
            sys.stdout.flush()
    
    def __login(self, driver):
        self.__sys_out("Logging in", 2)
    
        driver.get(self.__LOGIN_URL)
        ActionChains(driver).send_keys(base64.b64decode(self.email).decode(), Keys.RETURN).perform()
        WebDriverWait(driver, self.__WEB_DRIVER_WAIT_LONG).until(EC.visibility_of_element_located((By.ID, "i0118"))).send_keys(base64.b64decode(self.password).decode(), Keys.RETURN)

        self.__sys_out("Successfully logged in", 2, True)

    def __get_search_progress(self, driver, device):
        if len(driver.window_handles) == 1: # open new tab
            driver.execute_script('''window.open("{0}");'''.format(self.__POINTS_URL))
        driver.switch_to.window(driver.window_handles[-1])
        
        driver.refresh()
        progress_elements = WebDriverWait(driver, self.__WEB_DRIVER_WAIT_LONG).until(EC.visibility_of_all_elements_located((By.XPATH, '//*[@id="userPointsBreakdown"]/div/div[*]')))[1:]

        if device == Driver.WEB_DEVICE:
            web_progress_elements = [None, None]
            for element in progress_elements:
                progress_name = element.find_element_by_xpath('./div/div[2]/mee-rewards-user-points-details/div/div/div/div/p[1]').text.lower()
                if "pc" in progress_name or ("daily" in progress_name and "activities" not in progress_name):
                    web_progress_elements[0] = element.find_element_by_xpath('./div/div[2]/mee-rewards-user-points-details/div/div/div/div/p[2]')
                elif "bonus" in progress_name:
                    web_progress_elements[1] = element.find_element_by_xpath('./div/div[2]/mee-rewards-user-points-details/div/div/div/div/p[2]')

            if web_progress_elements[0]:
                current_progress, complete_progress = [int(i) for i in re.findall(r'(\d+)', web_progress_elements[0].text)]

                # get bonus points 
                if web_progress_elements[1]:
                    bonus_progress = [int(i) for i in re.findall(r'(\d+)', web_progress_elements[1].text)]
                    current_progress += bonus_progress[0]
                    complete_progress += bonus_progress[1]

            else:
                current_progress, complete_progress = 0, -1

        else:
            mobile_progress_element = None
            for element in progress_elements:
                progress_name = element.find_element_by_xpath('./div/div[2]/mee-rewards-user-points-details/div/div/div/div/p[1]').text.lower()
                if "mobile" in progress_name or ("daily" in progress_name and "activities" not in progress_name):
                    mobile_progress_element = element.find_element_by_xpath('./div/div[2]/mee-rewards-user-points-details/div/div/div/div/p[2]')

            if mobile_progress_element:
                current_progress, complete_progress = [int(i) for i in re.findall(r'(\d+)', mobile_progress_element.text)]

            else:
                current_progress, complete_progress = 0, -1

        driver.switch_to.window(driver.window_handles[0])
        #driver.get(self.__BING_URL)
        return current_progress, complete_progress
    def __search(self, driver, device):
        self.__sys_out("Starting search", 2)
        driver.get(self.__BING_URL)    

        prev_progress = -1
        try_count = 0
        while True:
            current_progress, complete_progress = self.__get_search_progress(driver, device)
            if complete_progress > 0:
                self.__sys_out_progress(current_progress, complete_progress, 3)
            if current_progress == complete_progress:
                break
            elif current_progress == prev_progress:
                try_count += 1
                if try_count == 4:
                    self.__sys_out("Failed to complete search", 2, True, True)
                    return False
            else:
                prev_progress = current_progress
                try_count = 0
        
            search_box = driver.find_element_by_id("sb_form_q")
            search_box.clear()
            search_box.send_keys(str(time.time()*10000000), Keys.RETURN) # unique search term
            #time.sleep(random.uniform(0, 5)) # avoid getting flagged as a bot

        self.__sys_out("Completed searching", 2, True, True)
        return True

    def __get_quiz_progress(self, driver, try_count=0):
        try:
            questions = driver.find_elements_by_xpath('//*[@id="rqHeaderCredits"]/div[2]/*')
            current_progress, complete_progress = 0, len(questions)
            for question in questions:
                if question.get_attribute("class") == "filledCircle":
                    current_progress += 1
                else:
                    break
            return current_progress-1, complete_progress
        except:
            if try_count < 4:
                return self.__get_quiz_progress(driver, try_count+1)
            else:
                return 0, -1
    def __quiz(self, driver):
        self.__sys_out("Starting quiz", 3)


        ## start quiz
        try_count = 0
        while True:
            try:
                driver.find_element_by_id("btOverlay")
                break
            except:
                try_count += 1
                if try_count == 4:
                    break
                time.sleep(1)

        if driver.find_element_by_id("rqStartQuiz").is_displayed():
            try_count = 0
            while True:
                start_quiz = driver.find_element_by_id("rqStartQuiz")
                if start_quiz.is_displayed():
                    try:
                        start_quiz.click()
                    except:
                        driver.refresh()
                else:
                    try:
                        if driver.find_element_by_id("quizWelcomeContainer").get_attribute("style") == "display: none;":
                            break
                    except: 
                        driver.refresh()
                try_count += 1
                if try_count == 4:
                    break
        else:
            self.__sys_out("Already started quiz", 4)

        quiz_options_len = 4



        is_drag_and_drop = False
        try:
            WebDriverWait(driver, self.__WEB_DRIVER_WAIT_SHORT).until(EC.visibility_of_element_located((By.ID, 'rqAnswerOptionNum0')))
            is_drag_and_drop = True
            self.__sys_out("Drag and drop", 4)
        except:
            self.__sys_out("Multiple choice", 4)


        ## drag and drop
        if is_drag_and_drop:
            time.sleep(5) # let demo complete

            # get all possible combinations
            to_from_combos = []
            for from_index in range(quiz_options_len):
                for to_index in range(quiz_options_len):
                    if from_index != to_index:
                        to_from_combos.append((from_index, to_index))
        
            prev_progress = -1
            incorrect_options = []
            from_option_index, to_option_index = -1, -1
            while True:
                current_progress, complete_progress = self.__get_quiz_progress(driver)
                if complete_progress > 0:
                    self.__sys_out_progress(current_progress, complete_progress, 4)

                # get all correct combinations so to not use them again
                correct_options = []
                option_index = 0
                while option_index < quiz_options_len:
                    option = WebDriverWait(driver, self.__WEB_DRIVER_WAIT_LONG).until(EC.visibility_of_element_located((By.ID, "rqAnswerOption{0}".format(option_index))))
                    if option.get_attribute("class") == "rqOption rqDragOption correctDragAnswer":
                        correct_options.append(option_index)
                    option_index += 1

                if current_progress != prev_progress: # new question
                    incorrect_options = []
                    prev_progress =  current_progress
                else:
                    # update incorrect options
                    incorrect_options.append((from_option_index, to_option_index))
                    incorrect_options.append((to_option_index, from_option_index))
            

                exit_code = -1 # no choices were swapped
                for combo in to_from_combos:
                    from_option_index, to_option_index = combo[0], combo[1]
                    # check if combination has already been tried
                    if combo not in incorrect_options and from_option_index not in correct_options and to_option_index not in correct_options:
                        # drag from option to to option
                        from_option = WebDriverWait(driver, self.__WEB_DRIVER_WAIT_LONG).until(EC.visibility_of_element_located((By.ID, "rqAnswerOption{0}".format(from_option_index))))
                        to_option = WebDriverWait(driver, self.__WEB_DRIVER_WAIT_LONG).until(EC.visibility_of_element_located((By.ID, "rqAnswerOption{0}".format(to_option_index))))
                        ActionChains(driver).drag_and_drop(from_option, to_option).perform()
                        time.sleep(self.__WEB_DRIVER_WAIT_SHORT)
                        self.__handle_alerts(driver)

                        if current_progress == complete_progress-1: # last question
                            try:
                                header = WebDriverWait(driver, self.__WEB_DRIVER_WAIT_SHORT).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="quizCompleteContainer"]/span/div[1]')))
                                if header.text == "Way to go!":
                                    self.__sys_out_progress(complete_progress, complete_progress, 4)
                                    exit_code = 0 # successfully completed
                                    break
                            except:
                                pass
                        exit_code = 1 # successfully swapped 2 choices (can still be wrong)
                        break
                
                if exit_code == -1: 
                    self.__sys_out("Failed to complete quiz", 3, True, True)
                    return False
                elif exit_code == 0:
                    break



        ## multiple choice
        else:
            option_index = 0
            try_count = 0
            prev_progress = -1
            while True:
                current_progress, complete_progress = self.__get_quiz_progress(driver)
                if complete_progress > 0:
                    self.__sys_out_progress(current_progress, complete_progress, 4)
                    if current_progress != prev_progress:
                        prev_progress = current_progress

                try:
                    WebDriverWait(driver, self.__WEB_DRIVER_WAIT_SHORT).until(EC.element_to_be_clickable((By.ID, "rqAnswerOption{0}".format(option_index)))).click()
                    time.sleep(self.__WEB_DRIVER_WAIT_SHORT)
                    self.__handle_alerts(driver)

                    if current_progress == complete_progress-1: # last question
                        try:
                            header = WebDriverWait(driver, self.__WEB_DRIVER_WAIT_SHORT).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="quizCompleteContainer"]/span/div[1]')))
                            if header.text == "Way to go!":
                                self.__sys_out_progress(complete_progress, complete_progress, 4)
                                break
                        except:
                            pass
                    option_index = 0

                except: # option was not clickable = already clicked
                    option_index += 1
                    if option_index == quiz_options_len:
                        self.__sys_out("Failed to complete quiz", 3, True, True)
                        return False


        self.__sys_out("Successfully completed quiz", 3, True, True)
        return True

    def __handle_alerts(self, driver):
        try:
            driver.switch_to.alert.dismiss()
        except:
            pass
    def __click_offer(self, driver, offer, title_xpath, checked_xpath, checked_class):
        title = offer.find_element_by_xpath(title_xpath).text
        self.__sys_out("Trying {0}".format(title), 2)

        # check whether it was already completed
        checked = False
        try:
            icon = offer.find_element_by_xpath(checked_xpath)
            if icon.get_attribute('class') == checked_class:
                checked = True
                self.__sys_out("Already checked", 2, True)
        except:
            pass

        completed = True
        if not checked:
            offer.click()
            #driver.execute_script('''window.open("{0}","_blank");'''.format(offer.get_attribute("href")))
            driver.switch_to.window(driver.window_handles[-1])
        
            self.__handle_alerts(driver)

            if "quiz" in title.lower():
                completed = self.__quiz(driver)
            else:
                time.sleep(self.__WEB_DRIVER_WAIT_SHORT)
            if completed:
                self.__sys_out("Successfully completed {0}".format(title), 2, True)
            else:
                self.__sys_out("Failed to complete {0}".format(title), 2, True)

            driver.switch_to.window(driver.window_handles[0])
            driver.get(self.__DASHBOARD_URL) # for stale element exception
        
        return completed
    def __offers(self, driver):
        ## showcase offer
        driver.get(self.__DASHBOARD_URL)
        
        completed = []
        ## daily set
        for i in range(3):
            offer = driver.find_element_by_xpath('//*[@id="daily-sets"]/mee-rewards-card-placement[1]/div/div/div[{}]/{}/mee-rewards-daily-sets-item/mee-rewards-card/div/div'.format(1 if i == 0 else 2, 'item{}'.format(i) if i == 0 else 'div[{0}]/item{0}'.format(i)))
            c = self.__click_offer(driver, offer, './section/div/div[2]/h3', './section/div/div[2]/mee-rewards-points/div/div/span[1]', "mee-icon mee-icon-SkypeCircleCheck ng-scope")
            completed.append(c)
        ## more activities
        item_num = 0
        i = 0
        while i < 8:
            # if offer takes up 2 spaces length wise
            try:
                offer = driver.find_element_by_xpath('//*[@id="more-activities"]/div/div/div[{}]/item{}/mee-rewards-more-activities-item/mee-mosaic-item/div/section/div'.format(int(i/2)+1, item_num))
                c = self.__click_offer(driver, offer, './div[2]/h3', './mee-rewards-points/div/div/span[1]', "mee-icon mee-icon-SkypeCircleCheck ng-scope")
                completed.append(c)
                i += 1
                item_num += 1
            except:
                # if offer takes up 1 space
                try:
                    offer = driver.find_element_by_xpath('//*[@id="more-activities"]/div/div/div[{}]/div[{}]/item{}/mee-rewards-more-activities-item/mee-mosaic-item/div/section/div'.format(int(i/2)+1, (i%2)+1, item_num))
                    c = self.__click_offer(driver, offer, './div[2]/h3', './mee-rewards-points/div/div/span[1]', "mee-icon mee-icon-SkypeCircleCheck ng-scope")
                    completed.append(c)
                    item_num += 1
                # if offer takes up 4 spaces (length 2, width 2)
                except:
                    pass
            #offer = driver.find_element_by_xpath('//*[@id="more-activities"]/div/div/div[{}]/div[{}]/item{}/mee-rewards-more-activities-item/mee-mosaic-item/div/section/div'.format(int(i/2)+1, (i%2)+1, i))
            #c = self.__click_offer(driver, offer, './div[2]/h3', './mee-rewards-points/div/div/span[1]', "mee-icon mee-icon-SkypeCircleCheck ng-scope")
            #completed.append(c)
            i += 1

        return min(completed)

    def __complete_web_search(self, close=True):
        self.__sys_out("Starting web search", 1)

        try:
            web_driver = Driver(self.path, Driver.WEB_DEVICE, self.headless)
            self.__login(web_driver.driver)
        
            self.__completion.web_search = self.__search(web_driver.driver, Driver.WEB_DEVICE)
            if self.__completion.web_search:
                self.__sys_out("Successfully completed web search", 1, True)
            else:
                self.__sys_out("Failed to complete web search", 1, True)
        except:
            try:
                web_driver.close()
            except: # not yet initialized
                pass
            raise

        if close:
            web_driver.close()
        else:
            return web_driver
    def __complete_mobile_search(self, close=True): 
        self.__sys_out("Starting mobile search", 1)

        try:
            mobile_driver = Driver(self.path, Driver.MOBILE_DEVICE, self.headless)
            self.__login(mobile_driver.driver)
    
            self.__completion.mobile_search = self.__search(mobile_driver.driver, Driver.MOBILE_DEVICE)
            if self.__completion.mobile_search:
                self.__sys_out("Successfully completed mobile search", 1, True)
            else:
                self.__sys_out("Failed to complete mobile search", 1, True)
        except:
            try:
                mobile_driver.close()
            except: # not yet initialized
                pass
            raise

        if close:
            mobile_driver.close()
        else:
            return mobile_driver
    def __complete_offers(self, driver=None):
        self.__sys_out("Starting offers", 1)

        try:
            if not driver:
                driver = Driver(self.path, Driver.MOBILE_DEVICE, self.headless)
                self.__login(driver.driver)
        
            self.__completion.offers = self.__offers(driver.driver)
            if self.__completion.offers:
                self.__sys_out("Successfully completed offers", 1, True)
            else:
                self.__sys_out("Failed to complete offers", 1, True)

            driver.close()
        except:
            try:
                driver.close()
            except:
                pass
            raise

    def complete_mobile_search(self): 
        self.__complete_mobile_search()
        return self.__completion
    def complete_web_search(self):
        self.__complete_web_search()
        return self.__completion
    def complete_both_searches(self):
        self.__complete_web_search()
        self.__complete_mobile_search()
        return self.__completion
    def complete_offers(self):
        self.__complete_offers()
        return self.__completion
    def complete_all(self):
        self.__complete_web_search()
        mobile_driver = self.__complete_mobile_search(close=False)
        self.__complete_offers(mobile_driver)
        return self.__completion


