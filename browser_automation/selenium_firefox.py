# coding=utf-8
import json
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from seleniumwire.webdriver import Firefox

logging.basicConfig(level=logging.INFO)
logging.getLogger("seleniumwire").setLevel(logging.ERROR)

token_contract = "0x12BB890508c125661E03b09EC06E404bc9289040"
base_url = "https://ceye.bitying.cn"
expect_url = "https://tool.biteagle.net/ceye/contract"

mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"


def run_selenium():
    options = webdriver.FirefoxOptions()
    options.headless = False
    # options.set_preference('general.useragent.override', mobile_ua)
    # service = Service(executable_path=GeckoDriverManager().install())
    service = Service(
        executable_path="/Users/sharp/.wdm/drivers/geckodriver/macos-aarch64/0.31/geckodriver"
    )
    wd = Firefox(options=options, service=service)
    wd.implicitly_wait(10)

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
