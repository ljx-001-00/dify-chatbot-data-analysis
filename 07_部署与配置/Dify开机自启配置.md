# Dify 开机自启配置（openEuler 22.03）

> 目标：虚拟机重启后，Docker → 11 个 Dify 容器 → 端口映射，全部自动恢复，不需要人工敲命令。
> 适用：node2（192.168.1.10），Dify 1.8.0 位于 `/usr/local/dify`。

## 原理：三层保障

| 层 | 负责什么 | 失败后果 |
|---|---|---|
| `docker.service` | 开机拉起 Docker 守护进程 | 所有容器消失 |
| 容器 `restart: always` | Docker 起来后自动拉起每个容器 | 容器不启动 |
| `dify.service`（本手册新增） | Docker 起来后再执行一次 `compose up -d` | 容器存在但不齐 |
| `fix-docker-nat.sh` | 修复 iptables 链丢失导致的端口不通 | 容器 Up 但 307 打不开 |

四层缺一层都可能出现"看起来起来了，但网页打不开"。

## 第 1 步：确认 Docker 开机自启

```bash
systemctl is-enabled docker
```

- 输出 `enabled` → 已开启，跳到第 2 步
- 输出 `disabled` → 执行：

```bash
systemctl enable docker
systemctl start docker
```

再确认一次：

```bash
systemctl is-active docker      # 期望：active
systemctl is-enabled docker     # 期望：enabled
```

## 第 2 步：确认容器的 restart 策略

Dify 官方 compose 默认给了 `restart: always`，先确认：

```bash
cd /usr/local/dify/docker
grep -c "restart: always" docker-compose.yaml
```

期望输出 ≥ 8。

如果数量偏少，用 override 补齐（不影响原有配置）。编辑已有的 override 文件：

```bash
vi docker-compose.override.yaml
```

在每个服务下补 `restart: always`，例如：

```yaml
services:
  api:
    restart: always
  worker:
    restart: always
  worker_beat:
    restart: always
  web:
    restart: always
  db:
    restart: always
  redis:
    restart: always
  weaviate:
    restart: always
  sandbox:
    restart: always
  plugin_daemon:
    restart: always
  ssrf_proxy:
    restart: always
  nginx:
    restart: always
```

保存后让配置生效：

```bash
docker compose up -d
```

## 第 3 步：创建 dify.service

先确认 compose 命令的确切路径（Dify 1.8 用 v2 插件，但也可能装了 v1）：

```bash
which docker-compose || echo "无 v1"
docker compose version
```

创建服务文件：

```bash
vi /etc/systemd/system/dify.service
```

**情况 A：用 `docker compose`（v2 插件，推荐）**

```ini
[Unit]
Description=Dify - docker compose up
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/usr/local/dify/docker
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

**情况 B：只有 `docker-compose`（v1）**

把 ExecStart / ExecStop 两行换成：

```ini
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
```

> ⚠️ systemd 的 PATH 很短，**必须写绝对路径**，不能只写 `docker compose`。
> 查 docker 路径：`which docker`（通常是 `/usr/bin/docker`）。

## 第 4 步：启用服务

```bash
systemctl daemon-reload
systemctl enable dify.service
systemctl is-enabled dify.service      # 期望：enabled
```

**不要现在 start**，容器已经在跑，直接 `start` 会重复执行一次 `up -d`（无害，但没必要）。

## 第 5 步：加上 iptables 自愈（你踩过的坑）

你之前遇到过"容器全部 Up、`docker port` 也显示映射了，但宿主机 curl 307 打不开"——那是 firewalld 把 Docker 的链删了。

如果还没有这个脚本，建一个：

```bash
vi /usr/local/bin/fix-docker-nat.sh
```

```bash
#!/bin/bash
# 检测 Docker 的 iptables 链是否缺失，缺失则重启 docker 重建
if ! iptables -t nat -L DOCKER-ISOLATION-STAGE-1 -n >/dev/null 2>&1; then
    echo "$(date '+%F %T') DOCKER chain missing, restart docker" >> /var/log/fix-docker-nat.log
    systemctl restart docker
    sleep 20
fi
```

赋权：

```bash
chmod +x /usr/local/bin/fix-docker-nat.sh
```

然后在 dify.service 的 `[Service]` 段加一行（放在 ExecStart 之前）：

```ini
ExecStartPre=/usr/local/bin/fix-docker-nat.sh
```

改完记得 `systemctl daemon-reload`。

## 第 6 步：确认 firewalld 不再捣乱

你之前已经 `disable --now firewalld` 了，确认它不会开机回来：

```bash
systemctl is-enabled firewalld      # 期望：disabled
systemctl is-active firewalld       # 期望：inactive
```

如果是 `enabled`：

```bash
systemctl disable --now firewalld
```

端口放行继续用 iptables 持久化（80 / 3306 / 9997 / 8095），或者干脆依赖 firewalld 关闭后的默认放行。

## 第 7 步：Xinference 也要自启

Xinference 是独立容器，之前启动时带了 `--restart unless-stopped`，确认一下：

```bash
docker inspect xinference_container --format '{{.HostConfig.RestartPolicy.Name}}'
```

期望输出 `unless-stopped` 或 `always`。

如果是 `no`，两种补救方式：

**方式一（推荐，不动容器）：**

```bash
docker update --restart unless-stopped xinference_container
```

**方式二（重建）：** 沿用之前的 `docker run` 命令，把 `--restart unless-stopped` 加回去。

## 第 8 步：验证

不重启也能验证大部分环节：

```bash
# 1. 服务状态
systemctl is-enabled docker dify
systemctl is-active docker

