################################################################################
# pip install playwright
# playwright install chromium
#
# def event_request_handler(request: Request):
#     logging.debug(f'a request was made: {request.method} {request.url}')
#
# def route_handler(route: Route, request: Request):
#     print(f'route_handler {request.url}')
#     rst: APIResponse = page.request.get('')
#     route.fulfill(response=rst, status=404)
# 执行js
# webdriver_flag = page.evaluate("window.navigator.webdriver")  # ===undefined
# 路由拦截
# page.route(re.compile(r"/.*\.(png|jpg|jpeg)\?imageview.*", re.IGNORECASE), route_handler)
# 添加监听
# page.on("request", event_request_handler)
# 移除监听
# page.remove_listener("request", event_request_handler)
# context.cookies()
# 自动化工具会设置这个值为True，站点反爬可以检测到
# wipe_webdriver_flag = "delete navigator.__proto__.webdriver"
# context.add_init_script(wipe_webdriver_flag)
################################################################################

import logging

import playwright.sync_api
from playwright.sync_api import *

logging.basicConfig(level=logging.INFO)
logging.getLogger("seleniumwire").setLevel(logging.ERROR)

token_contract = "0x12BB890508c125661E03b09EC06E404bc9289040"
base_url = "https://ceye.bitying.cn"
expect_url = "https://tool.biteagle.net/ceye/contract"
# chrome的headless模式下的ua带有Headless字样，其他没有
ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"

iphone12 = playwright.sync_api.sync_playwright()


def run_playwright(pw: Playwright):
    chrome_args = ["--disable-blink-features=AutomationControlled"]
    browser = pw.chromium.launch(headless=True, args=chrome_args, channel="chrome")
    context = browser.new_context(user_agent=ua)
    # iphone = pw.devices["iPhone 13 Pro"]
    # browser = pw.webkit.launch(headless=False)
    # context = browser.new_context(**iphone)

    page = context.new_page()
    page.goto(base_url)
    page.locator('[placeholder="粘贴或输入合约地址"]').fill(token_contract)
    page.locator("text=立即检测").click()
    with page.expect_response(expect_url) as exp_rsp:
        rsp: Response = exp_rsp.value
        print(rsp.json())

    page.screenshot(path="screenshot.png")
    browser.close()


with sync_playwright() as pw:
    run_playwright(pw)
