"""
PDF文字批量替换工具 v1.0
支持替换任意文字，不再局限于班号
作者：微酱
"""

import streamlit as st
import pymupdf
import zipfile
import io
import re
from datetime import datetime

st.set_page_config(
    page_title="PDF文字替换工具",
    page_icon="📝",
    layout="wide"
)

st.title("📝 PDF文字批量替换工具")
st.markdown("---")

with st.expander("📖 使用说明"):
    st.markdown("""
    ### 功能说明
    批量替换PDF中的任意文字，支持：
    - 班号、日期、地点、人名等任何文字
    - 多个PDF文件同时处理
    - 多组文字同时替换
    
    ### 为什么需要上传字体？
    PDF中的字体通常是**子集化**的，只包含文档中已使用的字符。
    如果新文字包含原文没有的字符，就必须上传完整字体文件。
    
    ### 使用步骤
    1. 上传PDF文件
    2. 上传字体文件（可多个，如 Regular + Bold）
    3. 输入要替换的文字对（每行一组：旧文字 → 新文字）
    4. 点击开始替换
    """)

st.markdown("### 1️⃣ 上传PDF文件")
uploaded_files = st.file_uploader(
    "选择PDF文件（可多选）",
    type=["pdf"],
    accept_multiple_files=True
)
if uploaded_files:
    st.success(f"已上传 {len(uploaded_files)} 个文件")
    
    # 显示PDF中的字体信息
    if st.checkbox("查看PDF字体信息"):
        for f in uploaded_files[:3]:
            st.text(f"\n📄 {f.name}")
            try:
                pdf_bytes = f.read()
                doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
                for page in doc[:1]:
                    fonts = page.get_fonts()
                    for font in fonts:
                        st.text(f"  字体: {font[3]}")
                doc.close()
                f.seek(0)  # 重置指针
            except Exception as e:
                st.text(f"  读取失败: {e}")

st.markdown("---")
st.markdown("### 2️⃣ 上传字体文件（推荐）")
font_files = st.file_uploader(
    "上传字体文件（TTF格式，可上传多个）",
    type=["ttf"],
    accept_multiple_files=True,
    help="上传PDF中使用的字体文件，确保新文字能正确显示"
)
if font_files:
    st.success(f"已上传 {len(font_files)} 个字体文件")
    for f in font_files:
        st.text(f"  • {f.name}")

st.markdown("---")
st.markdown("### 3️⃣ 输入替换内容")

st.markdown("**格式：每行一组，用 `→` 或 `=` 分隔旧文字和新文字**")
st.markdown("示例：")
st.code("""
B250728 → B260830
2025 → 2026
张三 → 李四
开学典礼 = 结业典礼
""")

replace_input = st.text_area(
    "输入要替换的文字对",
    height=150,
    placeholder="B250728 → B260830\n2025 → 2026\n张三 → 李四"
)

def parse_replace_pairs(text):
    """解析替换对"""
    pairs = []
    if not text:
        return pairs
    
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # 支持 → 和 = 作为分隔符
        if '→' in line:
            parts = line.split('→', 1)
        elif '=' in line:
            parts = line.split('=', 1)
        else:
            continue
        
        if len(parts) == 2:
            old_text = parts[0].strip()
            new_text = parts[1].strip()
            if old_text and new_text:
                pairs.append((old_text, new_text))
    
    return pairs

replace_pairs = parse_replace_pairs(replace_input)

if replace_pairs:
    st.success(f"✅ 识别到 {len(replace_pairs)} 组替换")
    for old, new in replace_pairs:
        st.text(f"  '{old}' → '{new}'")
elif replace_input:
    st.warning("⚠️ 未能识别替换内容，请检查格式")

st.markdown("---")
st.markdown("### 4️⃣ 开始替换")

can_process = (
    uploaded_files and 
    len(replace_pairs) > 0
)

if not font_files and can_process:
    st.info("💡 建议上传字体文件，以确保替换效果")


def get_pixel_color(page, x, y):
    """获取指定坐标的像素颜色"""
    try:
        rect = pymupdf.Rect(x-2, y-2, x+2, y+2)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=rect)
        cx, cy = pix.width // 2, pix.height // 2
        pixel = pix.pixel(cx, cy)
        return (pixel[0]/255, pixel[1]/255, pixel[2]/255)
    except:
        return None