# 2. 容器数量（应为 12：11 个 Dify + 1 个 Xinference）
docker ps --format '{{.Names}}' | wc -l

# 3. 端口映射
docker port docker-nginx-1

# 4. 实际访问（307 是正常的重定向到 /apps）
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/
curl -s -o /dev/null -w '%{http_code}\n' http://192.168.1.10/

# 5. Xinference
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:9997/v1/models
```

全部符合预期后，**真正重启一次**才叫验证完成：

```bash
reboot
```

等 2~3 分钟（Xinference 冷启动就要 60 秒左右），然后在 Windows 上：

```powershell
curl.exe -s -o NUL -w "%{http_code}`n" http://192.168.1.10/
curl.exe -s -o NUL -w "%{http_code}`n" http://192.168.1.10:9997/v1/models
```

都返回 200/307 就成功了。

## 第 9 步（可选）：开机自动加载 Xinference 模型

Xinference 容器起来后**不会自动加载任何模型**，`/v1/models` 会返回空列表。如果演示需要本地模型（Cherry Studio 对比、离线兜底），必须手动 POST 一次，或者用下面的脚本自动完成。

**先确认加载参数文件存在**（之前手动加载时用过的那份）：

```bash
ls -l /root/qwen.json
cat /root/qwen.json
```

如果没了，重新建一份：

```bash
cat > /root/qwen.json <<'EOF'
{
  "model_name": "qwen2.5-instruct",
  "model_engine": "llama.cpp",
  "model_format": "ggufv2",
  "model_size_in_billions": "1_5",
  "quantization": "q4_k_m",
  "model_path": "/data/models/qwen2.5-1.5b-instruct-q4_k_m.gguf",
  "model_uid": "qwen2.5-instruct",
  "n_gpu": "auto",
  "n_ctx": 4096,
  "n_threads": 8,
  "n_threads_batch": 8
}
EOF
```

**建预热脚本**：

```bash
vi /usr/local/bin/xinference-warmup.sh
```

```bash
#!/bin/bash
# 等 9997 就绪（最多 5 分钟，Xinference 冷启动约 60 秒）
for i in $(seq 1 60); do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:9997/v1/models)
    [ "$code" = "200" ] && break
    sleep 5
done

# 已经加载过就不重复加载
if curl -s http://127.0.0.1:9997/v1/models | grep -q 'qwen2.5-instruct'; then
    echo "$(date '+%F %T') model already loaded" >> /var/log/xinference-warmup.log
    exit 0
fi

# 加载模型（后台执行，加载要 60 秒左右）
curl -s -X POST http://127.0.0.1:9997/v1/models \
     -H 'Content-Type: application/json' \
     -d @/root/qwen.json >> /var/log/xinference-warmup.log 2>&1
```

```bash
chmod +x /usr/local/bin/xinference-warmup.sh
```

**建服务单元**：

```bash
vi /etc/systemd/system/xinference-warmup.service
```

```ini
[Unit]
Description=Xinference model warmup
After=docker.service dify.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/xinference-warmup.sh
TimeoutStartSec=600

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable xinference-warmup.service
```

> 注意：`Type=oneshot` 会阻塞后续 unit 直到脚本返回。脚本里等待最多 5 分钟 + 加载请求立即返回（加载是异步的），所以实际阻塞约 1~5 分钟。如果不想阻塞开机，把 `Type=oneshot` 改成 `Type=forking` 或在脚本末尾加 `&`。

**如果演示只用云端模型**（现在的 DeepSeek-V4.1-Flash），这一步可以跳过——`/v1/models` 返回空列表是正常的，不影响 Dify 工作流。

## 排错对照表

| 现象 | 原因 | 处理 |
|---|---|---|
| 重启后 `docker ps` 空 | docker.service 没 enable | `systemctl enable docker` |
| 只有部分容器起来 | compose 缺 restart 策略 | 补 override 后 `up -d` |
| 容器 Up 但 307 打不开 | iptables 链被删 | 跑 `fix-docker-nat.sh` |
| `docker compose` 报 command not found | systemd PATH 太短 | ExecStart 写绝对路径 |
| dify.service 启动失败 | 工作目录或 compose 文件路径写错 | `journalctl -u dify -n 50` 看日志 |
| Xinference 起不来 | 内存不足（<8G 会 OOM） | 检查 `free -h`，先停 Dify 再起 |
| 网页 502 | plugin_daemon 还没起来 | 等 1~2 分钟，或 `docker compose restart plugin_daemon` |

## 一句话总结

```bash
systemctl enable docker
systemctl enable dify.service
docker update --restart unless-stopped xinference_container
systemctl disable --now firewalld
```

四条命令，重启无忧。
