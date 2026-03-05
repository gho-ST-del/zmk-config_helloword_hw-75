"""
HW-75 E-Ink 硬件抖动支持模块

这个模块扩展了zmkx库的功能，增加了对设备端硬件抖动的支持。
设备端内置了Floyd-Steinberg抖动算法，可以通过发送灰度图像数据来利用此功能。
"""

import zmkx
from PIL import Image
import numpy as np


class EInkHardwareDither:
    """
    E-Ink硬件抖动支持类
    扩展zmkx.Device功能，支持发送灰度数据以利用设备端抖动算法
    """
    
    def __init__(self, device):
        """
        初始化硬件抖动支持
        :param device: 已连接的zmkx.Device实例
        """
        self.device = device
    
    def eink_set_grayscale_image(self, image, x=None, y=None, width=None, height=None, partial=False):
        """
        发送灰度图像到E-Ink屏幕，设备端将应用Floyd-Steinberg抖动算法
        :param image: PIL图像对象或灰度字节数组
        :param x: X坐标（可选）
        :param y: Y坐标（可选）
        :param width: 图像宽度（可选）
        :param height: 图像高度（可选）
        :param partial: 是否使用部分刷新
        :return: 响应对象
        """
        # 如果传入的是PIL图像对象，转换为灰度字节数组
        if isinstance(image, Image.Image):
            # 转换为灰度图像
            gray_img = image.convert("L")
            
            # 调整尺寸（如果指定了width和height）
            if width and height:
                gray_img = gray_img.resize((width, height))
            
            # 获取字节数组
            img_bytes = gray_img.tobytes()
        else:
            # 假设已经是字节数组
            img_bytes = image
        
        # 调用设备的eink_set_image方法，但这里我们发送的是灰度数据
        # 设备端的eink_update_grayscale函数将处理抖动
        return self.device.eink_set_image(
            img_bytes, 
            x, y, width, height, 
            partial=partial
        )
    
    def apply_floyd_steinberg_dither_to_image(self, image):
        """
        在上位机应用Floyd-Steinberg抖动（可选功能，用于对比）
        :param image: PIL图像对象
        :return: 抖动处理后的二值化图像
        """
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


def find_device_with_dither_support(**kwargs):
    """
    查找设备并返回带有硬件抖动支持的包装器
    :param kwargs: 传递给zmkx.find_devices的参数
    :return: EInkHardwareDither实例
    """
    devices = zmkx.find_devices(**kwargs)
    
    if not devices:
        return None
    
    # 使用第一个设备
    device = devices[0]
    return EInkHardwareDither(device)


def demo_hardware_dither():
    """
    硬件抖动演示函数
    """
    print("正在查找支持E-Ink的设备...")
    dither_tool = find_device_with_dither_support(features=['eink'])
    
    if dither_tool is None:
        print("未找到设备")
        return
    
    print(f"已连接到设备: {dither_tool.device.product}")
    
    with dither_tool.device.open() as dev:
        # 创建一个测试图像
        print("创建测试图像...")
        width, height = 128, 296  # HW-75 E-Ink屏幕尺寸
        
        # 创建一个带渐变的测试图像
        img = Image.new('RGB', (width, height), color='white')
        pixels = img.load()
        
        # 创建从左到右的渐变
        for x in range(width):
            for y in range(height):
                # 创建一个复杂的渐变模式
                r = int(255 * x / width)
                g = int(255 * y / height)
                b = int(128 + 127 * (x + y) / (width + height))
                pixels[x, y] = (r, g, b)
        
        print("发送灰度图像到设备（启用硬件抖动）...")
        # 发送灰度图像，设备端将应用抖动算法
        dither_tool.eink_set_grayscale_image(
            img, 
            x=0, y=0, width=width, height=height, 
            partial=False
        )
        
        print("图像已发送到E-Ink屏幕！")


if __name__ == "__main__":
    demo_hardware_dither()