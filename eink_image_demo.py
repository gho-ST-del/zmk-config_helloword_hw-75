import os
import time
from argparse import ArgumentParser
import inquirer
from PIL import Image, ImageDraw, ImageFont
import zmkx
import numpy as np

# E-Ink屏幕尺寸 - 竖屏模式
CANVAS_WIDTH = 128
CANVAS_HEIGHT = 296

# 定义Bayer抖动矩阵
bayer_matrix = np.array([
    [0, 48, 12, 60, 3, 51, 15, 63],
    [32, 16, 44, 28, 35, 19, 47, 31],
    [8, 56, 4, 52, 11, 59, 7, 55],
    [40, 24, 36, 20, 43, 27, 39, 23],
    [2, 50, 14, 62, 1, 49, 13, 61],
    [34, 18, 46, 30, 33, 17, 45, 29],
    [10, 58, 6, 54, 9, 57, 5, 53],
    [42, 26, 38, 22, 41, 25, 37, 21]
])

def bayer_dither(image, bayer_matrix):
    """使用Bayer矩阵对图像进行抖动处理"""
    gray_img = image.convert("L")  # 转为灰度图
    width, height = gray_img.size
    pixels = gray_img.load()

    # 应用Bayer抖动
    for y in range(height):
        for x in range(width):
            old_pixel = pixels[x, y]
            # 计算新像素值，考虑Bayer矩阵的阈值
            threshold = bayer_matrix[y % 8, x % 8]
            new_pixel = 255 if old_pixel > threshold * 4 else 0  # 乘以4是为了适配0-255范围
            pixels[x, y] = new_pixel

    return gray_img

def floyd_steinberg_dither(image):
    """使用Floyd-Steinberg算法进行抖动处理"""
    img = image.convert("L")  # 转为灰度图
    img_array = np.array(img).astype(np.float64)
    
    height, width = img_array.shape
    
    for y in range(height):
        for x in range(width):
            old_pixel = img_array[y, x]
            new_pixel = 255 if old_pixel > 128 else 0
            img_array[y, x] = new_pixel
            quant_error = old_pixel - new_pixel
            
            # 传播误差到相邻像素
            if x + 1 < width:
                img_array[y, x + 1] += quant_error * 7/16
            if y + 1 < height:
                if x > 0:
                    img_array[y + 1, x - 1] += quant_error * 3/16
                img_array[y + 1, x] += quant_error * 5/16
                if x + 1 < width:
                    img_array[y + 1, x + 1] += quant_error * 1/16
    
    # 转回PIL图像
    img_array = np.clip(img_array, 0, 255).astype(np.uint8)
    return Image.fromarray(img_array)

def get_device(features=[]):
    """获取设备连接"""
    devices = zmkx.find_devices(features=features)

    if len(devices) == 0:
        print('未找到符合条件的设备')
        return None

    if len(devices) == 1:
        return devices[0]

    choice = inquirer.prompt([
        inquirer.List('device', message='选择设备', choices=[
            (f'{d.manufacturer} {d.product} (SN: {d.serial})', d)
            for d in devices
        ]),
    ])

    if choice is None:
        return None

    return choice['device']

def create_test_image():
    """创建测试图像"""
    # 创建一个新图像
    img = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), color='white')
    draw = ImageDraw.Draw(img)
    
    # 绘制一些测试内容
    try:
        # 尝试使用默认字体
        font = ImageFont.load_default()
    except:
        font = None
    
    # 绘制标题
    title = "HW-75 E-Ink Demo"
    bbox = draw.textbbox((0, 0), title, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    title_x = (CANVAS_WIDTH - text_width) // 2
    draw.text((title_x, 20), title, fill='black', font=font)
    
    # 绘制渐变矩形
    for i in range(0, CANVAS_WIDTH, 4):
        # 计算颜色值，创建从黑到白的渐变
        color = int(255 * i / CANVAS_WIDTH)
        for y in range(60, 120):
            draw.point((i, y), fill=(color, color, color))
    
    # 绘制一些几何图形
    draw.rectangle([20, 130, 60, 170], outline='black', width=2)
    draw.ellipse([70, 130, 110, 170], outline='black', width=2)
    draw.line([0, 180, CANVAS_WIDTH, 180], fill='black', width=2)
    
    # 添加一些文字
    text = "Hello World!"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = (CANVAS_WIDTH - text_width) // 2
    draw.text((text_x, 200), text, fill='black', font=font)
    
    # 添加时间戳
    timestamp = time.strftime("%H:%M:%S")
    bbox = draw.textbbox((0, 0), timestamp, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = (CANVAS_WIDTH - text_width) // 2
    draw.text((text_x, 240), timestamp, fill='black', font=font)
    
    return img

def main():
    parser = ArgumentParser()
    parser.add_argument('--image', help='指定要显示的图片文件路径，如果不指定则使用测试图像')
    parser.add_argument('--dither', choices=['none', 'bayer', 'floyd'], default='floyd', 
                        help='选择抖动算法 (默认: floyd)')
    
    args = parser.parse_args()

    # 连接设备
    device = get_device(features=['knob'])
    if device is None:
        print("未找到设备")
        return

    # 准备图像
    if args.image and os.path.exists(args.image):
        image = Image.open(args.image)
    else:
        print("使用测试图像")
        image = create_test_image()
    
    # 调整图像大小以适应屏幕
    image = image.convert('RGB')
    image.thumbnail((CANVAS_WIDTH, CANVAS_HEIGHT), Image.LANCZOS)
    
    # 居中放置图像
    canvas = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), color='white')
    offset = ((CANVAS_WIDTH - image.width) // 2, (CANVAS_HEIGHT - image.height) // 2)
    canvas.paste(image, offset)
    
    print(f"原始图像尺寸: {canvas.width}x{canvas.height}")
    
    # 应用抖动算法
    if args.dither == 'bayer':
        print("应用Bayer抖动算法...")
        processed_img = bayer_dither(canvas, bayer_matrix)
    elif args.dither == 'floyd':
        print("应用Floyd-Steinberg抖动算法...")
        processed_img = floyd_steinberg_dither(canvas)
    else:
        print("不使用抖动算法，直接转换为黑白...")
        processed_img = canvas.convert('1', dither=Image.NONE)
    
    # 转换为1位黑白图像并获取字节数据
    if processed_img.mode != '1':
        processed_img = processed_img.convert('1')
    
    # 将图像数据转换为字节数组
    img_bytes = processed_img.tobytes()
    print(f"图像数据大小: {len(img_bytes)} 字节")
    print(f"期望大小: {(CANVAS_WIDTH * CANVAS_HEIGHT) // 8} 字节")
    
    # 发送到E-Ink屏幕
    print("正在发送图像到E-Ink屏幕...")
    with device.open() as dev:
        # 使用与成功代码相同的调用方式
        dev.eink_set_image(img_bytes, 0, 0, CANVAS_WIDTH, CANVAS_HEIGHT, partial=False)
    
    print("图像已发送到E-Ink屏幕！")

if __name__ == '__main__':
    main()