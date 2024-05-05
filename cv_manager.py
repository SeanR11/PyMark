import os
import cv2
import math
import numpy as np
from PyQt5.QtCore import Qt, QSize


class CVManager:
    def load_image(self, image_path):
        """ Load an image from the given path. """
        return cv2.imread(image_path)

    def save_images(self, folder, images):
        """ Save images to the specified folder. """
        # Generate folder names with sequential numbering if the folder already exists
        for n in range(100):
            path = f'{folder}/PyMark' if n == 0 else f'{folder}/PyMark_{n}'
            if not os.path.exists(path):
                os.makedirs(path)
                break
        # Save each image with its corresponding name
        for image_data, image_name in images:
            cv2.imwrite(f'{path}/{image_name}.png', image_data)

    def fitImage(self, image, canvas_size, background_image=None, gap=(0,0)):
        """ Resize and position the given image to fit within the canvas size."""
        if background_image is None:
            background_image = np.full((canvas_size.height(), canvas_size.width(), 3), (255, 255, 255), dtype=np.uint8)
        image_y, image_x = image.shape[:2]
        # Adjust image dimensions to fit within the canvas size
        image_x = canvas_size.width() if  image_x > canvas_size.width() else image_x
        image_y = canvas_size.height() if image_y > canvas_size.height() else image_y
        image = cv2.resize(image, (image_x - gap[0], image_y - gap[1]))
        # Position the image in the center of the canvas
        y = (canvas_size.height() - image.shape[0]) // 2
        x = (canvas_size.width() - image.shape[1]) // 2
        background_image[y:y + image.shape[0], x:x + image.shape[1]] = image
        return background_image, image

    def mark_selection(self, image, selection_pos, gap=1):
        """ Draw marking lines around a selected area in the image."""
        start_pos, end_pos = selection_pos
        start_pos = (start_pos[0] - gap, start_pos[1] - gap)
        end_pos = (end_pos[0] + gap, end_pos[1] + gap)
        x_gap, y_gap = self.getGap(start_pos, end_pos)
        x_dir, y_dir = self.getDirection(start_pos, end_pos)
        top_left = start_pos
        top_right = (end_pos[0], start_pos[1])
        bottom_left = (start_pos[0], end_pos[1])
        dst = 10
        # Draw horizontal marking lines
        for i in range(math.ceil(abs(x_gap) // dst) + 1):
            cv2.line(image, (top_left[0] + (dst * i * x_dir), top_left[1]),
                     (top_left[0] + (dst // 3 + (dst * i)) * x_dir, top_left[1]), (0, 0, 0), 1, cv2.LINE_AA)
            cv2.line(image, (bottom_left[0] + (dst * i * x_dir), bottom_left[1]),
                     (bottom_left[0] + (dst // 3 + (dst * i)) * x_dir, bottom_left[1]), (0, 0, 0), 1, cv2.LINE_AA)
        # Draw vertical marking lines
        for i in range(math.ceil(abs(y_gap) // dst)):
            cv2.line(image, (top_right[0], top_right[1] + (dst * i * y_dir)),
                     (top_right[0], top_right[1] + (dst // 3 + (dst * i)) * y_dir), (0, 0, 0), 1, cv2.LINE_AA)
            cv2.line(image, (top_left[0], top_left[1] + (dst * i * y_dir)),
                     (top_left[0], top_left[1] + (dst // 3 + (dst * i)) * y_dir), (0, 0, 0), 1, cv2.LINE_AA)

    def move_selection(self, image, selection, selection_pos, bounds):
        """ Move the selected area within the image bounds."""
        # Adjust selection position to fit within the image bounds
        if selection_pos[0][0] <= 4:
            selection_pos = ((4, selection_pos[0][1]), (4 + selection.shape[1], selection_pos[1][1]))
        if selection_pos[1][0] >= bounds.width() - 4:
            selection_pos = (
            (bounds.width() - 4 - selection.shape[1], selection_pos[0][1]), (bounds.width() - 4, selection_pos[1][1]))
        if selection_pos[0][1] <= 3:
            selection_pos = ((selection_pos[0][0], 3), (selection_pos[1][0], 3 + selection.shape[0]))
        if selection_pos[1][1] >= bounds.height() - 4:
            selection_pos = (
            (selection_pos[0][0], bounds.height() - 4 - selection.shape[0]), (selection_pos[1][0], bounds.height() - 4))
        # Move the selection to the new position
        start_pos, end_pos = selection_pos
        end_pos = end_pos if end_pos[1]-start_pos[1] == selection.shape[0] else (end_pos[0],end_pos[1]+1)
        end_pos = end_pos if end_pos[0]-start_pos[0] == selection.shape[1] else (end_pos[0]+1,end_pos[1])
        image[start_pos[1]:end_pos[1],start_pos[0]:end_pos[0]] = selection
        return image, selection_pos

    def draw_image(self, image, watermark, watermark_pos, watermark_area, scalar=1):
        origin_scalar = scalar
        scalar = 1 + (scalar - 1) * 0.2
        width = int((watermark_pos[1][0] - watermark_pos[0][0]) // scalar)
        heigth = int((watermark_pos[1][1] - watermark_pos[0][1]) // scalar)
        x = int(watermark_area[0][0] + watermark_pos[0][0] // scalar)
        y = int(watermark_area[0][1] + watermark_pos[0][1] // scalar + (12 * (origin_scalar - 1)))
        x_gap = x + width
        y_gap = y + heigth
        watermark = cv2.resize(watermark, (image[y:y_gap, x:x_gap].shape[:2:][::-1]))
        image[y:y_gap, x:x_gap] = watermark
        return image

    def draw_watermarks(self, image, watermark_objects, watermark_canvas_size, scalar=1):
        height, width = image.shape[:2]
        # Resize the image to ensure it fits within specified limits
        image = cv2.resize(image, (min(max(600, width), 1920), min(max(300, height), 1080)))
        if watermark_objects:
            height, width = image.shape[:2]
            for watermark, watermark_pos in watermark_objects:
                # Position and draw text watermark
                if type(watermark) == tuple:
                    watermark_area = ((0, int(height * (0.60 + 0.04 * watermark[1][2]))), (int(width * 0.55), height))
                    x_ratio = (watermark_area[1][0] - watermark_area[0][0]) / watermark_canvas_size.width()
                    y_ratio = (watermark_area[1][1] - watermark_area[0][1]) / watermark_canvas_size.height()
                    watermark_pos = (watermark_area[0][0] + int(watermark_pos[0][0] * x_ratio),
                                     watermark_area[0][1] + int(watermark_pos[0][1] * y_ratio) + 10)
                    cv2.putText(image, watermark[1][3], watermark_pos, watermark[1][1],
                                0.4 * watermark[1][2] - 0.1 * (scalar-1),
                                watermark[1][0], 2 if watermark[1][4] else 1)
                # Position and draw image watermark
                else:
                    watermark_area = ((0, int(height * 0.65)), (int(width * 0.55), height))
                    print(scalar)
                    x_ratio = (watermark_area[1][0] - watermark_area[0][0]) / watermark_canvas_size.width()
                    y_ratio = (watermark_area[1][1] - watermark_area[0][1]) / watermark_canvas_size.height()
                    watermark_pos = ((int(watermark_pos[0][0] * x_ratio), int(watermark_pos[0][1] * y_ratio)+(10 if scalar != 1 else 0)),
                                     (int(watermark_pos[1][0] * x_ratio), int(watermark_pos[1][1] * y_ratio)+(10 if scalar != 1 else 0)))
                    image = self.draw_image(image, watermark, watermark_pos, watermark_area, scalar)
        return image

    def getGap(self, start_pos, current_pos):
        """ Get the gap between two points. """
        x_gap = start_pos[0] - current_pos[0]
        y_gap = start_pos[1] - current_pos[1]
        return x_gap, y_gap

    def getDirection(self, start_pos, current_pos):
        """ Get the direction between two points. """
        x_dir = 1 if start_pos[0] < current_pos[0] else -1
        y_dir = 1 if start_pos[1] < current_pos[1] else -1
        return x_dir, y_dir

    def get_rect(self, outter_object, inner_object):
        """ Get the rectangle coordinates enclosing an inner object within an outer object. """
        canvas_center = (outter_object.width() // 2, outter_object.height() // 2)
        selection_y, selection_x = inner_object.shape[:2]
        start_pos = (canvas_center[0] - selection_x // 2, canvas_center[1] - selection_y // 2)
        end_pos = (canvas_center[0] + selection_x // 2, canvas_center[1] + selection_y // 2)
        return start_pos, end_pos
