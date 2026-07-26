class ConversationDomainError(Exception):
    """대화 도메인에서 발생하는 모든 예외의 부모 클래스입니다."""


class ConversationNotFoundError(ConversationDomainError):
    """요청한 대화방을 찾을 수 없을 때 발생합니다."""


class ConversationAccessDeniedError(ConversationDomainError):
    """사용자에게 대화방 접근 권한이 없을 때 발생합니다."""


class MessageNotFoundError(ConversationDomainError):
    """요청한 메시지를 찾을 수 없을 때 발생합니다."""


class InvalidConversationStateError(ConversationDomainError):
    """현재 대화방 상태에서 요청을 처리할 수 없을 때 발생합니다."""
