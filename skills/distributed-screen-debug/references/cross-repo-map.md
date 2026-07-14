# 分布式屏幕相关跨仓边界图

## 1. 只按 v1.0 分析

本 skill 只讨论 v1.0 路径。日志里即使出现 `screenVersion:"2.0"`，也先按 v1.0 控制面分析，并明确提醒用户 v2.0 已被忽略。

## 2. 主链、旁路、输入支路

### 2.1 投屏主链

`DHFWK -> DSCREEN Source -> window_manager MakeMirror -> DSCREEN Sink -> SoftBus -> 编码/解码`

用户说黑屏、秒断、没画面，先看这条链。

### 2.2 状态回调旁路

`DScreenStateManager -> DHARDWARECOMMON Service -> TriggerMessageCallback/TriggerStateChangeCallback -> NAPI/JS`

用户说状态通知不对、回调不触发、应用提示异常，先看这条链。

### 2.3 输入支路

`DHARDWARECOMMON StartPullInput -> distributed_input source/sink -> AddMonitor -> SimulateInputEvent`

只有在主链已经稳定出画后，再看这条链。

## 3. 关键边界和该看什么日志

| 层级 | 主要 TAG 或模块 | 优先检索词 | 用来判断什么 |
| --- | --- | --- | --- |
| 调用方 | `DHARDWARECOMMON`、`KhScreenService` | `StartShare`、`StopShare`、`NotifyDHCommonMessage`、`OnDscreenChange`、`stateChange` | 用户操作是否真正落到底层；状态回调是否只在上层丢失 |
| 窗口管理 | `ScreenManager`、`DisplayManagerService`、`JsScreenManager` | `MakeMirror`、`RemoveVirtualScreenFromGroup`、`CreateVirtualScreen` | 虚拟屏是否真正加入镜像组；stop 是否由调用方发起 |
| DHFWK | `DHFWK` | `SendOnLineEvent`、`OnLineTask`、`EnableTask`、`DisableTask`、`OffLineTask` | 设备上线、能力使能、回收、离线 |
| distributed_screen 主链 | `DSCREEN` | `HandleEnable`、`NotifyRemoteSinkSetUp`、`HandleNotifySetUp`、`HandleNotifySetUpResult`、`HandleConnect`、`SendFullData`、`OnStreamReceived` | Source/Sink 控制面和数据面主链 |
| distributed_input | 视具体仓 TAG 而定 | `StartCaptureMMInput`、`StopCaptureMMInput`、`NotifyRemoteSinkSetUp`、`HandleNotifySetUpResult`、`AddMonitor`、`SimulateInputEvent` | 出画正常但无法操作、坐标错位、输入链路中断 |
| 输入系统 | `multimodalinput_input` | `AddMonitor`、`RemoveMonitor`、`SimulateInputEvent` | Sink 捕获输入、Source 注入输入是否成功 |

## 4. 按现象决定先看哪一层

### 4.1 用户说开始投屏没反应

先看：

1. 调用方是否有 `StartShare`
2. `MakeMirror` 是否成功
3. Source 是否进入 `NotifyRemoteSinkSetUp`

### 4.2 用户说显示已连接但没画面

先看：

1. Source 有没有 `SendFullData`
2. Sink 有没有 `OnStreamReceived`
3. Sink 有没有 `OnDecodeOutputBufferAvailable`

### 4.3 用户说状态通知不对

先看：

1. `DSCREEN` 是否有 `OnDscreenChange`
2. `DHARDWARECOMMON` 是否有 `NotifyDHCommonMessage`
3. NAPI 是否有 `get callback reference failed`

### 4.4 用户说能看到画面但不能操作

先看：

1. 调用方是否真的发了 `StartPullInput`
2. distributed_input 是否建立 source/sink setup
3. Sink 是否 `AddMonitor`
4. Source 是否 `SimulateInputEvent`

## 5. `DHARDWARECOMMON` 常见状态码

只列正常样本里最常见、且已经从代码确认过的部分：

| cmd | 含义 | 常见出现侧 |
| --- | --- | --- |
| `3` | `NOTIFY_STATE_START` | Source、Sink 都可能收到 |
| `4` | `NOTIFY_STATE_STOP` | stop 完成后的最终停止 |
| `5` | `NOTIFY_STATE_STOP_BY_USER` | 本端用户主动停止时更常见 |
| `14` | `STOP_BY_USER_REMOTE_RQS` / 远端用户停止同步 | 对端收到远端用户停屏时更常见 |

不要把 `cmd 14` 或 stop 阶段重复的 `cmd 4` 直接当成故障起点。

## 6. 常用检索词

### 6.1 调用方

```bash
rg -n "DHARDWARECOMMON|OnDscreenChange|NotifyDHCommonMessage|StartShare|StopShare|StartPullInput|StopPullInput|stateChange|StateHandleLoop|get callback reference failed" <logfile>
```

### 6.2 窗口管理

```bash
rg -n "MakeMirror|RemoveVirtualScreenFromGroup|CreateVirtualScreen|ScreenGroup" <logfile>
```

### 6.3 DHFWK

```bash
rg -n "DHFWK|SendOnLineEvent|OnLineTask|EnableTask|DisableTask|OffLineTask|PublishMessage|ComponentManager" <logfile>
```

### 6.4 distributed_screen 主链

```bash
rg -n "HandleEnable|CreateVirtualScreen|NotifyRemoteSinkSetUp|HandleNotifySetUp|NotifyRemoteSourceSetUpResult|HandleNotifySetUpResult|HandleConnect|OnScreenSessionOpened|OnChannelSessionOpened|StartEncoder|SendFullData|OnStreamReceived|InputScreenData|OnDecodeOutputBufferAvailable|HandleDisconnect|HandleDisable" <logfile>
```

### 6.5 distributed_input

```bash
rg -n "StartCaptureMMInput|StopCaptureMMInput|HandleMMInputStartCapture|HandleMMInputStopCapture|NotifyRemoteSinkSetUp|HandleNotifySetUpResult|AddMonitor|RemoveMonitor|SimulateInputEvent|NOTIFY_SOURCE_SCREEN_CHANGE" <logfile>
```

## 7. 这份边界图的来源

这份边界图主要来自以下材料和代码：

- `6.1/extension/distributed/distributed_input/.codex/architecture-analysis.md`
- `6.1/extension/distributed/distributed_screen/.codex/architecture-analysis.md`
- `6.1/foundation/distributedhardware/distributed_screen/.codex/architecture-analysis-v1.md`
- `5.0/foundation/distributedhardware/distributed_screen/.claude/distributed_screen_runtime_v1_0.md`
- `5.0/foundation/distributedhardware/distributed_screen/.claude/dscreen_make_mirror_flow_v1_0.md`
- 当前 5.0 代码仓：
  - `extension/distributed/distributedhardware/distributed_screen`
  - `foundation/distributedhardware/distributed_screen`

用法上，先把问题归到某个边界，再回该边界的代码和日志，不要一开始就全仓乱搜。
