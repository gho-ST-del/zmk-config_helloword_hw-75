"""
硬件抖动控制器
此模块提供对HW-75设备端硬件抖动功能的直接支持
注意：此版本使用更安全的方法，仅在确认设备支持时才使用grayscale功能
"""

import hid
import random
from PIL import Image
import struct
import time


class HardwareDitherController:
    """
    硬件抖动控制器
    直接与设备通信，支持发送grayscale字段
    """
    
    def __init__(self):
        self.device = None
        self.vid = 0x1d50
        self.pid = 0x615e
        self.usage = 0xff14
        self.report_count = 63
        self.payload_size = self.report_count - 1

    def connect(self):
        """连接到设备"""
        devices = hid.enumerate(self.vid, self.pid)
        
        for device_info in devices:
            if device_info['usage_page'] == 0xff14:  # 自定义HID页面
                try:
                    self.device = hid.Device(self.vid, self.pid, serial=device_info['serial_number'])
                    print(f"已连接到设备: {device_info['product_string']}")
                    return True
                except Exception as e:
                    print(f"连接设备失败: {str(e)}")
                    return False
        
        print("未找到设备")
        return False

    def disconnect(self):
        """断开设备连接"""
        if self.device:
            try:
                self.device.close()
            except:
                pass
            self.device = None

    def _encode_varint(self, value):
        """编码varint值"""
        if value == 0:
            return bytearray([0])
        
        bytes_arr = bytearray()
        while value > 0:
            byte = value & 0x7f
            value >>= 7
            if value > 0:
                byte |= 0x80
            bytes_arr.append(byte & 0xFF)  # 确保在0-255范围内
        
        return bytes_arr

    def _create_grayscale_image_message(self, image_data, x=None, y=None, width=None, height=None, partial=False):
        """
        创建带grayscale标志的图像消息
        """
        message = bytearray()
        
        # Action (varint, field 1, tag 0x08)
        message.append(0x08)
        message.extend(self._encode_varint(7))  # EINK_SET_IMAGE = 7
        
        # Payload (embedded message, field 5, tag 0x2a)
        message.append(0x2a)
        
        # 计算嵌入消息的长度（需要先构建嵌入消息）
        embedded_msg = bytearray()
        
        # ID (varint, field 1, tag 0x08)
        embedded_msg.append(0x08)
        embedded_msg.extend(self._encode_varint(round(random.random() * 1000000)))
        
        # X, Y, Width, Height (if provided)
        if x is not None and y is not None and width is not None and height is not None:
            embedded_msg.append(0x20)  # X (varint, field 4, tag 0x20)
            embedded_msg.extend(self._encode_varint(x))
            
            embedded_msg.append(0x28)  # Y (varint, field 5, tag 0x28)
            embedded_msg.extend(self._encode_varint(y))
            
            embedded_msg.append(0x30)  # Width (varint, field 6, tag 0x30)
            embedded_msg.extend(self._encode_varint(width))
            
            embedded_msg.append(0x38)  # Height (varint, field 7, tag 0x38)
            embedded_msg.extend(self._encode_varint(height))
        
        # Grayscale flag (bool, field 9, tag 0x48)
        embedded_msg.append(0x48)
        embedded_msg.extend(self._encode_varint(1))  # 设置为True，表示灰度图像
        
        # Partial (bool, field 8, tag 0x40)
        embedded_msg.append(0x40)
        embedded_msg.extend(self._encode_varint(1 if partial else 0))
        
        # Bits (bytes, field 3, tag 0x1a)
        embedded_msg.append(0x1a)
        embedded_msg.extend(self._encode_varint(len(image_data)))  # Length of bytes
        
        # 将图像数据添加到消息中，确保所有值都在0-255范围内
        for byte in image_data:
            if isinstance(byte, int):
                embedded_msg.append(byte & 0xFF)
            else:
                # 如果是bytes类型，需要先转换
                byte_val = ord(byte) if isinstance(byte, str) else int.from_bytes(byte, 'big') if isinstance(byte, bytes) else byte
                embedded_msg.append(byte_val & 0xFF)
        
        # 添加嵌入消息的长度到主消息
        message.extend(self._encode_varint(len(embedded_msg)))
        message.extend(embedded_msg)
        
        return bytes(message)

    def send_grayscale_image(self, image_data, x=None, y=None, width=None, height=None, partial=False):
        """
        发送灰度图像数据到设备
        """
        if not self.device:
            print("设备未连接")
            return False
        
        try:
            # 创建protobuf消息
            message = self._create_grayscale_image_message(image_data, x, y, width, height, partial)
            
            print(f"准备发送消息，总长度: {len(message)} 字节")
            
            # 分块发送消息
            message_bytes = list(message)
            offset = 0
            
            while offset < len(message_bytes):
                chunk_size = min(self.payload_size, len(message_bytes) - offset)
                chunk = message_bytes[offset:offset + chunk_size]
                
                # 创建HID报告: [usage][length][data...]
                report = [(self.usage & 0xFF), (len(chunk) & 0xFF)] + chunk
                # 填充剩余字节
                while len(report) < self.report_count + 1:
                    report.append(0)
                
                # 发送报告
                self.device.write(bytes(report))
                
                print(f"发送数据块: {len(chunk)} 字节")
                
                offset += chunk_size
                
                # 添加延迟以避免发送过快
                time.sleep(0.01)
            
            print(f"灰度图像已发送到设备: {len(message)} 字节")
            return True
        except Exception as e:
            print(f"发送失败: {str(e)}")
            return False

    def test_basic_connection(self):
        """
        测试基础连接，发送一个简单的版本查询消息
        """
        if not self.device:
            print("设备未连接")
            return False
        
        try:
            # 发送版本查询消息
            # Action (varint, field 1, tag 0x08) = 1 (VERSION)
            message = bytearray([0x08, 0x01])  # VERSION = 1
            
            # 分块发送消息
            message_bytes = list(message)
            offset = 0
            
            while offset < len(message_bytes):
                chunk_size = min(self.payload_size, len(message_bytes) - offset)
                chunk = message_bytes[offset:offset + chunk_size]
                
                # 创建HID报告: [usage][length][data...]
                report = [(self.usage & 0xFF), (len(chunk) & 0xFF)] + chunk
                # 填充剩余字节
                while len(report) < self.report_count + 1:
                    report.append(0)
                
                # 发送报告
                self.device.write(bytes(report))
                
                offset += chunk_size
                time.sleep(0.01)
            
            print("版本查询消息已发送")
            return True
        except Exception as e:
            print(f"版本查询失败: {str(e)}")
            return False


