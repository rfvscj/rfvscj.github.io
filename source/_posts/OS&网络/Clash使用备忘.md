---
title: Clash 使用备忘
date: 2026-05-02 00:00:00
updated:
categories:
  - OS&网络
tags:
  - Clash
  - OpenClash
  - Switch
  - DNS
index_img: /img/bg0.png
excerpt: 记录 OpenClash、Clash Verge Rev、Sparkle 的少量必要配置：fake-ip 例外、GitHub SSH、Switch/Just Dance 加速和后续覆写维护。
published: true
---

这篇只记录我真正需要长期保留的 Clash 使用备忘。工具主要是路由器上的 OpenClash、本地的 Clash Verge Rev，以及移动端的 Sparkle。重点不是收集一堆规则，而是把几个容易忘、出问题时又很难定位的点固定下来。

## 基本原则

Clash 配置不要越写越大。优先把问题拆成三层：

- DNS 层：`fake-ip`、`fake-ip-filter`、上游 DNS、是否污染
- 路由层：域名规则、规则顺序、策略组选择
- 网络层：UDP、NAT、TUN、路由器是否支持端口映射

如果一个问题能通过连接日志定位到具体域名，就不要直接引入一个超大的规则集。大规则集看起来省事，但出错时很难知道是哪一条规则影响了结果。

## fake-ip-filter 不是垃圾桶

`fake-ip` 模式会给域名返回一段虚拟地址，再由 Clash 内部维护域名和真实连接之间的映射。这个模式对减少 DNS 泄漏、提高规则命中很有用，但某些服务不适合拿到 fake IP。

`fake-ip-filter` 的用途是：让这些域名走真实 DNS 解析，而不是拿 Clash 分配的虚拟地址。它应该只放确实需要真实解析的域名，不要把所有不稳定的网站都塞进去。

一个相对稳的基础块：

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
```

说明：

- 局域网域名必须尽量保持真实解析，否则路由器、NAS、打印机、HomeLab 服务容易变得不可达。
- NTP、系统联网检测这类东西不建议乱代理，保持真实解析和直连更少出怪问题。
- 新增例外时要写清原因，不要把 `fake-ip-filter` 当“疑难杂症收纳箱”。

## GitHub SSH 需要单独照顾

最近踩到的点是：GitHub 的 HTTPS 能正常打开，不代表 SSH 就一定正常。`git@github.com:xxx/yyy.git` 走的是 SSH，常见端口是 22；如果配置了 `ssh.github.com`，也可能走 443。

在 fake-ip 模式下，我更倾向把 GitHub SSH 相关域名加入 `fake-ip-filter`，让 SSH 连接拿到真实地址：

```yaml
dns:
  fake-ip-filter:
    - '+.github.com'
    - 'github.com'
    - 'ssh.github.com'
```

路由规则里再给 GitHub 一个明确策略组，避免 SSH 连接被最后的 `MATCH` 带偏：

```yaml
rules:
  - DOMAIN,github.com,PROXY
  - DOMAIN,ssh.github.com,PROXY
  - DOMAIN-SUFFIX,github.com,PROXY
  - DOMAIN-SUFFIX,githubusercontent.com,PROXY
  - DOMAIN-SUFFIX,githubassets.com,PROXY
```

如果公司、学校或运营商环境封 22，可以在 `~/.ssh/config` 里让 GitHub SSH 走 443：

```sshconfig
Host github.com
  HostName ssh.github.com
  User git
  Port 443
```

这不是 Clash 的配置，但它经常和 Clash 问题混在一起。判断方法很简单：

```bash
ssh -T git@github.com
ssh -T -p 443 git@ssh.github.com
```

哪个通，问题就在哪一层。

## OpenClash 放在路由器上时

路由器上的 OpenClash 适合给 Switch、电视、手机这类“不方便单独设置代理”的设备兜底。要注意三点：

- DNS 劫持和 DHCP 下发要一致，不要让设备一会儿问路由器，一会儿问运营商 DNS。
- 规则模式下，局域网、私有地址、路由器管理域名必须放在靠前的 `DIRECT`。
- 需要 UDP 的场景要确认节点和代理模式都支持 UDP，否则游戏加速看起来命中了规则，实际体验还是坏的。

建议长期保留的直连规则：

```yaml
rules:
  - IP-CIDR,10.0.0.0/8,DIRECT,no-resolve
  - IP-CIDR,172.16.0.0/12,DIRECT,no-resolve
  - IP-CIDR,192.168.0.0/16,DIRECT,no-resolve
  - IP-CIDR,127.0.0.0/8,DIRECT,no-resolve
  - DOMAIN-SUFFIX,lan,DIRECT
  - DOMAIN-SUFFIX,local,DIRECT
```

## Clash Verge Rev 和 Sparkle

本地客户端的重点不是复制路由器配置，而是承担两类工作：

- 调试：看连接日志，确认域名、策略组、DNS 结果是否符合预期。
- 临时覆写：把某个问题先在本地验证，再决定要不要同步到 OpenClash。

Clash Verge Rev 更适合做连接日志和覆写验证；Sparkle 更适合保留一套干净的移动端配置。不要让移动端配置变成所有实验规则的最终归宿。

## Switch 港服/日服加速

Switch 的问题要分清两类：商店/下载，和联机对战。

商店、账号、下载主要是 HTTPS 和 CDN 问题，规则能解决一部分。联机对战更依赖 UDP、NAT 类型、运营商网络和对端网络，Clash 规则只能解决路径问题，不能把一个不支持 UDP 或 NAT 很差的网络变成理想网络。

Nintendo 官方给出的 NAT 排查思路里，重点是测试 NAT 类型、避免双重 NAT，必要时给 Switch 固定 IP 并做 UDP 端口转发。日本任天堂的说明里提到，遇到错误时可将 Switch 的固定 IP 转发 `UDP 1024-65535`，且不需要 TCP 端口转发。这个配置安全面比较大，只适合给 Switch 单独固定 IP 后使用，不要对整个内网开放。

我这里先保留最小 Clash 规则，不收集过期域名清单。Switch 游戏统一走一个 `GAME` 策略组，Nintendo 自家服务和 Ubisoft/Just Dance 都放这里，节点选择时也少一个心智负担：

```yaml
proxy-groups:
  - name: GAME
    type: select
    proxies:
      - 香港节点
      - 日本节点
      - PROXY
      - DIRECT

