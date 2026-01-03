#!/usr/bin/env python3
"""
E-Ink Image Transfer Tool for HelloWord HW-75 Keyboard
This script sends image data to the E-Ink display on the HW-75 keyboard via USB.
"""

import sys
import usb.core
import usb.util
import argparse
from PIL import Image
import numpy as np


def find_hw75_device():
    """Find the HW-75 keyboard device on USB"""
    # These are placeholder values - you need to find the actual VID/PID
    # You might need to check what the actual USB device identifies as
    device = usb.core.find(idVendor=0x0483, idProduct=0x572b)  # STM32 HID device as example
    
    if device is None:
        print("HW-75 device not found. Please check connection.")
        return None
    
    # Detach kernel driver if active
    if device.is_kernel_driver_active(0):
        try:
            device.detach_kernel_driver(0)
        except usb.core.USBError as e:
            print(f"Could not detach kernel driver: {e}")
    
    try:
        device.set_configuration()
        usb.util.claim_interface(device, 0)
    except usb.core.USBError as e:
        print(f"Could not set configuration: {e}")
        return None
    
    return device


def convert_image_to_eink_format(image_path, width=296, height=128):
    """
    Convert an image to the format required by the E-Ink display
    The E-Ink display expects 1-bit data in a specific format
    """
    # Open and resize the image
    img = Image.open(image_path).convert('L')  # Convert to grayscale
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    
    # Convert to numpy array and threshold to binary
    img_array = np.array(img)
    threshold = 128
    binary_array = (img_array > threshold).astype(np.uint8)
    
    # Convert to packed bits (each byte contains 8 pixels)
    # E-Ink format: 1 bit per pixel, packed in bytes
    packed_data = []
    for y in range(height):
        for x in range(0, width, 8):
            byte = 0
            for bit in range(8):
                px = x + bit
                if px < width:
                    # Invert so 0=black, 1=white to match E-Ink behavior
                    byte |= (binary_array[y, px] & 1) << (7 - bit)
            packed_data.append(byte)
    
    return bytes(packed_data)


def create_eink_message(image_data, image_id=1, x=0, y=0, width=296, height=128, partial=False):
    """
    Create a protobuf message for EINK_SET_IMAGE command
    This is a simplified version - in reality you'd use the generated protobuf classes
    """
    # This is a simplified manual protobuf encoding
    # For a complete implementation, you'd need the generated classes from usb_comm.proto
    
    # This is a placeholder implementation - in reality you'd use the generated protobuf code
    # The actual protobuf encoding is more complex and requires the generated classes
    
    # Action enum for EINK_SET_IMAGE is 7
    action = 7
    
    # We'll use a simplified approach to build the message
    # This is not a complete protobuf implementation but gives the idea
    message_bytes = bytearray()
    
    # Add action field (required, varint, tag 1)
    message_bytes.append(0x08)  # Field 1 (action), wire type 0 (varint)
    message_bytes.append(action)
    
    # Add payload (oneof, embedded message, tag 5 for eink_image)
    # Start of EinkImage message
    message_bytes.append(0x2a)  # Field 5 (eink_image payload), wire type 2 (length-delimited)
    
    # Calculate the size of the EinkImage message (we'll fill this in later)
    eink_msg_start = len(message_bytes)
    message_bytes.extend(b'\x00\x00')  # Placeholder for length
    
    # Add id field (required, varint, tag 1)
    message_bytes.append(0x08)  # Field 1 (id), wire type 0 (varint)
    message_bytes.append(image_id & 0xFF)
    if image_id > 0xFF:
        message_bytes.append((image_id >> 8) & 0xFF)
    
    # Add x field (optional, varint, tag 4)
    if x != 0:
        message_bytes.append(0x20)  # Field 4 (x), wire type 0 (varint)
        message_bytes.append(x & 0xFF)
        if x > 0xFF:
            message_bytes.append((x >> 8) & 0xFF)
    
    # Add y field (optional, varint, tag 5)
    if y != 0:
        message_bytes.append(0x28)  # Field 5 (y), wire type 0 (varint)
        message_bytes.append(y & 0xFF)
        if y > 0xFF:
            message_bytes.append((y >> 8) & 0xFF)
    
    # Add width field (optional, varint, tag 6)
    message_bytes.append(0x30)  # Field 6 (width), wire type 0 (varint)
    message_bytes.append(width & 0xFF)
    if width > 0xFF:
        message_bytes.append((width >> 8) & 0xFF)
    
    # Add height field (optional, varint, tag 7)
    message_bytes.append(0x38)  # Field 7 (height), wire type 0 (varint)
    message_bytes.append(height & 0xFF)
    if height > 0xFF:
        message_bytes.append((height >> 8) & 0xFF)
    
    # Add partial field (optional, varint, tag 8)
    if partial:
        message_bytes.append(0x40)  # Field 8 (partial), wire type 0 (varint)
        message_bytes.append(0x01)  # true
    
    # Add bits field (optional, bytes, tag 3)
    # First the field tag
    message_bytes.append(0x1a)  # Field 3 (bits), wire type 2 (length-delimited)
    # Then the length of the image data
    data_len = len(image_data)
    if data_len < 0x80:
        message_bytes.append(data_len)
    else:
        # Varint encoding for longer lengths
        while data_len > 0:
            byte = data_len & 0x7F
            data_len >>= 7
            if data_len > 0:
                byte |= 0x80
            message_bytes.append(byte)
    
    # Finally, append the actual image data
    message_bytes.extend(image_data)
    
    # Now we need to update the length of the EinkImage message
    eink_msg_len = len(message_bytes) - eink_msg_start - 2  # Subtract placeholder
    # Replace the placeholder with actual length
    if eink_msg_len < 0x80:
        message_bytes[eink_msg_start:eink_msg_start+2] = [eink_msg_len]
    else:
        # For simplicity, assume length < 256
        message_bytes[eink_msg_start:eink_msg_start+2] = [eink_msg_len & 0xFF, (eink_msg_len >> 8) & 0xFF]
    
    return bytes(message_bytes)


def send_image_to_hw75(image_path, device_id=None, x=0, y=0, partial=False):
    """Send an image to the HW-75 E-Ink display"""
    print(f"Converting image: {image_path}")
    image_data = convert_image_to_eink_format(image_path)
    
    print("Connecting to HW-75 device...")
    device = find_hw75_device()
    if device is None:
        print("Failed to connect to device")
        return False
    
    print("Creating E-Ink message...")
    message = create_eink_message(image_data, image_id=1, x=x, y=y, partial=partial)
    
    print("Sending image data to device...")
    try:
        # Send the message via USB control transfer
        # The exact endpoint and parameters depend on the device implementation
        device.ctrl_transfer(0x21, 0x09, 0x0200, 0, message)
        print("Image sent successfully!")
    except usb.core.USBError as e:
        print(f"Failed to send image: {e}")
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(description='Send image to HW-75 E-Ink display')
    parser.add_argument('image_path', help='Path to the image to send')
    parser.add_argument('--x', type=int, default=0, help='X position for partial update')
    parser.add_argument('--y', type=int, default=0, help='Y position for partial update')
    parser.add_argument('--partial', action='store_true', help='Use partial update')
    
    args = parser.parse_args()
    
    if not send_image_to_hw75(args.image_path, x=args.x, y=args.y, partial=args.partial):
        sys.exit(1)


if __name__ == "__main__":
    main()