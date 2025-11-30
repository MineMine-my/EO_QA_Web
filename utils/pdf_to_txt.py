import os
from pathlib import Path
import time


def pdf_to_text_simple(pdf_folder, text_folder):
    """
    使用简单可靠的PDF处理库
    """

    # 创建输出文件夹
    Path(text_folder).mkdir(parents=True, exist_ok=True)

    # 获取所有PDF文件
    pdf_files = list(Path(pdf_folder).glob("*.pdf"))
    pdf_files.extend(Path(pdf_folder).glob("*.PDF"))

    if not pdf_files:
        print(f"在文件夹 {pdf_folder} 中没有找到PDF文件")
        return

    print(f"找到 {len(pdf_files)} 个PDF文件")

    success_count = 0
    error_count = 0

    for pdf_path in pdf_files:
        try:
            print(f"正在处理: {pdf_path.name}")
            start_time = time.time()

            # 方法1：优先尝试使用pdfplumber（最稳定）
            text_content = extract_text_with_pdfplumber(pdf_path)

            # 如果pdfplumber失败，尝试pymupdf
            if not text_content.strip():
                text_content = extract_text_with_pymupdf(pdf_path)

            # 如果还是没有内容，使用最后的手段
            if not text_content.strip():
                text_content = extract_text_fallback(pdf_path)

            # 生成输出文件名
            output_filename = pdf_path.stem + ".txt"
            output_path = Path(text_folder) / output_filename

            # 保存文本文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text_content)

            processing_time = time.time() - start_time
            print(f"✓ 完成: {pdf_path.name} -> {output_filename} (耗时: {processing_time:.2f}秒)")
            print(f"提取字符数: {len(text_content)}")
            success_count += 1

        except Exception as e:
            print(f"✗ 处理失败: {pdf_path.name} - 错误: {str(e)}")
            error_count += 1

    print(f"\n转换完成!")
    print(f"成功: {success_count} 个文件")
    print(f"失败: {error_count} 个文件")


def extract_text_with_pdfplumber(pdf_path):
    """使用pdfplumber提取文本"""
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        return text
    except ImportError:
        print("pdfplumber未安装，将尝试其他方法")
        return ""
    except Exception as e:
        print(f"pdfplumber处理失败: {e}")
        return ""


def extract_text_with_pymupdf(pdf_path):
    """使用pymupdf (fitz) 提取文本"""
    try:
        import fitz
        text = ""
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text() + "\n\n"
        doc.close()
        return text
    except ImportError:
        print("pymupdf未安装，将尝试其他方法")
        return ""
    except Exception as e:
        print(f"pymupdf处理失败: {e}")
        return ""


def extract_text_fallback(pdf_path):
    """最后的手段：使用pdfminer或其他简单方法"""
    try:
        # 尝试使用pdfminer（更轻量）
        from io import StringIO
        from pdfminer.high_level import extract_text_to_fp
        from pdfminer.layout import LAParams

        output_string = StringIO()
        with open(pdf_path, 'rb') as pdf_file:
            extract_text_to_fp(pdf_file, output_string, laparams=LAParams())
        return output_string.getvalue()
    except:
        return "无法提取文本内容"


def main():
    pdf_folder = r"D:\作业过渡\dachuang\file---pdf"
    text_folder = r"D:\作业过渡\dachuang\file---text"

    if not os.path.exists(pdf_folder):
        print(f"错误: PDF文件夹不存在 - {pdf_folder}")
        return

    pdf_to_text_simple(pdf_folder, text_folder)


if __name__ == "__main__":
    main()