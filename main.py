import cv2
import numpy as np
from ui_manager import UIManager
from cv_manager import CVManager
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLayout, QHBoxLayout, QVBoxLayout, QListWidget, \
    QListWidgetItem, QFileDialog, QLabel, QColorDialog


class Core(QMainWindow):
    def __init__(self, app, width, height, title):
        super().__init__()
        # Core setup
        self.max_width = app.desktop().width()
        self.max_height = app.desktop().height()
        self.setFixedSize(width, height)
        self.setGeometry(self.max_width // 2 - width // 2, self.max_height // 2 - height // 2, width, height)
        self.setWindowTitle(title)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        # Core attributes
        self.app = app
        self.ui = UIManager()
        self.cv = CVManager()
        # Image attributes
        self.image_list = []
        self.image_list_widget = None
        self.watermark_canvas = None
        # Watermark attributes
        self.watermark = np.full([150, 450, 3], (255, 255, 255), dtype=np.uint8)
        self.watermark_copy = self.watermark.copy()
        self.watermark_objects = []
        self.start_pos = None
        self.selection = None
        self.selection_pos = (None, None)
        self.selection_move = False
        self.text = 'text'
        self.text_font = 0
        self.text_size = 1
        self.text_bold = False
        self.text_color = (0, 0, 0)
        self.text_mode = False
        self.color_picker = None
        # Preview attributes
        self.preview_canvas = None
        self.preview_image = np.full([300, 600, 3], (255, 255, 255), dtype=np.uint8)
        self.preview_scale = 1

        self.loadUI()

    def loadUI(self):
        # Central widget setup
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setMouseTracking(True)

        # Main layout setup
        main_layout = QHBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignCenter)

        # Left layout setup
        left_layout = self.ui.create_layout(main_layout, 'v', Qt.AlignLeft, (25, 0, 0, 0))
        right_layout = self.ui.create_layout(main_layout, 'v', Qt.AlignRight, (50, 0, 20, 25))

        # Left layout content
        file_button_layout = self.ui.create_layout(left_layout, 'h', Qt.AlignLeft)
        self.ui.create_button(file_button_layout, self.add_preview_images, icon='assets/add.png', text='')
        self.ui.create_button(file_button_layout, self.delete_preview_image, icon='assets/delete.png', text='')
        self.ui.create_button(file_button_layout, self.save_images, icon='assets/save.png', text='')

        self.image_list_widget = self.ui.create_list_widget(left_layout, 300, 600, self.set_preview_image)

        # Right layout content
        self.ui.create_text(right_layout, 'Watermark Edit:').setContentsMargins(0, 50, 0, 0)
        watermark_tools_layout = self.ui.create_layout(right_layout, 'h', Qt.AlignLeft, (0, 0, 0, 0))
        self.ui.create_button(watermark_tools_layout, self.add_watermark_image, '', 'assets/add.png')
        self.ui.create_button(watermark_tools_layout, self.delete_selection, '', 'assets/delete.png')
        self.ui.create_button(watermark_tools_layout, self.add_watermark_text, '', 'assets/text.png')
        self.ui.create_button(watermark_tools_layout,self.set_text_bold,'','assets/bold.png')
        self.color_picker = self.ui.create_button(watermark_tools_layout, self.set_text_color, '',
                                                  self.ui.to_pixmap(np.full([40, 40, 3], (0, 0, 0), dtype=np.uint8)))
        self.ui.create_combo(watermark_tools_layout, self.set_text_font, (140, 25),
                             ['hershey simplex', 'hershey plain', 'hershey duplex', 'hershey complex',
                              'hershey triplex', 'hershey complex small', 'hershey script simplex',
                              'hershey script complex', 'italic'])
        self.ui.create_combo(watermark_tools_layout, self.set_text_size, (70, 25),
                             ['x-small', 'small', 'medium', 'large'])
        self.ui.create_button(watermark_tools_layout, self.reset_watermark_canvas, '', 'assets/reset.png')
        watermark_canvas_layout = self.ui.create_layout(right_layout, 'h', Qt.AlignLeft, (0, 0, 0, 0))
        self.watermark_canvas = self.ui.create_canvas(watermark_canvas_layout, 450, 150, self.watermark)
        radio_layout = self.ui.create_layout(watermark_canvas_layout, 'v', bounds=(25, 0, 0, 0))
        self.ui.create_radio(radio_layout, 'Watermark scale', self.set_preview_scale, ['small', 'medium', 'large'])
        right_layout.addStretch(1)
        self.ui.create_text(right_layout, 'Preview Image:')
        self.preview_canvas = self.ui.create_canvas(right_layout, 600, 300, self.preview_image)

    # Event handlers
    def mouseMoveEvent(self, event):
        if self.watermark_canvas.underMouse():
            mouse_pos = self.relative_position(self.watermark_canvas, (event.x(), event.y()))
            if self.selection is not None:
                if self.is_hover(mouse_pos, self.selection_pos):
                    self.app.setOverrideCursor(Qt.SizeAllCursor)
                else:
                    self.app.setOverrideCursor(Qt.ArrowCursor)
                if self.selection_move == 'obj' and self.is_hover(mouse_pos, (
                        (0, 0), (self.watermark_canvas.width(), self.watermark_canvas.height()))):
                    self.watermark_copy = self.watermark.copy()
                    x_gap, y_gap = self.cv.getGap(self.start_pos, mouse_pos)
                    self.selection_pos = (
                        (self.selection_pos[0][0] + (x_gap * -1), self.selection_pos[0][1] + (y_gap * -1)),
                        (self.selection_pos[1][0] + (x_gap * -1), self.selection_pos[1][1] + (y_gap * -1)))
                    self.watermark, self.selection_pos = self.cv.move_selection(self.watermark, self.selection,
                                                                                self.selection_pos,
                                                                                self.watermark_canvas.size())
                    self.cv.mark_selection(self.watermark, self.selection_pos)
                    self.watermark_objects[-1] = (self.watermark_objects[-1][0], self.selection_pos)
                    self.render_watermark()
                    self.watermark = self.watermark_copy.copy()
                    self.start_pos = mouse_pos
                elif self.selection_move == 'text' and self.is_hover(mouse_pos, (
                (0, 0), (self.watermark_canvas.width(), self.watermark_canvas.height()))):
                    self.watermark_copy = self.watermark.copy()
                    x_gap, y_gap = self.cv.getGap(self.start_pos, mouse_pos)
                    self.selection_pos = (
                        (self.selection_pos[0][0] + (x_gap * -1), self.selection_pos[0][1] + (y_gap * -1)),
                        (self.selection_pos[1][0] + (x_gap * -1), self.selection_pos[1][1] + (y_gap * -1)))
                    if self.selection_pos[0][0] < 1:
                        self.selection_pos = ((1, self.selection_pos[0][1]), (
                            1 + self.selection_pos[1][0] - self.selection_pos[0][0], self.selection_pos[1][1]))
                    elif self.selection_pos[1][0] > 495:
                        self.selection_pos = (
                            (495 - (self.selection_pos[1][0] - self.selection_pos[0][0]), self.selection_pos[0][1]),
                            (495, self.selection_pos[1][1]))
                    elif self.selection_pos[0][1] < 10:
                        self.selection_pos = ((self.selection_pos[0][0], 10), (
                            self.selection_pos[1][0], 10 + self.selection_pos[1][1] - self.selection_pos[0][1]))
                    elif self.selection_pos[1][1] > self.watermark_canvas.height() - 10:
                        self.selection_pos = ((self.selection_pos[0][0], self.watermark_canvas.height() - 10 - (
                                self.selection_pos[1][1] - self.selection_pos[0][1])),
                                              (self.selection_pos[1][0], self.watermark_canvas.height() - 10))
                    cv2.putText(self.watermark, self.text, (self.selection_pos[0][0], self.selection_pos[1][1]),
                                self.text_font, 0.5 * self.text_size, self.text_color, 2 if self.text_bold else 1)
                    start_pos, end_pos = self.selection_pos
                    start_pos = (start_pos[0], start_pos[1] - 2 * self.text_size)
                    end_pos = (
                        start_pos[0] + (len(self.text) * (10 * self.text_size) - (0 if self.text_size == 1 else 0)),
                        end_pos[1] + 2 * self.text_size)
                    self.cv.mark_selection(self.watermark, (start_pos, end_pos))
                    self.watermark_objects[-1] = (self.watermark_objects[-1][0], self.selection_pos)
                    self.render_watermark()
                    self.watermark = self.watermark_copy.copy()
                    self.start_pos = mouse_pos
                else:
                    self.selection_move = False

    def mousePressEvent(self, event):
        if self.watermark_canvas.underMouse():
            mouse_pos = self.relative_position(self.watermark_canvas, (event.x(), event.y()))
            if self.selection is not None:
                if self.is_hover(mouse_pos, self.selection_pos):
                    if self.text_mode:
                        self.selection_move = 'text'
                    else:
                        self.selection_move = 'obj'
                    self.start_pos = mouse_pos
                else:
                    if self.text_mode:
                        self.text_mode = False
                        cv2.putText(self.watermark, self.text, (self.selection_pos[0][0], self.selection_pos[1][1]),
                                    self.text_font, 0.5 * self.text_size, self.text_color, 2 if self.text_bold else 1)
                        self.text = 'text'
                        self.watermark_copy = self.watermark.copy()
                    else:
                        self.watermark, self.selection_pos = self.cv.move_selection(self.watermark, self.selection,
                                                                                    self.selection_pos,
                                                                                    self.watermark_canvas.size())
                    self.selection = None
                    self.selection_pos = None
                    self.render_watermark()

    def mouseReleaseEvent(self, event):
        if self.watermark_canvas.underMouse():
            mouse_pos = self.relative_position(self.watermark_canvas, (event.x(), event.y()))
            if self.selection is not None:
                self.selection_move = False

    def keyPressEvent(self, event):
        if self.text_mode:
            if self.text == 'text':
                self.text = ''
            if event.key() == Qt.Key_Backspace:
                self.text = self.text[:-1]
            elif event.key() == Qt.Key_Space:
                self.text += ' '
            elif 64 < event.key() < 91:
                self.text += chr(event.key())
            else:
                return
            cv2.putText(self.watermark, self.text, (self.selection_pos[0][0], self.selection_pos[1][1]),
                        self.text_font, 0.5 * self.text_size, self.text_color, 2 if self.text_bold else 1)
            start_pos, end_pos = self.selection_pos
            start_pos = (start_pos[0], start_pos[1] - 2 * self.text_size)
            end_pos = (start_pos[0] + (len(self.text) * (10 * self.text_size) - (0 if self.text_size == 1 else 0)),
                       end_pos[1] + 2 * self.text_size)
            self.cv.mark_selection(self.watermark, (start_pos, end_pos))
            self.selection_pos = (self.selection_pos[0], (end_pos[0], self.selection_pos[1][1]))
            self.watermark_objects[-1] = (
                (self.selection, (self.text_color, self.text_font, self.text_size, self.text,self.text_bold)), self.selection_pos)
            self.render_watermark()
            self.watermark = self.watermark_copy.copy()

    def set_preview_image(self, image_index):
        image = self.image_list[int(image_index)]
        image = cv2.resize(image, (600, 300))
        self.preview_image = image
        self.render_preview()

    def render_preview(self):
        preview_copy = self.preview_image.copy()
        preview_copy = self.cv.draw_watermarks(preview_copy, self.watermark_objects, self.watermark_canvas.size(),
                                               self.preview_scale)
        self.preview_canvas.setPixmap(self.ui.to_pixmap(preview_copy))

    def add_preview_images(self):
        dialog = QFileDialog(self)
        image_paths = dialog.getOpenFileNames(caption='Open Images', filter='Images *.png *.jpg *.jpeg')[0]
        if image_paths:
            image_names = [name[0].split('.')[0] for name in [name.split('/')[-1:] for name in image_paths]]
            for name in image_names:
                self.image_list_widget.addItem(QListWidgetItem(name))
            for path in image_paths:
                self.image_list.append(self.cv.load_image(path))

    def save_images(self):
        if self.image_list and self.watermark_objects:
            folder = QFileDialog.getExistingDirectory(caption='Select Folder')
            ready_images = []
            for index, image in enumerate(self.image_list):
                image = self.cv.draw_watermarks(image, self.watermark_objects, self.watermark_canvas.size(),
                                                self.preview_scale)
                ready_images.append((image, self.image_list_widget.item(index).text()))
            self.cv.save_images(folder, ready_images)

    def delete_preview_image(self):
        if self.image_list:
            self.image_list_widget.takeItem(self.image_list_widget.currentIndex().row())
            del self.image_list[self.image_list_widget.currentIndex().row()]
            if not self.image_list:
                self.preview_image = np.full([300, 600, 3], (255, 255, 255), dtype=np.uint8)
                self.render_preview()

    def set_preview_scale(self):
        scale = self.sender().text()
        if scale == 'small':
            self.preview_scale = 3
        elif scale == 'medium':
            self.preview_scale = 2
        else:
            self.preview_scale = 1
        self.render_preview()

    def render_watermark(self):
        self.watermark_canvas.setPixmap(self.ui.to_pixmap(self.watermark))
        self.render_preview()

    def reset_watermark_canvas(self):
        self.selection = None
        self.selection_pos = None
        self.text_mode = None
        self.selection_move = False
        self.watermark_objects = []
        self.watermark = np.full([150, 450, 3], (255, 255, 255), dtype=np.uint8)
        self.watermark_copy = self.watermark.copy()
        self.render_watermark()

    def add_watermark_image(self):
        if self.selection is not None:
            self.delete_selection()
        if self.text_mode:
            self.delete_selection()
        dialog = QFileDialog(self)
        image_path = dialog.getOpenFileName(caption='Open watermark', filter='Images *.png')[0]
        if image_path:
            if self.watermark_objects:
                self.watermark_copy = self.watermark.copy()
            self.selection = self.cv.load_image(image_path)
            self.watermark, self.selection = self.cv.fitImage(self.selection, self.watermark_canvas,
                                                              background_image=self.watermark, gap=(40, 40))
            self.selection_pos = (self.cv.get_rect(self.watermark_canvas.size(), self.selection))
            start_pos, end_pos = self.selection_pos
            start_pos = (start_pos[0] - 1, start_pos[1] - 1)
            self.cv.mark_selection(self.watermark, (start_pos,end_pos))
            self.watermark_objects.append((self.selection, self.selection_pos))
            self.render_watermark()
            self.watermark = self.watermark_copy.copy()

    def add_watermark_text(self, default_text=None):
        if self.selection is not None:
            self.delete_selection()
        if self.watermark_objects:
            self.watermark_copy = self.watermark.copy()
        if default_text:
            self.text = default_text

        self.text_mode = True
        self.selection = 'text'
        start_pos = (225 - (30 * self.text_size), 70 - (5 * self.text_size))
        end_pos = (225 + ((4 * len(self.text)) * self.text_size), 70 + (5 * self.text_size))
        self.selection_pos = (start_pos, end_pos)
        cv2.putText(self.watermark, self.text, (start_pos[0], end_pos[1]), self.text_font, 0.5 * self.text_size,
                    self.text_color, 2 if self.text_bold else 1)
        start_pos = (start_pos[0], start_pos[1] - 2 * self.text_size)
        end_pos = (start_pos[0] + (len(self.text) * (10 * self.text_size) - (0 if self.text_size == 1 else 0)),
                   end_pos[1] + 2 * self.text_size)
        self.cv.mark_selection(self.watermark, (start_pos, end_pos))
        self.watermark_objects.append(
            ((self.selection, (self.text_color, self.text_font, self.text_size, self.text,self.text_bold)), self.selection_pos))
        self.render_watermark()
        self.watermark = self.watermark_copy.copy()

    def set_text_font(self, font_index):
        self.text_font = font_index if font_index != 8 else 16
        if self.text_mode:
            saved_text = self.text
            self.delete_selection()
            self.add_watermark_text(saved_text)

    def set_text_size(self, size_index):
        self.text_size = size_index + 1
        if self.text_mode:
            saved_text = self.text
            self.delete_selection()
            self.add_watermark_text(saved_text)

    def set_text_color(self):
        self.text_color = QColorDialog().getColor(QColor(0, 0, 255)).getRgb()[:3][::-1]
        self.color_picker.setIcon(
            QIcon(self.ui.to_pixmap(np.full((40, 40, 3), self.text_color, dtype=np.uint8))))
        if self.text_mode:
            saved_text = self.text
            self.delete_selection()
            self.add_watermark_text(saved_text)

    def set_text_bold(self):
        if self.text_bold:
            self.sender().setStyleSheet('background-color:none')
            self.text_bold = False
        else:
            self.sender().setStyleSheet('background-color:#92DCFF;border-radius:5px')
            self.text_bold = True
        if self.text_mode:
            saved_text = self.text
            self.delete_selection()
            self.add_watermark_text(saved_text)

    def delete_selection(self):
        if self.selection is not None:
            self.text = 'text'
            self.text_mode = None
            self.selection = None
            self.selection_pos = None
            self.selection_move = False
            self.watermark_objects = self.watermark_objects[:-1]
            self.render_watermark()

    @staticmethod
    def relative_position(canvas, mouse_pos):
        base_x, base_y = canvas.geometry().getRect()[:2]
        return mouse_pos[0] - base_x, mouse_pos[1] - base_y

    @staticmethod
    def is_hover(mouse_pos, object_pos):
        # Check if mouse is hovering over object
        start_pos, end_pos = object_pos
        if start_pos[0] < mouse_pos[0] < end_pos[0] and start_pos[1] < mouse_pos[1] < end_pos[1]:
            return True
        return False


if __name__ == '__main__':
    app = QApplication([])
    core = Core(app, 1000, 700, 'PyMark')
    core.show()
    app.exec_()

# TODO
# 1.iter through all images in image list, add watermark to each and save them in new folder
# 2.preview-scale DONE
# 2c.check re use of button set text to TEXT Done
# 2b.set logo
# 3.orginize code
# 4.add comments
# 5.upload
