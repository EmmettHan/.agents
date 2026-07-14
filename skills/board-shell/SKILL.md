---
name: board-shell
description: Execute commands and drive interactive programs on OpenHarmony development boards via SSH or hdc. Use this skill whenever the user wants to run commands on a development board, debug board-side programs, interact with tools like softbus_tool, automate board tasks, control a Windows-USB-connected board from an LXC/remote Linux server through ssh board-win and Windows hdc, or mentions hdc shell, 开发板, board shell, reverse SSH tunnel, or connected device control. Supports LXC/Linux controllers, Windows PowerShell, WSL, and Git Bash.
---

# Board Shell

Execute commands and drive interactive programs on OpenHarmony development boards via SSH with PTY support.

## First Pick the Control Topology

Do not assume a fixed `Host board`, fixed local port, or fixed device. Pick the topology from live evidence.

### Topology A: LXC/Linux controls a Windows USB board

Use this when the Linux/LXC host can SSH into Windows through a reverse tunnel, usually with:

```sshconfig
Host board-win
    HostName 127.0.0.1
    Port 2222
    User kaihong
```

In this topology, Windows owns USB and `hdc.exe`; Linux only orchestrates commands through SSH.

Validate the chain first:

```bash
ssh board-win "hostname && where hdc && hdc list targets"
```

Choose the device ID from `hdc list targets`:

- If exactly one target is listed, use it.
- If multiple targets are listed, do not guess. Ask for the intended device ID unless the user already supplied one.
- Do not bind the skill to a long-lived `board` alias or a fixed `12224`/`2224` forwarding port.

Run normal board commands through Windows hdc:

```bash
ssh board-win "hdc -t <device-id> shell \"echo ok; uname -a; id\""
```

Restart board sshd after reboot:

```bash
ssh board-win "hdc -t <device-id> shell \"/bin/sshd -p 2223\""
```

Use `hdc` directly for non-interactive work. Only create `fport` when SSH/PTTY is needed for interactive programs.

**CRITICAL: fport is session-scoped.** `hdc fport` lives only inside the Windows cmd session that created it. The moment that cmd exits, the forward dies. You MUST create fport and use it in the same `cmd /c "..."` one-liner — never split across two `ssh board-win` calls.

For temporary SSH/PTTY access through Windows, use this single-chain pattern:

```bash
# Create fport AND use it in one shot (both survive inside the same cmd /c):
ssh board-win "cmd /c \"hdc -t <device-id> fport tcp:<windows-port> tcp:2223 && ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -i C:\\Users\\kaihong\\.ssh\\agent_key -p <windows-port> root@127.0.0.1 <command>\""

# With PTY for interactive programs:
ssh board-win "cmd /c \"hdc -t <device-id> fport tcp:<windows-port> tcp:2223 && ssh -tt -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -i C:\\Users\\kaihong\\.ssh\\agent_key -p <windows-port> root@127.0.0.1 <interactive-command>\""
```

Key details of this pattern:
- `cmd /c "..."` wraps the whole fport+ssh chain so both commands share the same Windows session.
- fport connects to Windows `127.0.0.1:<windows-port>`, which hdc forwards to the device's `2223`.
- The SSH key path uses Windows-style backslashes: `C:\\Users\\kaihong\\.ssh\\agent_key`. Each `\` is escaped for the LXC bash → Windows cmd layer.
- Use a free Windows-side port such as `12224`, `12225`, etc. Treat this as temporary plumbing, not identity. The device identity is the hdc device ID.
- **Do NOT use `ProxyCommand`** (e.g. `ssh board-win -W 127.0.0.1:<port>`). It fails with "kex_exchange_identification: Connection closed by remote host" because the SSH client's protocol exchange does not survive the double-hop. The two-hop pattern above works.

**Why not ProxyCommand?** The SSH key exchange happens between the LXC SSH client and the device's sshd. When using ProxyCommand, the client sends its version string through Windows → fport → device, but the response path breaks because the SSH protocol requires a direct bidirectional stream. The `ssh board-win "cmd /c \"fport && ssh...\""` pattern keeps the SSH client on Windows, where fport is local.

## Why SSH instead of hdc

`hdc shell` does not allocate a PTY (pseudo-terminal). Interactive programs that call `isatty()` on stdin will detect a non-terminal environment and may behave incorrectly or refuse to work. SSH with `-tt` forces PTY allocation, making programs believe they run in a real terminal.

## hdc Reference

When the user needs hdc commands beyond what's covered here (file transfer, port forwarding, app install, etc.), read `references/hdc.md` for the full command reference.

In WSL, call Windows hdc as `hdc.exe` — interop handles the bridge. Example: `hdc.exe shell "echo ok"`. From an LXC/Linux controller, call Windows hdc through `ssh board-win "hdc ..."`.

## Connection Methods

After checking Topology A, there are two local ways to reach a board. Use direct SSH when the board has network; fall back to hdc port forwarding when it doesn't.

### Method 1: Direct SSH (preferred)

Board has network (eth0/wlan0 with IP). Connect directly:

| Parameter | Value |
|-----------|-------|
| Host | Board's IP (e.g., `192.168.1.108`) |
| Port | `2223` |
| User | `root` |
| Auth | Public key (`agent_key`) |

```bash
ssh -i ~/.ssh/agent_key -p 2223 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@192.168.1.108 "command"
```

### Method 2: hdc port forwarding (no network)

Board has no network (eth0/wlan0 down). Use hdc USB tunnel. If hdc runs on Windows but the controller is LXC/Linux, prefix hdc commands with `ssh board-win "..."`.

```bash
# 1. Find device ID
hdc.exe list targets

