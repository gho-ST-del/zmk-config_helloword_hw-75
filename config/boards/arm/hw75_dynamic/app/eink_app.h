/*
 * Copyright (c) 2022-2023 XiNGRZ
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>

int eink_update(const uint8_t *image, uint32_t image_len, bool partial);

int eink_update_region(const uint8_t *image, uint32_t image_len, uint32_t x, uint32_t y,
		       uint32_t width, uint32_t height, bool partial);

// 支持灰度图像输入的函数，通过抖动算法模拟灰度
int eink_update_grayscale(const uint8_t *grayscale_image, uint32_t width, uint32_t height, 
                         bool partial);
