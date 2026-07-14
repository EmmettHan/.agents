# 分布式屏幕 v1.0 关键事件基线

## 1. 快速用法

先跑摘要视图，确认关键阶段在哪一侧出现、停在了哪一步：

```bash
python3 scripts/extract_dscreen_timeline.py \
  --focus "01-30 16:46:32.450" \
  --window 6 \
  --summary \
  /path/to/source.log /path/to/sink.log
```

如果已经知道断点大概在哪，再展开原始时间窗看上下文：

```bash
python3 scripts/extract_dscreen_timeline.py \
  --focus "01-30 16:46:32.450" \
  --window 2 \
  /path/to/source.log /path/to/sink.log
```

脚本之外，常用二次检索词：

```bash
rg -n "HandleEnable|CreateVirtualScreen|MakeMirror|NotifyRemoteSinkSetUp|HandleNotifySetUp|NotifyRemoteSourceSetUpResult|HandleNotifySetUpResult|HandleConnect|OnScreenSessionOpened|OnChannelSessionOpened|StartEncoder|SendFullData|OnStreamReceived|InputScreenData|OnDecodeOutputBufferAvailable|HandleDisconnect|HandleDisable|StateHandleLoop get callback reference failed" <logfile>
```

## 2. 先分清三条链

- 主链：
  `HandleEnable -> CreateVirtualScreen -> MakeMirror -> NotifyRemoteSinkSetUp -> HandleNotifySetUp -> NotifyRemoteSourceSetUpResult -> HandleNotifySetUpResult -> HandleConnect -> OnScreenSessionOpened -> OnChannelSessionOpened -> StartEncoder -> SendFullData -> OnStreamReceived -> InputScreenData -> OnDecodeOutputBufferAvailable`
- 状态回调旁路：
  `OnDscreenChange -> NotifyDHCommonMessage -> TriggerMessageCallback/TriggerStateChangeCallback -> NAPI/JS`
- 停止与回收链：
  `cmd 5 或 cmd 14 -> HandleDisconnect -> CloseSession -> OnSessionClosed -> StopHeartBeatProcesser -> StopDecoder -> ReleaseSession -> HandleDisable -> DisableTask/OffLineTask`

先判断主链是否走通，再判断状态回调和输入支路。不要拿旁路报错否定主链。

## 3. 正常样本主链基线

| 阶段 | 正常关键日志 | 正常样本时间 | 代码落点 | 断在这里先看什么 |
| --- | --- | --- | --- | --- |
| 状态监听注册 | `RegisterDScreenStateListener` | source `16:46:29.378` / `16:46:29.408` | `extension/distributed/distributed_screen/services/src/dhardwarecommon_mgr.cpp` | 只是旁路就绪，不代表已经开始投屏 |
| 设备上线 | `SendOnLineEvent`、`OnLineTask` | sink `16:46:28.836`；source `16:46:29.433` | `distributed_hardware_fwk` | 远端设备未被感知，后续 Enable 往往不会触发 |
| DHFWK 使能 | `EnableDistributedScreen1.0`、`EnableTask` | source `16:46:29.858` | `services/screenservice/sourceservice/dscreenmgr/1.0/src/dscreen_manager.cpp` | 入口还在 DHFWK、IPC 或 handler |
| Source 进入 Enable | `HandleEnable` | source `16:46:29.859` | `services/screenservice/sourceservice/dscreenmgr/1.0/src/dscreen.cpp` | Source SA 没收到使能，或任务队列没执行 |
| 创建虚拟屏 | `CreateVirtualScreen` | source `16:46:29.862` | `services/screenservice/sourceservice/dscreenmgr/common/src/screen_manager_adapter.cpp` | 参数、编解码协商、虚拟屏创建 |
| 调用方发起镜像 | `MakeMirror`、`MakeMirror success` | source `16:46:31.689` 到 `16:46:31.693` | `extension/distributed/distributedhardware/distributed_screen/services/src/dhardwarecommon_service.cpp` + `window_manager` | 调用方没把主屏加入虚拟屏组 |
| Source 通知 Sink 建链 | `NotifyRemoteSinkSetUp` | source `16:46:31.695` | `services/screenservice/sourceservice/dscreenmgr/1.0/src/dscreen_manager.cpp` | 跨设备 RPC、`mapRelation`、远端 SA 可达性 |
| Sink 收到 setup | `HandleNotifySetUp` | sink `16:46:32.116` | `services/screenservice/sinkservice/screenregionmgr/1.0/src/screenregionmgr.cpp` | Sink SA 没收到通知，或 setup JSON 不合法 |
| Sink 解码器 ready | `StartDecoder` | sink `16:46:32.190` | `services/screentransport/screensinkprocessor/src/image_sink_processor.cpp` | window surface、decoder、sink trans 初始化 |
| Sink setup 回包 | `NotifyRemoteSourceSetUpResult errCode: 0` | sink `16:46:32.258` | `services/screenservice/sinkservice/screenregionmgr/1.0/src/screenregionmgr.cpp` | 回包没发出，或 Source 没收到 |
| Source 收到 setup 结果 | `HandleNotifySetUpResult` | source `16:46:32.334` | `services/screenservice/sourceservice/dscreenmgr/1.0/src/dscreen_manager.cpp` | `KEY_SESSION_ID` 不匹配、结果超时、`dScreenIdx` 不存在 |
| Source 进入 Connect | `HandleConnect` | source `16:46:32.334` | `services/screenservice/sourceservice/dscreenmgr/1.0/src/dscreen.cpp` | `SetUp`/`Start` 失败、窗口 surface 未绑定 |
| Source 数据 session 打开 | `OnScreenSessionOpened, sessionId: 5` | source `16:46:32.444` | `services/screentransport/screendatachannel/src/screen_data_channel_impl.cpp` | SoftBus state session/data session 没建起来 |
| Source 编码启动 | `OnChannelSessionOpened`、`StartEncoder` | source `16:46:32.456` | `services/screentransport/screensourcetrans/src/screen_source_trans.cpp` + `services/screentransport/screensourceprocessor/encoder/src/image_source_encoder.cpp` | encoder、Surface、image processor |
| Source 首帧发送 | `SendFullData` | source `16:46:32.503` | `services/screentransport/screensourcetrans/src/screen_source_trans.cpp` | 没帧、没编码成功、data queue 不出队 |
| Sink 首帧接收 | `OnStreamReceived`、`InputScreenData` | sink `16:46:32.552` | `services/screentransport/screendatachannel/src/screen_data_channel_impl.cpp` + `services/screentransport/screensinktrans/src/screen_sink_trans.cpp` | SoftBus 数据面、listener 注册、码流收包 |
| Sink 首次解码输出 | `OnDecodeOutputBufferAvailable` | sink `16:46:32.799` | `services/screentransport/screensinkprocessor/decoder/src/image_sink_decoder.cpp` | decoder、输出 surface、码流格式 |