# 2. Remount filesystem as read-write (if needed for setup)
hdc.exe -t <device-id> shell "mount -o rw,remount /"

# 3. Do initial setup (steps 1-5) if not done yet
# 4. Start sshd on board
hdc.exe -t <device-id> shell "/bin/sshd -p 2223"

# 5. Forward local port to board's sshd
hdc.exe -t <device-id> fport tcp:2224 tcp:2223

# 6. SSH through the tunnel
ssh -i ~/.ssh/agent_key -p 2224 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "command"
```

Use a different local port (2225, 2226...) for each additional board.

From LXC/Linux through Windows:

```bash
# Non-interactive commands: use hdc shell (no PTY needed)
ssh board-win "hdc -t <device-id> shell \"uname -a; free -m; ps -ef | head -20\""

# Single SSH command via fport (create fport + ssh in one cmd /c chain):
ssh board-win "cmd /c \"hdc -t <device-id> fport tcp:12224 tcp:2223 && ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -i C:\\Users\\kaihong\\.ssh\\agent_key -p 12224 root@127.0.0.1 'uname -a'\""

# SSH with PTY for interactive programs:
ssh board-win "cmd /c \"hdc -t <device-id> fport tcp:12224 tcp:2223 && ssh -tt -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -i C:\\Users\\kaihong\\.ssh\\agent_key -p 12224 root@127.0.0.1 'tty'\""

# Multiple commands on device (quoting: avoid ; $ ' — keep it simple):
ssh board-win "cmd /c \"hdc -t <device-id> fport tcp:12224 tcp:2223 && ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -i C:\\Users\\kaihong\\.ssh\\agent_key -p 12224 root@127.0.0.1 uname -a\""
```

### Which method to use

First, understand the network topology: can your controller reach the device's IP?

```bash
# From LXC/Linux controller, check device network:
ssh board-win "hdc -t <device-id> shell \"ip addr show eth0 | grep 'inet '\""
```

Then decide:

- **Controller on same network as device** (e.g., Windows laptop with USB, or same LAN): Has IP → Method 1 (direct SSH). No IP → Method 2 (hdc forwarding).
- **Controller is LXC/remote Linux** (Topology A): The LXC almost never has a route to the device's IP (192.168.x.x, 10.x.x.x). **Always use the `cmd /c` fport chain pattern** from the Topology A section, regardless of whether the device has an IP. The device IP is irrelevant when the controller can't reach it.

If unsure whether the controller can reach the device, test it:

```bash
# From the controller (not from Windows), try to reach the device's IP:
ping -c 1 -W 1 <device-ip> 2>&1 || echo "No route → use fport chain"
```

## Platform-Specific Commands

### Windows PowerShell

```powershell
# Single command
ssh -i $env:USERPROFILE\.ssh\agent_key -p 2223 -o StrictHostKeyChecking=no -o UserKnownHostsFile=$env:USERPROFILE\.ssh\known_hosts root@192.168.1.108 "command"

# Interactive shell
ssh -tt -i $env:USERPROFILE\.ssh\agent_key -p 2223 -o StrictHostKeyChecking=no -o UserKnownHostsFile=$env:USERPROFILE\.ssh\known_hosts root@192.168.1.108