rules:
  - DOMAIN-SUFFIX,nintendo.com,GAME
  - DOMAIN-SUFFIX,nintendo.net,GAME
  - DOMAIN-SUFFIX,nintendowifi.net,GAME
  - DOMAIN-SUFFIX,nintendoswitch.cn,DIRECT
```

港服和日服的选择：

- 港服商店和账号服务，先试香港节点；如果下载慢，再看连接日志里 CDN 实际命中的域名和节点表现。
- 日服商店和联机，先试日本节点；联机对战要重点看 UDP 是否可用、NAT 类型是否改善。
- 如果只是在国内网络下载系统更新或游戏更新，不要默认全走代理；Nintendo 的 CDN 可能直连更快。

Switch 连接方式上，路由器 OpenClash 比电脑热点更稳定。电脑热点能用来临时验证节点和规则，但长期玩联机时，路由器上直接处理 DNS、UDP 和 NAT 更容易排查。

## Just Dance 2026 和 Ubisoft 服务

`Just Dance 2026` 这类新版本已经不是“卡带里有完整游戏，偶尔联网”的模式。Ubisoft 自己的 FAQ 对 2024 版已经说得很直白：Switch 上想获得完整体验需要联网，访问全部歌曲也需要联网；离线最多下载基础游戏内的一部分歌曲，Just Dance+ 曲库不能下载，必须在线访问。

所以这里要把三类流量分开看：

- Nintendo eShop 下载游戏本体：优先看前面的 Nintendo 规则。
- Ubisoft Connect 登录、账号、权益、状态：走 Ubisoft 规则。
- Just Dance 曲库、活动、素材、歌曲流：走 Ubisoft/Just Dance CDN 规则。

这部分也归进上面的 `GAME` 策略组：

```yaml
rules:
  - DOMAIN-SUFFIX,ubisoft.com,GAME
  - DOMAIN-SUFFIX,ubi.com,GAME
  - DOMAIN-SUFFIX,ubisoftconnect.com,GAME
  - DOMAIN-SUFFIX,justdancegame.com,GAME
  - DOMAIN-SUFFIX,ubistatic-a.akamaihd.net,GAME
  - DOMAIN-SUFFIX,ubistatic2-a.akamaihd.net,GAME
  - DOMAIN-SUFFIX,staticctf.akamaized.net,GAME
```

如果连接日志里能看到更具体的主机名，再追加精确规则，而不是扩大到所有 Akamai：

```yaml
rules:
  - DOMAIN,connect.cdn.ubisoft.com,GAME
  - DOMAIN,account.cdn.ubisoft.com,GAME
  - DOMAIN,public-ubiservices.ubi.com,GAME
```

不要轻易写 `DOMAIN-SUFFIX,akamaized.net,GAME` 或 `DOMAIN-SUFFIX,akamaihd.net,GAME`。这两个后缀太大，会把大量无关 CDN 一起带走，下载速度和排错都会变差。只有在连接日志确认 Just Dance 某个歌曲资源落在具体 Akamai 主机名上时，再加那一条具体主机或更窄的后缀。

Just Dance 排查顺序：

1. 先确认 Switch 系统网络测试正常，NAT 至少不是很差的类型。
2. 打开 OpenClash 连接日志，启动 Just Dance，停在“连接 Ubisoft”或下载歌曲的位置。
3. 把命中的 `ubisoft.com`、`ubi.com`、`justdancegame.com`、具体 CDN 主机名放进 `GAME`。
4. 优先测试香港节点和日本节点。如果某个节点 HTTPS 能连但歌曲加载卡住，换一个支持 UDP 且晚高峰不拥塞的节点。
5. 如果多条线路都卡在同一个 Ubisoft 错误码，先查服务端状态或等一段时间；这时继续堆规则通常没有收益。

## 我常用覆写配置

后续把稳定覆写补在这里。每一段覆写只保留三类信息：

- 解决什么问题
- 具体 YAML
- 验证方式

先不要把订阅转换器、规则集、客户端自动生成的大段配置原样贴进来。真正有价值的是“为什么加这几行”和“怎么确认它还有效”。

## 参考

- [Mihomo DNS 配置文档](https://wiki.metacubex.one/en/config/dns/)
- [OpenClash 配置文件说明](https://github.com/vernesong/OpenClash/wiki/%E9%85%8D%E7%BD%AE%E6%96%87%E4%BB%B6)
- [任天堂香港 Switch 网络连接说明](https://www.nintendo.com.hk/switch/support/internet/index.html)
- [任天堂日本 Switch 端口开放说明](https://support-jp.nintendo.com/app/answers/detail/a_id/36082)
- [Nintendo Switch Brew: Network](https://switchbrew.org/wiki/Network)
- [Just Dance 2024 FAQ](https://www.ubisoft.com/fr-ca/game/just-dance/2024/frequently-asked-questions)
- [Ubisoft Connect](https://www.ubisoft.com/en-us/ubisoft-connect/)
