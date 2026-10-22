#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把高清图片转成 PDF。

默认：每张图占一页，页面尺寸 = 图片尺寸（按 --dpi 换算），无白边，适合印刷封面/精装书脊。

用法示例：
    python img2pdf.py 封面.jpg 内页1.png 内页2.png -o 输出.pdf
    python img2pdf.py ./图片文件夹 -o 输出.pdf
    python img2pdf.py *.png
    python img2pdf.py 封面.jpg --separate            # 每张图单独生成一个 PDF
    python img2pdf.py 图.png --dpi 300 --quality 100 # 最高保真
    python img2pdf.py ./文件夹 -r                     # 递归收集子文件夹

说明：
    --dpi 决定页面物理尺寸：像素 ÷ DPI × 2.54 = 厘米。
    例如 2550×3300 像素、300 DPI → 21.59×27.94 厘米（8.5×11 英寸）。
    若需指定成品尺寸，调整 --dpi 即可，图片本身不缩放、不裁剪。
"""

import argparse
import os
import re
import sys

from PIL import Image, ImageOps

# 解除超大图（高清大图）的解压炸弹保护限制
Image.MAX_IMAGE_PIXELS = None

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".gif"}


def natural_key(name):
    """自然排序：数字按数值比较，如 图2 < 图10。"""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def collect_files(paths, recursive):
    files = []
    for p in paths:
        if os.path.isdir(p):
            if recursive:
                for root, _dirs, names in os.walk(p):
                    for n in names:
                        if os.path.splitext(n)[1].lower() in IMAGE_EXTS:
                            files.append(os.path.join(root, n))
            else:
                for n in os.listdir(p):
                    if os.path.splitext(n)[1].lower() in IMAGE_EXTS:
                        full = os.path.join(p, n)
                        if os.path.isfile(full):
                            files.append(full)
        elif os.path.isfile(p):
            files.append(p)
        else:
            print(f"[跳过] 找不到：{p}", file=sys.stderr)

    seen, uniq = set(), []
    for f in files:
        a = os.path.abspath(f)
        if a not in seen:
            seen.add(a)
            uniq.append(f)
    uniq.sort(key=lambda f: natural_key(os.path.basename(f)))
    return uniq


def load_image(path):
    im = Image.open(path)
    im.load()
    # 按 EXIF 方向信息纠正（手机/相机照片常见）
    im = ImageOps.exif_transpose(im)

    # 透明背景 → 白底（印刷封面通常是白底）
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    elif im.mode == "P":
        im = im.convert("RGB")
    elif im.mode not in ("RGB", "L", "CMYK"):
        im = im.convert("RGB")
    return im


def save_pdf(images, output, dpi, quality):
    first, rest = images[0], images[1:]
    first.save(
        output,
        "PDF",
        resolution=dpi,
        quality=quality,
        save_all=True,
        append_images=rest,
    )


def main(argv):
    ap = argparse.ArgumentParser(
        description="把高清图片转成 PDF（每张图一页，页面尺寸 = 图片尺寸）。"
    )
    ap.add_argument("inputs", nargs="+", help="图片文件，或包含图片的文件夹")
    ap.add_argument("-o", "--output",
                    help="输出 PDF 路径（默认：第一张图所在目录/输出.pdf；"
                         "--separate 时视为输出目录）")
    ap.add_argument("--dpi", type=int, default=300, help="页面分辨率 DPI（默认 300）")
    ap.add_argument("--quality", type=int, default=95,
                    help="JPEG 质量 1-100（默认 95，100 最高保真、文件更大）")
    ap.add_argument("--separate", action="store_true", help="每张图片单独生成一个 PDF")
    ap.add_argument("-r", "--recursive", action="store_true",
                    help="递归收集子文件夹中的图片")
    args = ap.parse_args(argv)

    if not (1 <= args.quality <= 100):
        print("错误：--quality 需在 1-100 之间。", file=sys.stderr)
        return 1
    if args.dpi <= 0:
        print("错误：--dpi 需为正数。", file=sys.stderr)
        return 1

    files = collect_files(args.inputs, args.recursive)
    if not files:
        print("没有找到可转换的图片（支持 jpg/png/bmp/tif/webp/gif）。", file=sys.stderr)
        return 1

    if args.separate:
        out_dir = args.output or os.path.dirname(os.path.abspath(files[0]))
        if args.output:
            os.makedirs(out_dir, exist_ok=True)
        for f in files:
            try:
                im = load_image(f)
            except Exception as e:
                print(f"[跳过] 无法读取 {f}：{e}", file=sys.stderr)
                continue
            out = os.path.join(out_dir, os.path.splitext(os.path.basename(f))[0] + ".pdf")
            im.save(out, "PDF", resolution=args.dpi, quality=args.quality)
            print(f"已生成：{out}")
        return 0

    output = args.output or os.path.join(
        os.path.dirname(os.path.abspath(files[0])), "输出.pdf"
    )
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)

    images = []
    for f in files:
        try:
            images.append(load_image(f))
        except Exception as e:
            print(f"[跳过] 无法读取 {f}：{e}", file=sys.stderr)
    if not images:
        print("没有任何图片可以转换。", file=sys.stderr)
        return 1

    save_pdf(images, output, args.dpi, args.quality)
    print(f"已生成：{output}（共 {len(images)} 页）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
