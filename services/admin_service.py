"""Администратор: журнал всех действий и отмена операции (FR-15).

Сама отмена тоже пишется в журнал: история должна показывать и то, что отменили,
и то, кто отменил.
"""
from models import ACTION_UNDO, LOG_CANCELLED
from repositories.log_repository import LogRepository
from services.commands import COMMANDS, UndoError


class AdminService:
    @staticmethod
    def logs(limit: int | None = None) -> list:
        return LogRepository.get_all(limit)

    @staticmethod
    def undo(log_id: int, admin_id: int) -> tuple[bool, str]:
        log = LogRepository.get_by_id(log_id)
        if log is None:
            return False, "запись журнала не найдена"
        if log.status == LOG_CANCELLED:
            return False, "действие уже отменено"
        if log.action_type == ACTION_UNDO:
            return False, "отмену отменить нельзя"
        if not log.payload:
            return False, "запись создана старой версией системы — отмена недоступна"
        command_class = COMMANDS.get(log.action_type)
        if command_class is None:
            return False, "для этого действия отмена не поддерживается"

        try:
            command_class(log).undo()
            LogRepository.mark_cancelled(log)
            LogRepository.create(
                ACTION_UNDO,
                actor_id=admin_id,
                payload={"log_id": log.id, "action_type": log.action_type},
            )
        except UndoError as error:
            LogRepository.rollback()
            return False, str(error)
        except Exception:
            LogRepository.rollback()
            raise
        return True, f"действие «{log.action_title}» отменено"
