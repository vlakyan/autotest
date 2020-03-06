import logging
import time
from functools import wraps
from time import sleep

import pytest
from appium.webdriver.common.touch_action import TouchAction
from mapsmefr.pageobjects.base import BottomPanel
from mapsmefr.steps.locators import Locator, LocalizedButtons, BookingButtons
from mapsmefr.utils import expected_conditions as EC2
from mapsmefr.utils.driver import WebDriverManager
from mapsmefr.utils.tools import get_settings, is_element_scrolled
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

def check_not_crash(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if get_settings("System", "platform") == "Android":
            cur_focus = WebDriverManager.get_instance().driver.execute_script("mobile: shell", {
                'command': "dumpsys window windows | grep -E 'mObscuringWindow|mHoldScreenWindow|mCurrentFocus'"})
            if not get_settings("Android", "package") in cur_focus or "Application Error" in cur_focus:
                if "LauncherActivity" in cur_focus or "mCurrentFocus=null" in cur_focus or "lockito" in cur_focus:
                    pass
                else:
                    logging.info(cur_focus)
                    pytest.fail("Mapsme closed activity before step {}".format(func.__name__))
            result = func(*args, **kwargs)
            sleep(7)
            cur_focus = WebDriverManager.get_instance().driver.execute_script("mobile: shell", {
                'command': "dumpsys window windows | grep -E 'mObscuringWindow|mHoldScreenWindow|mCurrentFocus'"})
            if not get_settings("Android", "package") in cur_focus or "Application Error" in cur_focus:
                if "LauncherActivity" in cur_focus or "mCurrentFocus=null" in cur_focus or "lockito" in cur_focus:
                    pass
                else:
                    logging.info(cur_focus)
                    pytest.fail("Mapsme closed activity after step {}".format(func.__name__))
            return result
        else:
            driver = WebDriverManager.get_instance().driver
            if driver.context == "NATIVE_APP":
                alerts = driver.find_elements_by_xpath("//*[@type='XCUIElementTypeAlert']")
                if len(alerts) > 0:
                    driver.execute_script('mobile: alert', {'action': 'dismiss'})
                    sleep(3)
            # cur_app = driver.find_element_by_xpath(
            #    "//*[@type='XCUIElementTypeApplication']").text
            # if "maps.me" not in cur_app:
            #    pytest.fail("Mapsme closed activity before step {}".format(func.__name__))
            return func(*args, **kwargs)

    return wrapper


class CommonSteps(object):

    def __init__(self):
        self.driver = WebDriverManager.get_instance().driver

    # @check_not_crash
    def scroll_down(self, from_el=None, small=False):
        logging.info("Swipe up")
        actions = TouchAction(self.driver)
        x = self.driver.get_window_size()['width'] / 2
        y_top = self.driver.get_window_size()['height'] * 0.7
        y_bot = self.driver.get_window_size()['height'] * 0.2
        if small:
            y_top = self.driver.get_window_size()['height'] * 0.55
            y_bot = self.driver.get_window_size()['height'] * 0.4
        sleep(1)
        if from_el:
            actions.press(None, from_el.location["x"], from_el.location["y"]).wait(500).move_to(None, x,
                                                                                                y_bot).release().perform()
        else:
            actions.press(None, x, y_top).wait(500).move_to(None, x, y_bot).release().perform()

    @check_not_crash
    def scroll_up(self, from_el=None, small=False):
        logging.info("Swipe down")
        actions = TouchAction(self.driver)
        x = self.driver.get_window_size()['width'] / 2
        y_top = self.driver.get_window_size()['height'] * 0.2
        y_bot = self.driver.get_window_size()['height'] * 0.8
        if small:
            y_top = self.driver.get_window_size()['height'] * 0.3
            y_bot = self.driver.get_window_size()['height'] * 0.7
        if from_el:
            actions.press(from_el).wait(300).move_to(None, x,
                                                     self.driver.get_window_size()['height'] * 0.99).release().perform()
            sleep(3)
        else:
            actions.press(None, x, y_top).wait(300).move_to(None, x, y_bot).release().perform()

    def try_get_by_xpath(self, xpath):
        try:
            logging.info("Try find element by id: {}".format(xpath))
            return self.driver.find_element_by_xpath(xpath)
        except NoSuchElementException as nse:
            logging.info("Element not found")
            return None

    def try_get(self, locator):
        logging.info("Try find element by id: {}".format(locator))
        try:
            return self.driver.find_element_by_id(locator)
        except NoSuchElementException as nse:
            logging.info("Element not found")
            return None

    def try_get_by_text(self, text, locator=None, strict=True):
        # it was very stupid way to debug credentials from jenkins
        # with open("wtf.txt", "a") as ff:
        #     ff.write(text)
        logging.info("Try find element by text: {}".format(text))
        if not locator:
            try:
                if strict:
                    return self.driver.find_element_by_xpath(
                        "//*[@text='{0}' or @value='{0}' or @label='{0}' or @text='{1}' or @value='{1}' or @label='{1}' or @text='{2}' or @value='{2}' or @label='{2}']"
                            .format(text, text.upper(), text.lower()))
                else:
                    return self.driver.find_element_by_xpath(
                        "//*[contains(@text,'{0}') or contains(@value,'{0}') or contains(@label,'{0}') or contains(@text,'{1}') or contains(@value,'{1}') or contains(@label,'{1}') or contains(@text,'{2}') or contains(@value,'{2}') or contains(@label,'{2}')]"
                            .format(text, text.upper(), text.lower))
            except NoSuchElementException:
                logging.info("Element not found")
                return None
        sleep(2)  # for really slow phones heey hi kludges
        for i, el in enumerate(self.driver.find_elements_by_id(locator.get())):
            if text in el.text:
                return el, i
        else:
            return None, None


class BaseSteps(CommonSteps):

    def __init__(self):
        super().__init__()

    @staticmethod
    def get():
        if WebDriverManager.get_instance().device.platform == "Android":
            return AndroidSteps()
        else:
            return IosSteps()

    def choose_first_search_result(self, category=None):
        pass

    def scroll_down_to_element(self, xpath=None, locator=None, scroll_time=120):
        pass

    def assert_element_presence(self, locator):
        assert self.driver.find_element_by_id(locator.get())

    def accept_privacy_policy(self):
        pass

    def download_map(self, country_name, state_name, *loc_names):
        pass

    def search(self, loc, click_search_button=True):
        pass

    def click_search_button(self):
        button = self.try_get(Locator.SEARCH_BUTTON.get()) or self.try_get(Locator.SEARCH_BUTTON_ROUTING.get())
        button.click()

    def assert_pp(self, text):
        pass

    def assert_category_on_pp(self, text):
        pass

    def download_map_from_pp(self):
        pass

    def press_back_until_main_page(self):
        pass

    def delete_map(self, country_name, state_name, city_name):
        pass

    def try_find_map_with_scroll(self, name):
        pass

    def edit_level_field(self, new_value):
        pass

    def find_and_click_send(self):
        pass

    def show_place_on_map(self, country_name, state_name, city_name):
        pass

    def stop_routing(self):
        pass

    def off_wifi(self):
        pass

    def on_wifi(self):
        pass

    def switch_to_native(self):
        pass

    def enable_google_geolocation(self):
        pass

    def wait_map_download(self, map_name):
        pass

    def wait_map_auto_download(self, map_name):
        pass

    def assert_map_downloaded(self, country_name, state_name, city_name):
        pass

    def assert_map_deleted(self, country_name, state_name, city_name):
        pass

    def click_categories(self):
        categories = self.try_get_by_text(text=LocalizedButtons.SEARCH_CATEGORIES_TAB.get())
        if not categories:
            categories = self.try_get(LocalizedButtons.SEARCH_CATEGORIES_TAB.get())
        categories.click()

    def choose_category_in_list(self, category_name):
        pass

    def restart_app(self):
        pass

    def pp_get_title(self):
        pass


class AndroidSteps(BaseSteps):

    @check_not_crash
    def choose_first_search_result(self, category=None):
        if category:
            first_result = self.try_get_by_text(category)
            while not first_result and not is_element_scrolled(self.driver, first_result):
                self.scroll_down(small=True)
        else:
            first_result = WebDriverManager.get_instance().driver.find_element_by_id(Locator.TITLE.get())
        logging.info("Choose first search result: {}".format(first_result.text))
        first_result.click()

    @check_not_crash
    def close_first_time_frame(self):
        try:
            self.driver.find_element_by_id(Locator.FIRST_TIME_INFO_FRAME.get()).click()
        except NoSuchElementException as nse:
            pass

    def choose_category_in_list(self, category_name):
        cat = self.try_get_by_text(text=category_name)
        old_page_elements = [x.text for x in
                             self.driver.find_elements_by_xpath("//*[@class='android.widget.TextView']")]
        new_page_elements = []
        timeout = time.time() + 60
        while not cat and old_page_elements != new_page_elements:
            old_page_elements = new_page_elements
            self.scroll_down(small=True)
            cat = self.try_get_by_text(text=category_name)
            new_page_elements = [x.text for x in
                                 self.driver.find_elements_by_xpath("//*[@class='android.widget.TextView']")]
            if time.time() > timeout:
                break
        self.try_get_by_text(text=category_name).click()
        try:
            in_progress = self.driver.find_element_by_id(Locator.SEARCH_PROGRESS.get())
            WebDriverWait(self.driver, 120).until(EC.staleness_of(in_progress))
        except NoSuchElementException as nse:
            pass

    def accept_privacy_policy(self):
        try:
            self.driver.find_element_by_id(Locator.AGREE_PRIVACY.get()).click()
            self.driver.find_element_by_id(Locator.AGREE_TERMS.get()).click()
            logging.info("Clicked Accept policy button")
        except NoSuchElementException as nse:
            try:
                self.driver.find_element_by_id(Locator.ACCEPT_POLICY_BUTTON.get()).click()
                logging.info("Clicked Accept policy button")
            except:
                pass
        while self.try_get(Locator.ACCEPT_BUTTON.get()):
            self.try_get(Locator.ACCEPT_BUTTON.get()).click()

    def show_place_on_map(self, country_name, state_name, city_name):
        self._wait_in_progress()
        self.driver.find_element_by_id(Locator.MENU_BUTTON.get()).click()
        self.driver.find_element_by_id(Locator.DOWNLOAD_MAPS.get()).click()
        if country_name:
            country, _ = self.try_find_map_with_scroll(country_name.get())
            country.click()
            if state_name:
                state, _ = self.try_find_map_with_scroll(state_name.get())
                state.click()
        city, _ = self.try_find_map_with_scroll(city_name.get())
        city.click()
        self.try_get_by_text(text=LocalizedButtons.SHOW_ON_MAP.get()).click()

    @check_not_crash
    def download_map(self, country_name, state_name, *loc_names):
        self._wait_in_progress()
        self.driver.find_element_by_id(Locator.MENU_BUTTON.get()).click()
        self.driver.find_element_by_id(Locator.DOWNLOAD_MAPS.get()).click()
        country = None
        state = None
        for loc_name in loc_names:
            if country_name:
                logging.info("Trying to find {} folder".format(country_name.get()))
                country, _ = self.try_find_map_with_scroll(country_name.get())
                if country:
                    logging.info("Folder {} found.".format(country_name.get()))
                    country.click()
                    if state_name:
                        logging.info("Trying to find {} folder".format(state_name.get()))
                        state, _ = self.try_find_map_with_scroll(state_name.get())
                        if state:
                            logging.info("Folder {} found.".format(state_name.get()))
                            state.click()
            logging.info("Trying to find city {}".format(loc_name.get()))
            city, _ = self.try_find_map_with_scroll(loc_name.get())

            if not city:
                logging.info("City {} not found. Try find city in search.".format(loc_name.get()))
                if country_name and country:
                    self.driver.find_element_by_class_name("android.widget.ImageButton").click()
                if state_name and state:
                    self.driver.find_element_by_class_name("android.widget.ImageButton").click()
                search_field = self.try_get(Locator.SEARCH_FIELD.get())
                if not search_field:
                    self.driver.find_element_by_class_name("android.widget.ImageButton").click()
                    search_field = self.try_get(Locator.SEARCH_FIELD.get())
                search_field.send_keys(loc_name.get())
                try:
                    in_progress = self.driver.find_element_by_id(Locator.SEARCH_PROGRESS.get())
                    WebDriverWait(self.driver, 120).until(EC.staleness_of(in_progress))
                except NoSuchElementException as nse:
                    pass
                city, num = self.try_get_by_text(locator=Locator.NAME, text=loc_name.get())
                assert city, "Element not found!"
                self.driver.find_elements_by_id(Locator.DOWNLOAD_ICON.get())[num].click()
                logging.info("Wait {} map downloading".format(loc_name.get()))
                self._wait_in_progress()
                self.driver.back()
        self.press_back_until_main_page()

    # @check_not_crash
    def search(self, loc, click_search_button=True):
        logging.info("Searching location {}".format(loc))
        if click_search_button:
            self.click_search_button()
        self.driver.find_element_by_id(Locator.SEARCH_FIELD.get()).send_keys(loc)
        try:
            self.driver.hide_keyboard()
            in_progress = self.driver.find_element_by_id(Locator.SEARCH_PROGRESS.get())
            WebDriverWait(self.driver, 120).until(EC.staleness_of(in_progress))
        except NoSuchElementException as nse:
            pass

    @check_not_crash
    def assert_pp(self, text):
        assert self.driver.find_element_by_id(Locator.PP.get())
        assert text in self.driver.find_element_by_id(Locator.TV_TITLE.get()).text

    def assert_category_on_pp(self, text):
        pass

    @check_not_crash
    def press_back_until_main_page(self):
        logging.info("Go back to main page")
        self.driver.implicitly_wait(3)
        timeout = time.time() + 60  # 1 minute from now

        while self.try_get("clear"):
            self.try_get("clear").click()

        while not self.try_get(Locator.MENU_BUTTON.get()):
            self.driver.back()
            if time.time() > timeout:
                break

        while self.try_get(Locator.PP_BUTTONS.get()):
            self.driver.back()
            if time.time() > timeout:
                break
        self.driver.implicitly_wait(10)

    @check_not_crash
    def delete_map(self, country_name, state_name, city_name):
        self._wait_in_progress()
        self.press_back_until_main_page()
        self.driver.find_element_by_id(Locator.MENU_BUTTON.get()).click()
        self.driver.find_element_by_id(Locator.DOWNLOAD_MAPS.get()).click()
        if country_name:
            country, _ = self.try_find_map_with_scroll(country_name.get())
            if country:
                country.click()
                if state_name:
                    state, _ = self.try_find_map_with_scroll(state_name.get())
                    if state:
                        state.click()

        city, _ = self.try_find_map_with_scroll(city_name.get())

        if city:
            city.click()
            self.try_get_by_text(text=LocalizedButtons.DELETE.get()).click()

        self.press_back_until_main_page()

    def try_find_map_with_scroll(self, name):
        country, i = self.try_get_by_text(locator=Locator.NAME, text=name)
        if not country:
            old_page_elements = [x.text for x in self.driver.find_elements_by_id(Locator.NAME.get())]
            self.scroll_down()
            country, i = self.try_get_by_text(locator=Locator.NAME, text=name)
            new_page_elements = [x.text for x in self.driver.find_elements_by_id(Locator.NAME.get())]
            timeout = time.time() + 60 * 2
            while not country and old_page_elements != new_page_elements:
                old_page_elements = new_page_elements
                self.scroll_down()
                country, i = self.try_get_by_text(locator=Locator.NAME, text=name)
                new_page_elements = [x.text for x in self.driver.find_elements_by_id(Locator.NAME.get())]
                if time.time() > timeout:
                    break
        return country, i

    @check_not_crash
    def scroll_down_to_element(self, xpath=None, locator=None, scroll_time=120):
        assert xpath or locator, "Xpath or Locator must be not None"
        el = self.try_get_by_xpath(xpath) if xpath else self.try_get(locator.get())
        timeout = time.time() + scroll_time
        while not (el and el.get_attribute("clickable") == 'true'):
            if self.try_get(Locator.PP_ANCHOR.get()) and self.try_get(Locator.PP_ANCHOR.get()).location["y"] > \
                    self.driver.get_window_size()["height"] * 0.5:
                self.scroll_down(from_el=self.try_get(Locator.PP_ANCHOR.get()))
            else:
                self.scroll_down()
            el = self.try_get_by_xpath(xpath) if xpath else self.try_get(locator.get())
            if time.time() > timeout:
                break
        return el

    @check_not_crash
    def edit_level_field(self, new_value):
        field = self.scroll_down_to_element(
            xpath="//*[@resource-id='{}']//*[@class='android.widget.EditText']".format(Locator.LEVELS_LAYOUT.get()))
        field.clear()
        field.send_keys(new_value)

    @check_not_crash
    def find_and_click_send(self):
        self.try_get_by_text(LocalizedButtons.OK.get()).click()

    @check_not_crash
    def stop_routing(self):
        self.try_get(Locator.TOGGLE.get()).click()
        self.try_get(Locator.STOP.get()).click()

    def enable_google_geolocation(self):
        ok_button = self.try_get("android:id/button1")
        if ok_button:
            ok_button.click()

    def switch_to_native(self):
        if self.driver.context != "NATIVE_APP":
            try:
                self.driver.close()
            except Exception as e:
                logging.warning("Something went wrong during closing webview: \n{}".format(e))
            self.driver.switch_to.context("NATIVE_APP")
            try:
                self.driver.execute_script("mobile: shell", {
                    'command': "am start {}/com.mapswithme.maps.SplashActivity".format(
                        get_settings("Android", "package"))})
                self.close_first_time_frame()
            except:
                pass
        self.driver.implicitly_wait(10)

    def wait_map_download(self, map_name):
        in_progress = self.try_get("onmap_downloader")
        assert self.try_get_by_text(map_name)
        button_download = self.try_get(Locator.DOWNLOAD_MAP_BUTTON.get())
        assert button_download
        button_download.click()
        WebDriverWait(self.driver, 120).until(EC.staleness_of(in_progress))

    def wait_map_auto_download(self, map_name):
        in_progress = self.try_get("onmap_downloader")
        if in_progress:
            WebDriverWait(self.driver, 60).until(EC.staleness_of(in_progress))

    def download_map_from_pp(self):
        download = BottomPanel().download()
        download.click()
        WebDriverWait(self.driver, 60).until(EC.staleness_of(download))

    @check_not_crash
    def _wait_in_progress(self):
        try:
            in_progress = self.driver.find_element_by_id(Locator.IN_PROGRESS.get())
            WebDriverWait(self.driver, 150).until(EC.staleness_of(in_progress))
        except NoSuchElementException as nse:
            pass

    def restart_app(self):
        self.driver.execute_script("mobile: shell",
                                   {'command': "am force-stop {}".format(get_settings("Android", "package"))})
        sleep(3)
        self.driver.execute_script("mobile: shell", {
            'command': "am start {}/com.mapswithme.maps.SplashActivity".format(get_settings("Android", "package"))})
        sleep(5)
        self.close_first_time_frame()


class IosSteps(BaseSteps):

    @check_not_crash
    def choose_first_search_result(self, category=None):
        if category:
            first_result = self.try_get_by_xpath("//*[@name='searchType' and @value='{}']".format(category))
            while not is_element_scrolled(self.driver, first_result):
                self.scroll_down(small=True)
        else:
            first_result = WebDriverManager.get_instance().driver.find_element_by_id(Locator.TITLE.get())
        logging.info("Choose first search result: {}".format(first_result.text))
        first_result.click()

    def choose_category_in_list(self, category_name):
        cat = self.try_get(category_name)
        old_page_elements = [x.text for x in
                             self.driver.find_elements_by_xpath("//*[@type='XCUIElementTypeStaticText']")]
        new_page_elements = []
        timeout = time.time() + 60
        while not (cat and cat.get_attribute("visible") == 'true') and old_page_elements != new_page_elements:
            old_page_elements = new_page_elements
            self.scroll_down(small=True)
            cat = self.try_get(category_name)
            new_page_elements = [x.text for x in
                                 self.driver.find_elements_by_xpath("//*[@type='XCUIElementTypeStaticText']")]
            if time.time() > timeout:
                break
        sleep(1)
        self.try_get(category_name).click()
        try:
            WebDriverWait(self.driver, 20).until(EC.visibility_of_element_located((By.ID, Locator.SHOW_ON_MAP.get())))
        except TimeoutException as nse:
            self.try_get(category_name).click()
            WebDriverWait(self.driver, 20).until(EC.visibility_of_element_located((By.ID, Locator.SHOW_ON_MAP.get())))

    @check_not_crash
    def accept_privacy_policy(self):
        try:
            self.driver.find_element_by_id(Locator.AGREE_PRIVACY.get()).click()
            self.driver.find_element_by_id(Locator.AGREE_TERMS.get()).click()
            try:
                self.driver.find_element_by_id(Locator.ACCEPT_POLICY_BUTTON.get()).click()
            except NoSuchElementException:
                pass
            logging.info("Clicked Accept policy button")
            self.driver.find_element_by_id(Locator.IOS_NEXT_BUTTON.get()).click()
            sleep(1)
            try:
                self.driver.find_element_by_id(Locator.IOS_NEXT_BUTTON.get()).click()
            except NoSuchElementException:
                pass

            alerts = self.driver.find_elements_by_xpath("//*[@type='XCUIElementTypeAlert']")
            while len(alerts) > 0:
                try:
                    alert_buttons = self.driver.execute_script('mobile: alert', {'action': 'getButtons'})
                    alert_params = {'action': 'accept'}
                    alert = [x for x in alert_buttons if
                             "всегда" in x or "Always" in x or "App" in x or "использовании" in x]
                    if len(alert) > 0:
                        alert_params["buttonLabel"] = alert[0]
                    self.driver.execute_script('mobile: alert', alert_params)
                    logging.info("Alert accepted")
                except:
                    pass

                sleep(5)
                self.try_get(Locator.IOS_NEXT_BUTTON.get()).click()
                sleep(1)
                alerts = self.driver.find_elements_by_xpath("//*[@type='XCUIElementTypeAlert']")

        except NoSuchElementException as nse:
            pass

    def show_place_on_map(self, country_name, state_name, city_name):
        self.driver.find_element_by_id(Locator.MENU_BUTTON.get()).click()
        sleep(1)
        self.driver.find_element_by_id(LocalizedButtons.DOWNLOAD_MAPS.get()).click()
        if country_name:
            country, _ = self.try_find_map_with_scroll(country_name)
            sleep(1)
            country.click()
            if state_name:
                state, _ = self.try_find_map_with_scroll(state_name)
                sleep(1)
                state.click()
        city, _ = self.try_find_map_with_scroll(city_name)
        sleep(1)
        city.click()
        self.try_get(LocalizedButtons.SHOW_ON_MAP.get()).click()

    def assert_map_downloaded(self, country_name, state_name, city_name):
        self.driver.find_element_by_id(Locator.MENU_BUTTON.get()).click()
        sleep(1)
        self.driver.find_element_by_id(LocalizedButtons.DOWNLOAD_MAPS.get()).click()
        if country_name:
            country, _ = self.try_find_map_with_scroll(country_name)
            sleep(1)
            country.click()
            if state_name:
                state, _ = self.try_find_map_with_scroll(state_name)
                sleep(1)
                state.click()
        city, _ = self.try_find_map_with_scroll(city_name)
        assert city

    @check_not_crash
    def download_map(self, country_name, state_name, *loc_names):
        self.driver.find_element_by_id(Locator.MENU_BUTTON.get()).click()
        sleep(1)
        self.driver.find_element_by_id(LocalizedButtons.DOWNLOAD_MAPS.get()).click()
        country = None
        state = None
        for loc_name in loc_names:
            if country_name:
                country, _ = self.try_find_map_with_scroll(country_name)
                if country:
                    sleep(1)
                    country.click()
                    if state_name:
                        state, _ = self.try_find_map_with_scroll(state_name)
                        if state:
                            sleep(1)
                            state.click()
            city, _ = self.try_find_map_with_scroll(loc_name)

            if not city:
                if country_name and country:
                    self.driver.back()
                if state_name and state:
                    self.driver.back()
                el = self.try_get_by_xpath("//*[@type='XCUIElementTypeSearchField']")
                el.click()
                el.send_keys(loc_name.get())
                city = None
                num = None
                sleep(3)
                for i, el in enumerate(self.driver.find_elements_by_xpath("//*[@type='XCUIElementTypeCell']")):
                    els = el.find_elements_by_xpath("./*[@type='XCUIElementTypeStaticText']")
                    need_el = els[1]
                    if len(els) <= 3:
                        need_el = els[0]
                    if loc_name.get() in need_el.text:
                        city = el
                        num = i
                        break
                assert city, "Element not found!"
                self.driver.find_elements_by_id(Locator.DOWNLOAD_ICON.get())[num].click()
                WebDriverWait(self.driver, 150).until(EC.presence_of_element_located((By.ID, "ic check")))

                self.driver.find_element_by_id(LocalizedButtons.CANCEL.get()).click()
        self.press_back_until_main_page()

    @check_not_crash
    def search(self, loc, click_search_button=True):
        logging.info("Searching location {}".format(loc))
        if click_search_button:
            self.click_search_button()
        self.driver.find_element_by_id(Locator.SEARCH_FIELD.get()).send_keys(loc)
        button = self.try_get_by_xpath("//*[@label='{}' or @label='{}']".format(LocalizedButtons.SEARCH.get(),
                                                                                LocalizedButtons.SEARCH.get().lower()))
        while not button:
            self.try_get(LocalizedButtons.NEXT_KEYBOARD.get()).click()
            button = self.try_get_by_xpath("//*[@label='{}' or @label='{}']".format(LocalizedButtons.SEARCH.get(),
                                                                                    LocalizedButtons.SEARCH.get().lower()))
        try:
            WebDriverWait(self.driver, 60).until(EC.visibility_of_element_located((By.ID, Locator.SHOW_ON_MAP.get())))
        except TimeoutException as te:
            pass

    @check_not_crash
    def assert_pp(self, text):
        assert self.driver.find_element_by_id(text)

    def assert_category_on_pp(self, text):
        assert self.try_get_by_xpath("//*[contains(@name, '{}')]".format(text))

    @check_not_crash
    def press_back_until_main_page(self):
        # logging.info("Go back to main page")
        self.close_first_time_frame()
        self.driver.implicitly_wait(3)
        self._press_back_all(Locator.SEND.get(), LocalizedButtons.CANCEL.get(), LocalizedButtons.CANCELLATION.get(),
                             Locator.CANCEL_BUTTON.get(), "goBackButton", LocalizedButtons.BACK.get(), "ic cancel",
                             "notNowButton")

        anchor_timeout = time.time() + 30  # 30s from now

        try:
            el = self.driver.find_element_by_id(Locator.PP_ANCHOR.get())
            if el.get_attribute("visible") == "true" and \
                    self.driver.find_element_by_id(Locator.PP_ANCHOR.get()).location["y"] > 70:
                self.scroll_up(from_el=el)
            else:
                while self.driver.find_element_by_id(Locator.PP_ANCHOR.get()).location["y"] < 50:
                    self.scroll_up()
                    if time.time() > anchor_timeout:
                        break
                if self.driver.find_element_by_id(Locator.PP_ANCHOR.get()).location["y"] < \
                        self.driver.get_window_size()["height"]:
                    self.scroll_up(from_el=el)
        except NoSuchElementException:
            el = self.try_get_by_xpath(
                "//*[@type='XCUIElementTypeScrollView']/*[@type='XCUIElementTypeOther']")
            if el:
                if el.get_attribute("visible") == "true" and \
                        self.try_get_by_xpath(
                            "//*[@type='XCUIElementTypeScrollView']/*[@type='XCUIElementTypeOther']").location[
                            "y"] > 70:
                    self.scroll_up(from_el=el)
                else:
                    while self.try_get_by_xpath(
                            "//*[@type='XCUIElementTypeScrollView']/*[@type='XCUIElementTypeOther']").location[
                        "y"] < 50:
                        self.scroll_up()
                        if time.time() > anchor_timeout:
                            break
                    if self.try_get_by_xpath(
                            "//*[@type='XCUIElementTypeScrollView']/*[@type='XCUIElementTypeOther']").location["y"] < \
                            self.driver.get_window_size()["height"]:
                        self.scroll_up(from_el=el)

        timeout = time.time() + 40  # 40s from now

        while not self.try_get(Locator.MENU_BUTTON.get()):
            self.driver.back()
            if time.time() > timeout:
                break

        while self.try_get(Locator.MENU_BUTTON.get()) and self.try_get(Locator.MENU_BUTTON.get()).get_attribute(
                "visible") != "true":
            self.driver.back()
            if time.time() > timeout:
                break
        try:
            BottomPanel().to().click()
            self._press_back_all("goBackButton", "notNowButton")
        except NoSuchElementException:
            pass
        self.driver.implicitly_wait(10)

    def _press_back_all(self, *locators):
        timeout = time.time() + 60
        xpath = "//*[@name='" + "' or @name='".join(
            locators) + "']"  # + "' @label='" + "' or @label='".join(["1233", "1", "2"]) + "' @value='" + "' or @value='".join(["1233", "1", "2"]) + "']"
        while len(self.driver.find_elements_by_xpath(xpath)) > 0:
            self.driver.find_element_by_xpath(xpath).click()
            sleep(1)
            if time.time() > timeout:
                break

    @check_not_crash
    def close_first_time_frame(self):
        self._press_back_all("tips_bookmarks_got_it", "tips_subway_got_it", "tips_search_got_it")


    @check_not_crash
    def delete_map(self, country_name, state_name, city_name):
        self.press_back_until_main_page()
        self.driver.find_element_by_id(Locator.MENU_BUTTON.get()).click()
        sleep(1)
        self.driver.find_element_by_id(LocalizedButtons.DOWNLOAD_MAPS.get()).click()
        if country_name:
            country, _ = self.try_find_map_with_scroll(country_name)
            if country:
                sleep(1)
                country.click()
            if state_name:
                state, _ = self.try_find_map_with_scroll(state_name)
                if state:
                    sleep(1)
                    state.click()

        city, _ = self.try_find_map_with_scroll(city_name)

        if city:
            sleep(1)
            city.click()
            self.try_get(Locator.DELETE_MAP.get()).click()

        self.press_back_until_main_page()

    def try_find_map_with_scroll(self, name):
        country, _ = self.try_get_by_text(locator=name, text=name.get())
        if not country:
            old_page_elements = [x.text for x in
                                 self.driver.find_elements_by_xpath("//*[@type='XCUIElementTypeStaticText']")]
            self.scroll_down()
            country, _ = self.try_get_by_text(locator=name, text=name.get())
            new_page_elements = [x.text for x in
                                 self.driver.find_elements_by_xpath("//*[@type='XCUIElementTypeStaticText']")]
            timeout = time.time() + 60
            while not country and old_page_elements != new_page_elements:
                old_page_elements = new_page_elements
                self.scroll_down()
                country, _ = self.try_get_by_text(locator=name, text=name.get())
                new_page_elements = [x.text for x in
                                     self.driver.find_elements_by_xpath("//*[@type='XCUIElementTypeStaticText']")]
                if time.time() > timeout:
                    break
        return country, _

    @check_not_crash
    def scroll_down_to_element(self, xpath=None, locator=None, scroll_time=120):
        assert xpath or locator, "Xpath or Locator must be not None"
        el = self.try_get_by_xpath(xpath) if xpath else self.try_get(locator.get())
        timeout = time.time() + scroll_time
        while not (el and el.get_attribute("visible") == 'true'):
            self.scroll_down()
            el = self.try_get_by_xpath(xpath) if xpath else self.try_get(locator.get())
            if time.time() > timeout:
                break
        return el

    @check_not_crash
    def edit_level_field(self, new_value):
        field = self.try_get_by_xpath("//*[@type='XCUIElementTypeCell']//*[@value='9']")
        field.click()
        self.try_get(LocalizedButtons.CLEAR_TEXT.get()).click()
        field.send_keys(new_value)
        logging.info("Level input edited. New value: ".format(new_value))

    @check_not_crash
    def find_and_click_send(self):
        self.try_get(Locator.SEND.get()).click()

    def stop_routing(self):
        while True:
            try:
                self.driver.find_element_by_id(Locator.MENU_BUTTON.get()).click()
                self.driver.find_element_by_id(LocalizedButtons.STOP.get()).click()
            except NoSuchElementException:
                self.driver.find_element_by_id(Locator.MENU_BUTTON.get()).click()
                break

    def off_wifi(self):
        actions = TouchAction(self.driver)
        win_size = self.driver.get_window_size()
        x = win_size['width'] / 2
        y_top = win_size['height']
        y_bot = win_size['height'] * 0.2
        actions.press(None, x, y_top).wait(500).move_to(None, x, y_bot).release().perform()
        wifi = None
        try:
            wifi = self.driver.find_element_by_id("wifi-button")
        except NoSuchElementException:
            wifi = self.driver.find_elements_by_xpath("//*[@type='XCUIElementTypeSwitch']")[2]
        val = wifi.get_attribute("value")
        logging.info("Wifi value: {}".format("On" if val == "1" else "Off"))
        if val == "1":
            wifi.click()
            time.sleep(5)
            logging.info("Wifi switched to value Off")
        actions.press(None, x, win_size['height'] * 0.5).wait(500).move_to(None, x, y_top).release().perform()
        if len(self.driver.find_elements_by_xpath("//*[@type='XCUIElementTypeSwitch']")) > 0:
            actions.press(None, x, win_size['height'] * 0.3).wait(500).move_to(None, x, y_top).release().perform()

    def on_wifi(self):
        actions = TouchAction(self.driver)
        win_size = self.driver.get_window_size()
        x = win_size['width'] / 2
        y_top = win_size['height']
        y_bot = win_size['height'] * 0.2
        actions.press(None, x, y_top).wait(500).move_to(None, x, y_bot).release().perform()
        wifi = None
        try:
            wifi = self.driver.find_element_by_id("wifi-button")
        except NoSuchElementException:
            wifi = self.driver.find_elements_by_xpath("//*[@type='XCUIElementTypeSwitch']")[2]
        val = wifi.get_attribute("value")
        logging.info("Wifi value: {}".format("On" if val == "1" else "Off"))
        if val == "0":
            wifi.click()
            time.sleep(5)
            logging.info("Wifi switched to value On")
        actions.press(None, x, win_size['height'] * 0.5).wait(500).move_to(None, x, y_top).release().perform()
        if len(self.driver.find_elements_by_xpath("//*[@type='XCUIElementTypeSwitch']")) > 0:
            actions.press(None, x, win_size['height'] * 0.3).wait(500).move_to(None, x, y_top).release().perform()

    def switch_to_native(self):
        if self.driver.context != "NATIVE_APP":
            try:
                self.driver.close()
            except Exception as e:
                logging.warning("Something went wrong during closing webview: \n{}".format(e))
            self.driver.switch_to.context("NATIVE_APP")
            try:
                self.driver.find_element_by_id("Tabs").click()
                for tab in self.driver.find_elements_by_id("closeTabButton"):
                    tab.click()
                self.driver.execute_script("mobile: terminateApp", {"bundleId": 'com.apple.mobilesafari'})
                self.driver.execute_script("mobile: activateApp", {"bundleId": 'com.my.maps-beta-enterprise'})
                self.close_first_time_frame()
            except:
                pass
            self.driver.find_element_by_id("breadcrumb").click()
        self.driver.implicitly_wait(10)

    def wait_map_download(self, map_name):
        button_download = self.try_get(Locator.DOWNLOAD_MAP_BUTTON.get())
        assert button_download
        button_download.click()

        WebDriverWait(self.driver, 120).until(EC2.element_to_be_dissapeared((By.ID, map_name)))

    def wait_map_auto_download(self, map_name):
        in_progress = self.try_get(map_name)
        if in_progress:
            WebDriverWait(self.driver, 60).until(EC2.element_to_be_dissapeared((By.ID, map_name)))

    def download_map_from_pp(self):
        download = BottomPanel().download()
        download.click()
        WebDriverWait(self.driver, 60).until(
            EC2.element_to_be_dissapeared((By.ID, LocalizedButtons.DOWNLOAD_FROM_PP_BUTTON.get())))

    def assert_map_deleted(self, country_name, state_name, city_name):
        self.press_back_until_main_page()
        self.driver.find_element_by_id(Locator.MENU_BUTTON.get()).click()
        sleep(1)
        self.driver.find_element_by_id(LocalizedButtons.DOWNLOAD_MAPS.get()).click()
        if country_name:
            country, _ = self.try_find_map_with_scroll(country_name)
            if country:
                sleep(1)
                country.click()
            if state_name:
                state, _ = self.try_find_map_with_scroll(state_name)
                if state:
                    sleep(1)
                    state.click()

        city, _ = self.try_find_map_with_scroll(city_name)
        assert city is None

    def pp_get_title(self):
        el = self.try_get_by_xpath("//*[@type='XCUIElementTypeScrollView']//*[@type='XCUIElementTypeStaticText']") or \
             self.try_get_by_xpath("//*[@type='XCUIElementTypeTable']//*[@type='XCUIElementTypeStaticText']")
        return el.text


class BookingSteps:

    def __init__(self):
        self.driver = WebDriverManager.get_instance().driver

    @staticmethod
    def get():
        if WebDriverManager.get_instance().device.platform == "Android":
            return AndroidBookingSteps()
        else:
            return IosBookingSteps()

    def find_booking_button_on_pp(self, button_locator):
        pass

    def search_booking_hotel(self, hotel_name):
        pass

    def search_osm_hotel(self, hotel_name):
        pass

    def close_after_booked_window(self):
        pass

    def assert_available_hotels_in_search(self):
        pass

    def assert_booking_buttons_on_rich_pp(self):
        pass

    def assert_hotel_description(self):
        pass

    def assert_filtered_hotels(self, rating=None, price_category=None, type=None):
        pass

    def assert_hotel_filter_cleared(self, cleared_type=None):
        pass


class AndroidBookingSteps(BookingSteps, AndroidSteps):

    def find_booking_button_on_pp(self, button_locator):
        button = self.try_get(button_locator.get())
        timeout = time.time() + 120
        while not (button and is_element_scrolled(self.driver, button)):
            self.scroll_down(small=True)
            button = self.try_get(button_locator.get())
            if time.time() > timeout:
                break
        return button

    def search_booking_hotel(self, hotel_name):
        self.search(hotel_name)
        results = self.driver.find_elements_by_xpath(
            "//*[@class='android.widget.RelativeLayout' and ./*[@resource-id='{}']]".format(Locator.TITLE.get()))
        for i, el in enumerate(results):
            els = self.driver.find_elements_by_xpath(
                "//*[@class='android.widget.RelativeLayout' and ./*[@resource-id='{}']][{}]/*".format(
                    Locator.TITLE.get(), i + 1))
            if len(els) > 4 and els[0].text == hotel_name:
                el.click()
                sleep(1)
                break
        else:
            assert False

    def search_osm_hotel(self, hotel_name="SkyPoint"):
        self.search(hotel_name)
        results = self.driver.find_elements_by_xpath(
            "//*[@class='android.widget.RelativeLayout' and ./*[@resource-id='{}']]".format(Locator.TITLE.get()))
        for i, el in enumerate(results):
            els = self.driver.find_elements_by_xpath(
                "//*[@class='android.widget.RelativeLayout' and ./*[@resource-id='{}']][{}]/*".format(
                    Locator.TITLE.get(), i + 1))
            if len(els) == 4 and els[0].text in hotel_name:
                el.click()
                sleep(1)
                break
        else:
            assert False

    def assert_available_hotels_in_search(self):
        sleep(5)  # чтобы успело прогрузиться на тормозящих телефонах
        available = 0
        for _ in range(3):
            results = self.driver.find_elements_by_id("description")
            for res in results:
                if BookingButtons.AVAILABLE.get() in res.text:
                    available = available + 1
            self.scroll_down()
        assert available > 0

    def assert_booking_buttons_on_rich_pp(self):
        buttons = [Locator.MORE_ON_BOOKING, Locator.MORE_REVIEWS_ON_BOOKING, Locator.DETAILS_ON_BOOKING]
        for button in buttons:
            assert self.find_booking_button_on_pp(button)
        assert BottomPanel().book()

    def assert_hotel_description(self):
        assert self.try_get(Locator.HOTEL_DESCRIPTION.get()).get_attribute("displayed") == "true"
        assert self.try_get_by_xpath("//*[contains(@text, '{}')]".format(LocalizedButtons.AEROPOLIS_DESCRIPTION.get()))

    def assert_filtered_hotels(self, rating=None, price_category=None, type=None):
        sleep(5)  # чтобы успело прогрузиться на тормозящих телефонах
        for _ in range(3):
            results = [x.text for x in self.driver.find_elements_by_id("description")]
            for res in results:
                if rating:
                    assert BookingButtons.RATING.get() in res
                    assert float(res.split("{}: ".format(BookingButtons.RATING.get()))[-1].split()[0]) >= rating
                if type:
                    assert type in res

            if price_category:
                results = [x.text for x in self.driver.find_elements_by_id("price_category")]
                for res in results:
                    assert res == price_category

            self.scroll_down()

    def assert_hotel_filter_cleared(self, cleared_type=None):
        rating = 0
        without_rating = 0
        price_low = 0
        price_medium = 0
        not_apartments = 0

        sleep(5)  # чтобы успело прогрузиться на тормозящих телефонах

        for _ in range(3):
            results = [x.text for x in self.driver.find_elements_by_id("price_category")]
            for res in results:
                if res == "$":
                    price_low = price_low + 1
                if res == "$$":
                    price_medium = price_medium + 1

            results = [x.text for x in self.driver.find_elements_by_id("description")]
            for res in results:
                if BookingButtons.RATING.get() in res:
                    rating = rating + 1
                else:
                    without_rating = without_rating + 1
                if cleared_type not in res:
                    not_apartments = not_apartments + 1

            self.scroll_down()

        assert rating > 0
        assert without_rating > 0
        assert price_medium + price_low > 0
        assert not_apartments > 0


class IosBookingSteps(BookingSteps, IosSteps):

    def find_booking_button_on_pp(self, button_locator):
        button = self.try_get(button_locator.get())
        timeout = time.time() + 60
        while not (button and is_element_scrolled(self.driver, button)):
            self.scroll_down(small=True)
            button = self.try_get(button_locator.get())
            if time.time() > timeout:
                break
        return button

    def search_booking_hotel(self, hotel_name):
        self.search(hotel_name)
        sleep(2)
        results = self.driver.find_elements_by_xpath("//*[@type='XCUIElementTypeCell']")
        for i, el in enumerate(results):
            els = el.find_elements_by_xpath("./*")
            if len(els) > 8 and els[1].text == hotel_name:
                el.click()
                break
            if len(els) == 8 and els[0].text == hotel_name:
                el.click()
                break
        else:
            assert False

    def search_osm_hotel(self, hotel_name="SkyPoint"):
        self.search(hotel_name)
        results = self.driver.find_elements_by_xpath("//*[@type='XCUIElementTypeCell']")
        for i, el in enumerate(results):
            els = el.find_elements_by_xpath("./*")
            if (len(els) <= 5 or len(els) == 8) and els[0].text in hotel_name:
                el.click()
                break
        else:
            assert False

    def close_after_booked_window(self):
        window = self.try_get(LocalizedButtons.CANCEL.get())
        if window:
            window.click()

    def assert_available_hotels_in_search(self):
        results = self.driver.find_elements_by_xpath(
            "//*[@type='XCUIElementTypeTable']/*[@type='XCUIElementTypeCell']")
        available = 0
        for res in results:
            els = res.find_elements_by_xpath("./*[@type='XCUIElementTypeStaticText' and contains(@value, '{}')]".format(
                BookingButtons.AVAILABLE.get()))
            if len(els) > 0:
                available = available + 1

        assert available > 0

    def assert_booking_buttons_on_rich_pp(self):
        assert self.try_get(Locator.DETAILS_ON_BOOKING.get())
        assert self.try_get(Locator.MORE_REVIEWS_ON_BOOKING.get())
        assert self.try_get(Locator.MORE_ON_BOOKING.get())
        assert BottomPanel().book()

    def assert_hotel_description(self):
        assert self.try_get(LocalizedButtons.SHOW_MORE.get())
        assert self.try_get_by_xpath("//*[contains(@name, '{}')]".format(LocalizedButtons.AEROPOLIS_DESCRIPTION.get()))

    def assert_filtered_hotels(self, rating=None, price_category=None, type=None):
        sleep(3)  # чтобы успело прогрузиться на тормозящих телефонах
        results = self.driver.find_elements_by_xpath(
            "//*[@type='XCUIElementTypeTable']/*[@type='XCUIElementTypeCell']")
        for res in results:
            if rating:
                el = res.find_element_by_xpath(
                    "./*[@type='XCUIElementTypeStaticText' and contains(@value, '{}')]".format(
                        BookingButtons.RATING.get()))
                assert float(el.text.split("{}: ".format(BookingButtons.RATING.get()))[-1].split()[0]) >= rating
            if price_category:
                el = res.find_element_by_xpath(
                    "./*[@type='XCUIElementTypeStaticText' and contains(@value, '$')]")
                assert el.text == price_category

            if type:
                els = res.find_elements_by_xpath("./*[@name='searchType' and @value='{}']".format(type))
                assert len(els) == 1

    def assert_hotel_filter_cleared(self, cleared_type=None):
        rating = 0
        without_rating = 0
        price_low = 0
        price_medium = 0
        not_apartments = 0

        results = self.driver.find_elements_by_xpath(
            "//*[@type='XCUIElementTypeTable']/*[@type='XCUIElementTypeCell']")
        for res in results:
            el = res.find_elements_by_xpath(
                "./*[@type='XCUIElementTypeStaticText' and contains(@value, '{}')]".format(
                    BookingButtons.RATING.get()))
            if len(el) > 0:
                rating = rating + 1
            else:
                without_rating = without_rating + 1

            el = res.find_elements_by_xpath(
                "./*[@type='XCUIElementTypeStaticText' and contains(@value, '$')]")
            if len(el) > 0:
                if el[0].text == "$":
                    price_low = price_low + 1
                if el[0].text == "$$":
                    price_medium = price_medium + 1
            if cleared_type:
                els = res.find_elements_by_xpath("./*[@name='searchType' and @value='{}']".format(cleared_type))
                if len(els) == 0:
                    not_apartments = not_apartments + 1

        assert rating > 0
        assert without_rating > 0
        assert price_medium + price_low > 0
        assert not_apartments > 0