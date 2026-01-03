/*
 * Copyright (c) 2022-2023 XiNGRZ
 * SPDX-License-Identifier: MIT
 */

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/init.h>

#include <zephyr/logging/log.h>
LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#include <zephyr/drivers/display.h>

#include <zmk/event_manager.h>
#include <app/events/eink_state_changed.h>

#include "eink_app.h"

#define EINK_NODE DT_ALIAS(eink)
#define EINK_WIDTH DT_PROP(EINK_NODE, width)
#define EINK_HEIGHT DT_PROP(EINK_NODE, height)

static const struct device *eink = DEVICE_DT_GET(EINK_NODE);

ZMK_EVENT_IMPL(app_eink_state_changed);

// Floyd-Steinberg抖动算法实现
static int apply_floyd_steinberg_dither(const uint8_t *grayscale_image, 
                                       uint8_t *binary_image,
                                       uint32_t width, uint32_t height) {
    // 分配临时误差数组
    int16_t *error_row1 = k_calloc(width, sizeof(int16_t));
    int16_t *error_row2 = k_calloc(width, sizeof(int16_t));
    
    if (!error_row1 || !error_row2) {
        if (error_row1) k_free(error_row1);
        if (error_row2) k_free(error_row2);
        return -ENOMEM;
    }
    
    for (uint32_t y = 0; y < height; y++) {
        for (uint32_t x = 0; x < width; x++) {
            // 获取原始灰度值 (假设 8bpp 输入)
            uint8_t old_pixel = grayscale_image[y * width + x];
            
            // 应用误差
            int new_val = old_pixel + error_row1[x];
            if (new_val < 0) new_val = 0;
            if (new_val > 255) new_val = 255;
            
            // 二值化 (阈值 128)
            uint8_t new_pixel = (new_val > 128) ? 255 : 0;
            
            // 设置二进制图像位
            uint32_t byte_idx = (y * width + x) / 8;
            uint32_t bit_idx = (y * width + x) % 8;
            if (new_pixel == 255) { // 白色
                binary_image[byte_idx] &= ~(1 << (7 - bit_idx));
            } else { // 黑色
                binary_image[byte_idx] |= (1 << (7 - bit_idx));
            }
            
            // 计算误差
            int quant_error = new_val - (new_pixel == 255 ? 255 : 0);
            
            // 传播误差到相邻像素 (Floyd-Steinberg)
            if (x + 1 < width) {
                error_row1[x + 1] += quant_error * 7 / 16;
            }
            if (y + 1 < height) {
                if (x > 0) {
                    error_row2[x - 1] += quant_error * 3 / 16;
                }
                error_row2[x] += quant_error * 5 / 16;
                if (x + 1 < width) {
                    error_row2[x + 1] += quant_error * 1 / 16;
                }
            }
        }
        
        // 交换误差行
        int16_t *temp = error_row1;
        error_row1 = error_row2;
        error_row2 = temp;
        memset(error_row2, 0, width * sizeof(int16_t));
    }
    
    k_free(error_row1);
    k_free(error_row2);
    return 0;
}

int eink_update_grayscale(const uint8_t *grayscale_image, uint32_t width, uint32_t height, 
                         bool partial) {
    if (width > EINK_WIDTH || height > EINK_HEIGHT) {
        LOG_ERR("Invalid image dimensions: %dx%d", width, height);
        return -EINVAL;
    }

    // 计算二进制图像缓冲区大小
    size_t binary_size = (width * height + 7) / 8; // 向上取整确保足够空间
    
    uint8_t *binary_image = k_calloc(binary_size, 1);
    if (!binary_image) {
        LOG_ERR("Failed to allocate memory for binary image");
        return -ENOMEM;
    }

    // 应用抖动算法
    int ret = apply_floyd_steinberg_dither(grayscale_image, binary_image, width, height);
    if (ret != 0) {
        LOG_ERR("Failed to apply dithering: %d", ret);
        k_free(binary_image);
        return ret;
    }

    // 使用现有的二进制更新函数
    ret = eink_update_region(binary_image, binary_size, 0, 0, width, height, partial);
    
    k_free(binary_image);
    return ret;
}

int eink_update(const uint8_t *image, uint32_t image_len, bool partial)
{
	return eink_update_region(image, image_len, 0, 0, EINK_WIDTH, EINK_HEIGHT, partial);
}

int eink_update_region(const uint8_t *image, uint32_t image_len, uint32_t x, uint32_t y,
		       uint32_t width, uint32_t height, bool partial)
{
	if (x >= EINK_WIDTH || y >= EINK_HEIGHT || x + width > EINK_WIDTH ||
	    y + height > EINK_HEIGHT) {
		LOG_ERR("Invalid partial update region: (%d, %d, %d, %d)", x, y, width, height);
		return -EINVAL;
	}

	if (image_len != width * height / 8) {
		LOG_ERR("Invalid image length: %d", image_len);
		return -EINVAL;
	}

	struct display_buffer_descriptor desc = {
		.buf_size = image_len,
		.width = width,
		.height = height,
		.pitch = width,
	};

	LOG_DBG("Start updating E-Ink");

	ZMK_EVENT_RAISE(new_app_eink_state_changed((struct app_eink_state_changed){
		.busy = true,
	}));

	if (!partial) {
		display_blanking_on(eink);
	}

	int ret = display_write(eink, x, y, &desc, image);
	if (ret != 0) {
		LOG_ERR("Failed updating E-ink image: %d", ret);
		return ret;
	}

	if (!partial) {
		display_blanking_off(eink);
	}

	ZMK_EVENT_RAISE(new_app_eink_state_changed((struct app_eink_state_changed){
		.busy = false,
	}));

	LOG_DBG("E-Ink update finished");

	return 0;
}