### 正常样本里的次级锚点

- `16:46:32.249` sink `OnDecodeInputBufferAvailable`
  - 说明 decoder 已经启动并具备输入 buffer，不等于已经出画。
- `16:46:32.445` source `OnDscreenChange for cmd 3`
  - 这是状态回调旁路，不是主链断点。

## 4. 正常样本停止与回收基线

| 阶段 | 正常关键日志 | 正常样本时间 | 解释 |
| --- | --- | --- | --- |
| Source 侧用户主动停止通知 | `OnDscreenChange for cmd 5` | source `16:46:47.416` | 本端用户主动停投屏 |
| Sink 侧远端用户停止通知 | `OnDscreenChange for cmd 14` | sink `16:46:47.466` | 远端用户触发停止，属于正常 stop 链 |
| Source 真正断连 | `HandleDisconnect` | source `16:46:47.630` | 主 stop 入口 |
| Source 关闭 session | `CloseSession`、`OnSessionClosed`、`RemoveScreenFromGroup` | source `16:46:47.692` 到 `16:46:47.708` | 数据通道和镜像组开始回收 |
| Sink 收到 session close | `OnSessionClosed` | sink `16:46:47.748` | 对端数据面已断 |
| Sink 停心跳与解码 | `StopHeartBeatProcesser`、`StopDecoder` | sink `16:46:47.760` 到 `16:46:47.769` | 正常回收 |
| 双端最终 stop 状态 | `OnDscreenChange for cmd 4` | source `16:46:47.697` / sink `16:46:47.826` | 最终进入 stop |
| DHFWK 回收 | `DisableTask`、`OffLineTask` | source `16:46:54.124` 到 `16:46:54.134` | 能力与设备下线回收 |

## 5. 快速定界规则

### 5.1 没画面或一直黑屏

- 有 `CreateVirtualScreen`，没有 `MakeMirror`
  - 先查调用方和 `window_manager`
- 有 `MakeMirror success`，没有 `NotifyRemoteSinkSetUp`
  - 先查 Source 控制面、`mapRelation`、远端 SA
- 有 `HandleNotifySetUp`，没有 `NotifyRemoteSourceSetUpResult`
  - 先查 Sink `ScreenRegion::SetUp/Start`
- Sink 已回 `NotifyRemoteSourceSetUpResult`，Source 没 `HandleNotifySetUpResult`
  - 先查跨设备回包、`KEY_SESSION_ID` 是否匹配
- Source 已 `HandleConnect`，没有 `OnScreenSessionOpened`
  - 先查 SoftBus session 建链
- Source 已 `OnChannelSessionOpened`，没有 `SendFullData`
  - 先查编码器、image surface、`StartImageProcessor`
- Source 已 `SendFullData`，Sink 没 `OnStreamReceived`
  - 先查 SoftBus 数据面
- Sink 已 `InputScreenData`，没有 `OnDecodeOutputBufferAvailable`
  - 先查 decoder、输出 surface、码流格式

### 5.2 显示已连接但状态通知不对

- 主链正常且 `DHARDWARECOMMON` 有 `OnDscreenChange`
  - 优先查 `TriggerMessageCallback`、`TriggerStateChangeCallback`、NAPI
- 主链正常但 `StateHandleLoop get callback reference failed`
  - 这更像 JS/NAPI 回调引用失效，不是投屏主链失败

