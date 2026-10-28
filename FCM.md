# FCM 解析方案

当前方案：`config.ini` 和 `no_rate_config.ini` 共用的 `clash-base.yml` 里，
用 `dns.nameserver-policy` 把 12 个 FCM 域名单独指向自建静态 DoH
`https://fcm-static-doh.jwcc.workers.dev/dns-query`。其他域名仍走原有的
`nameserver` / `nameserver-policy` / `fallback` / `direct-nameserver` 逻辑，
不受影响。`no_dns_override.ini` 和 `no_dns_override_no_rate.ini` 使用转换后端
默认模板，保持原样。

## 为什么不用 hosts

hosts 需要定时同步上游优选 IP，链路长（上游 → Actions → 仓库 → 转换后端
缓存 → 客户端），而且要等订阅更新才生效。静态 DoH 直接在 DNS 层返回固定结果，
客户端更新一次订阅后即生效，之后无需任何同步。`fcm_dual.hosts` 文件和
`scripts/sync_fcm_hosts.py` 仍然保留，只是 `clash-base.yml` 里的 hosts 块
已经整块注释掉，便于随时切回。

## 切回 hosts 方式

1. 打开 `clash-base.yml`，在 `hosts:` 下找到
   `# BEGIN AUTO FCM HOSTS (commented out)` 到
   `# END AUTO FCM HOSTS (commented out)` 之间的块，去掉每行前面的 `  # `，
   并把两行标记里的 ` (commented out)` 删掉，恢复成
   `  # BEGIN AUTO FCM HOSTS` / `  # END AUTO FCM HOSTS`。
2. 删除 `dns.nameserver-policy` 下那 12 条 `*-mtalk.google.com` /
   `mtalk.google.com` 之类的 FCM 条目（保留 `"geosite:cn"` 及其他条目）。
3. `scripts/sync_fcm_hosts.py` 中的 `BEGIN` / `END` / `LINE` 三个常量需要改回
   非注释形态（`BEGIN = "  # BEGIN AUTO FCM HOSTS"`、`END = "  # END AUTO FCM HOSTS"`、
   去掉 `LINE` 前缀），否则工作流只会改写注释块。
4. 重新更新订阅。

## 自动同步（仅在 hosts 方式启用时需要）

1. `scripts/sync_fcm_hosts.py` 下载
   `https://raw.githubusercontent.com/cagedbird043/fcm-hosts-next/main/fcm_dual.hosts`，
   把同一域名的 IPv4/IPv6 合并成 IP 列表，只更新两个标记之间的内容。
2. `.github/workflows/sync-fcm-hosts.yml` 每 6 小时（北京时间 03:37、09:37、
   15:37、21:37）运行一次，把结果提交到 `codex` 分支，并同步更新
   `fcm_dual.hosts` 镜像文件。
3. 定时事件只在默认分支 `main` 触发，因此 `main` 上也需要这一份工作流；
   工作流执行时检出 `codex`，运行该分支的脚本。

下载失败、IP 格式错误、出现非 FCM 域名或缺少 `mtalk.google.com` 时脚本会失败，
工作流不提交变更，仓库继续保留上一份成功数据。

## 注意事项

- `nameserver-policy` 的键是精确域名匹配；FCM 客户端只会请求这些固定域名，
  所以不需要通配符。若上游新增域名，需要同时补充到这里。
- 自建 DoH 只返回静态结果，不支持 DoH POST（只接受 GET），Mihomo 默认使用
  GET，无需额外配置。
- 原有 `fake-ip-filter` 已包含 `+.google.com`，FCM 域名属于该范围。
- `📢 谷歌FCM` 策略组的默认选项仍为 `DIRECT`；DNS 与策略组互不影响。
- 该 DoH 本身也可能单点故障；出现问题时删除对应 policy 条目即可回到
  `nameserver` 正常解析。