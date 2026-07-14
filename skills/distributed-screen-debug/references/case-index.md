# Case Index

Use this file as the fast memory of resolved patterns. Match the symptom first, then jump to the first abnormal event and code anchor.

## Setup and compatibility

| Symptom | First abnormal event | Layer | Code anchor | Common trap |
| --- | --- | --- | --- | --- |
| Start share succeeds in UI but remote side does not continue | `MakeMirror` result is not propagated | caller / window_manager | `DHardwareCommonService::StartShare()` | A successful caller return can still hide a failed `MakeMirror()` |
| 投屏失败且 sink 定屏 after OTA / version mix | stale DB or type mismatch before sink recovery | DHFWK + sink | DHFWK registration / sink rollback path | Do not blame sink decode first |
| Setup response arrives too early after network recovery | state callback registration is late | caller callback | status callback registration path | The path can look connected while callback is still missing |
| `HandleNotifySetUp` missing | cross-device setup never arrived | source / RPC | source setup notification path | Do not jump to sink decode |

## Data path

| Symptom | First abnormal event | Layer | Code anchor | Common trap |
| --- | --- | --- | --- | --- |
| DFX reports ERROR during normal open | duplicate JPEG session callback re-enters `StartEncoder()` | source data session | `screen_data_channel_impl.cpp` / `screen_source_trans.cpp` | `StartEncoder` failure can be a false failure after the encoder already started |
| Source sends frames but sink does not draw | `OnStreamReceived` or `InputScreenData` missing | data transport | SoftBus data path | Do not blame decoder before proving data arrival |
| Sink has input buffers but no output | `OnDecodeOutputBufferAvailable` missing | sink decoder | decoder output path | Input buffer ready is not the same as display output |

## Stop and recovery

| Symptom | First abnormal event | Layer | Code anchor | Common trap |
| --- | --- | --- | --- | --- |
| Disconnect on weak network with delayed recovery | heartbeat RPC times out, then rollback is incomplete | stop / recovery | heartbeat and closeSession path | A later disconnect can be noise after the first rollback failure |
| Source does not roll back after sink rollback | `closeSession` fails on sink rollback | session teardown | closeSession path | The source may look stuck even though the rollback failed earlier |
| Stop logs look noisy | `cmd 5 -> cmd 14 -> cmd 4` is normal | status / stop | DHARDWARECOMMON state path | Do not treat later stop states as root cause |

## Status and input

| Symptom | First abnormal event | Layer | Code anchor | Common trap |
| --- | --- | --- | --- | --- |
| Status callback missing or JS side silent | `StateHandleLoop get callback reference failed` | NAPI / JS | `dhardwarecommon_napi.cpp` | This is a callback reference issue, not main-chain failure |
| Visible video but no control | input chain never starts or monitor is missing | distributed_input | `StartPullInput`, `AddMonitor`, `SimulateInputEvent` | Do not inspect input before proving the main path is alive |

## How to use

1. Match the symptom row.
2. Take the first abnormal event as the search target.
3. Verify the named code anchor.
4. Use the common trap column to avoid overcalling the failure.
