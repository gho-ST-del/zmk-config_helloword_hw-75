/*
 * Copyright (c) 2022-2023 XiNGRZ
 * SPDX-License-Identifier: MIT
 */

#include "handler.h"
#include "usb_comm.pb.h"

#include <zephyr/device.h>
#include <zephyr/drivers/display.h>

#include <zephyr/logging/log.h>
LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#include <eink_app.h>

#include <pb_encode.h>
#include <pb_decode.h>

static bool handle_eink_set_image(const usb_comm_MessageH2D *h2d, usb_comm_MessageD2H *d2h,
				  const void *bytes, uint32_t bytes_len)
{
	const usb_comm_EinkImage *req = &h2d->payload.eink_image;
	usb_comm_EinkImage *res = &d2h->payload.eink_image;

	res->id = req->id;

	// 检查是否为灰度图像
	if (req->has_grayscale && req->grayscale) {
		// 如果是灰度图像，使用eink_update_grayscale函数
		if (req->has_width && req->has_height) {
			// bytes参数应该是原始灰度数据，每个像素1字节
			eink_update_grayscale(bytes, req->width, req->height, 
			                     req->has_partial ? req->partial : false);
		}
	} else {
		// 如果是二值图像，使用原有的处理逻辑
		bool partial = req->has_partial && req->partial;

		if (req->has_x && req->has_y && req->has_width && req->has_height) {
			eink_update_region(bytes, bytes_len, req->x, req->y, req->width, req->height,
					   partial);
		} else {
			eink_update(bytes, bytes_len, partial);
		}
	}

	return true;
}

USB_COMM_HANDLER_DEFINE(usb_comm_Action_EINK_SET_IMAGE, usb_comm_MessageD2H_eink_image_tag,
			handle_eink_set_image);