# Drive interactive program (pipe input)
# IMPORTANT: softbus_tool menu items are zero-padded (08, not 8). Always include exit commands.
"0`n08`n34`n7`n" | ssh -tt -i $env:USERPROFILE\.ssh\agent_key -p 2223 -o StrictHostKeyChecking=no -o UserKnownHostsFile=$env:USERPROFILE\.ssh\known_hosts root@192.168.1.108 "/bin/softbus_tool"
```

Note: PowerShell uses `` `n `` for newline in strings, not `\n`.

### WSL / Git Bash

```bash
# --- Direct SSH (board has network) ---
ssh -i ~/.ssh/agent_key -p 2223 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@192.168.1.108 "command"

# --- hdc forwarding (board has no network) ---
# First: hdc.exe -t <id> shell "/bin/sshd -p 2223"
# Then:  hdc.exe -t <id> fport tcp:2224 tcp:2223
ssh -i ~/.ssh/agent_key -p 2224 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "command"

# --- Interactive shell (both methods, just change -p and host) ---
ssh -tt -i ~/.ssh/agent_key -p 2223 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@192.168.1.108

# --- Drive interactive program (pipe input, always wrap with timeout) ---
printf '0\n08\n34\n7\n' | timeout 10 ssh -tt -i ~/.ssh/agent_key -p 2223 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@192.168.1.108 "/bin/softbus_tool"
```

### Detecting the Platform

Check `uname` or the shell environment:

- **Running inside LXC/Linux** (uname = Linux): You're in bash. Board commands go through `ssh board-win "..."`. Use the `cmd /c` fport chain pattern — not WSL/PowerShell. All commands shown in this skill under "From LXC/Linux through Windows" apply.
- **Running inside Claude Code on Windows**: The shell is likely Git Bash (use WSL/Git Bash commands). `hdc.exe` is available directly via interop.
- **User explicitly says PowerShell**: Use the PowerShell variant.

## Three Usage Modes

### 1. Single Command

For non-interactive commands (ls, cat, ps, etc.):

```
ssh ... root@<ip> "command"
```

No `-tt` needed. Output is captured directly.

### 2. Interactive Shell

For a live shell session where the user types commands:

```
ssh -tt ... root@<ip>
```

The `-tt` flag allocates a PTY. The session stays open until the user types `exit`.

### 3. Driving Interactive Programs

For programs with menus, prompts, or sequential inputs (like `softbus_tool`):

```bash
printf 'input1\ninput2\n...\n' | ssh -tt ... root@<ip> "/path/to/program"
```

From LXC/Linux through Windows, use `echo` piped inside the `cmd /c` chain (Windows cmd has no `printf`):

```bash
ssh board-win "cmd /c \"hdc -t <device-id> fport tcp:<port> tcp:2223 && (echo input1 && echo input2 && echo exit) | ssh -tt -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -i C:\\Users\\kaihong\\.ssh\\agent_key -p <port> root@127.0.0.1 /bin/softbus_tool\""
```

