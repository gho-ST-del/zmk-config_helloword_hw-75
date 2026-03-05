"""
扩展zmkx库以支持硬件抖动功能
此模块扩展了原始zmkx库，添加了对设备端硬件抖动的支持
"""

import zmkx
from PIL import Image


class ExtendedDevice(zmkx.Device):
    """
    扩展的zmkx.Device类，添加了对硬件抖动的支持
    """
    
    def eink_set_grayscale_image(self, image, x=None, y=None, width=None, height=None, partial=False):
        """
        发送灰度图像到E-Ink屏幕，设备端将应用Floyd-Steinberg抖动算法
        这是一个与eink_set_image平级的新方法，直接发送灰度数据到设备端
        """
        # 复用原始的 eink_set_image 方法
        # 设备端将根据数据长度自动识别为灰度图像并启用硬件抖动
        return self.eink_set_image(image, x, y, width, height, partial)


def find_devices_extended(serial=None, features=[]):
    """
    扩展的设备查找函数，返回ExtendedDevice实例
    """
    # 使用原始函数查找设备
    original_devices = zmkx.find_devices(serial=serial, features=features)
    
    # 将原始设备包装为扩展设备
    extended_devices = []
    for original_device in original_devices:
        # 创建ExtendedDevice实例，需要传入原始设备的属性
        extended_device = ExtendedDevice(original_device.path, original_device.usage)
        extended_devices.append(extended_device)
    
    return extended_devices


def find_device_extended(features=[]):
    """
    查找单个设备并返回ExtendedDevice实例
    """
    devices = find_devices_extended(features=features)
    
    if not devices:
        return None
    
    return devices[0]


def demo_hardware_dither():
    """
    硬件抖动演示函数
    """
    print("正在查找支持E-Ink的设备...")
    device = find_device_extended(features=['eink'])
    
    if device is None:
        print("未找到设备")
        return
    
    # 在访问设备属性之前需要先打开设备
    print(f"找到设备，路径: {device.path}")
    
    with device.open() as dev:
        # 访问设备信息
        print(f"已连接到设备: {dev.product}")
        
        # 创建一个较小的测试图像用于测试
        print("创建测试图像...")
        width, height = 64, 128  # 使用较小的尺寸进行测试
        
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
        
        # 转换为灰度图像
        gray_img = img.convert("L")
        img_bytes = gray_img.tobytes()
        
        print(f"发送灰度图像数据到设备（启用硬件抖动）... 尺寸: {len(img_bytes)} 字节")
        # 发送灰度图像，设备端将应用抖动算法
        dev.eink_set_grayscale_image(
            img_bytes, 
            x=0, y=0, width=width, height=height, 
            partial=False
        )
        
        print("图像已发送到E-Ink屏幕！")


if __name__ == "__main__":
    demo_hardware_dither()