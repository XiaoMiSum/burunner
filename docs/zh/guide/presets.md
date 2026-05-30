# 预设与 Cookie

## 预设（Presets）

多个用例共享相同前置步骤时，使用 `presets` 定义公共流程，避免重复。

### 定义预设

在 YAML 顶层 `presets` 字段定义：

```yaml
presets:
  已登录用户:
    steps:
      - 访问 https://example.com/login
      - 输入用户名 admin 和密码 123456
      - 点击登录按钮
      - 等待页面跳转到首页

  打开商品页:
    steps:
      - 访问 https://example.com/products
      - 等待商品列表加载完成
```

### 继承预设

在用例中通过 `preset` 关键字引用预设名称：

```yaml
cases:
  - name: 查看订单
    preset: 已登录用户
    steps:
      - 点击 "我的订单"
      - 验证订单列表不为空

  - name: 修改个人信息
    preset: 已登录用户
    steps:
      - 进入个人设置页面
      - 修改昵称为 "test_user"
      - 点击保存
```

### 执行顺序

用例执行时，步骤按以下顺序合并：

1. **preset steps**（预设步骤）
2. **case steps**（用例步骤）

以上面 "查看订单" 为例，实际执行流程为：

```
1. 访问 https://example.com/login
2. 输入用户名 admin 和密码 123456
3. 点击登录按钮
4. 等待页面跳转到首页
5. 点击 "我的订单"
6. 验证订单列表不为空
```

## Cookie 注入

通过预设 Cookie 实现免登录等场景，无需每次执行登录流程。

### 全局 Cookie

在顶层 `config.cookies` 中定义，对所有用例生效：

```yaml
config:
  cookies:
    - name: token
      value: abc123
      domain: .example.com
    - name: user_id
      value: "1001"
      domain: .example.com

cases:
  - name: 免登录访问个人主页
    steps:
      - 访问 https://example.com/profile
      - 验证页面显示用户信息
```

### 用例级 Cookie

在用例中通过 `cookies` 字段定义，仅对当前用例生效：

```yaml
cases:
  - name: 以管理员身份访问
    cookies:
      - name: role
        value: admin
        domain: .example.com
      - name: session_id
        value: xyz789
        domain: .example.com
    steps:
      - 访问管理后台
      - 验证显示管理员面板
```

### Cookie 字段说明

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | string | 是 | Cookie 名称 |
| `value` | string | 是 | Cookie 值 |
| `domain` | string | 是 | Cookie 域名 |

### 合并规则

当全局 Cookie 和用例级 Cookie 同时存在时：

- 用例级 `cookies` **优先于** 全局 `config.cookies`
- 同名同 domain 的 Cookie，以用例级为准
- 不同名的 Cookie 会合并

## 完整示例

```yaml
presets:
  打开首页:
    steps:
      - 访问 https://example.com
      - 验证页面标题包含 "首页"

config:
  cookies:
    - name: lang
      value: zh-CN
      domain: .example.com
    - name: token
      value: global-token
      domain: .example.com

cases:
  - name: 普通用户浏览
    preset: 打开首页
    steps:
      - 验证页面语言为中文
      - 浏览推荐内容

  - name: VIP 用户浏览
    preset: 打开首页
    cookies:
      - name: token
        value: vip-token
        domain: .example.com
      - name: vip_level
        value: "3"
        domain: .example.com
    steps:
      - 验证显示 VIP 专属内容
      - 验证显示 VIP 标识
```

在 "VIP 用户浏览" 用例中，`token` Cookie 被用例级覆盖为 `vip-token`，同时额外注入 `vip_level` 和全局的 `lang`。