def get_background_color(page, rect):
    """智能获取背景色"""
    samples = []
    sample_points = [
        (rect.x0 - 5, rect.y0 - 5),
        (rect.x1 + 5, rect.y0 - 5),
        (rect.x0 - 5, rect.y1 + 5),
        (rect.x1 + 5, rect.y1 + 5),
        (rect.x0 - 5, (rect.y0 + rect.y1) / 2),
        (rect.x1 + 5, (rect.y0 + rect.y1) / 2),
    ]
    
    for x, y in sample_points:
        if 0 <= x <= page.rect.width and 0 <= y <= page.rect.height:
            color = get_pixel_color(page, x, y)
            if color:
                samples.append(color)
    
    if samples:
        r_sorted = sorted([s[0] for s in samples])
        g_sorted = sorted([s[1] for s in samples])
        b_sorted = sorted([s[2] for s in samples])
        mid = len(samples) // 2
        return (r_sorted[mid], g_sorted[mid], b_sorted[mid])
    
    return (0.8, 0.2, 0.2)


def replace_text(page, old_text, new_text, fonts_data):
    """替换文字"""
    replacements = 0
    
    # 搜索所有匹配位置
    instances = page.search_for(old_text)
    
    if not instances:
        return 0
    
    for rect in instances:
        try:
            # 获取文本样式
            text_info = page.get_text("dict", clip=rect)
            
            font_size = 14
            text_color = (1, 1, 1)
            
            for block in text_info.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            font_size = span.get("size", 14)
                            color = span.get("color", 0)
                            if isinstance(color, int):
                                r = ((color >> 16) & 0xFF) / 255.0
                                g = ((color >> 8) & 0xFF) / 255.0
                                b = (color & 0xFF) / 255.0
                                text_color = (r, g, b)
            
            # 获取背景色
            bg_color = get_background_color(page, rect)
            
            # 覆盖原文字
            cover_rect = pymupdf.Rect(
                rect.x0 - 0.5, rect.y0 - 0.5,
                rect.x1 + 0.5, rect.y1 + 0.5
            )
            page.draw_rect(cover_rect, color=bg_color, fill=bg_color)
            
            # 注册字体
            if fonts_data:
                for font_name, font_buffer in fonts_data.items():
                    try:
                        page.insert_font(fontname=font_name, fontbuffer=font_buffer)
                    except:
                        pass
            
            # 插入新文字
            insert_y = rect.y1 - font_size * 0.25
            primary_font = list(fonts_data.keys())[0] if fonts_data else "helv"
            
            page.insert_text(
                (rect.x0, insert_y),
                new_text,
                fontname=primary_font,
                fontsize=font_size,
                color=text_color
            )
            
            replacements += 1
            
        except Exception as e:
            st.text(f"  替换出错: {e}")
    
    return replacements


if st.button("🚀 开始替换", disabled=not can_process, type="primary"):
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    processed_files = []
    
    # 读取所有字体
    fonts_data = {}
    if font_files:
        for f in font_files:
            font_name = f.name.replace(" ", "_").replace(".", "_")
            fonts_data[font_name] = f.read()
    
    for i, uploaded_file in enumerate(uploaded_files):
        try:
            status_text.text(f"处理: {uploaded_file.name} ({i+1}/{len(uploaded_files)})")
            
            pdf_bytes = uploaded_file.read()
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            
            total_replacements = 0
            
            for page_num, page in enumerate(doc):
                for old_text, new_text in replace_pairs:
                    instances = page.search_for(old_text)
                    if instances:
                        st.text(f"  第{page_num+1}页: '{old_text}' 找到 {len(instances)} 处")
                    
                    reps = replace_text(page, old_text, new_text, fonts_data)
                    total_replacements += reps
            
            # 保存
            output_buffer = io.BytesIO()
            doc.save(output_buffer, garbage=4, deflate=True)
            doc.close()
            
            output_buffer.seek(0)
            new_name = uploaded_file.name.replace(".pdf", "_replaced.pdf")
            processed_files.append({
                "name": new_name,
                "data": output_buffer,
                "replacements": total_replacements
            })
            
            st.success(f"✅ {uploaded_file.name}: 替换了 {total_replacements} 处")
            
        except Exception as e:
            st.error(f"处理失败: {uploaded_file.name} - {e}")
        
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    status_text.text("处理完成！")
    
    st.markdown("---")
    st.markdown("### 5️⃣ 下载结果")
    
    total_reps = sum(f["replacements"] for f in processed_files)
    st.metric("总替换次数", total_reps)
    
    if len(processed_files) == 1:
        st.download_button(
            "📥 下载处理后的文件",
            data=processed_files[0]["data"],
            file_name=processed_files[0]["name"],
            mime="application/pdf"
        )
    elif len(processed_files) > 1:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in processed_files:
                zf.writestr(f["name"], f["data"].getvalue())
        zip_buffer.seek(0)
        
        st.download_button(
            "📥 下载所有文件（ZIP）",
            data=zip_buffer,
            file_name=f"PDF替换结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip"
        )

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 12px;">
    Made with ❤️ by 微酱 | v1.0 通用版
</div>
""", unsafe_allow_html=True)
