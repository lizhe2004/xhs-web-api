import asyncio
from concurrent.futures import ThreadPoolExecutor
import datetime
from functools import partial
import os
import concurrent
import tempfile
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
# from playwright.async_api import async_playwright
from pydantic import BaseModel


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
        if self.instance:
            self.instance.stop()
        self.A1= ""
        self.instance = sync_playwright().start()
        self.chromium = self.instance.chromium
        self.browser = self.chromium.launch(headless=True)
        self.context = self.browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        self.context.add_init_script(path=stealth_js_path)
        self.page = self.context.new_page()
        self.A1= ""
        print("启动浏览器完成")
    def reset_instance(self,a1=None):
        print("初始化页面实例")
        self.A1= ""
        for _ in range(2):
            try:
                self.page.goto("https://www.xiaohongshu.com/explore")
                print("正在跳转至小红书首页")
                time.sleep(2)
                break
            except Exception as e:
                     
                    print("第%d次打开小红书首页" % (_ + 1),e)
                    print(self.page.url)
            
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

            for _ in range(2):
                try:
                    self.page.reload()
                    print("重新加载页面")
                    self.A1 = a1
                    time.sleep(3)
                    break
                except Exception as e:
                        
                        print("第%d次更新cookie重新加载页面异常" % (_ + 1),e)
                        print(self.page.url)
            

    def sign(self,uri, data, a1, web_session):
        if(a1!=None and a1!=self.A1):
            print("a1不一样，更新cookie")
            
            self.update_a1(a1)
        print("url:%s data:%s a1:%s" % (uri, data, a1))
         
        for _ in range(10):
            try:
                print("生成签名之前的页面地址"+self.page.url)
                encrypt_params = self.page.evaluate("([url, data]) => window._webmsxyw(url, data)", [uri, data])
                return {
                    "x-s": encrypt_params["X-s"],
                    "x-t": str(encrypt_params["X-t"])
                }
            except Exception as e:
                # 这儿有时会出现 window._webmsxyw is not a function 或未知跳转错误，因此加一个失败重试趴
                print("第%d次尝试签名失败，尝试重置浏览器" % (_ + 1),e)
                print("生成签名失败之后查看当前页面地址"+self.page.url)
                self.reset_instance(a1)
        raise Exception("重试了这么多次还是无法签名成功")


def sign(uri, data=None, a1="", web_session=""):
    global signBrowser
    if(signBrowser==None):
        signBrowser = BrowserInstance()
    print("开始签名啦！！！！")
    return signBrowser.sign(uri, data, a1, web_session)



executor = ThreadPoolExecutor(max_workers=5)

@app.post("/create_image_note")
async def create_image_note_api(
    cookie: str = Form(...),
    title: str = Form(...),
    desc: str = Form(...),
    is_private: bool = Form(False),
    post_time: str = Form(None),
    images: list[UploadFile] = File(...)
):

    image_paths = []
    temp_files = []  # 用于存储临时文件对象

    for file in images:
        if file.filename == '':
            raise HTTPException(status_code=400, detail="No selected file")
        filename = secure_filename(file.filename)
        
        # 创建一个临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1], mode='wb', dir='./images') as temp:
            file_path = temp.name
            temp.write(await file.read())
            image_paths.append(file_path)
            temp_files.append(temp)  # 保存临时文件对象

    try:
        note = await asyncio.to_thread(create_image_note, cookie, title, desc, image_paths, is_private, post_time)
        print("创建笔记成功")
        beauty_print(note)
        return JSONResponse(content=note, status_code=200)
    finally:
        # 删除临时文件
        for temp_file in temp_files:
            try:
                os.remove(temp_file.name)
            except OSError as e:
                print(f"Error deleting {temp_file.name}: {e}")


class CreateImageNoteRequest(BaseModel):
    cookie: str
    title: str
    desc: str
    is_private: bool = False
    post_time: str = None
    image_urls: list[str]

@app.post("/create_image_note_from_urls")
async def create_image_note_from_urls(request: CreateImageNoteRequest):
    cookie = request.cookie
    title = request.title
    desc = request.desc
    is_private = request.is_private
    post_time = request.post_time
    image_urls = request.image_urls

    image_paths = []
    temp_files = []  # 用于存储临时文件对象

    for url in image_urls:
        try:
            response = requests.get(url)
            response.raise_for_status()
            filename = secure_filename(url.split('/')[-1])
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1], mode='wb', dir='./images') as temp:
                file_path = temp.name
                temp.write(response.content)
                image_paths.append(file_path)
                temp_files.append(temp)  # 保存临时文件对象
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to download image from {url}: {str(e)}")

    try:
        note = await asyncio.to_thread(create_image_note, cookie, title, desc, image_paths, is_private, post_time)
        print("创建笔记成功")
        beauty_print(note)
        return JSONResponse(content=note, status_code=200)
    finally:
        # 删除临时文件
        for temp_file in temp_files:
            try:
                os.remove(temp_file.name)
            except OSError as e:
                print(f"Error deleting {temp_file.name}: {e}")

def create_xhs_client(cookie):

    xhs_client = XhsClient(cookie=cookie, sign=sign)
    return xhs_client

def create_image_note(cookie,title, desc, image_paths,is_private,post_time):
    # 同步代码
    xhs_client = create_xhs_client(cookie=cookie)
    try:
        note =  xhs_client.create_image_note(title, desc, image_paths, is_private=is_private, post_time=post_time)
        return note
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