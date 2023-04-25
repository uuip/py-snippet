################################################################################
# 执行js
# print(wd.execute_script("return navigator.userAgent;"))
# print(wd.execute_script("return window.navigator.webdriver===undefined;"))
# 遍历当前的请求
#     for x in wd.requests:  # type: Request
#         print(x.url)
# def response_handler(request: Request, response: Response):
#     if request.url == "https://tool.biteagle.net/ceye/contract":
#         print(response.body.decode())
# 路由拦截 response
# wd.response_interceptor = response_handler
# 显式等待元素, until 多种方式:
# from selenium.webdriver.support import expected_conditions as ec
# 1. lambda d: d.find_element(By.TAG_NAME,"p")
# 2. ec.presence_of_element_located((By.CLASS_NAME, check_classname))
# WebDriverWait(wd, 8).until(...)
# wd.get_cookies()
# wd.switch_to.window(wd.window_handles[])
# 自动化工具会设置这个值为True，站点反爬可以检测到，备选
# wipe_webdriver_flag = "delete navigator.__proto__.webdriver"
# wd.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": wipe_webdriver_flag})
################################################################################

import json
import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from seleniumwire.webdriver import Chrome
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO)
logging.getLogger("seleniumwire").setLevel(logging.ERROR)

token_contract = "0x12BB890508c125661E03b09EC06E404bc9289040"
base_url = "https://ceye.bitying.cn"
expect_url = "https://tool.biteagle.net/ceye/contract"
# headless模式下的ua带有Headless字样
ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"


def run_selenium():
    options = webdriver.ChromeOptions()
    options.headless = False
    options.add_argument(f"--user-agent={ua}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # options.add_experimental_option("mobileEmulation", {"deviceName": "iPhone 12 Pro"})
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    service = Service(executable_path=ChromeDriverManager().install())
    wd = Chrome(options=options, service=service)
    wd.implicitly_wait(10)  # 隐式设置元素等待时间

    wd.get(base_url)
    wd.find_element(By.CSS_SELECTOR, '[placeholder="粘贴或输入合约地址"]').send_keys(token_contract)
    wd.find_element(By.CSS_SELECTOR, ".custom-button").click()

    request = wd.wait_for_request(expect_url)
    rst = request.response.body.decode()
    if request.response.headers["content-type"] == "application/json":
        rst = json.loads(rst)
    print(rst)
    wd.save_screenshot("screenshot.png")
    wd.quit()


run_selenium()
