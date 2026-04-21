# PDF文字批量替换工具

## 功能说明
批量替换PDF中的任意文字，适用于线下物料的快速修改。

## 支持的替换类型
- 班号（如 B250728 → B260830）
- 日期（如 2025 → 2026）
- 地点、人名、课程名等任何文字
- 支持中文和英文

## 部署步骤

### 方法一：Render 部署（推荐）

1. 在 GitHub 创建新仓库
2. 上传本工具的三个文件：
   - `app.py`
   - `requirements.txt`
   - `README.md`
3. 访问 [Render](https://render.com)
4. 创建新的 Web Service，连接 GitHub 仓库
5. 配置：
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
6. 部署完成后获得公网地址

### 方法二：Streamlit Cloud 部署

1. 将代码上传到 GitHub
2. 访问 [share.streamlit.io](https://share.streamlit.io)
3. 连接 GitHub 仓库并部署

## 使用说明

1. **上传PDF文件** - 可同时上传多个文件
2. **上传字体文件** - 推荐，确保新文字正确显示
3. **输入替换内容** - 每行一组，格式：`旧文字 → 新文字`
4. **点击替换** - 下载处理后的文件

## 替换格式示例

```
B250728 → B260830
2025 → 2026
张三 → 李四
开学典礼 = 结业典礼
```

支持 `→` 或 `=` 作为分隔符

## 注意事项

- PDF中的字体通常是子集化的，建议上传完整字体文件
- 支持的字体格式：TTF
- 如果新文字显示异常，请检查字体文件是否正确

## 技术栈
- Streamlit - Web界面
- PyMuPDF - PDF处理
