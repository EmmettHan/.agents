# hdc 常用命令参考

hdc（OpenHarmony Device Connector）是 OpenHarmony 设备连接调试命令行工具。

## 架构

- **hdc client**：运行于开发机，执行用户命令
- **hdc server**：开发机后台进程，管理 client 与 daemon 间通信
- **hdc daemon**：设备端守护进程，处理 client 请求

## 在 WSL 中使用 hdc

hdc 通常安装在 Windows 侧。WSL 可通过 interop 直接调用 `hdc.exe`：

```bash
hdc.exe list targets
hdc.exe shell "command"
hdc.exe file send ./local.txt /data/local/tmp/remote.txt
```

## 常用命令

### 设备管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `list targets [-v]` | 显示已连接设备列表，`-v` 显示详细信息 | `hdc list targets` |
| `tconn host[:port]` | 通过 TCP 连接设备 | `hdc tconn 192.168.0.100:10178` |
| `tmode usb` | 切换为 USB 连接模式 | `hdc tmode usb` |
| `tmode port <port>` | 切换为 TCP 连接模式 | `hdc tmode port 10178` |
| `target mount` | 以读写模式挂载 /vendor、/data 等分区 | `hdc target mount` |
| `target boot` | 重启设备 | `hdc target boot` |

### 文件传输

| 命令 | 说明 | 示例 |
|------|------|------|
| `file send <local> <remote>` | 推送文件到设备 | `hdc file send ./a.txt /data/local/tmp/a.txt` |
| `file recv [-a] <remote> <local>` | 从设备拉取文件 | `hdc file recv /data/local/tmp/a.txt ./a.txt` |

### 端口转发

| 命令 | 说明 | 示例 |
|------|------|------|
| `fport <local> <remote>` | 主机端口转发到设备端口 | `hdc fport tcp:1234 tcp:1080` |
| `rport <remote> <local>` | 设备端口转发到主机端口 | `hdc rport tcp:1234 tcp:1080` |
| `fport ls` | 列出所有转发任务 | `hdc fport ls` |
| `fport rm <local> <remote>` | 删除转发任务 | `hdc fport rm tcp:1234 tcp:1080` |

### 应用管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `install [-r/-s/-g] <package>` | 安装 OpenHarmony 应用 | `hdc install app.hap` |
| `uninstall [-k/-s] <package>` | 卸载应用 | `hdc uninstall com.example.app` |

### 调试

| 命令 | 说明 | 示例 |
|------|------|------|
| `shell [command]` | 远程执行命令或进入交互式 shell | `hdc shell "ls /data"` |
| `hilog` | 查看设备日志 | `hdc hilog` |
| `jpid` | 获取 JDWP 调试进程列表 | `hdc jpid` |

### 服务管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `kill [-r]` | 终止 hdc 服务，`-r` 触发重启 | `hdc kill` |
| `start [-r]` | 启动 hdc 服务，`-r` 触发重启 | `hdc start` |
| `checkserver` | 获取 client-server 版本 | `hdc checkserver` |
| `smode [-r]` | 授予后台服务 root 权限，`-r` 取消 | `hdc smode` |

### 全局选项

| 选项 | 说明 | 示例 |
|------|------|------|
| `-t <key>` | 指定目标设备 ID | `hdc -t <id> shell` |
| `-s <socket>` | 指定服务监听 socket | `hdc -s ip:port` |
| `-l 0-5` | 指定日志等级 | `hdc -l5 start` |
| `-h / --help` | 帮助信息 | `hdc -h` |
| `-v / --version` | 版本信息 | `hdc -v` |

## Linux USB 权限

非 root 用户下 hdc 可能找不到设备，解决方法：

```bash
# 方法 1：临时开放（有安全风险）
sudo chmod -R 777 /dev/bus/usb/

# 方法 2：永久修改 udev 规则
# 先用 lsusb 查找设备 vendorID 和 productID
sudo vim /etc/udev/rules.d/90-myusb.rules
# 添加：SUBSYSTEMS=="usb", ATTRS{idVendor}=="xxxx", ATTRS{idProduct}=="xxxx", GROUP="users", MODE="0666"
sudo udevadm control --reload
```
