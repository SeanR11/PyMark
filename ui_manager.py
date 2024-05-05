import cv2
from cv_manager import CVManager
from PyQt5.QtCore import QSize,Qt
from PyQt5.QtGui import QIcon, QPixmap, QImage,QFont
from PyQt5.QtWidgets import QPushButton, QWidget, QLabel, QHBoxLayout, QVBoxLayout, QListWidget,QComboBox,QRadioButton,QGroupBox


class UIManager:
    # Create layout for placing widgets
    def create_layout(self, parent, type=None, alignment=None, bounds=None):
        # Determine layout type based on input argument
        layout = QVBoxLayout() if type == 'v' else QHBoxLayout()
        # Set alignment if provided
        if alignment:
            layout.setAlignment(alignment)
        # Set margins if provided
        if bounds:
            layout.setContentsMargins(*bounds)

        # Add the created layout to the parent layout
        parent.addLayout(layout)
        return layout

    # Create list widget for displaying lists
    def create_list_widget(self, layout, width, height, action):
        list_widget = QListWidget()
        list_widget.setFixedSize(width, height)
        list_widget.currentItemChanged.connect(lambda: action(list_widget.currentIndex().row()))

        # Add list widget to the layout
        layout.addWidget(list_widget)
        return list_widget

    # Create button widget
    def create_button(self, layout, action, text=None, icon=None):
        button = QPushButton(QIcon(icon), text) if icon else QPushButton(text)
        button.setFocusPolicy(Qt.NoFocus)
        button.clicked.connect(action)
        # If icon is provided, set fixed size
        if icon:
            icon_size = QIcon(icon).availableSizes()[0]
            button.setFixedSize(int(icon_size.width() // 1.5), int(icon_size.height() // 1.5))

        # Add button to the layout
        layout.addWidget(button)
        return button

    # Create canvas widget for displaying images
    def create_canvas(self, layout, width, height, image):
        canvas = QLabel()
        canvas.setFixedSize(width, height)
        canvas.setMouseTracking(True)
        canvas.setPixmap(self.to_pixmap(image))

        # Add canvas to the layout
        layout.addWidget(canvas)
        return canvas

    # Create text label widget
    def create_text(self,layout,text,size=12):
        text_label = QLabel(text)
        text_label.setFont(QFont('Arial',size))
        # Add text label to the layout
        layout.addWidget(text_label)
        return text_label

    # Create combo box widget
    def create_combo(self,layout,action,size,items):
        combo = QComboBox()
        combo.setFixedSize(*size)
        combo.currentIndexChanged.connect(lambda:action(combo.currentIndex()))
        # Add items to the combo box
        for item in items:
            combo.addItem(item)

        # Add combo box to the layout
        layout.addWidget(combo)
        return combo

    # Create radio button group widget
    def create_radio(self,layout,title,action,items):
        self.create_text(layout,title)
        buttons = []
        # Create radio buttons for each item
        for item in items:
            button = QRadioButton(item)
            button.setFont(QFont('Ariel',10))
            button.setStyleSheet("padding:10px;")
            button.clicked.connect(action)
            layout.addWidget(button)
            buttons.append(button)
        # Set the last button as checked by default
        buttons[-1].setChecked(True)
        return buttons

    # Convert OpenCV image to QPixmap
    def to_pixmap(self, image):
        height, width, channels = image.shape
        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return QPixmap(QImage(image.data, width, height, width * channels, QImage.Format_RGB888))
