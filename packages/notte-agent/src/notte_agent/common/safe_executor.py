from typing import final

from notte_browser.session import NotteSession
from notte_core.actions import BaseAction
from notte_core.browser.observation import Observation, StepResult
from notte_core.common.config import RaiseCondition, config
from notte_core.errors.base import NotteBaseError
from notte_core.errors.provider import RateLimitError
from pydantic import BaseModel
from pydantic.fields import computed_field
from pydantic_core import ValidationError


class ExecutionStatus(BaseModel):
    action: BaseAction
    obs: Observation
    result: StepResult

    @computed_field
    @property
    def success(self) -> bool:
        return self.result.success

    @computed_field
    @property
    def message(self) -> str:
        if self.result.message is None:
            raise ValueError("Execution failed with no message")
        return self.result.message

    def get(self) -> Observation:
        if not self.result.success:
            raise ValueError(f"Execution failed with message: {self.result.message}")
        return self.obs


class StepExecutionFailure(NotteBaseError):
    def __init__(self, message: str):
        super().__init__(
            user_message=message,
            agent_message=message,
            dev_message=message,
        )


class MaxConsecutiveFailuresError(NotteBaseError):
    def __init__(self, max_failures: int):
        self.max_failures: int = max_failures
        message = f"Max consecutive failures reached in a single step: {max_failures}."
        super().__init__(
            user_message=message,
            agent_message=message,
            dev_message=message,
        )


@final
class SafeActionExecutor:
    def __init__(
        self,
        session: NotteSession,
        max_consecutive_failures: int = config.max_consecutive_failures,
        raise_on_failure: bool = config.raise_condition is RaiseCondition.IMMEDIATELY,
    ) -> None:
        self.session = session
        self.max_consecutive_failures = max_consecutive_failures
        self.consecutive_failures = 0
        self.raise_on_failure = raise_on_failure

    def reset(self) -> None:
        self.consecutive_failures = 0

    async def on_failure(self, action: BaseAction, error_msg: str, e: Exception) -> ExecutionStatus:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.max_consecutive_failures:
            raise MaxConsecutiveFailuresError(self.max_consecutive_failures) from e
        if self.raise_on_failure:
            raise StepExecutionFailure(error_msg) from e

        obs = await self.session.aobserve()
        return ExecutionStatus(
            action=action,
            obs=obs,
            result=StepResult(success=False, message=error_msg),
        )

    async def execute(self, action: BaseAction) -> ExecutionStatus:
        try:
            result = await self.session.astep(action)
            obs = await self.session.aobserve()
            self.consecutive_failures = 0
            return ExecutionStatus(
                action=action,
                obs=obs,
                result=result,
            )
        except RateLimitError as e:
            return await self.on_failure(action, "Rate limit reached. Waiting before retry.", e)
        except NotteBaseError as e:
            # When raise_on_failure is True, we use the dev message to give more details to the user
            msg = e.dev_message if self.raise_on_failure else e.agent_message
            return await self.on_failure(action, msg, e)
        except ValidationError as e:
            return await self.on_failure(
                action,
                (
                    "JSON Schema Validation error: The output format is invalid. "
                    f"Please ensure your response follows the expected schema. Details: {str(e)}"
                ),
                e,
            )
        except Exception as e:
            return await self.on_failure(action, f"An unexpected error occurred: {e}", e)
