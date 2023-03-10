本项目旨在帮助大家搭建基于微信公众号的 ChatGPT 智能助理。

上几个聊天截图，大家先睹为快。
（todo）

### 为什么需要本项目

为什么 OpenAI 开放了网页版本的聊天功能之后，还需要一个基于微信公众号的版本？主要原因是：

1. 国内网络无法直接访问
2. 网页版本体验较差，无法在任意时刻任意地点有手机就能用

微信作为一个广泛使用的专业的聊天软件，是智能助手的理想载体。

### 项目的初衷和目的

项目的目标是提供一套可用的代码及尽可能简单完善的步骤，帮助一般开发人员通过几步操作就能搭建自己的微信智能助理。

本项目不会致力于让代码具备高性能和高并发，因为出于个人用途（或者小的团体，比如家庭），这些特性是没必要的，只能白白的增加复杂度。

如果希望基于此项目，搭建并发布自己的对外公共服务，出现的一切问题，请自行负责。

## 教程

要搭建自己的基于微信公众号的智能助力，主要需要完成以下几步：

1. 注册 aws 云服务账号，并启动虚拟机
2. 注册 OpenAI 开发者账号，获取 token
3. 注册微信公众号
4. 部署此服务
5. 配置微信公众号自动回复

### 注册 aws 云服务账号，并启动虚拟机

后续所有步骤的前提是一台海外的虚拟机，否则无法访问 OpenAI 的文档和服务。具体如何申请？请参考：

- 如何创建并激活新的 AWS 账户： https://aws.amazon.com/cn/premiumsupport/knowledge-center/create-and-activate-aws-account/
- AWS 免费套餐介绍：https://aws.amazon.com/cn/premiumsupport/knowledge-center/what-is-free-tier/
- EC2 介绍及准备工作：https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/get-set-up-for-amazon-ec2.html
- 启动实例：https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EC2_GetStarted.html

### 注册 OpenAI 开发者账号

有了虚拟机之后，可以通过虚拟机的网络访问 OpenAI 的文档和服务。

具体做法很多，以下是一种简单易行的方式（以下假定你的虚拟机是基于 Ubuntu 的系统，其它系统的对应命令可以类比）：

- 在虚拟机中安装并启动代理服务：`sudo apt-get install squid`
- 通过 ssh 隧道将远程主机的代理映射到本地：`ssh -L 3128:localhost:3128 YOUR_USER_NAME@YOUR_EC2_INSTANCE`
- 本地安装 Firefox，并配置代理为 http://localhost:3128（Firefox 的好处是其代理是独立的，不会和系统的冲突）
- 用 Firefox 打开 OpenAI 的网站，并注册开发者账号
- 生成 token: https://platform.openai.com/account/api-keys

### 注册微信公众号

参考微信的文档：https://kf.qq.com/faq/120911VrYVrA151009eIrYvy.html

本项目使用微信公众号的自动回复功能来搭建智能助理，所以，注册时，请选择公众号类型为个人微信订阅号。

### 部署此项目
