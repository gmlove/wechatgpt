import unittest
import random
import threading
import time
import requests

from .server import app


class ServerTest(unittest.TestCase):
    server_port = None

    @classmethod
    def setUpClass(cls):
        ServerTest.server_port = random.randint(5243, 20000)
        server = threading.Thread(target=lambda: app.run("localhost", ServerTest.server_port))
        server.setDaemon(True)
        server.start()
        time.sleep(2)

    def test_detect_task_add(self):
        data = """<xml>
            <ToUserName><![CDATA[gh_f08f404ebac3]]></ToUserName>
            <FromUserName><![CDATA[o4sfxsp-43LX2Oihg_YL3VQyT0Yk]]></FromUserName>
            <CreateTime>1515830851</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[你是谁]]></Content>
            <MsgId>6510443931858529216</MsgId>
        </xml>"""
        response = requests.post("http://localhost:%s/wechat" % (ServerTest.server_port), data.encode("utf8"), headers={"content-type": "text/xml"})
        self.assertEqual(response.status_code, 200)
        print("response: %s" % str(response.content, "utf8"))
