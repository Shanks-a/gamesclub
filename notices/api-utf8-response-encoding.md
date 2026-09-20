# API 中文响应乱码记录

## 现象

使用 Windows PowerShell 调用：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/games/
```

返回的中文显示为 `çèè£è`、`åå¹³ç²¾è±` 等乱码。商品接口也出现相同问题。

## 根因

后端返回的 JSON 字节实际是 UTF-8，但响应头只有 `Content-Type: application/json`，没有声明字符集。Windows PowerShell 在缺少字符集声明时按系统代码页解码，导致 UTF-8 中文被错误显示。

## 修复

新增 `backend/core/renderers.py`，让 DRF 使用 `UTF8JSONRenderer`，响应媒体类型显式包含 `charset=utf-8`；并在 `backend/config/settings.py` 中将其设为默认 JSON renderer。

## 验证

重启 Django 开发服务器后，确认响应头为：

```text
application/json; charset=utf-8
```

再执行原 PowerShell `Invoke-RestMethod` 命令，游戏名称和商品名称应正常显示为中文。
