# 变量与函数

burunner 支持在 YAML 用例中使用变量替换和内置函数，实现动态化测试。

## 变量替换语法

使用 `${var}` 语法引用变量：

```yaml
variables:
  base_url: "https://example.com"
  username: "testuser"

cases:
  - name: 动态访问
    steps:
      - 访问 ${base_url}/login
      - 输入用户名 ${username}
```

## 变量定义

在 YAML 顶层 `variables` 字段中定义变量：

```yaml
variables:
  base_url: "https://example.com"
  username: "admin"
  password: "123456"
  product_name: "测试商品"
```

变量值支持字符串、数字等基本类型，最终在 steps 中以字符串形式替换。

## 函数调用语法

使用 `${func()}` 语法调用内置函数：

```yaml
variables:
  today: "${today()}"
  request_id: "${uuid()}"

cases:
  - name: 带动态数据的用例
    steps:
      - 输入日期 ${today}
      - 输入订单号 ${request_id}
      - 输入随机验证码 ${random_int(1000, 9999)}
```

## 内置函数

| 函数 | 说明 | 返回值示例 |
| --- | --- | --- |
| `${today()}` | 当前日期 | `2024-01-15` |
| `${now()}` | 当前时间戳（秒） | `1700000000` |
| `${now_iso()}` | 当前时间 ISO 格式 | `2024-01-15T10:30:00` |
| `${uuid()}` | 随机 UUID | `550e8400-e29b-41d4-a716-446655440000` |
| `${random_int(min, max)}` | 指定范围随机整数 | `42` |

## 三种访问方式

变量支持三种等价的访问方式：

| 语法 | 说明 |
| --- | --- |
| `${base_url}` | 直接引用 |
| `${env.base_url}` | 通过 env 前缀引用 |
| `${env.current.base_url}` | 通过 env.current 引用（多环境模式） |

三者完全等价，推荐使用最简短的 `${base_url}` 形式。

## 使用示例

```yaml
variables:
  base_url: "https://example.com"
  admin_user: "admin"
  admin_pass: "secret123"

cases:
  - name: 创建唯一订单
    steps:
      - 访问 ${base_url}/orders/new
      - 输入订单编号 ORDER-${uuid()}
      - 输入下单日期 ${today()}
      - 输入随机金额 ${random_int(100, 9999)}
      - 点击提交按钮
      - 验证订单创建成功

  - name: 登录并验证时间
    steps:
      - 访问 ${base_url}/login
      - 输入用户名 ${admin_user}
      - 输入密码 ${admin_pass}
      - 点击登录
      - 验证页面显示当前日期 ${today()}
```

## 注意事项

- 变量在用例执行前一次性解析替换
- 未定义的变量将保持原样（`${undefined_var}` 不做替换）
- 函数在每次引用时独立计算（每次 `${uuid()}` 生成不同值）
- 变量名区分大小写
