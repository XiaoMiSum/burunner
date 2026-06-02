# 变量与函数

burunner 支持在 YAML 用例中使用变量替换和内置函数，实现动态化测试。

底层基于 [Mako 模板引擎](https://www.makotemplates.org/) 实现，语法保持 `${...}` 不变，同时额外支持条件表达式和 Python 内联表达式。

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
  today: "${date()}"
  request_id: "${uuid()}"

cases:
  - name: 带动态数据的用例
    steps:
      - 输入日期 ${today}
      - 输入订单号 ${request_id}
      - 输入随机验证码 ${random_int(1000, 9999)}
```

## 表达式能力

得益于 Mako 模板引擎，`${...}` 中支持任意合法的 Python 表达式（在安全沙箱范围内）：

### 条件表达式

```yaml
steps:
  - 输入优惠码 ${"VIP100" if level == "vip" else "NEW50"}
  - 选择配送方式 ${"加急" if amount > 500 else "普通"}
```

### Python 内联表达式

```yaml
variables:
  first_name: "张"
  last_name: "三"

steps:
  - 输入全名 ${first_name + last_name}
  - 输入大写用户名 ${username.upper()}
  - 输入截取值 ${long_text[:10]}
```

> **注意**：表达式在安全沙箱中执行，仅能访问已定义的变量和内置函数，详见下方 [安全说明](#安全说明)。

## 内置函数

| 函数 | 说明 | 返回值示例 |
| --- | --- | --- |
| `${date()}` | 当前日期 | `2024-01-15` |
| `${datetime()}` | 当前日期时间 | `2024-01-15 10:30:00` |
| `${utc_datetime()}` | 当前 UTC 日期时间 | `2024-01-15 02:30:00` |
| `${timestamp()}` | 当前时间戳（秒） | `1700000000` |
| `${uuid()}` | 随机 UUID | `550e8400-e29b-41d4-a716-446655440000` |
| `${random_int()}` | 随机整数 (0-9999) | `4231` |
| `${random_int(max)}` | 随机整数 (0-max) | `42` |
| `${random_int(min, max)}` | 指定范围随机整数 | `50` |
| `${random_string()}` | 随机字母数字字符串 (长度8) | `aB3kZ9xQ` |
| `${random_string(length)}` | 随机字母数字字符串 (指定长度) | `xY7z` |
| `${env(VAR_NAME)}` | 读取环境变量 | `/usr/bin` |
| `${env(VAR_NAME, default)}` | 读取环境变量 (带默认值) | `default` |
| `${calc(expression)}` | 安全数学表达式计算 | `42` |

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
      - 输入下单日期 ${date()}
      - 输入随机金额 ${random_int(100, 9999)}
      - 点击提交按钮
      - 验证订单创建成功

  - name: 登录并验证时间
    steps:
      - 访问 ${base_url}/login
      - 输入用户名 ${admin_user}
      - 输入密码 ${admin_pass}
      - 点击登录
      - 验证页面显示当前日期 ${date()}
```

## 安全说明

burunner 的变量引擎运行在安全沙箱中，以下操作会被拒绝并抛出错误：

| 禁止的操作 | 说明 |
| --- | --- |
| `import` | 禁止导入任何模块 |
| `eval()` / `exec()` | 禁止动态执行代码 |
| `open()` | 禁止文件系统访问 |
| `__import__` / `__builtins__` | 禁止访问 Python 内部机制 |
| `getattr()` / `setattr()` | 禁止反射操作 |
| `globals()` / `locals()` | 禁止访问作用域 |

示例（以下表达式会报错）：

```yaml
# ❌ 错误用法 - 会被安全检查拦截
steps:
  - ${__import__('os').system('rm -rf /')}
  - ${eval('1+1')}
  - ${open('/etc/passwd').read()}
```

模板中仅能访问：
- YAML 中定义的变量
- 上述内置函数
- 基本的 Python 表达式运算（算术、字符串操作、条件表达式等）

## 注意事项

- 变量在用例执行前一次性解析替换
- 未定义的变量将抛出 `VariableError` 错误
- 函数在每次引用时独立计算（每次 `${uuid()}` 生成不同值）
- 变量名区分大小写
- 底层使用 Mako 模板的 `strict_undefined=True` 模式，引用未定义变量会立即报错而非静默忽略
