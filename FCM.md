# FCM hosts 自动同步

`config.ini` 和 `no_rate_config.ini` 共用 `clash-base.yml`，通过顶层
`hosts` 和 `dns.use-hosts: true` 使用上游优选 IP。`no_dns_override.ini`
和 `no_dns_override_no_rate.ini` 继续使用转换后端的默认基础模板，不接入 FCM hosts。

## 数据流

1. `scripts/sync_fcm_hosts.py` 下载
   `https://raw.githubusercontent.com/cagedbird043/fcm-hosts-next/main/fcm_dual.hosts`。
2. 保留一份原始文件到本仓库的 `fcm_dual.hosts`，将同一域名的 IPv4/IPv6
   合并为 IP 列表，只更新 `clash-base.yml` 中两个 FCM 标记之间的内容。
3. GitHub Actions 将变更提交到 `codex`；转换后端下次获取基础模板时使用新 IP。
4. 在客户端重新更新订阅，使新 hosts 进入实际使用的 Clash 配置。转换后端
   如果缓存基础模板，需等待缓存过期或刷新后端缓存。

下载失败、IP 格式错误、出现非 FCM 域名或缺少 `mtalk.google.com` 时，
脚本会失败，工作流不会提交变更，仓库继续提供上一份成功数据。

## 部署一次

1. 将本次修改和新增文件推送到 `codex` 分支。
2. 将同一份 `.github/workflows/sync-fcm-hosts.yml` 也添加到默认分支 `main`。
   `main` 只需要这一个工作流文件；执行时它会检出 `codex`，运行该分支的脚本。
   GitHub 定时事件只在默认分支触发，工作流只放在 `codex` 不会定时运行。
3. 在仓库 Actions 页面启用工作流，手动执行一次 `Sync FCM hosts`。
   工作流请求 `contents: write`；如写入被仓库策略或分支保护阻止，需允许
   GitHub Actions 向 `codex` 写入这两个生成文件。

默认每 6 小时同步一次，计划时间为北京时间 03:37、09:37、15:37、21:37，
GitHub 实际触发时间可能延迟。电脑无需保持开机，也不需要额外配置 PAT。

## 使用边界

- 此配置采用 Mihomo / Clash Meta 的 hosts IP 列表格式。
- 上游双栈地址均保留，不修改现有 IPv6 开关。Hosts 是显式映射，不能仅凭
  `dns.ipv6: false` 假定 hosts 中的 IPv6 会被忽略。若设备 IPv6 不可用，
  可将脚本 `SOURCE` 的文件名改为 `fcm_ipv4.hosts` 后重新同步。
  实际 IPv6 连接还取决于客户端设置和本地网络可用性。
- 原有 `fake-ip-filter` 已包含 `+.google.com`，FCM 域名属于该范围。
- `📢 谷歌FCM` 策略组的默认选项仍为 `DIRECT`。Hosts 只控制域名映射，
  不会改变该策略组的路由选择。
- 上游是在其测试机器上优选 IP；本地网络的实际可达性可能不同。
- 不要手工改动自动生成区域；其他自定义 hosts 可放在该区域之外。

本地手动刷新可执行 `python scripts/sync_fcm_hosts.py`，只依赖 Python 标准库。
