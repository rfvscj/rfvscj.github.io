---
title: Clash 使用备忘
date: 2026-05-02 00:00:00
updated: 2026-05-02 17:55:00
categories:
  - OS&网络
tags:
  - Clash
  - OpenClash
  - Switch
  - DNS
index_img: /img/bg0.png
excerpt: 只保留两类长期配置：GitHub SSH 需要的 fake-ip-filter，以及本地 mihomo-party 订阅覆写规则。
published: true
---

这篇只保留两个长期需要的配置：`fake-ip-filter` 和订阅覆写。完整覆写文件在这里：[ACL4SSR_Online_Full_WithIcon.local.yaml](/files/mihomo/ACL4SSR_Online_Full_WithIcon.local.yaml)。

## fake-ip-filter 和 GitHub SSH

`fake-ip-filter` 只放必须真实解析的域名。GitHub SSH 建议放进去，否则 HTTPS 能打开但 `git@github.com` 仍可能异常。

```yaml
dns:
  enable: true
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter:
    - '*.lan'
    - '*.local'
    - 'localhost'
    - 'localhost.*'
    - '+.msftconnecttest.com'
    - '+.msftncsi.com'
    - '+.pool.ntp.org'
    - 'time.*.com'
    - '+.github.com'
    - 'github.com'
    - 'ssh.github.com'
```

GitHub 路由单独指定，避免被最后的 `MATCH` 带偏：

```yaml
rules:
  - DOMAIN,github.com,PROXY
  - DOMAIN,ssh.github.com,PROXY
  - DOMAIN-SUFFIX,github.com,PROXY
  - DOMAIN-SUFFIX,githubusercontent.com,PROXY
  - DOMAIN-SUFFIX,githubassets.com,PROXY
```

如果 22 端口不通，SSH 走 443：

```sshconfig
Host github.com
  HostName ssh.github.com
  User git
  Port 443
```

验证：

```bash
ssh -T git@github.com
ssh -T -p 443 git@ssh.github.com
```

## 订阅覆写配置

基于 mihomo-party override-hub 的 `ACL4SSR_Online_Full_WithIcon.yaml`，本地只追加这些长期规则。

新增策略组：

```yaml
proxy-groups:
  - name: Switch服务
    type: select
    proxies:
      - DIRECT
      - 节点选择
      - 美国节点
      - 香港节点
      - 台湾节点
      - 狮城节点
      - 日本节点
      - 韩国节点
      - 手动切换

  - name: Switch直连
    type: select
    proxies:
      - DIRECT
      - 全球直连

  - name: Steam平台
    type: select
    proxies:
      - DIRECT
      - 节点选择
      - 美国节点
      - 香港节点
      - 台湾节点
      - 狮城节点
      - 日本节点
      - 韩国节点
      - 手动切换

  - name: Steam下载直连
    type: select
    proxies:
      - DIRECT
      - 全球直连
```

新增规则放在大型 `RULE-SET` 和 `MATCH` 前面，保证优先命中：

```yaml
rules:
  - DOMAIN-SUFFIX,sugon.com,全球直连
  - DOMAIN-SUFFIX,hygon.com,全球直连
  - DOMAIN-SUFFIX,rogon.com,全球直连

  - DOMAIN-SUFFIX,steamcontent.com,Steam下载直连
  - DOMAIN-SUFFIX,steamserver.net,Steam下载直连
  - DOMAIN-SUFFIX,steamstatic.com,Steam下载直连
  - DOMAIN-SUFFIX,steamcdn-a.akamaihd.net,Steam下载直连
  - DOMAIN-SUFFIX,steampowered.com,Steam平台
  - RULE-SET,Steam,Steam平台

  - DOMAIN-SUFFIX,nintendo.com,Switch服务
  - DOMAIN-SUFFIX,nintendo.net,Switch服务
  - DOMAIN-SUFFIX,nintendowifi.net,Switch服务
  - DOMAIN-SUFFIX,nintendoswitch.com,Switch服务
  - DOMAIN-SUFFIX,nintendoswitch.cn,Switch直连
  - RULE-SET,Nintendo,Switch服务

  - DOMAIN-SUFFIX,ubisoft.com,游戏平台
  - DOMAIN-SUFFIX,ubi.com,游戏平台
  - DOMAIN-SUFFIX,ubisoftconnect.com,游戏平台
  - DOMAIN-SUFFIX,justdancegame.com,游戏平台
  - DOMAIN,connect.cdn.ubisoft.com,游戏平台
  - DOMAIN,account.cdn.ubisoft.com,游戏平台
  - DOMAIN,public-ubiservices.ubi.com,游戏平台

  - DOMAIN-SUFFIX,epicgames.com,游戏平台
  - DOMAIN-SUFFIX,epicgames.dev,游戏平台
  - DOMAIN-SUFFIX,ea.com,游戏平台
  - DOMAIN-SUFFIX,origin.com,游戏平台
  - DOMAIN-SUFFIX,playstation.com,游戏平台
  - DOMAIN-SUFFIX,playstation.net,游戏平台
  - DOMAIN-SUFFIX,xboxlive.com,游戏平台
  - DOMAIN-SUFFIX,xbox.com,游戏平台
  - DOMAIN-SUFFIX,battle.net,游戏平台
  - DOMAIN-SUFFIX,blizzard.com,游戏平台
  - DOMAIN-SUFFIX,riotgames.com,游戏平台
  - DOMAIN-SUFFIX,riotcdn.net,游戏平台
  - DOMAIN-SUFFIX,rockstargames.com,游戏平台
  - DOMAIN-SUFFIX,hoyoverse.com,游戏平台
  - DOMAIN-SUFFIX,hoyolab.com,游戏平台
```

要点：

- `sugon.com/cn`、`hygon.com/cn`、`rogon.com/cn` 用域名后缀直连，Clash/mihomo 普通域名规则不匹配 URL path。
- Steam 下载/CDN 走 `Steam下载直连`，不吃代理流量；Steam 商店、社区、登录走 `Steam平台`。
- Switch/Nintendo 单独走 `Switch服务`，国内 Switch 域名走 `Switch直连`。
- Ubisoft/Just Dance 和主流游戏平台走 `游戏平台`。
