# PyPI 可信发布者配置指南

burunner 使用 [PyPI 可信发布者（Trusted Publisher）](https://docs.pypi.org/trusted-publishers/) 机制进行自动发布，无需手动配置 API Token。

## 配置步骤

### 1. 在 PyPI 注册项目

首次发布前，需要先在 PyPI 注册项目名称：

1. 访问 https://pypi.org/account/register/ 注册账号
2. 确保项目名称 `burunner` 可用

### 2. 配置 GitHub 仓库

#### 2.1 创建 PyPI 环境

1. 打开 GitHub 仓库 → Settings → Environments
2. 点击 "New environment"
3. 创建名为 `pypi` 的环境
4. （可选）设置环境保护规则

#### 2.2 配置可信发布者

1. 访问 https://pypi.org/manage/account/publishing/
2. 点击 "Add a pending publisher"
3. 填写以下信息：
   - **Project name**: `burunner`
   - **Owner**: `XiaoMiSum`（你的 GitHub 用户名）
   - **Repository**: `burunner`（仓库名）
   - **Workflow**: `publish.yml`
   - **Environment**: `pypi`
   - **Branch**: `master`

4. 提交后会生成 Pending Publisher

### 3. 测试发布（可选）

建议先在 TestPyPI 上测试：

1. 在 PyPI Test 注册账号：https://test.pypi.org/
2. 配置 `testpypi` 环境（同步骤 2.1）
3. 添加 TestPyPI 的可信发布者（同步骤 2.2）
4. 手动触发工作流：
   ```bash
   gh workflow run publish.yml
   ```

### 4. 正式发布

1. 更新版本号（在 `pyproject.toml` 中）
2. 创建 Git Tag：
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```
3. 在 GitHub 创建 Release：
   - 访问 https://github.com/XiaoMiSum/burunner/releases
   - 点击 "Draft a new release"
   - 选择刚才创建的 tag
   - 填写发布说明
   - 点击 "Publish release"

4. GitHub Actions 会自动：
   - 构建 wheel 和 sdist
   - 验证分发包
   - 发布到 PyPI

## 安全优势

✅ **无需 API Token** - 避免令牌泄露风险  
✅ **OIDC 认证** - 使用 GitHub Actions 的 OIDC 令牌  
✅ **环境隔离** - PyPI 发布在独立环境中进行  
✅ **可追溯** - 每次发布都有完整的 GitHub Actions 日志  

## 故障排查

### 发布失败

检查 GitHub Actions 日志，常见原因：
- 项目名称已被占用
- 版本号已存在
- 可信发布者配置不匹配

### 权限错误

确保：
- 仓库 Settings → Actions → General → Workflow permissions 设置为 "Read and write permissions"
- Environment 配置正确
- Trusted Publisher 已批准

## 参考资料

- [PyPI Trusted Publishing 文档](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions 发布指南](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [pypa/gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish)
