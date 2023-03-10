from __future__ import annotations

from datetime import datetime
from typing import List, Union

from lxml import etree


class WechatMsg:
    def __init__(self, to_user_name, from_user_name, content: Union[str, MessageContent], create_time=None, msg_type="text"):
        self.to_user_name = to_user_name
        self.from_user_name = from_user_name
        self.content: MessageContent = TextMessageContent(content.strip()) if isinstance(content, (str)) else content
        self.msg_type = msg_type
        self.msg_id = None
        self.create_time = create_time or datetime.now()

    def copy(self) -> WechatMsg:
        return WechatMsg(self.to_user_name, self.from_user_name, self.content.copy(), self.create_time, self.msg_type)

    def update_time(self):
        self.create_time = datetime.now()

    @staticmethod
    def from_raw_xml(raw_xml):
        xml = etree.XML(raw_xml)  # type: ignore
        ele_value = lambda xpath: xml.xpath(xpath)[0]
        msg = WechatMsg(
            ele_value("//ToUserName/text()"),
            ele_value("//FromUserName/text()"),
            ele_value("//Content/text()"),
        )
        return msg

    def xml_str(self):
        root = etree.Element("xml")  # type: ignore
        etree.SubElement(root, "ToUserName").text = etree.CDATA(self.to_user_name)  # type: ignore
        etree.SubElement(root, "FromUserName").text = etree.CDATA(self.from_user_name)  # type: ignore
        etree.SubElement(root, "CreateTime").text = etree.CDATA(self.create_time.strftime("%s"))  # type: ignore
        etree.SubElement(root, "MsgType").text = etree.CDATA(self.msg_type)  # type: ignore
        self.content.xml(root)
        return etree.tostring(root, encoding=str)  # type: ignore


class MessageContent:
    def xml(self, parentEle):
        raise NotImplementedError()

    def copy(self) -> MessageContent:
        raise NotImplementedError()


class TextMessageContent(MessageContent):
    def __init__(self, text):
        self.text = text

    def xml(self, parentEle):
        etree.SubElement(parentEle, "Content").text = etree.CDATA(self.text)  # type: ignore

    def copy(self) -> MessageContent:
        return TextMessageContent(self.text)

    def change_text(self, text: str):
        self.text = text


class RichMessageContent(MessageContent):
    def __init__(self, articles: List[RichMessageArticleContent]):
        self.articles = articles

    def xml(self, parentEle):
        etree.SubElement(parentEle, "ArticleCount").text = str(len(self.articles))  # type: ignore
        articlesEle = etree.SubElement(parentEle, "Articles")  # type: ignore
        for article in self.articles:
            itemEle = etree.SubElement(articlesEle, "item")  # type: ignore
            article.xml(itemEle)

    def copy(self) -> MessageContent:
        return RichMessageContent([a.copy() for a in self.articles])


class RichMessageArticleContent(MessageContent):
    def __init__(self, title: str, desc: str, pic_url: str = "", url: str = ""):
        self.title = title
        self.desc = desc
        self.pic_url = pic_url
        self.url = url

    def xml(self, parentEle):
        etree.SubElement(parentEle, "Title").text = self.title  # type: ignore
        etree.SubElement(parentEle, "Description").text = self.desc  # type: ignore
        etree.SubElement(parentEle, "PicUrl").text = self.pic_url  # type: ignore
        etree.SubElement(parentEle, "Url").text = self.url  # type: ignore

    def copy(self) -> RichMessageArticleContent:
        return RichMessageArticleContent(self.title, self.desc, self.pic_url, self.url)
