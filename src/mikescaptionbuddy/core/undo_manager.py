"""Undo/Redo management system."""

from abc import ABC, abstractmethod
from typing import List, Optional, Any, Callable
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal


class Command(ABC):
    """Abstract base class for undoable commands."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the command."""
        pass

    @abstractmethod
    def execute(self) -> None:
        """Execute the command."""
        pass

    @abstractmethod
    def undo(self) -> None:
        """Undo the command."""
        pass


@dataclass
class SubtitleEditCommand(Command):
    """Command for editing subtitle text."""
    subtitle_id: int
    old_text: str
    new_text: str
    get_subtitle: Callable
    on_change: Callable

    @property
    def description(self) -> str:
        return f"Edit subtitle text"

    def execute(self) -> None:
        subtitle = self.get_subtitle(self.subtitle_id)
        if subtitle:
            subtitle.text = self.new_text
            self.on_change()

    def undo(self) -> None:
        subtitle = self.get_subtitle(self.subtitle_id)
        if subtitle:
            subtitle.text = self.old_text
            self.on_change()


@dataclass
class SubtitleTimingCommand(Command):
    """Command for changing subtitle timing."""
    subtitle_id: int
    old_start: int
    old_end: int
    new_start: int
    new_end: int
    get_subtitle: Callable
    on_change: Callable

    @property
    def description(self) -> str:
        return f"Change subtitle timing"

    def execute(self) -> None:
        subtitle = self.get_subtitle(self.subtitle_id)
        if subtitle:
            subtitle.start_ms = self.new_start
            subtitle.end_ms = self.new_end
            self.on_change()

    def undo(self) -> None:
        subtitle = self.get_subtitle(self.subtitle_id)
        if subtitle:
            subtitle.start_ms = self.old_start
            subtitle.end_ms = self.old_end
            self.on_change()


@dataclass
class WordStyleCommand(Command):
    """Command for styling a word."""
    subtitle_id: int
    word_index: int
    old_override: dict
    new_override: dict
    get_word: Callable
    on_change: Callable

    @property
    def description(self) -> str:
        return f"Style word"

    def execute(self) -> None:
        word = self.get_word(self.subtitle_id, self.word_index)
        if word:
            from .models import StyleOverride
            word.style_override = StyleOverride.from_dict(self.new_override)
            self.on_change()

    def undo(self) -> None:
        word = self.get_word(self.subtitle_id, self.word_index)
        if word:
            from .models import StyleOverride
            word.style_override = StyleOverride.from_dict(self.old_override)
            self.on_change()


@dataclass
class AddSubtitleCommand(Command):
    """Command for adding a subtitle."""
    subtitle_data: dict
    project: Any
    on_change: Callable
    _subtitle_id: Optional[int] = None

    @property
    def description(self) -> str:
        return "Add subtitle"

    def execute(self) -> None:
        from .models import Subtitle
        subtitle = Subtitle(**self.subtitle_data)
        self.project.add_subtitle(subtitle)
        self._subtitle_id = subtitle.id
        self.on_change()

    def undo(self) -> None:
        if self._subtitle_id:
            self.project.remove_subtitle(self._subtitle_id)
            self.on_change()


@dataclass
class DeleteSubtitleCommand(Command):
    """Command for deleting a subtitle."""
    subtitle_data: dict
    project: Any
    on_change: Callable

    @property
    def description(self) -> str:
        return "Delete subtitle"

    def execute(self) -> None:
        self.project.remove_subtitle(self.subtitle_data['id'])
        self.on_change()

    def undo(self) -> None:
        from .models import Subtitle, Word, StyleOverride
        # Reconstruct subtitle with words
        words_data = self.subtitle_data.pop('words', [])
        subtitle = Subtitle(**self.subtitle_data)
        for wd in words_data:
            override_data = wd.pop('style_override', {})
            word = Word(**wd)
            word.style_override = StyleOverride.from_dict(override_data)
            subtitle.words.append(word)
        self.subtitle_data['words'] = words_data  # Restore for future undos
        self.project.add_subtitle(subtitle)
        self.on_change()


class UndoManager(QObject):
    """Manages undo/redo operations with a fixed history size."""

    # Signals
    can_undo_changed = Signal(bool)
    can_redo_changed = Signal(bool)
    stack_changed = Signal()

    MAX_HISTORY = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []

    def execute(self, command: Command) -> None:
        """Execute a command and add it to the undo stack."""
        command.execute()
        self._undo_stack.append(command)

        # Clear redo stack when new command is executed
        self._redo_stack.clear()

        # Trim undo stack to max size
        while len(self._undo_stack) > self.MAX_HISTORY:
            self._undo_stack.pop(0)

        self._emit_changes()

    def undo(self) -> Optional[str]:
        """Undo the last command. Returns the command description."""
        if not self._undo_stack:
            return None

        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)

        self._emit_changes()
        return command.description

    def redo(self) -> Optional[str]:
        """Redo the last undone command. Returns the command description."""
        if not self._redo_stack:
            return None

        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)

        self._emit_changes()
        return command.description

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0

    def get_undo_description(self) -> Optional[str]:
        """Get description of the next undo command."""
        if self._undo_stack:
            return self._undo_stack[-1].description
        return None

    def get_redo_description(self) -> Optional[str]:
        """Get description of the next redo command."""
        if self._redo_stack:
            return self._redo_stack[-1].description
        return None

    def clear(self) -> None:
        """Clear all undo/redo history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._emit_changes()

    def _emit_changes(self) -> None:
        """Emit signals for state changes."""
        self.can_undo_changed.emit(self.can_undo())
        self.can_redo_changed.emit(self.can_redo())
        self.stack_changed.emit()
