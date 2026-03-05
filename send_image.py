import os
import time
from argparse import ArgumentParser
import inquirer
from PIL import Image
import zmkx
import numpy as np
CANVAS_WIDTH = 128
CANVAS_HEIGHT = 296
bayer_matrix = np.array([[0, 48, 12, 60, 3, 51, 15, 63],
                         [32, 16, 44, 28, 35, 19, 47, 31],
                         [8, 56, 4, 52, 11, 59, 7, 55],
                         [40, 24, 36, 20, 43, 27, 39, 23],
                         [2, 50, 14, 62, 1, 49, 13, 61],
                         [34, 18, 46, 30, 33, 17, 45, 29],
                         [10, 58, 6, 54, 9, 57, 5, 53],
                         [42, 26, 38, 22, 41, 25, 37, 21]])
def bayer_dither(image, bayer_matrix, num_levels):
    gray_img = image.convert("L")
    width, height = gray_img.size
    pixels = gray_img.load()

    for y in range(height):
        for x in range(width):
            pixel_value = pixels[x, y]
            threshold = bayer_matrix[y % 8, x % 8]
            pixels[x, y] = int(pixel_value // (256 // num_levels)) * (256 // (num_levels - 1))  # calculate new pixel value based on num_levels

    return gray_img
# def bayer_dither(image, bayer_matrix, num_lists):
#     gray_img = image.convert("L")
#     width, height = gray_img.size
#     pixels = gray_img.load()
#     gray_lists = [[] for _ in range(num_lists)]  # create num_lists empty lists
    
#     for y in range(height):
#         for x in range(width):
#             pixel_value = pixels[x, y]
#             threshold = bayer_matrix[y % 8, x % 8]
#             pixels[x, y] = 255 if pixel_value > threshold else 0
#             index = pixel_value // (256 // num_lists)  # calculate index of the list to add pixel_value
            
#             gray_lists[index-1].append(255 if pixel_value > threshold else 0) 

#     return gray_lists
def get_device(features=[]):
    devices = zmkx.find_devices(features=features)

    if len(devices) == 0:
        # print('未找到符合条件的设备')
        return None

    if len(devices) == 1:
        return devices[0]

    choice = inquirer.prompt([
        inquirer.List('device', message='2', choices=[
            (f'{d.manufacturer} {d.product} (SN: {d.serial})', d)
            for d in devices
        ]),
    ])

    if choice is None:
        return None

    return choice['device']

def getImage():
    folder_path = "./image"
    image_extensions = (".jpg", ".jpeg", ".png")
    image_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            # 获取文件的扩展名并将其转换为小写
            file_extension = os.path.splitext(file)[-1].lower()
            # 如果文件扩展名在支持的图片文件扩展名列表中，则将其路径添加到image_paths列表中
            if file_extension in image_extensions:
                image_paths.append(os.path.join(root, file))
    return image_paths
if __name__ == '__main__':
    # parser = ArgumentParser()
    # parser.add_argument('file', help='指定要显示的图片文件')
    #
    # args = parser.parse_args()


    device = get_device(features=['knob'])
    if device is None:
        exit(1)
    # args.file
    stare = 4
    with device.open() as device, Image.open(r"C:\Users\zx131\Pictures\0d4cb3bdd27a4088ae62c36f75d98738.png") as image:
        image.thumbnail((CANVAS_WIDTH, CANVAS_HEIGHT))
        center = ((CANVAS_WIDTH - image.width) // 2,
                    (CANVAS_HEIGHT - image.height) // 2)
        
        image = bayer_dither(image,bayer_matrix*(100),5)
        canvas = Image.new('L', (CANVAS_WIDTH, CANVAS_HEIGHT), color=0xFF)
        # for i in image_list:
        #     # print(i)
        #     img_new = Image.new('L', (image.width, image.height), color=0xFF)
        #     img_new.putdata(i)
        #     print(img_new)
        #     now = time.localtime()
            
        #     text = time.strftime("%H:%M", now)
        #     partial = False if now.tm_min % 30 == 0 else True
        #     canvas = Image.new('L', (CANVAS_WIDTH, CANVAS_HEIGHT), color=0xFF)
            
        #     canvas.paste(img_new, center)
        #     # time.sleep(2)
        #     canvas = canvas.convert('1', dither=Image.FLOYDSTEINBERG)
        #     if(i==0):
        #         device.eink_set_image(canvas.tobytes())
        #     else:
        #         device.eink_set_image(canvas.tobytes(), 0, 0, canvas.width, canvas.height, partial)
                
            

        canvas.paste(image, center)
            # time.sleep(2)
        canvas = canvas.convert('1', dither=Image.FLOYDSTEINBERG)
        device.eink_set_image(canvas.tobytes(),0,0,canvas.width,canvas.height,partial=False)
  
        # device.eink_set_image(canvas.tobytes(), 0, 0,canvas.width, canvas.height, partial)
        
        
