import asyncio
from concurrent.futures import ThreadPoolExecutor
import datetime
from functools import partial
import os
import concurrent
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from werkzeug.utils import secure_filename
import requests
from xhs import XhsClient
from xhs.exception import SignError, DataFetchError
import time
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright

app = FastAPI()

# 如下更改为 stealth.min.js 文件路径地址
stealth_js_path = "./stealth.min.js"
signBrowser = None
class BrowserInstance:

    def __init__(self):
        self.A1= ""
        self.instance = None
        self.chromium = None
        self.browser = None
        self.context = None
         
        self.page = None
        self.start()
        self.reset_instance()
    def start(self):
        print("启动浏览器")
        self.instance = sync_playwright().start()
        self.chromium = self.instance.chromium
        if self.instance:
            self.instance.stop()
        self.A1= ""
        self.instance = sync_playwright().start()
        self.chromium = self.instance.chromium
        self.browser = self.chromium.launch(headless=True)
        self.context = self.browser.new_context()
        self.context.add_init_script(path=stealth_js_path)
        self.page = self.context.new_page()
        self.A1= ""
        print("启动浏览器完成")
    def reset_instance(self,a1=None):
        print("初始化页面实例")
        self.A1= ""
        self.page.goto("https://www.xiaohongshu.com")
        print("正在跳转至小红书首页")
        # time.sleep(1)
        cookies = self.context.cookies()
        for cookie in cookies:
            if cookie["name"] == "a1":
                self.A1 = cookie["value"]
        self.update_a1(a1)

    def update_a1(self,a1):
        if(a1!=None and a1!=self.A1):
            self.context.add_cookies([
                                {'name': 'a1', 'value': a1, 'domain': ".xiaohongshu.com", 'path': "/"}]
                            )
            print("更新cookie")
            self.page.reload()
            print("重新加载页面")
            self.A1 = a1
            time.sleep(3)


    def sign(self,uri, data, a1, web_session):
        if(a1!=None and a1!=self.A1):
            print("a1不一样，更新cookie")
            
            self.update_a1(a1)
        print("url:%s data:%s a1:%s" % (uri, data, a1))
        print(self.page.url)
        for _ in range(10):
            try:
                print(self.page.url)
                encrypt_params = self.page.evaluate("([url, data]) => window._webmsxyw(url, data)", [uri, data])
                return {
                    "x-s": encrypt_params["X-s"],
                    "x-t": str(encrypt_params["X-t"])
                }
            except Exception as e:
                # 这儿有时会出现 window._webmsxyw is not a function 或未知跳转错误，因此加一个失败重试趴
                print("第%d次尝试签名失败，尝试重置浏览器" % (_ + 1),e)
                print(self.page.url)
                self.reset_instance(a1)
        raise Exception("重试了这么多次还是无法签名成功，寄寄寄")


def sign(uri, data=None, a1="", web_session=""):
    global signBrowser
    print("开始签名啦！！！！")
    return signBrowser.sign(uri, data, a1, web_session)



executor = ThreadPoolExecutor(max_workers=5)

@app.post("/create_image_note")
async def create_image_note(
    cookie: str = Form(...),
    title: str = Form(...),
    desc: str = Form(...),
    is_private: bool = Form(False),
    post_time: str = Form(None),
    images: list[UploadFile] = File(...)
):
    image_paths = []
    for file in images:
        if file.filename == '':
            raise HTTPException(status_code=400, detail="No selected file")
        filename = secure_filename(file.filename)
        file_path = os.path.join('./images', filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        image_paths.append(file_path)

    try:
       
        note = await  asyncio.to_thread(create_image_note,cookie,title, desc, image_paths, is_private, post_time)
         
        return JSONResponse(content=note, status_code=200)
    except (SignError, DataFetchError) as e:
        raise HTTPException(status_code=400, detail=str(e))


def create_xhs_client(cookie):
    global signBrowser
    if(signBrowser==None):
        signBrowser = BrowserInstance()
    xhs_client = XhsClient(cookie=cookie, sign=sign)
    return xhs_client

def create_image_note(cookie,title, desc, image_paths,is_private,post_time):
    # 同步代码
    xhs_client = create_xhs_client(cookie=cookie)
    try:
        note =  xhs_client.create_image_note(title, desc, image_paths, is_private=is_private, post_time=post_time)
    except (SignError, DataFetchError) as e:
            raise HTTPException(status_code=400, detail=str(e))



# @app.post("/create_video_note")
# async def create_video_note(
#     cookie: str,
#     title: str,
#     video_path: str,
#     desc: str = "",
#     cover_path: str = None,
#     is_private: bool = False
# ):
#     xhs_client = XhsClient(cookie=cookie, sign=sign)
#     try:
#         note =  xhs_client.create_video_note(title, video_path, desc=desc, cover_path=cover_path, is_private=is_private)
#         return JSONResponse(content=note, status_code=200)
#     except (SignError, DataFetchError) as e:
#         raise HTTPException(status_code=400, detail=str(e))

def beauty_print(data: dict):
    import json
    print(json.dumps(data, ensure_ascii=False, indent=2))
 
async def main():
 
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == '__main__':
    asyncio.run(main())