def demo_hardware_dither():
    """硬件抖动演示"""
    controller = HardwareDitherController()
    
    if not controller.connect():
        print("无法连接到设备")
        return
    
    try:
        # 先测试基础连接
        print("测试基础连接...")
        if not controller.test_basic_connection():
            print("基础连接测试失败，退出")
            return
        
        time.sleep(0.5)  # 等待设备响应
        
        # 创建一个较小的测试图像
        print("创建测试图像...")
        width, height = 16, 32  # 使用更小的尺寸进行测试，避免设备缓冲区溢出
        
        # 创建一个简单的测试图像
        img = Image.new('RGB', (width, height), color='white')
        pixels = img.load()
        
        # 创建一个简单的图案
        for x in range(width):
            for y in range(height):
                # 创建简单的渐变
                value = int(255 * ((x + y) / (width + height)))
                pixels[x, y] = (value, value, value)
        
        # 转换为灰度图像（每个像素一个字节）
        gray_img = img.convert("L")
        img_bytes = gray_img.tobytes()
        
        print(f"发送灰度图像数据到设备（启用硬件抖动）... 尺寸: {len(img_bytes)} 字节")
        
        # 发送灰度图像，设备端将应用抖动算法
        controller.send_grayscale_image(
            img_bytes, 
            x=0, y=0, width=width, height=height, 
            partial=False
        )
        
        print("图像已发送到E-Ink屏幕！")
        
    except Exception as e:
        print(f"运行演示时出错: {str(e)}")
        
    finally:
        controller.disconnect()


if __name__ == "__main__":
    demo_hardware_dither()