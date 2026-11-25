# Windows reverse SSH

Windows initiates an outbound SSH connection to LXC and forwards an LXC loopback port to Windows `127.0.0.1:22`. This needs no inbound port mapping on the Windows router. The LXC alias `board-win` connects to the forwarded port using the Windows SSH account.

## Current deployment

- On Annan's LXC, `board-win` currently uses `kaihong@127.0.0.1:2224`. Read `ssh -G board-win` before choosing a port. The legacy `2222` forward can belong to an ordinary Windows-to-LXC terminal.
- Windows task `BoardWinReverseSsh` starts at the Windows user's logon, with single-instance policy and no execution time limit. Its action runs `%LOCALAPPDATA%\BoardWinReverseSsh\BoardWinReverseSsh.exe 2224`. The source is alongside the executable as `BoardWinReverseSsh.cs`.
- The launcher is built with the Windows GUI subsystem (`csc /target:winexe`) and creates no UI. It starts `ssh.exe` with `UseShellExecute = false` and `CreateNoWindow = true`, waits for it to exit, then retries after 10 seconds.
- LXC has `ClientAliveInterval 15` and `ClientAliveCountMax 3` under `Match User huaannan` in `/etc/ssh/sshd_config.d/60-huaannan-client-alive.conf`. New sessions use it, including normal logins by that account. Online idle clients respond automatically. This LXC starts a new `sshd` per connection through `ssh.socket`.

## Reproduce on another host

Choose an unused LXC loopback port and verify that the Windows user's existing key and known-hosts entry allow noninteractive login to LXC. Use these SSH arguments in the windowless launcher, replacing `2224` and the LXC login with the target deployment's values.

```powershell
ssh.exe -NT -R 127.0.0.1:2224:127.0.0.1:22 -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 huaannan@10.71.1.181
```

Give the launcher a logon trigger under that Windows user. Point the LXC `board-win` alias at the same loopback port. Configure server-side `ClientAliveInterval` and `ClientAliveCountMax` for the LXC login so stale sessions release the port. Validate server configuration with `sshd -t` and check the effective settings with `sshd -T -C` before applying them using the host's SSH service model.

## Recovery

Use the resolved alias port in `ss -ltnp` and use the bounded hostname probe from the skill. A missing listener calls for checking the Windows scheduled task. If a listener exists but the SSH banner times out, identify its owning LXC session and check whether Windows OpenSSH responds on `127.0.0.1:22` from Windows itself. TCP `ESTAB` alone does not prove that the tunnel passes traffic.

If a replacement tunnel reports `Address already in use`, identify the listener before taking action. An ordinary LXC terminal can own a reverse forward. Let the scheduled task handle reconnects and preserve unrelated terminal sessions. When replacing a task action, check whether its old `ssh.exe` child survived; stop only the process whose command line and parent match the replaced tunnel.

Recovery is complete when `ssh board-win hostname` reaches the expected Windows host. The current deployment was tested by terminating its dedicated `ssh.exe` child and verifying automatic reconnection. Annan confirmed the black console window disappeared. Network loss and Windows sleep recovery have not been tested.
