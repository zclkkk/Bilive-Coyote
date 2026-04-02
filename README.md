# Bilive Coyote

一个尽量简单的 Python 工具，用来做两件事：

- 调用本地 `DG-Lab-Coyote-Game-Hub` HTTP API
- 监听 Bilibili 开放平台直播礼物，并把礼物映射成强度变化

## 结构

- `cli.py`
  应用层命令行入口，负责组装控制层和各类 integration
- `main.py`
  最薄启动入口
- `coyote_controller/api.py`
  对外的控制层，别的模块只需要调这里
- `coyote_controller/client.py`
  只负责 Coyote HTTP API 请求
- `integrations/gift_actions.py`
  负责礼物事件、礼物规则和执行逻辑
- `integrations/bilibili_live.py`
  只负责 Bilibili 开放平台接入和事件接收

## 安装

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

## 配置

复制 `config.example.json` 为 `config.json`，然后填写：

```json
{
  "base_url": "http://127.0.0.1:8920",
  "client_id": "YOUR_CLIENT_UUID",
  "token": "",
  "timeout": 10,
  "bilibili": {
    "code": "YOUR_ANCHOR_CODE",
    "app_id": 0,
    "access_key_id": "YOUR_ACCESS_KEY_ID",
    "access_key_secret": "YOUR_ACCESS_KEY_SECRET",
    "host": "https://live-open.biliapi.com",
    "gift_actions": [
      {
        "gift_id": 31039,
        "target": "base",
        "action": "add",
        "value": 1,
        "multiply_by_gift_num": true
      }
    ]
  }
}
```

### 字段说明

- `client_id`
  DG-Lab-Coyote-Game-Hub 里的游戏客户端 UUID
- `bilibili.code`
  主播身份码
- `bilibili.app_id`
  Bilibili 开放平台应用 ID
- `bilibili.access_key_id`
  开放平台 access key id
- `bilibili.access_key_secret`
  开放平台 access key secret
- `bilibili.gift_actions`
  礼物和强度变化的映射规则

### 礼物规则

每条规则格式如下：

```json
{
  "gift_id": 31039,
  "target": "base",
  "action": "add",
  "value": 1,
  "multiply_by_gift_num": true
}
```

含义：

- 当收到 `gift_id = 31039` 的礼物
- 修改 `base` 或 `random` 强度
- 动作为 `add` / `sub` / `set`
- 基础值为 `value`
- 如果 `multiply_by_gift_num = true`，最终变化量会乘以礼物数量

例如：

- 1 个礼物加 1：`value = 1`
- 10 个礼物加 10：`value = 1` 且 `multiply_by_gift_num = true`
- 无论送几个都固定设为 20：`action = "set"`，`value = 20`，`multiply_by_gift_num = false`

## 命令

查看本地 API：

```bash
python main.py server-info
python main.py game-api-info
python main.py game-info
python main.py strength-info
python main.py strength --target base --action add --value 5
python main.py fire --strength 25 --time-ms 3000 --override
```

启动直播礼物监听：

```bash
python main.py watch-live-gifts
```

启动后流程是：

1. 调用 Bilibili 开放平台 `/v2/app/start`
2. 建立 websocket 连接
3. 监听 `LIVE_OPEN_PLATFORM_SEND_GIFT`
4. 命中规则后调用本地 Coyote HTTP API 改强度

## Python 调用

```python
from coyote_controller import CoyoteAPI, DGLabClient

api = CoyoteAPI(
    DGLabClient(
        base_url="http://127.0.0.1:8920",
        client_id="YOUR_CLIENT_UUID",
    )
)

print(api.get_game_info())
print(api.change_strength(target="base", action="add", value=5))
```

## 当前范围

当前版本只实现：

- 礼物事件监听
- 礼物到强度变化的映射

没有实现：

- 前端配置页面
- 波形发送
- 更复杂的过滤条件
- 自动重连和持久化状态管理

## 注意

- 使用直播互动玩法可能存在平台风控或封禁风险
- 请自行确认直播内容、设备使用方式和平台规则是否合规
