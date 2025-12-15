"""Dialog for shifting subtitle timings."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QRadioButton, QButtonGroup, QGroupBox
)


class ShiftTimingsDialog(QDialog):
    """Dialog for shifting all subtitle timings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        self.setWindowTitle("Shift Timings")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        # Direction
        direction_group = QGroupBox("Direction")
        direction_layout = QVBoxLayout(direction_group)

        self.btn_group = QButtonGroup(self)

        self.radio_forward = QRadioButton("Shift forward (delay captions)")
        self.radio_forward.setChecked(True)
        self.btn_group.addButton(self.radio_forward)
        direction_layout.addWidget(self.radio_forward)

        self.radio_backward = QRadioButton("Shift backward (advance captions)")
        self.btn_group.addButton(self.radio_backward)
        direction_layout.addWidget(self.radio_backward)

        layout.addWidget(direction_group)

        # Amount
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel("Shift by:"))

        self.spin_ms = QSpinBox()
        self.spin_ms.setRange(0, 60000)
        self.spin_ms.setValue(500)
        self.spin_ms.setSuffix(" ms")
        self.spin_ms.setSingleStep(100)
        amount_layout.addWidget(self.spin_ms)

        layout.addLayout(amount_layout)

        # Quick presets
        presets_layout = QHBoxLayout()
        presets_layout.addWidget(QLabel("Quick:"))

        for ms in [100, 500, 1000, 2000]:
            btn = QPushButton(f"{ms}ms")
            btn.clicked.connect(lambda checked, v=ms: self.spin_ms.setValue(v))
            presets_layout.addWidget(btn)

        presets_layout.addStretch()
        layout.addLayout(presets_layout)

        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_cancel)

        btn_apply = QPushButton("Apply")
        btn_apply.setDefault(True)
        btn_apply.clicked.connect(self.accept)
        buttons.addWidget(btn_apply)

        layout.addLayout(buttons)

    def get_shift_ms(self) -> int:
        """Get the shift amount in milliseconds (negative for backward)."""
        ms = self.spin_ms.value()
        if self.radio_backward.isChecked():
            ms = -ms
        return ms