### 5.3 用户说点击停止后日志很多错误

- 先找第一次 `cmd 5 / cmd 14 / HandleDisconnect`
- 再确认有没有完整的 `CloseSession -> OnSessionClosed -> StopDecoder/ReleaseSession`
- 如果完整 stop 已经结束，后续重复 `HandleDisconnect`、`Channel listener is null`、`Send heartbeat data because data queue wait timed out` 往往不是首因

### 5.4 输入问题单独走输入支路

- 只有在主链已经稳定 `SendFullData` 且 Sink 已 `OnDecodeOutputBufferAvailable` 后，才进入 distributed_input 链路
- 此时优先看：
  - `StartPullInput`
  - distributed_input 的 `NotifyRemoteSinkSetUp / HandleNotifySetUpResult`
  - Sink `AddMonitor`
  - Source `SimulateInputEvent`

## 6. 正常样本里容易误判的日志

### 6.1 `CreateVirtualScreen: surface is nullptr` 在 v1.0 正常出现

正常样本里，创建虚拟屏时会出现：

- `DisplayManagerProxy: CreateVirtualScreen: surface is nullptr`
- `RSScreenManager CreateVirtualScreen: surface is nullptr`

这不是首因。v1.0 的真实顺序是：

1. `DScreen::HandleEnable()` 先 `CreateVirtualScreen()`
2. `DScreen::HandleConnect()` 里 `Start()`
3. `DScreen::Start()` 再 `ScreenMgrAdapter::SetImageSurface(screenId_, windowSurface)`

也就是说，创建虚拟屏时 surface 还没绑定，本来就可能打印这类日志。

### 6.2 `screenVersion:"2.0"` 不等于走了 v2.0 控制面

正常样本的 `NotifyRemoteSinkSetUp` 里带有：

- `screenVersion:"2.0"`

但 5.0 v1.0 代码里：

- `DScreenManager::EnableDistributedScreen()` 把 `param.sinkVersion` 写入 `DScreen::version_`
- `ScreenSourceTrans::InitScreenTrans()` 和 `ScreenSinkTrans::InitScreenTrans()` 只是在 `version_ > 1` 时打开 JPEG session

所以这里仍按 v1.0 控制面分析，`2.0` 更常见的意义是双 session 行为，不是直接跳到 v2.0 业务代码。

### 6.3 第二个 session 打开后 `StartEncoder failed -53002` 不是这次正常投屏的首因

正常样本里：

- `16:46:32.619` 又打开了 `sessionId: 6`
- 紧接着 `StartEncoder failed -53002`

但同一时间窗内：

- `sessionId: 5` 仍持续 `SendFullData`
- Sink 仍持续 `OnStreamReceived`
- Sink 仍持续 `OnDecodeOutputBufferAvailable`

所以这更像第二个 JPEG session 的重复启动噪声，不是主链失败。

### 6.4 `cmd 5 / cmd 14 / cmd 4` 的 stop 顺序容易被误读

正常样本 stop 阶段可见：

- source 先收到 `cmd 5`
- sink 随后收到 `cmd 14`
- 之后双端还会收到 `cmd 4`

这是一条正常的停止链：

- `cmd 5`: 本端用户主动停止
- `cmd 14`: 远端用户停止同步到对端
- `cmd 4`: 最终 stop 状态

不要把后两个状态通知当成新的故障起点。

### 6.5 `StateHandleLoop get callback reference failed` 不等于主链失败

这条日志来自：

- `extension/distributed/distributedhardware/distributed_screen/interface/js/src/dhardwarecommon_napi.cpp`

对应的是 `napi_get_reference_value()` 失败。只要同时已经看到：

- `MakeMirror success`
- `SendFullData`
- `OnStreamReceived`
- `OnDecodeOutputBufferAvailable`

就应先把它归到 JS/NAPI 回调问题，而不是分布式屏幕主链问题。

## 7. 关键代码落点

- Source 控制面：
  `services/screenservice/sourceservice/dscreenmgr/1.0/src/dscreen_manager.cpp`
- Source 状态机：
  `services/screenservice/sourceservice/dscreenmgr/1.0/src/dscreen.cpp`
- Sink 控制面：
  `services/screenservice/sinkservice/screenregionmgr/1.0/src/screenregionmgr.cpp`
- SoftBus session 与收流：
  `services/screentransport/screendatachannel/src/screen_data_channel_impl.cpp`
- Source 编码与发流：
  `services/screentransport/screensourcetrans/src/screen_source_trans.cpp`
  `services/screentransport/screensourceprocessor/encoder/src/image_source_encoder.cpp`
- Sink 解码与显示：
  `services/screentransport/screensinktrans/src/screen_sink_trans.cpp`
  `services/screentransport/screensinkprocessor/decoder/src/image_sink_decoder.cpp`
- 调用方镜像与状态回调：
  `extension/distributed/distributedhardware/distributed_screen/services/src/dhardwarecommon_service.cpp`
  `extension/distributed/distributedhardware/distributed_screen/interface/js/src/dhardwarecommon_napi.cpp`
