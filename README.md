# Bilive-Coyote

目前只实现了Controller，剩下的是TODO

## 功能

- 查看服务端信息
- 查看游戏 API 信息
- 查询指定客户端的游戏信息
- 查询指定客户端的强度配置
- 修改基础强度或随机强度
- 触发 `fire` 动作

## 安装

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

## 配置

复制 `config.example.json` 为 `config.json`，然后填写你自己的配置：

```json
{
  "base_url": "http://127.0.0.1:8920",
  "client_id": "YOUR_CLIENT_UUID",
  "token": "",
  "timeout": 10
}
```

## 命令示例

```bash
python main.py server-info
python main.py game-api-info
```

```bash
python main.py game-info
python main.py strength-info
python main.py strength --target base --action add --value 5
python main.py strength --target base --action sub --value 3
python main.py strength --target base --action set --value 20
python main.py strength --target random --action add --value 2
python main.py strength --target random --action sub --value 1
python main.py strength --target random --action set --value 10
python main.py fire --strength 25 --time-ms 3000 --override
```

## Python 调用

```python
from dglab_controller import DGLabClient

client = DGLabClient(
    base_url="http://127.0.0.1:8920",
    client_id="YOUR_CLIENT_UUID",
)

print(client.get_game_info())
print(client.change_strength(target="base", action="add", value=5))
print(client.change_strength(target="random", action="set", value=10))
print(client.fire(strength=25, time_ms=3000, override=True))
```

## 说明

- `server-info` 和 `game-api-info` 不需要 `client_id`
- 其他命令都必须在当前目录的 `config.json` 里提供 `client_id`
