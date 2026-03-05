"""
安全的硬件抖动控制器
此模块使用zmkx库与设备通信，避免直接操作HID导致设备异常
"""

import zmkx
from PIL import Image
import numpy as np


class SafeHardwareDither:
    """
    安全的硬件抖动实现
    使用zmkx库进行通信，避免直接HID操作导致的设备异常
    """
    
    def __init__(self):
        self.device = None
    
    def connect(self):
        """连接到设备"""
        devices = zmkx.find_devices(features=['eink'])
        
        if not devices:
            print("未找到支持E-Ink的设备")
            return False
        
        self.device = devices[0]
        print(f"已连接到设备: {self.device.product}")
        return True
    
    def convert_to_grayscale_bytes(self, image, width=None, height=None):
        """
        将图像转换为灰度字节数组
        """
        # 转换为灰度图像
        gray_img = image.convert("L")
        
        # 调整尺寸（如果指定了width和height）
        if width and height:
            gray_img = gray_img.resize((width, height))
        
        # 获取字节数组（每个像素一个字节）
        return gray_img.tobytes()
    
    def send_grayscale_image(self, image, x=None, y=None, width=None, height=None, partial=False):
        """
        发送灰度图像到设备
        注意：此方法依赖于设备端固件是否支持grayscale字段
        """
        if not self.device:
            print("设备未连接")
            return False
        
        try:
            # 将图像转换为灰度数据
            grayscale_data = self.convert_to_grayscale_bytes(image, width, height)
            
            # 获取图像尺寸
            if width is None or height is None:
                width, height = image.size
            
            print(f"发送灰度图像数据到设备... 尺寸: {len(grayscale_data)} 字节")
            print(f"图像尺寸: {width}x{height}")
            
            # 使用zmkx库的eink_set_image方法发送数据
            # 这将通过protobuf消息发送，如果设备端支持grayscale字段，会正确处理
            with self.device.open() as dev:
                # 这里我们尝试发送灰度数据，设备端会根据数据长度判断如何处理
                # 如果设备端支持grayscale，会调用eink_update_grayscale函数
                # 否则会按二值化数据处理
                result = dev.eink_set_image(
                    grayscale_data,
                    x, y, width, height,
                    partial=partial
                )
                
                print("图像已发送到设备")
                return result
                
        except Exception as e:
            print(f"发送失败: {str(e)}")
            return False


def demo_safe_hardware_dither():
    """安全的硬件抖动演示"""
    controller = SafeHardwareDither()
    
    if not controller.connect():
        print("无法连接到设备")
        return
    
    try:
        # 创建一个较小的测试图像
        print("创建测试图像...")
        width, height = 64, 128  # 使用较小的尺寸进行测试
        
        # 创建一个简单的测试图像
        img = Image.new('RGB', (width, height), color='white')
        pixels = img.load()
        
        # 创建一个简单的图案
        for x in range(width):
            for y in range(height):
                # 创建简单的渐变
                value = int(255 * ((x + y) / (width + height)))
                pixels[x, y] = (value, value, value)
        
        # 发送灰度图像
        controller.send_grayscale_image(
            img,
            x=0, y=0, width=width, height=height,
            partial=False
        )
        
        print("图像已发送到E-Ink屏幕！")
        
    except Exception as e:
        print(f"运行演示时出错: {str(e)}")


if __name__ == "__main__":
    demo_safe_hardware_dither()