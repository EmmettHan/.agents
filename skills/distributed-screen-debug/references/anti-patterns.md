# Anti-patterns

These are logs that are easy to misread. Treat them as hints, not root causes.

## Known false positives

- `CreateVirtualScreen: surface is nullptr`
  - v1.0 may create the virtual screen before `SetImageSurface()`. Do not call this the first fault by itself.
- A second `OnChannelSessionOpened` followed by `StartEncoder failed -53002`
  - if the first session is already sending `SendFullData`, this is usually a duplicate JPEG-session noise path.
- `cmd 5 -> cmd 14 -> cmd 4`
  - this stop order is normal. Do not treat later stop notifications as a new defect.
- Repeated `HandleDisconnect`, `Channel listener is null`, or `Send heartbeat data because data queue wait timed out`
  - if the main stop flow already completed, these are often teardown noise.
- `StateHandleLoop get callback reference failed`
  - this is a callback reference problem in the JS/NAPI path, not proof that the main screen chain failed.
- `screenVersion:"2.0"`
  - this skill still analyzes the v1.0 control path. `2.0` here often means dual-session behavior, not a v2.0 control plane.

## Read order

1. Check whether the main path reached `SendFullData` and `OnDecodeOutputBufferAvailable`.
2. If yes, inspect callback and input branches.
3. If no, stay on the main chain and find the first missing event.