Key points:
- Always use `-tt` for interactive programs
- Pipe the input sequence with newlines separating each input
- **From LXC: use `(echo a && echo b && echo c)` in Windows cmd**, not `printf` or `echo -e` (they don't exist in cmd)
- **Always wrap with `timeout`** (Unix) or set `ConnectTimeout` (Windows cmd `timeout` has different syntax and doesn't work the same way). Many embedded programs don't exit on stdin EOF — they loop forever waiting for input, leaving orphan processes on the device that accumulate and waste resources.
- Include exit commands in the input sequence (menu item for "exit" or "quit") so the program exits cleanly
- No delays needed between inputs (unlike the FIFO hack)
- **Quoting trap**: When driving interactive programs through `ssh board-win "cmd /c \"...\""`, every layer of quoting strips one level. Prefer simple commands without `;`, `$`, or nested quotes on the device side. If you need a complex command, test the simplest version first.

## Quoting: The Three-Shell Problem

When driving from LXC Linux through Windows to a device, commands pass through three shells:

```
LXC bash  →  Windows cmd  →  Device sh (Toybox)
```

Each layer strips one level of quoting. This creates two recurring failure modes:

**Failure 1: Command treated as filename.** When the device shell receives `echo hello; uname -a` as a single token, it looks for a file literally named `echo hello; uname -a` and fails with "inaccessible or not found".

**Failure 2: Premature interpretation.** `$VAR`, `;`, and `|` get consumed by the wrong shell before reaching the device.

**Working rules:**

| Device command complexity | Approach |
|---------------------------|----------|
| Single word, no special chars | Use directly: `ssh ... root@127.0.0.1 uname` |
| Simple args, no `;` `$` `'` | Wrap in single quotes: `ssh ... root@127.0.0.1 'uname -a'` |
| Multiple commands with `;` or `$` | Use `hdc shell` instead (single hdc call avoids the extra cmd layer): `ssh board-win "hdc -t <id> shell \"cmd1; cmd2\""` |
| Complex interactive driving | Build input on Windows side with `(echo ...)` chain, send to simple device command |

**Golden rule:** If the device command contains `;`, `$`, `|`, `'`, or `"`, ask yourself: "Can I do this via `hdc shell` instead?" If yes, do it — one less shell layer to fight.

## Initial Device Setup

Run these once via `hdc shell` when setting up a new device or after device factory reset:

```bash
# 1. Generate SSH host keys
hdc shell "ssh-keygen -A"

# 2. Fix root shell (default is /bin/false which blocks SSH login)
hdc shell "sed -i 's|root:x:0:0:::/bin/false|root:x:0:0::/root:/bin/sh|' /etc/passwd"

# 3. Set up authorized_keys
hdc shell "mkdir -p /.ssh && chmod 700 /.ssh"

# 4. Push public key (generate locally first if needed: ssh-keygen -t ed25519 -f ~/.ssh/agent_key -N "")
PUBKEY=$(cat ~/.ssh/agent_key.pub)
hdc shell "echo '$PUBKEY' > /.ssh/authorized_keys && chmod 600 /.ssh/authorized_keys"

# 5. Fix sshd authorized_keys path (ChrootDirectory=/ makes relative paths fail)
hdc shell "sed -i 's|AuthorizedKeysFile\t.ssh/authorized_keys|AuthorizedKeysFile\t/.ssh/authorized_keys|' /etc/sshd_config"

# 6. Start sshd
hdc shell "/bin/sshd -p 2223"
```

After device reboot, only step 6 needs to be repeated. The rest persists on the filesystem.

## Common Operations

### Check if sshd is running on device

```bash
hdc shell "ps -ef | grep sshd | grep -v grep"
```

From LXC/Linux through Windows:

```bash
ssh board-win "hdc -t <device-id> shell \"ps -ef | grep sshd | grep -v grep\""
```

### Restart sshd after reboot

```bash
hdc shell "/bin/sshd -p 2223"
```

From LXC/Linux through Windows:

```bash
ssh board-win "hdc -t <device-id> shell \"/bin/sshd -p 2223\""
```

### hilog 日志抓取与调试

hilog 是 OpenHarmony 的系统日志服务。日志文件存储在 `/data/log/hilog/`。

**实时查看日志**（流式输出，Ctrl+C 停止）：

```bash
# 通过 SSH 实时查看（推荐，可用管道过滤）
ssh -i ~/.ssh/agent_key -p 2223 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@192.168.1.108 "hilog"

# 或通过 hdc
hdc hilog
```

**按级别过滤**（D=Debug, I=Info, W=Warn, E=Error, F=FATAL）：

```bash
ssh ... root@<ip> "hilog -b E"           # Error 及以上
ssh ... root@<ip> "hilog -b W"           # Warn 及以上
```

**按 tag 过滤**：

```bash
ssh ... root@<ip> "hilog -T MyTag"                    # 按 tag（注意是大写 -T）
ssh ... root@<ip> "hilog -L W -T HiviewXPC"           # 组合：级别 + tag
```

**按 domain 过滤**（用 grep，因为 `-D` 参数在部分设备上报错 `Invalid domain string`）：

```bash
# 日志格式：日期 时间 PID TID 级别 domain/tag: 内容
# domain 在日志中显示为 "C05740/TransSdk" 这样的格式
ssh ... root@<ip> "hilog" | grep --line-buffered "C05740"     # 按 domain
ssh ... root@<ip> "hilog" | grep --line-buffered "TransSdk"   # 按 tag（效果同 -T）
```

**实时日志 + 管道处理**（SSH 管道比 hdc 更灵活）：

```bash
# 实时过滤特定 tag 并保存到本地
ssh ... root@<ip> "hilog" | grep --line-buffered "MyTag" | tee board_log.txt

# 只看 Error 并高亮
ssh ... root@<ip> "hilog -b E" | grep --line-buffered -E "E |F "
```

**导出已有日志文件**：

```bash
# 拉取全部日志到本地
hdc file recv /data/log/hilog/ ./local_logs/

# 读取设备上的历史日志
ssh ... root@<ip> "hilog -r -f /data/log/hilog/"
```

**清除日志**：

```bash
hdc shell "hilog -c"                    # 清除内存缓存
hdc shell "rm -rf /data/log/hilog/*"    # 删除日志文件
```

**日志配置**：

```bash
hdc shell "hilog -h"                    # 查看完整帮助
hdc shell "hilog -G <size>"             # 设置单文件大小上限
hdc shell "hilog -L <num>"              # 设置日志文件数量上限
```

### Reboot after pushing compiled libraries

When you push compiled libraries (编译推库) to the device, the running system still uses the old files loaded in memory. You must reboot to force the device to reload the new dynamic libraries.

```bash
# Reboot the device (via SSH or hdc)
ssh -i ~/.ssh/agent_key -p 2223 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@192.168.1.108 "reboot"
# or
hdc shell "reboot"

# Wait ~60 seconds for the device to fully boot
sleep 60

# Restart sshd (lost after reboot)
hdc shell "/bin/sshd -p 2223"

# Verify device is responsive
ssh ... root@<ip> "echo ok"
```

Why sleep 60? OpenHarmony devices take roughly 40-50 seconds to reach a usable state after reboot. Waiting 60s avoids racing against incomplete initialization. If the device is unusually slow (debug builds, first boot after flash), extend to 90s.

### Copy files to/from device

Use `scp` with the same SSH key:

```bash
# Upload
scp -i ~/.ssh/agent_key -P 2223 -o StrictHostKeyChecking=no local_file root@192.168.1.108:/remote/path

# Download
scp -i ~/.ssh/agent_key -P 2223 -o StrictHostKeyChecking=no root@192.168.1.108:/remote/path local_file
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ssh board-win` fails | Reverse SSH tunnel from Windows to LXC is down or LXC `Host board-win` is missing | Re-establish the Windows `RemoteForward 2222 127.0.0.1:22` tunnel and verify `ssh board-win "hostname"` |
| `hdc list targets` works on Windows but not from LXC | LXC is trying local hdc instead of Windows hdc | Use `ssh board-win "hdc list targets"` |
| Multiple `hdc list targets` entries | More than one board/device is visible | Do not guess. Use `hdc -t <device-id> ...` with the intended device |
| `Host board` points to the wrong board | Fixed port forwarding is not device identity | Use hdc device ID as identity; create fport only when needed |
| `Permission denied (publickey)` | authorized_keys not found or wrong path | Check step 5 of setup: `sshd_config` AuthorizedKeysFile must be absolute path |
| `Permission denied` after reboot | sshd not restarted | Run `hdc shell "/bin/sshd -p 2223"` |
| SSH connects but commands return exit 1, no output | Root shell is `/bin/false` | Fix with step 2 of setup |
| `ssh: connect to host ... port 2223: Connection refused` | sshd not running or wrong IP | Check sshd is running, verify IP with `hdc shell "ip addr show"` |
| Interactive program hangs or loops | Missing `-tt` flag | Always use `ssh -tt` for interactive programs |
| `fport result:OK` but `Connection refused` | fport died because the Windows cmd session ended between creating fport and using it | Create fport and SSH in the same `cmd /c "fport && ssh ..."` chain |
| `kex_exchange_identification: Connection closed by remote host` | Using ProxyCommand (`ssh -W`) for double-hop SSH — the SSH protocol exchange doesn't survive the proxy path | Use the two-hop pattern: `ssh board-win "cmd /c \"fport && ssh ...\""` — let Windows SSH client talk to the device directly through fport |
| `fport ls` returns `[Empty]` but fport was just created | fport is session-scoped; `fport ls` ran in a different cmd session | Always check `fport ls` in the same `cmd /c` chain as the fport creation |
| `ssh: connect to host 192.168.x.x: No route to host` | LXC controller has no route to the device's network | Use fport chain through Windows even if device has an IP — the device IP is unreachable from LXC |
| `sh: <command>: inaccessible or not found` but the command exists | Multi-shell quoting: `;` or spaces inside the SSH command argument got consumed by an outer shell, turning the whole thing into a filename token | Use `hdc shell` instead (avoids one shell layer), or simplify to a single command without `;` |
| Orphan processes accumulate on device | Program doesn't exit on stdin EOF | Always use `timeout` wrapper; include exit commands in piped input |
| Cleanup orphaned processes | Leftover from previous runs | `hdc shell "ps -ef | grep <program> | grep -v grep"` then `kill <pids>` |
